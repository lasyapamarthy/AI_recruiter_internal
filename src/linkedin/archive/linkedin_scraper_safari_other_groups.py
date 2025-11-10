#!/usr/bin/env python3
"""
LinkedIn Safari Scraper for Other Groups Dataset
Uses Safari WebDriver for better anti-detection with separate output directories
"""
import os
import sys

# Import the base Safari scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from linkedin_scraper_safari import LinkedInSafariScraper

# Override configuration for this specific dataset
class OtherGroupsSafariScraper(LinkedInSafariScraper):
    def __init__(self):
        # First initialize parent class
        super().__init__()
        
        # Override paths for separate output
        self.HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/other_groups_htmls"
        self.FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/other_groups_failed_urls.txt"
        self.PROGRESS_LOG = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/other_groups_safari_scraper_log.csv"
        
        # Update processed and failed URLs based on new paths
        self.processed_urls = self.get_processed_urls_custom()
        self.failed_urls = self.get_failed_urls_custom()
    
    def check_safari_setup(self):
        """Skip automated checks since Safari has been manually configured."""
        print("✓ Safari has been manually configured for automation")
        return True
    
    def get_processed_urls_custom(self) -> set:
        """Get URLs that have been successfully processed from custom directory."""
        processed = set()
        if os.path.exists(self.HTML_DIR):
            for html_file in os.listdir(self.HTML_DIR):
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
    
    def get_failed_urls_custom(self) -> set:
        """Get URLs that have failed from custom file."""
        failed = set()
        if os.path.exists(self.FAILED_URLS_FILE):
            with open(self.FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                failed.update(url.strip() for url in f.readlines() if url.strip())
        return failed
    
    def scrape_batch(self, urls):
        """Override to use custom paths."""
        # Create custom output directory
        os.makedirs(self.HTML_DIR, exist_ok=True)
        
        # Use parent's scrape_batch but with our custom paths
        results = {}
        
        print(f"\n🔄 Processing batch of {len(urls)} profiles in Safari...")
        
        for i, url in enumerate(urls):
            print(f"\n[{i+1}/{len(urls)}] Loading: {url}")
            
            try:
                # Navigate to URL
                self.driver.get(url)
                
                # Wait for initial load
                import time
                import random
                time.sleep(random.uniform(3, 5))
                
                # Check for auth wall
                current_url = self.driver.current_url
                if 'authwall' in current_url or 'login' in current_url:
                    print(f"🔒 Auth wall detected")
                    # Try ESC key
                    from selenium.webdriver.common.keys import Keys
                    from selenium import webdriver
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
                    filepath = os.path.join(self.HTML_DIR, filename)
                    
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
                wait_time = random.uniform(3, 7)
                print(f"⏳ Waiting {wait_time:.1f}s before next profile...")
                time.sleep(wait_time)
        
        return results
    
    def run(self, input_file=None):
        """Run the scraper with the other_groups data file."""
        if input_file is None:
            input_file = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
        
        # Call parent run method
        super().run(input_file)
        
        # Print custom output locations
        print(f"\n📁 Output saved to:")
        print(f"  - HTML files: {self.HTML_DIR}")
        print(f"  - Progress log: {self.PROGRESS_LOG}")
        print(f"  - Failed URLs: {self.FAILED_URLS_FILE}")


def main():
    """Main entry point."""
    print("🚀 LinkedIn Safari Scraper for Other Groups Dataset")
    print("=" * 60)
    
    scraper = OtherGroupsSafariScraper()
    scraper.run()


if __name__ == "__main__":
    main() 