#!/usr/bin/env python3
"""
Script to append newly parsed profiles with experience data to the existing collected_files.csv
"""
import csv
import re
from pathlib import Path

def extract_handle_from_url(url):
    """Extract handle from LinkedIn URL."""
    if not url or url in ['/authwall', '/public-profile/in/', 'NA']:
        return None
    
    # Handle different URL patterns
    patterns = [
        r'linkedin\.com/in/([^/?]+)',
        r'linkedin\.com/in/([^/?]+)\?',
        r'linkedin\.com/in/([^/?]+)/',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            handle = match.group(1)
            # Clean up handle
            handle = handle.replace('%3A', ':').replace('%2F', '/')
            return handle
    
    return None

def main():
    # Read the newly parsed results
    new_profiles = []
    with open('collected_htmls_experiences_parsed.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only include profiles with experience data (not empty)
            if row['experience_empty'] == 'False':
                new_profiles.append(row)
    
    print(f"Found {len(new_profiles)} profiles with experience data from newly parsed results")
    
    # Read existing collected_files.csv to get existing URLs
    existing_urls = set()
    with open('data/linkedin/collected_files.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['V1'] and row['V1'] != 'NA':
                existing_urls.add(row['V1'])
    
    print(f"Found {len(existing_urls)} existing URLs in collected_files.csv")
    
    # Filter out profiles that already exist
    new_unique_profiles = []
    for profile in new_profiles:
        url = profile['linkedin_url']
        if url not in existing_urls and url not in ['/authwall', '/public-profile/in/', 'NA']:
            new_unique_profiles.append(profile)
    
    print(f"Found {len(new_unique_profiles)} new unique profiles to add")
    
    if not new_unique_profiles:
        print("No new profiles to add.")
        return
    
    # Append to collected_files.csv
    with open('data/linkedin/collected_files.csv', 'a', newline='', encoding='utf-8') as f:
        # The header format from existing file:
        # "V1","handle","linkedin_url","job_title","company","start_date","profile_empty","experience_empty","source_directory","file_path","error","data_collected"
        
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        
        for profile in new_unique_profiles:
            # Extract handle from URL
            handle = extract_handle_from_url(profile['linkedin_url'])
            
            # Create row in the format expected by collected_files.csv
            row = [
                profile['linkedin_url'],  # V1
                handle,  # handle
                profile['linkedin_url'],  # linkedin_url
                profile['job_title'],  # job_title
                profile['company'],  # company
                profile['start_date'],  # start_date
                profile['profile_empty'],  # profile_empty
                profile['experience_empty'],  # experience_empty
                profile['source_directory'],  # source_directory
                profile['file_path'],  # file_path
                'NA',  # error
                1  # data_collected
            ]
            
            writer.writerow(row)
    
    print(f"Successfully appended {len(new_unique_profiles)} new profiles to data/linkedin/collected_files.csv")
    
    # Show some examples
    if new_unique_profiles:
        print("\nFirst 5 new profiles added:")
        for i, profile in enumerate(new_unique_profiles[:5], 1):
            print(f"  {i}. {profile['job_title']} at {profile['company']} ({profile['start_date']})")

if __name__ == "__main__":
    main() 