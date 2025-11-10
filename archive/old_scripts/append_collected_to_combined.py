#!/usr/bin/env python3
"""
Append Collected Profiles to Combined CSV
Parses new collected_htmls files and adds them to the existing combined_safari_htmls_experiences.csv
"""
import os
import csv
import pathlib
import pandas as pd
from linkedin_safari_parser import parse_safari_profile

# Configuration
COLLECTED_HTMLS_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
COMBINED_CSV_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/combined_safari_htmls_experiences.csv"

def get_existing_urls():
    """Get set of URLs already in the combined CSV."""
    existing_urls = set()
    try:
        if os.path.exists(COMBINED_CSV_PATH):
            df = pd.read_csv(COMBINED_CSV_PATH)
            existing_urls = set(df['linkedin_url'].tolist())
            print(f"Found {len(existing_urls)} existing URLs in combined file")
        return existing_urls
    except Exception as e:
        print(f"Error reading existing CSV: {e}")
        return set()

def parse_collected_files():
    """Parse all files in collected_htmls directory."""
    html_files = list(pathlib.Path(COLLECTED_HTMLS_DIR).glob("*.html"))
    print(f"Found {len(html_files)} HTML files in collected_htmls directory")
    
    results = []
    
    for i, html_file in enumerate(html_files, 1):
        if i % 20 == 0:  # Progress indicator
            print(f"Processing {i}/{len(html_files)}: {html_file.name}")
        
        try:
            result = parse_safari_profile(html_file)
            result['source_directory'] = 'collected_htmls'
            result['file_path'] = str(html_file)
            result['error'] = ''  # Add error column to match existing format
            
            results.append(result)
        except Exception as e:
            print(f"Error parsing {html_file.name}: {e}")
            continue
    
    return results

def append_to_combined_csv(new_results, existing_urls):
    """Append new results to the combined CSV file - only profiles with experience data."""
    # Filter for profiles with experience data first
    profiles_with_experience = [result for result in new_results if not result['experience_empty']]
    print(f"Found {len(profiles_with_experience)} profiles with experience data out of {len(new_results)} total")
    
    # Filter out duplicates
    new_unique_results = []
    duplicates_count = 0
    
    for result in profiles_with_experience:
        if result['linkedin_url'] not in existing_urls:
            new_unique_results.append(result)
        else:
            duplicates_count += 1
    
    print(f"Found {duplicates_count} duplicates (skipped)")
    print(f"Adding {len(new_unique_results)} new unique profiles with experience data")
    
    if not new_unique_results:
        print("No new profiles with experience data to add!")
        return
    
    # Append to existing CSV
    fieldnames = ['linkedin_url', 'job_title', 'company', 'start_date', 
                 'profile_empty', 'experience_empty', 'source_directory', 'file_path', 'error']
    
    with open(COMBINED_CSV_PATH, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        for result in new_unique_results:
            writer.writerow(result)
    
    print(f"Successfully appended {len(new_unique_results)} new profiles with experience data to {COMBINED_CSV_PATH}")

def main():
    """Main function."""
    print("🔄 Parsing collected_htmls and appending to combined CSV...")
    print("=" * 60)
    
    # Get existing URLs to avoid duplicates
    existing_urls = get_existing_urls()
    
    # Parse collected files
    print("\n📋 Parsing collected HTML files...")
    new_results = parse_collected_files()
    
    if not new_results:
        print("❌ No results from parsing!")
        return
    
    # Append to combined CSV
    print(f"\n📊 Processing {len(new_results)} parsed results...")
    append_to_combined_csv(new_results, existing_urls)
    
    # Final statistics
    try:
        final_df = pd.read_csv(COMBINED_CSV_PATH)
        total_profiles = len(final_df)
        profiles_with_experience = len(final_df[final_df['experience_empty'] == False])
        
        print(f"\n📈 FINAL STATISTICS:")
        print(f"   📁 Total profiles in combined file: {total_profiles}")
        print(f"   🎯 Profiles with experience: {profiles_with_experience}")
        print(f"   📈 Experience rate: {profiles_with_experience/total_profiles*100:.1f}%")
        
        # Show breakdown by source directory
        source_counts = final_df['source_directory'].value_counts()
        print(f"\n📊 BREAKDOWN BY SOURCE:")
        for source, count in source_counts.items():
            print(f"   {source}: {count} profiles")
            
    except Exception as e:
        print(f"Error calculating final statistics: {e}")

if __name__ == "__main__":
    main() 