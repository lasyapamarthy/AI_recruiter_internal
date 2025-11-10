#!/usr/bin/env python3
import os
import csv
import shutil
from bs4 import BeautifulSoup
import re

# Directories
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/all_htmls"
REMOVED_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/auth_pages"
OUTPUT_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/uncollected_profiles.csv"

# File size threshold (100KB)
SIZE_THRESHOLD = 100 * 1024  # 100KB in bytes

def setup_directories():
    """Create necessary directories."""
    os.makedirs(REMOVED_DIR, exist_ok=True)

def extract_profile_url_and_name(file_path, filename):
    """Extract LinkedIn URL and profile name from HTML file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract profile name
        profile_name = "Unknown"
        
        # Try various methods to get the name
        name_selectors = [
            'h1.top-card-layout__title',
            'h1.text-heading-xlarge',
            'h1.inline',
            'h1'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                name = name_elem.get_text().strip()
                if name and len(name) > 2 and name != "LinkedIn Member":
                    profile_name = name
                    break
        
        # If still unknown, try title tag
        if profile_name == "Unknown":
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()
                if ' - ' in title_text and '| LinkedIn' in title_text:
                    name_part = title_text.split(' - ')[0].strip()
                    if name_part and name_part != 'LinkedIn' and len(name_part) > 2:
                        profile_name = name_part
                elif '| LinkedIn' in title_text:
                    name_part = title_text.split('|')[0].strip()
                    if name_part and name_part != 'LinkedIn' and len(name_part) > 2:
                        profile_name = name_part
        
        # Generate LinkedIn URL from filename
        linkedin_url = filename.replace('.html', '').replace('_', '/').replace('linkedin.com/', 'https://linkedin.com/')
        if not linkedin_url.startswith('http'):
            linkedin_url = 'https://' + linkedin_url
        
        # Clean up URL parameters
        if '?' in linkedin_url:
            linkedin_url = linkedin_url.split('?')[0]
        
        return linkedin_url, profile_name
        
    except Exception as e:
        print(f"Error extracting from {filename}: {str(e)}")
        return None, None

def main():
    """Main function to filter files and create CSV."""
    print("🚀 Starting profile filtering and extraction...")
    print(f"📏 File size threshold: {SIZE_THRESHOLD / 1024:.0f}KB")
    
    # Setup directories
    setup_directories()
    
    if not os.path.exists(HTML_DIR):
        print(f"❌ Directory {HTML_DIR} does not exist!")
        return
    
    # Get all HTML files
    html_files = [f for f in os.listdir(HTML_DIR) if f.endswith('.html')]
    total_count = len(html_files)
    print(f"📁 Found {total_count} HTML files to process")
    
    kept_profiles = []
    removed_count = 0
    kept_count = 0
    
    print("\n🔍 Processing files...")
    
    for i, filename in enumerate(html_files):
        file_path = os.path.join(HTML_DIR, filename)
        file_size = os.path.getsize(file_path)
        
        if file_size < SIZE_THRESHOLD:
            # Move small files (auth pages) to removed directory
            shutil.move(file_path, os.path.join(REMOVED_DIR, filename))
            removed_count += 1
            
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{total_count} files processed...")
        else:
            # Keep large files and extract profile info
            linkedin_url, profile_name = extract_profile_url_and_name(file_path, filename)
            
            if linkedin_url:
                kept_profiles.append({
                    'filename': filename,
                    'file_size_kb': f"{file_size / 1024:.1f}",
                    'linkedin_url': linkedin_url,
                    'profile_name': profile_name,
                    'status': 'uncollected'
                })
                kept_count += 1
            
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{total_count} files processed... ({kept_count} profiles kept)")
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Results:")
    print(f"   Total processed: {total_count}")
    print(f"   Auth pages removed: {removed_count} ({removed_count/total_count*100:.1f}%)")
    print(f"   Real profiles kept: {kept_count} ({kept_count/total_count*100:.1f}%)")
    
    # Save to CSV
    if kept_profiles:
        fieldnames = ['filename', 'file_size_kb', 'linkedin_url', 'profile_name', 'status']
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept_profiles)
        
        print(f"\n💾 Results saved to: {OUTPUT_CSV}")
        print(f"📁 Auth pages moved to: {REMOVED_DIR}")
        
        # Show sample results
        print(f"\n📋 Sample profiles found:")
        for i, profile in enumerate(kept_profiles[:10]):
            print(f"   {i+1}. {profile['profile_name']} - {profile['linkedin_url']}")
            print(f"      Size: {profile['file_size_kb']}KB")
    else:
        print("❌ No valid profiles found!")

if __name__ == "__main__":
    main() 