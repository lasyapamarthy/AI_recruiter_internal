#!/usr/bin/env python3
import os
import csv
import pandas as pd

# File paths
ROOT_DIR = "/Users/emilpalikot/Research/AI-Recruiter"
URLS_FILE = os.path.join(ROOT_DIR, "data/linkedin_urls.txt")
FAILED_URLS_FILE = os.path.join(ROOT_DIR, "data/linkedin/profiles/failed_urls.txt")
HTML_DIR = os.path.join(ROOT_DIR, "data/linkedin/output/htmls")
OUTPUT_CSV = os.path.join(ROOT_DIR, "data/linkedin/remaining_urls_to_scrape.csv")

def clean_linkedin_url(url):
    """Clean and standardize LinkedIn URLs."""
    if not url or url.lower() == 'na':
        return None
    
    # Remove any leading @ symbol
    url = url.lstrip('@')
    
    # Ensure URL starts with https://
    if not url.startswith('https://'):
        url = 'https://' + url.replace('http://', '')
    
    # Remove regional prefixes (al., fr., de., etc.) from LinkedIn URLs
    import re
    url = re.sub(r'https://([a-z]{2}\.)(www\.)?linkedin\.com', r'https://www.linkedin.com', url)
    
    # Ensure www. is present
    if 'www.' not in url:
        url = url.replace('linkedin.com', 'www.linkedin.com')
    
    # Remove trailing slashes and clean up
    url = url.rstrip('/')
    
    # Remove any query parameters
    url = url.split('?')[0]
    
    return url

def get_html_filename(profile_url):
    """Create a valid filename from the URL."""
    clean_url = profile_url.split('?')[0]
    filename = clean_url.replace("https://", "").replace("www.", "").replace("/", "_")
    return f"{filename}.html"

def get_processed_urls():
    """Get URLs that have been successfully processed (have HTML files)."""
    processed_urls = set()
    
    try:
        if os.path.exists(HTML_DIR):
            for html_file in os.listdir(HTML_DIR):
                if html_file.endswith('.html'):
                    # Remove .html extension
                    url_part = html_file[:-5]
                    
                    # Extract the username from various filename formats
                    username = None
                    
                    # Handle different filename patterns
                    if '_in_' in url_part:
                        # Extract username after '_in_'
                        parts = url_part.split('_in_')
                        if len(parts) >= 2:
                            username = parts[-1]  # Take the last part after '_in_'
                            # Clean up the username - remove trailing underscores and other artifacts
                            username = username.rstrip('_')
                            username = username.strip()
                    
                    if username:
                        # Create standardized URL
                        standardized_url = f'https://www.linkedin.com/in/{username}'
                        processed_urls.add(standardized_url)
                        
                        # Also add the cleaned version to catch any variations
                        cleaned_url = clean_linkedin_url(standardized_url)
                        if cleaned_url:
                            processed_urls.add(cleaned_url)
        
        return processed_urls
    except Exception as e:
        print(f"Error getting processed URLs: {e}")
        return set()

def main():
    print("Creating CSV file with failed and untried LinkedIn URLs...")
    
    # Read all original URLs
    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        all_urls = [url.strip() for url in f.readlines()]
    
    # Clean and filter URLs
    valid_urls = []
    for url in all_urls:
        cleaned_url = clean_linkedin_url(url)
        if cleaned_url and 'linkedin.com' in cleaned_url:
            valid_urls.append(cleaned_url)
    
    # Read failed URLs
    failed_urls = set()
    if os.path.exists(FAILED_URLS_FILE):
        with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
            failed_urls = set(url.strip() for url in f.readlines() if url.strip())
    
    # Get processed URLs (successfully scraped)
    processed_urls = get_processed_urls()
    
    # Create list for CSV
    csv_data = []
    
    # Add failed URLs
    for url in failed_urls:
        csv_data.append({
            'url': url,
            'status': 'failed',
            'reason': 'Previously failed to scrape'
        })
    
    # Add untried URLs (not in processed or failed)
    untried_urls = [url for url in valid_urls if url not in processed_urls and url not in failed_urls]
    for url in untried_urls:
        csv_data.append({
            'url': url,
            'status': 'untried',
            'reason': 'Not yet attempted'
        })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(csv_data)
    df.to_csv(OUTPUT_CSV, index=False)
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"Total original URLs: {len(all_urls)}")
    print(f"Valid LinkedIn URLs: {len(valid_urls)}")
    print(f"Successfully processed: {len(processed_urls)}")
    print(f"Failed URLs: {len(failed_urls)}")
    print(f"Untried URLs: {len(untried_urls)}")
    print(f"Total remaining to scrape: {len(csv_data)}")
    print(f"\n📁 CSV file created: {OUTPUT_CSV}")
    print(f"   - Failed URLs: {len([d for d in csv_data if d['status'] == 'failed'])}")
    print(f"   - Untried URLs: {len([d for d in csv_data if d['status'] == 'untried'])}")

if __name__ == "__main__":
    main() 