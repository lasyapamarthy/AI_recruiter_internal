#!/usr/bin/env python3
"""
LinkedIn Stealth Chrome Scraper for Other Groups Dataset
Optimized for anti-detection with conservative settings
"""
import os
import sys
import time
import random
from typing import List, Dict

# Import base scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from linkedin_scraper_hybrid import LinkedInBatchScraper

class StealthChromeScraper(LinkedInBatchScraper):
    def __init__(self):
        super().__init__()
        
        # Override with more conservative settings
        self.BATCH_SIZE = 5  # Smaller batches
        self.WAIT_BETWEEN_BATCHES = (60, 120)  # 1-2 minutes between batches
        self.WAIT_AFTER_TAB_OPEN = (5, 10)  # Longer waits between tabs
        
        # Custom output paths
        self.HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/other_groups_htmls"
        self.FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/other_groups_failed_urls.txt"
        self.PROGRESS_LOG = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/other_groups_stealth_log.csv"
        
        # Update processed and failed URLs
        self.processed_urls = self.get_processed_urls()
        self.failed_urls = self.get_failed_urls()
    
    def setup_driver(self):
        """Enhanced anti-detection Chrome setup."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        
        # Stealth mode settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Additional stealth arguments
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        
        # Random window size
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # Random user agent
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # Execute stealth JavaScript
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({state: 'granted'})
                })
            });
        """)
        
        return driver
    
    def scrape_batch(self, urls: List[str]) -> Dict[str, bool]:
        """Scrape with enhanced stealth behavior."""
        results = {}
        
        print(f"\n🥷 Stealth mode: Processing {len(urls)} profiles...")
        
        for i, url in enumerate(urls):
            print(f"\n[{i+1}/{len(urls)}] Loading: {url}")
            
            try:
                # Random pre-navigation delay
                time.sleep(random.uniform(2, 4))
                
                # Navigate
                self.driver.get(url)
                
                # Human-like wait
                time.sleep(random.uniform(5, 8))
                
                # Random scrolling
                self.human_like_behavior()
                
                # Check current URL
                current_url = self.driver.current_url
                if 'authwall' in current_url or 'login' in current_url:
                    print(f"🔒 Auth wall detected")
                    self.try_bypass_authwall()
                    time.sleep(random.uniform(3, 5))
                
                # Get content
                html_content = self.driver.page_source
                
                if self.is_valid_profile_html(html_content):
                    filename = self.get_html_filename(url)
                    filepath = os.path.join(self.HTML_DIR, filename)
                    
                    os.makedirs(self.HTML_DIR, exist_ok=True)
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
            
            # Random wait between profiles
            if i < len(urls) - 1:
                wait_time = random.uniform(10, 20)
                print(f"⏳ Waiting {wait_time:.0f}s before next profile...")
                time.sleep(wait_time)
        
        return results
    
    def human_like_behavior(self):
        """Simulate human-like browsing behavior."""
        try:
            # Random scrolls
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(300, 700)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Sometimes scroll back up
            if random.random() < 0.3:
                self.driver.execute_script("window.scrollBy(0, -300);")
                time.sleep(random.uniform(0.5, 1))
            
            # Random mouse movements would go here if needed
        except:
            pass
    
    def run(self, input_file=None):
        """Run the stealth scraper."""
        if input_file is None:
            input_file = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
        
        print("🥷 Stealth Chrome Scraper")
        print("Conservative settings: smaller batches, longer waits")
        print("=" * 60)
        
        # Process with parent's run method
        super().run(input_file)


def main():
    """Main entry point."""
    scraper = StealthChromeScraper()
    scraper.run()


if __name__ == "__main__":
    main() 