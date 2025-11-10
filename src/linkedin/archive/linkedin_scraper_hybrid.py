#!/usr/bin/env python3
"""
LinkedIn Hybrid Scraper - Combines batch processing with Chrome automation
Inspired by the Safari batch scraper but using Chrome for cross-platform compatibility
"""
import os
import time
import random
import json
import csv
import re
import concurrent.futures
from typing import List, Tuple, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.keys import Keys
import pandas as pd
from tqdm import tqdm

# Configuration - Inspired by Safari batch approach
BATCH_SIZE = 10  # Number of profiles to open simultaneously (like Safari scraper)
WAIT_BETWEEN_BATCHES = (30, 60)  # Wait between batches
WAIT_AFTER_TAB_OPEN = (2, 5)  # Wait after opening each tab
MAX_RETRIES_PER_URL = 3  # Reduced retries since we process in batches
PAGE_LOAD_TIMEOUT = 30
HTML_MIN_LENGTH_THRESHOLD = 2500

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/"
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
FAILED_URLS_FILE = os.path.join(OUTPUT_DIR, "failed_urls.txt")
PROGRESS_LOG = os.path.join(OUTPUT_DIR, "hybrid_scraper_log.csv")

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

class LinkedInBatchScraper:
    def __init__(self):
        self.driver = None
        self.result_log = pd.DataFrame(columns=['url', 'status', 'filename', 'timestamp'])
        self.processed_urls = self.get_processed_urls()
        self.failed_urls = self.get_failed_urls()
        
    def setup_driver(self) -> webdriver.Chrome:
        """Configure Chrome with anti-detection measures."""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Randomize window size slightly
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # Random user agent
        user_agent = random.choice(USER_AGENTS)
        chrome_options.add_argument(f"--user-agent={user_agent}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Anti-detection JavaScript
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def clean_linkedin_url(self, url: str) -> str:
        """Clean and standardize LinkedIn URLs (from Safari scraper logic)."""
        if not url or url.lower() == 'na' or pd.isna(url):
            return None
        
        # Remove spaces and @ symbol
        url = url.replace(' ', '').lstrip('@')
        
        # Ensure https://
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Handle regional domains (pl.linkedin.com -> linkedin.com)
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
                    # Extract URL from filename
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
            # But also check for profile content
            profile_indicators = ['experience', 'education', 'skills', 'about']
            profile_count = sum(1 for indicator in profile_indicators if indicator in page_text)
            
            # If we have multiple profile indicators, it might still be valid
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
    
    def scrape_batch(self, urls: List[str]) -> Dict[str, bool]:
        """Scrape a batch of URLs by opening them in multiple tabs."""
        results = {}
        tab_handles = {}
        
        print(f"\n🔄 Opening batch of {len(urls)} profiles...")
        
        # Open all URLs in separate tabs
        for i, url in enumerate(urls):
            try:
                if i == 0:
                    # Use first tab
                    self.driver.get(url)
                    tab_handles[url] = self.driver.current_window_handle
                else:
                    # Open new tab
                    self.driver.execute_script("window.open('');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.driver.get(url)
                    tab_handles[url] = self.driver.current_window_handle
                
                # Random wait after opening each tab
                time.sleep(random.uniform(*WAIT_AFTER_TAB_OPEN))
                
            except Exception as e:
                print(f"❌ Error opening {url}: {str(e)[:50]}")
                results[url] = False
        
        # Wait for all pages to load
        print("⏳ Waiting for pages to load...")
        time.sleep(random.uniform(10, 15))
        
        # Now go through each tab and save the content
        for url, handle in tab_handles.items():
            if url in results:  # Skip if already failed
                continue
                
            try:
                self.driver.switch_to.window(handle)
                
                # Check if we need to handle auth wall
                current_url = self.driver.current_url
                if 'authwall' in current_url or 'login' in current_url:
                    print(f"🔒 Auth wall detected for {url}")
                    # Try to bypass
                    self.try_bypass_authwall()
                    time.sleep(2)
                
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
                    
                    # Log success
                    self.log_result(url, 'success', filename)
                else:
                    print(f"❌ Invalid content for {url}")
                    results[url] = False
                    self.log_result(url, 'invalid_content', '')
                    
            except Exception as e:
                print(f"❌ Error processing {url}: {str(e)[:50]}")
                results[url] = False
                self.log_result(url, 'error', '')
        
        # Close all tabs except the first one
        all_handles = self.driver.window_handles
        for handle in all_handles[1:]:
            self.driver.switch_to.window(handle)
            self.driver.close()
        
        # Switch back to first tab
        self.driver.switch_to.window(all_handles[0])
        
        return results
    
    def try_bypass_authwall(self):
        """Attempt to bypass LinkedIn auth wall."""
        try:
            # Press ESC
            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
            
            # Try to remove overlay with JavaScript
            self.driver.execute_script("""
                var elements = document.querySelectorAll('.authentication-outlet, .modal-wormhole');
                elements.forEach(e => e.remove());
                document.body.style.overflow = 'auto';
            """)
        except:
            pass
    
    def log_result(self, url: str, status: str, filename: str):
        """Log scraping result."""
        new_row = pd.DataFrame({
            'url': [url],
            'status': [status],
            'filename': [filename],
            'timestamp': [time.strftime('%Y-%m-%d %H:%M:%S')]
        })
        self.result_log = pd.concat([self.result_log, new_row], ignore_index=True)
        
        # Save log every 10 entries
        if len(self.result_log) % 10 == 0:
            self.result_log.to_csv(PROGRESS_LOG, index=False)
    
    def run(self, input_file: str):
        """Main execution function."""
        # Read URLs
        if input_file.endswith('.csv'):
            df = pd.read_csv(input_file)
            # Assume URL column is named 'links' or 'url'
            url_column = 'links' if 'links' in df.columns else 'url'
            all_urls = df[url_column].tolist()
        else:
            # Text file with one URL per line
            with open(input_file, 'r') as f:
                all_urls = [line.strip() for line in f.readlines()]
        
        # Clean URLs
        cleaned_urls = []
        for url in all_urls:
            cleaned = self.clean_linkedin_url(url)
            if cleaned and cleaned not in self.processed_urls and cleaned not in self.failed_urls:
                cleaned_urls.append(cleaned)
        
        print(f"📊 Total URLs: {len(all_urls)}")
        print(f"📊 Already processed: {len(self.processed_urls)}")
        print(f"📊 Previously failed: {len(self.failed_urls)}")
        print(f"📊 To process: {len(cleaned_urls)}")
        
        if not cleaned_urls:
            print("✅ No URLs to process!")
            return
        
        # Create output directory
        os.makedirs(HTML_DIR, exist_ok=True)
        
        # Process in batches
        for i in tqdm(range(0, len(cleaned_urls), BATCH_SIZE), desc="Processing batches"):
            batch = cleaned_urls[i:i + BATCH_SIZE]
            
            print(f"\n{'='*50}")
            print(f"Processing batch {i//BATCH_SIZE + 1} ({len(batch)} URLs)")
            print(f"{'='*50}")
            
            # Setup fresh driver for each batch
            if self.driver:
                self.driver.quit()
            
            self.driver = self.setup_driver()
            
            # Process batch
            results = self.scrape_batch(batch)
            
            # Update failed URLs
            for url, success in results.items():
                if not success:
                    with open(FAILED_URLS_FILE, 'a') as f:
                        f.write(url + '\n')
            
            # Save final log
            self.result_log.to_csv(PROGRESS_LOG, index=False)
            
            # Close driver
            self.driver.quit()
            self.driver = None
            
            # Wait between batches (except for last batch)
            if i + BATCH_SIZE < len(cleaned_urls):
                wait_time = random.uniform(*WAIT_BETWEEN_BATCHES)
                print(f"\n💤 Waiting {wait_time:.0f} seconds before next batch...")
                time.sleep(wait_time)
        
        print("\n✅ Scraping completed!")
        print(f"📊 Check {PROGRESS_LOG} for detailed results")


def main():
    """Main entry point."""
    import sys
    
    # Default to the standard URLs file if no argument provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = URLS_FILE_PATH
    
    scraper = LinkedInBatchScraper()
    scraper.run(input_file)


if __name__ == "__main__":
    main() 