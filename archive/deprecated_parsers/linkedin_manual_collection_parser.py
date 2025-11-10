#!/usr/bin/env python3
"""
Specialized parser for LinkedIn manual collection HTML files.
These files contain embedded JSON data with profile information.

The CSV columns are:
  linkedin_url, job_title, company, start_date, profile_empty, experience_empty, source_directory, file_path
"""
import glob
import json
import re
import csv
import sys
import pathlib
from datetime import datetime
from bs4 import BeautifulSoup
import os

def extract_url_from_filename(filename):
    """Extract LinkedIn URL from filename patterns."""
    # Handle different filename patterns
    if 'linkedin.com' in filename:
        # Extract from patterns like "linkedin.com_in_username.html"
        match = re.search(r'linkedin\.com[_/]in[_/]([^.]+)', filename)
        if match:
            username = match.group(1).replace('_', '-')
            return f"https://www.linkedin.com/in/{username}/"
    
    # For manual collection files, extract from title
    name_part = filename.replace(' _ LinkedIn.html', '').replace('%20', ' ')
    # Convert to a reasonable URL format
    username = name_part.lower().replace(' ', '-').replace('.', '')
    return f"https://www.linkedin.com/in/{username}/"

def parse_manual_collection_profile(path: pathlib.Path) -> dict:
    """Parse manual collection LinkedIn profile HTML files."""
    try:
        html = path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract URL from filename
        url = extract_url_from_filename(path.name)
        
        # Look for JSON data in script tags
        latest_experience = None
        
        # Search for position data in the HTML
        # The manual collection files contain JSON data with position information
        json_pattern = r'"positions":\s*\{[^}]*"elements":\s*\[([^\]]*)\]'
        json_matches = re.findall(json_pattern, html, re.DOTALL)
        
        if json_matches:
            try:
                # Try to parse the positions data
                positions_text = json_matches[0]
                # Look for individual position objects
                position_pattern = r'\{[^}]*"companyName":\s*"([^"]*)"[^}]*"title":\s*"([^"]*)"[^}]*"dateRange":\s*\{[^}]*"start":\s*\{[^}]*"year":\s*(\d+)[^}]*"month":\s*(\d+)[^}]*\}[^}]*\}'
                position_matches = re.findall(position_pattern, positions_text)
                
                if position_matches:
                    # Get the most recent position (first one)
                    company, title, year, month = position_matches[0]
                    start_date = f"{year}-{month:02d}"
                    latest_experience = {
                        'company': company,
                        'title': title,
                        'startDate': start_date
                    }
            except Exception as e:
                print(f"Error parsing positions for {path.name}: {e}")
        
        # Alternative approach: look for companyName and title patterns
        if not latest_experience:
            # Search for company and title information in the JSON data
            company_pattern = r'"companyName":\s*"([^"]+)"'
            title_pattern = r'"title":\s*"([^"]+)"'
            
            companies = re.findall(company_pattern, html)
            titles = re.findall(title_pattern, html)
            
            if companies and titles:
                # Take the first meaningful company and title
                for company, title in zip(companies, titles):
                    if company and title and len(company) > 2 and len(title) > 2:
                        latest_experience = {
                            'company': company,
                            'title': title,
                            'startDate': ''
                        }
                        break
        
        # Alternative approach: look for headline information
        if not latest_experience:
            headline_pattern = r'"headline":\s*"([^"]+)"'
            headline_matches = re.findall(headline_pattern, html)
            
            if headline_matches:
                headline = headline_matches[0]
                # Try to extract company from headline
                if ' at ' in headline:
                    parts = headline.split(' at ')
                    if len(parts) >= 2:
                        title = parts[0].strip()
                        company = parts[1].strip()
                        latest_experience = {
                            'company': company,
                            'title': title,
                            'startDate': ''
                        }
        
        # Return results
        if latest_experience:
            return dict(
                linkedin_url=url,
                job_title=latest_experience.get('title', ''),
                company=latest_experience.get('company', ''),
                start_date=latest_experience.get('startDate', ''),
                profile_empty=False,
                experience_empty=False
            )
        else:
            return dict(
                linkedin_url=url,
                job_title='',
                company='',
                start_date='',
                profile_empty=False,
                experience_empty=True
            )
            
    except Exception as e:
        print(f"Error processing {path}: {e}")
        return dict(
            linkedin_url=extract_url_from_filename(path.name),
            job_title='',
            company='',
            start_date='',
            profile_empty=True,
            experience_empty=True
        )

def main():
    """Main function to process all manual collection files."""
    
    # Define the manual collection directory
    manual_collection_dir = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/manual_collection"
    
    # Find all HTML files in manual collection
    html_files = list(pathlib.Path(manual_collection_dir).glob("*.html"))
    
    print(f"Found {len(html_files)} HTML files in manual collection")
    
    results = []
    
    for i, html_file in enumerate(html_files, 1):
        print(f"Processing {i}/{len(html_files)}: {html_file.name}")
        
        result = parse_manual_collection_profile(html_file)
        result['source_directory'] = 'manual_collection'
        result['file_path'] = str(html_file)
        
        results.append(result)
    
    # Write results to CSV
    output_file = 'manual_collection_experiences_parsed.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['linkedin_url', 'job_title', 'company', 'start_date', 
                     'profile_empty', 'experience_empty', 'source_directory', 'file_path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\nResults written to {output_file}")
    
    # Print summary statistics
    total_profiles = len(results)
    successful_profiles = len([r for r in results if not r['profile_empty']])
    profiles_with_experience = len([r for r in results if not r['experience_empty']])
    
    print(f"\nSummary:")
    print(f"Total profiles processed: {total_profiles}")
    print(f"Successful profiles: {successful_profiles}")
    print(f"Profiles with experience: {profiles_with_experience}")
    print(f"Success rate: {profiles_with_experience/total_profiles*100:.1f}%")

if __name__ == "__main__":
    main() 