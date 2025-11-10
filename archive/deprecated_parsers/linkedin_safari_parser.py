#!/usr/bin/env python3
"""
Specialized parser for LinkedIn safari_html files.
These files have clean HTML structure with proper experience sections.

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
    if 'linkedin.com_in_' in filename:
        # Pattern: linkedin.com_in_username.html
        username = filename.replace('linkedin.com_in_', '').replace('.html', '')
        return f"https://www.linkedin.com/in/{username}/"
    elif 'http:__linkedin.com_in_' in filename:
        # Pattern: http:__linkedin.com_in_username.html
        username = filename.replace('http:__linkedin.com_in_', '').replace('.html', '')
        return f"https://www.linkedin.com/in/{username}/"
    elif 'http%3A__linkedin.com_in_' in filename:
        # Pattern: http%3A__linkedin.com_in_username.html
        username = filename.replace('http%3A__linkedin.com_in_', '').replace('.html', '')
        return f"https://www.linkedin.com/in/{username}/"
    else:
        # Try to extract from any linkedin.com pattern
        match = re.search(r'linkedin\.com[_/]in[_/]([^.]+)', filename)
        if match:
            username = match.group(1).replace('_', '-')
            return f"https://www.linkedin.com/in/{username}/"
    
    return filename  # fallback to filename

def parse_safari_profile(path: pathlib.Path) -> dict:
    """Parse safari LinkedIn profile HTML files."""
    try:
        html = path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract URL from canonical link or filename
        canonical = soup.find('link', rel='canonical')
        if canonical:
            url = canonical.get('href', '')
        else:
            url = extract_url_from_filename(path.name)
        
        # Check if this is actually a LinkedIn profile page
        title = soup.find('title')
        if not title or 'LinkedIn' not in title.get_text():
            return dict(
                linkedin_url=url,
                job_title='',
                company='',
                start_date='',
                profile_empty=True,
                experience_empty=True
            )
        
        # Look for experience section
        experience_section = soup.find('section', {'data-section': 'experience'})
        
        latest_experience = None
        
        if experience_section:
            # Find experience items
            experience_items = experience_section.find_all('li', class_='experience-item')
            
            if experience_items:
                # Get the first (most recent) experience
                first_item = experience_items[0]
                
                # Extract job title
                title_elem = first_item.find('span', class_='experience-item__title')
                job_title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Extract company name
                company_elem = first_item.find('span', class_='experience-item__subtitle')
                company = company_elem.get_text(strip=True) if company_elem else ''
                
                # Extract start date
                date_range_elem = first_item.find('span', class_='date-range')
                start_date = ''
                if date_range_elem:
                    date_text = date_range_elem.get_text(strip=True)
                    # Extract start date from patterns like "Jun 2021 - Present" or "Jan 2020 - Dec 2022"
                    date_match = re.search(r'(\w{3}\s+\d{4})', date_text)
                    if date_match:
                        start_date = date_match.group(1)
                
                latest_experience = {
                    'job_title': job_title,
                    'company': company,
                    'start_date': start_date
                }
        
        # If no experience section found, try to extract from JSON-LD
        if not latest_experience:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string or '{}')
                    # Handle both single objects and arrays
                    if isinstance(data, dict) and '@graph' in data:
                        data = data['@graph']
                    if not isinstance(data, list):
                        data = [data]
                    
                    for obj in data:
                        if obj.get('@type') == 'Person':
                            works_for = obj.get('worksFor', [])
                            if isinstance(works_for, dict):
                                works_for = [works_for]
                            
                            for work in works_for:
                                if work.get('name'):
                                    latest_experience = {
                                        'job_title': obj.get('jobTitle', [''])[0] if isinstance(obj.get('jobTitle', []), list) else obj.get('jobTitle', ''),
                                        'company': work.get('name', ''),
                                        'start_date': ''
                                    }
                                    break
                            
                            if latest_experience:
                                break
                except Exception as e:
                    continue
        
        # If still no experience, try to extract from meta description
        if not latest_experience:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                desc = meta_desc.get('content', '')
                # Look for patterns like "Title at Company" or "Experience: Company"
                
                # Pattern 1: "Title at Company"
                title_company_match = re.search(r'([^·]+?)\s+at\s+([^·]+?)(?:\s*·|$)', desc)
                if title_company_match:
                    latest_experience = {
                        'job_title': title_company_match.group(1).strip(),
                        'company': title_company_match.group(2).strip(),
                        'start_date': ''
                    }
                else:
                    # Pattern 2: "Experience: Company"
                    exp_match = re.search(r'Experience:\s*([^·]+?)(?:\s*·|$)', desc)
                    if exp_match:
                        latest_experience = {
                            'job_title': '',
                            'company': exp_match.group(1).strip(),
                            'start_date': ''
                        }
        
        # Return results
        if latest_experience:
            return dict(
                linkedin_url=url,
                job_title=latest_experience.get('job_title', ''),
                company=latest_experience.get('company', ''),
                start_date=latest_experience.get('start_date', ''),
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
    """Main function to process all collected_html files."""
    
    # Define the collected_html directory
    safari_html_dir = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
    
    # Find all HTML files in collected_html directory
    html_files = list(pathlib.Path(safari_html_dir).glob("*.html"))
    
    print(f"Found {len(html_files)} HTML files in collected_htmls")
    
    results = []
    
    for i, html_file in enumerate(html_files, 1):
        if i % 50 == 0:  # Progress indicator
            print(f"Processing {i}/{len(html_files)}: {html_file.name}")
        
        result = parse_safari_profile(html_file)
        result['source_directory'] = 'collected_htmls'
        result['file_path'] = str(html_file)
        
        results.append(result)
    
    # Write results to CSV
    output_file = 'collected_htmls_experiences_parsed.csv'
    
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
    
    # Show some examples of successful extractions
    successful_examples = [r for r in results if not r['experience_empty']][:5]
    if successful_examples:
        print(f"\nFirst 5 successful extractions:")
        for example in successful_examples:
            print(f"  {example['job_title']} at {example['company']} ({example['start_date']})")

if __name__ == "__main__":
    main() 