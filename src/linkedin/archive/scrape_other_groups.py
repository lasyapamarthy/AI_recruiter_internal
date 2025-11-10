#!/usr/bin/env python3
"""
Script to scrape LinkedIn profiles from other_groups_linkedin_urls.txt
Uses the hybrid scraper for efficient batch processing
"""
import os
import sys

# Add the src/linkedin directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the hybrid scraper
from linkedin_scraper_hybrid import LinkedInBatchScraper

def main():
    # Path to the new data file
    input_file = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: File not found: {input_file}")
        return
    
    print(f"🚀 Starting LinkedIn scraping for: {input_file}")
    print("=" * 60)
    
    # Create and run the scraper
    scraper = LinkedInBatchScraper()
    scraper.run(input_file)
    
    print("\n✅ Scraping completed!")
    print("Check the output directory for results:")
    print("  - HTML files: data/linkedin/output/htmls/")
    print("  - Progress log: data/linkedin/profiles/hybrid_scraper_log.csv")
    print("  - Failed URLs: data/linkedin/profiles/failed_urls.txt")

if __name__ == "__main__":
    main() 