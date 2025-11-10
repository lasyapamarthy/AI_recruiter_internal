#!/usr/bin/env python3
"""
LinkedIn Safari Scraper - Uses Safari WebDriver for better anti-detection
Safari is less commonly automated and harder to detect as a bot
"""
import os
import time
import random
import json
import re
import subprocess
from typing import List, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.keys import Keys
import pandas as pd
from tqdm import tqdm

# Configuration
BATCH_SIZE = 5  # Smaller batches for Safari to be more careful
WAIT_BETWEEN_BATCHES = (45, 90)  # Longer waits
WAIT_AFTER_TAB_OPEN = (3, 7)  # More natural timing
PAGE_LOAD_TIMEOUT = 30
HTML_MIN_LENGTH_THRESHOLD = 2500

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/"
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
FAILED_URLS_FILE = os.path.join(OUTPUT_DIR, "failed_urls.txt")
PROGRESS_LOG = os.path.join(OUTPUT_DIR, "safari_scraper_log.csv")

class LinkedInSafariScraper:
    def __init__(self):
        self.driver = None
        self.result_log = pd.DataFrame(columns=['url', 'status', 'filename', 'timestamp'])
        self.processed_urls = self.get_processed_urls()
        self.failed_urls = self.get_failed_urls()
        
    def check_safari_setup(self):
        """Check if Safari is properly configured for automation."""
        try:
            # Check if Safari's Develop menu is enabled
            result = subprocess.run(
                ["defaults", "read", "com.apple.Safari", "IncludeDevelopMenu"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0 or result.stdout.strip() != "1":
                print("⚠️  Safari's Develop menu is not enabled.")
                print("   To enable: Safari > Preferences > Advanced > Show Develop menu")
                return False
                
            # Check if remote automation is allowed
            result = subprocess.run(
                ["defaults", "read", "com.apple.Safari", "AllowRemoteAutomation"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0 or result.stdout.strip() != "1":
                print("⚠️  Safari's Allow Remote Automation is not enabled.")
                print("   To enable: Safari > Develop > Allow Remote Automation")
                print("   Or run: defaults write com.apple.Safari AllowRemoteAutomation -bool true")
                return False
                
            return True
        except Exception as e:
            print(f"Error checking Safari setup: {e}")
            return False
    
    def setup_driver(self) -> webdriver.Safari:
        """Configure Safari WebDriver."""
        # Safari doesn't support as many options as Chrome, which actually helps with detection
        driver = webdriver.Safari()
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Maximize window
        driver.maximize_window()
        
        return driver
    
    def clean_linkedin_url(self, url: str) -> str:
        """Clean and standardize LinkedIn URLs."""
        if not url or url.lower() == 'na' or pd.isna(url):
            return None
        
        # Remove spaces and @ symbol
        url = url.replace(' ', '').lstrip('@')
        
        # Ensure https://
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Handle regional domains
        url = re.sub(r'https://([a-z]{2}\.)(www\.)?linkedin\.com', r'https://www.linkedin.com', url)
        
        # Remove /mwlite/ if present
        url = url.replace('/mwlite/', '/')
        
        # Ensure www.
        if 'www.' not in url:
            url = url.replace('linkedin.com', 'www.linkedin.com')
        
        # Clean up
        url = url.rstrip('/').split('?')[0]
        
        return url
    
    def get_processed_urls(self) -> set:
        """Get URLs that have been successfully processed."""
        processed = set()
        if os.path.exists(HTML_DIR):
            for html_file in os.listdir(HTML_DIR):
                if html_file.endswith('.html'):
                    url_part = html_file[:-5]
                    if '_in_' in url_part:
                        parts = url_part.split('_in_')
                        if len(parts) >= 2:
                            username = parts[-1].rstrip('_').strip()
                            if username:
                                url = f'https://www.linkedin.com/in/{username}'
                                processed.add(url)
        return processed
    
    def get_failed_urls(self) -> set:
        """Get URLs that have failed."""
        failed = set()
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                failed.update(url.strip() for url in f.readlines() if url.strip())
        return failed
    
    def get_html_filename(self, url: str) -> str:
        """Generate filename from URL."""
        clean_url = url.split('?')[0]
        filename = clean_url.replace("https://", "").replace("www.", "").replace("/", "_")
        return f"{filename}.html"
    
    def is_valid_profile_html(self, html_content: str) -> bool:
        """Check if HTML contains valid profile data."""
        if len(html_content) < HTML_MIN_LENGTH_THRESHOLD:
            return False
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for auth/login indicators
        auth_indicators = ['authwall', 'sign in', 'login', 'join linkedin']
        page_text = soup.get_text().lower()
        
        if any(indicator in page_text for indicator in auth_indicators):
            profile_indicators = ['experience', 'education', 'skills', 'about']
            profile_count = sum(1 for indicator in profile_indicators if indicator in page_text)
            
            if profile_count < 2:
                return False
        
        # Check for profile structure
        profile_selectors = [
            'div[class*="pv-top-card"]',
            'section[class*="artdeco-card"]',
            'main[class*="scaffold-layout__main"]',
            'div#experience',
            'div#education'
        ]
        
        return any(soup.select_one(sel) for sel in profile_selectors)
    
    def human_like_scroll(self):
        """Perform human-like scrolling on the page."""
        try:
            # Get page height
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll in chunks with random pauses
            current_position = 0
            while current_position < page_height:
                # Random scroll distance
                scroll_distance = random.randint(300, 700)
                current_position += scroll_distance
                
                # Smooth scroll
                self.driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
                
                # Random pause
                time.sleep(random.uniform(0.5, 1.5))
                
                # Sometimes scroll back up a bit
                if random.random() < 0.2:
                    back_distance = random.randint(100, 200)
                    current_position -= back_distance
                    self.driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
                    time.sleep(random.uniform(0.3, 0.7))
        except:
            pass
    
    def scrape_batch(self, urls: List[str]) -> Dict[str, bool]:
        """Scrape a batch of URLs using Safari."""
        results = {}
        
        print(f"\n🔄 Processing batch of {len(urls)} profiles in Safari...")
        
        for i, url in enumerate(urls):
            print(f"\n[{i+1}/{len(urls)}] Loading: {url}")
            
            try:
                # Navigate to URL
                self.driver.get(url)
                
                # Wait for initial load
                time.sleep(random.uniform(3, 5))
                
                # Check for auth wall
                current_url = self.driver.current_url
                if 'authwall' in current_url or 'login' in current_url:
                    print(f"🔒 Auth wall detected")
                    # Try ESC key
                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(2)
                
                # Perform human-like scrolling
                self.human_like_scroll()
                
                # Wait a bit more
                time.sleep(random.uniform(2, 4))
                
                # Get page source
                html_content = self.driver.page_source
                
                # Validate content
                if self.is_valid_profile_html(html_content):
                    # Save HTML
                    filename = self.get_html_filename(url)
                    filepath = os.path.join(HTML_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    print(f"✅ Saved: {filename}")
                    results[url] = True
                    self.log_result(url, 'success', filename)
                else:
                    print(f"❌ Invalid content")
                    results[url] = False
                    self.log_result(url, 'invalid_content', '')
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                results[url] = False
                self.log_result(url, 'error', '')
            
            # Wait between profiles
            if i < len(urls) - 1:
                wait_time = random.uniform(*WAIT_AFTER_TAB_OPEN)
                print(f"⏳ Waiting {wait_time:.1f}s before next profile...")
                time.sleep(wait_time)
        
        return results
    
    def log_result(self, url: str, status: str, filename: str):
        """Log scraping result."""
        new_row = pd.DataFrame({
            'url': [url],
            'status': [status],
            'filename': [filename],
            'timestamp': [time.strftime('%Y-%m-%d %H:%M:%S')]
        })
        self.result_log = pd.concat([self.result_log, new_row], ignore_index=True)
        
        # Save log periodically
        if len(self.result_log) % 5 == 0:
            self.result_log.to_csv(PROGRESS_LOG, index=False)
    
    def run(self, input_file: str):
        """Main execution function."""
        # Check Safari setup
        if not self.check_safari_setup():
            print("\n❌ Safari is not properly configured for automation.")
            print("Please follow the instructions above and try again.")
            return
        
        # Read URLs
        if input_file.endswith('.csv'):
            df = pd.read_csv(input_file)
            url_column = 'links' if 'links' in df.columns else 'url'
            all_urls = df[url_column].tolist()
        else:
            with open(input_file, 'r') as f:
                all_urls = [line.strip() for line in f.readlines()]
        
        # Clean URLs
        cleaned_urls = []
        for url in all_urls:
            cleaned = self.clean_linkedin_url(url)
            if cleaned and cleaned not in self.processed_urls and cleaned not in self.failed_urls:
                cleaned_urls.append(cleaned)
        
        print(f"\n📊 LinkedIn Safari Scraper")
        print(f"📊 Total URLs: {len(all_urls)}")
        print(f"📊 Already processed: {len(self.processed_urls)}")
        print(f"📊 Previously failed: {len(self.failed_urls)}")
        print(f"📊 To process: {len(cleaned_urls)}")
        
        if not cleaned_urls:
            print("✅ No URLs to process!")
            return
        
        # Create output directory
        os.makedirs(HTML_DIR, exist_ok=True)
        
        # Setup Safari driver
        print("\n🌐 Starting Safari WebDriver...")
        self.driver = self.setup_driver()
        
        try:
            # Process in batches
            for i in tqdm(range(0, len(cleaned_urls), BATCH_SIZE), desc="Processing batches"):
                batch = cleaned_urls[i:i + BATCH_SIZE]
                
                print(f"\n{'='*50}")
                print(f"Batch {i//BATCH_SIZE + 1} ({len(batch)} URLs)")
                print(f"{'='*50}")
                
                # Process batch
                results = self.scrape_batch(batch)
                
                # Update failed URLs
                for url, success in results.items():
                    if not success:
                        with open(FAILED_URLS_FILE, 'a') as f:
                            f.write(url + '\n')
                
                # Save log
                self.result_log.to_csv(PROGRESS_LOG, index=False)
                
                # Wait between batches
                if i + BATCH_SIZE < len(cleaned_urls):
                    wait_time = random.uniform(*WAIT_BETWEEN_BATCHES)
                    print(f"\n💤 Waiting {wait_time:.0f} seconds before next batch...")
                    time.sleep(wait_time)
            
        finally:
            # Clean up
            if self.driver:
                self.driver.quit()
            
        print("\n✅ Scraping completed!")
        print(f"📊 Check {PROGRESS_LOG} for detailed results")


def main():
    """Main entry point."""
    import sys
    
    # Check if running on macOS
    if os.uname().sysname != 'Darwin':
        print("❌ This scraper requires macOS with Safari.")
        print("   For other platforms, use linkedin_scraper_hybrid.py")
        return
    
    # Default to the standard URLs file if no argument provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = URLS_FILE_PATH
    
    scraper = LinkedInSafariScraper()
    scraper.run(input_file)


if __name__ == "__main__":
    main() 