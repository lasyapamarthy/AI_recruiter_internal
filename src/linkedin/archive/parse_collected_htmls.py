#!/usr/bin/env python3
import os
import csv
import re
from bs4 import BeautifulSoup
from datetime import datetime
import json

HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
OUTPUT_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_most_recent_experiences.csv"
OUTPUT_JSON = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_most_recent_experiences.json"

def is_auth_wall_or_error_page(soup):
    """Check if the page is an auth wall, error page, or has no profile content."""
    title = soup.find('title')
    title_text = title.get_text() if title else ""
    
    # Check for error pages first
    error_indicators = [
        "Failed to open page",
        "Safari Can't Find the Server"
    ]
    
    for indicator in error_indicators:
        if indicator in title_text:
            return True
    
    # Check for pure auth wall pages (title indicates auth wall)
    auth_wall_titles = [
        "Sign Up | LinkedIn",
        "Sign in | LinkedIn"
    ]
    
    for title_indicator in auth_wall_titles:
        if title_indicator in title_text:
            return True
    
    # Check for auth wall meta tag
    meta_auth = soup.find('meta', {'name': 'pageKey', 'content': 'auth_wall_desktop_profile'})
    if meta_auth:
        return True
    
    # Check if this is a valid profile page (has profile meta tag)
    meta_profile = soup.find('meta', {'name': 'pageKey', 'content': 'public_profile_v3_desktop'})
    if meta_profile:
        return False  # This is a valid profile page, don't filter it
    
    # Check for profile indicators in title (name - company/location | LinkedIn)
    if ' - ' in title_text and '| LinkedIn' in title_text:
        profile_name = title_text.split(' - ')[0].strip()
        if profile_name and profile_name != 'LinkedIn' and len(profile_name) > 2:
            return False  # This looks like a valid profile
    
    return True

def extract_profile_name(soup):
    """Extract the profile name from the page."""
    # Try multiple selectors for name
    name_selectors = [
        'h1.top-card-layout__title',
        'h1[data-test-id="top-card-title"]',
        '.top-card__title',
        '.top-card-layout__title'
    ]
    
    for selector in name_selectors:
        name_elem = soup.select_one(selector)
        if name_elem:
            return name_elem.get_text().strip()
    
    # Try JSON-LD structured data
    json_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and 'name' in data:
                return data['name']
        except:
            continue
    
    return "Unknown"

def extract_start_date_from_range(date_range):
    """Extract start date from date range string."""
    if not date_range or date_range in ["N/A", "Unknown"]:
        return "N/A"
    
    # Clean up the date range text
    date_range = re.sub(r'\s+', ' ', date_range).strip()
    
    # Common patterns for date ranges
    patterns = [
        r'(\w{3}\s+\d{4})\s*-',  # "Mar 2025 -" or "Mar 2025 - Present"
        r'(\w{3}\s+\d{4})',      # Just "Mar 2025" (fallback)
        r'(\d{4})\s*-',          # "2024 -" 
        r'(\d{4})',              # Just "2024" (fallback)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_range)
        if match:
            return match.group(1).strip()
    
    return "Unknown"

def extract_most_recent_experience(soup):
    """Extract the most recent job experience from the profile."""
    # Find the experience section
    experience_section = soup.find('section', {'data-section': 'experience'})
    if not experience_section:
        experience_section = soup.find('section', class_=lambda x: x and 'experience' in x)
    
    if not experience_section:
        # No experience section found, return placeholder data
        return {
            'job_title': "No experience listed",
            'company': "N/A",
            'date_range': "N/A",
            'start_date': "N/A",
            'location': "N/A",
            'description': "No work experience found on profile"
        }
    
    # Find the first experience item (most recent)
    experience_items = experience_section.find_all('li', class_=lambda x: x and 'experience-item' in x)
    
    if not experience_items:
        return {
            'job_title': "No experience items found",
            'company': "N/A",
            'date_range': "N/A",
            'start_date': "N/A",
            'location': "N/A",
            'description': "Experience section exists but no items found"
        }
    
    first_item = experience_items[0]
    
    # Extract job title
    title_elem = first_item.find(class_=lambda x: x and 'experience-item__title' in x)
    job_title = title_elem.get_text().strip() if title_elem else "Unknown"
    
    # Extract company name
    company_elem = first_item.find(class_=lambda x: x and 'experience-item__subtitle' in x)
    company = company_elem.get_text().strip() if company_elem else "Unknown"
    
    # Extract date range
    date_elem = first_item.find(class_=lambda x: x and 'date-range' in x)
    date_range = date_elem.get_text().strip() if date_elem else "Unknown"
    
    # Extract start date from date range
    start_date = extract_start_date_from_range(date_range)
    
    # Extract location
    location_elem = first_item.find('p', class_=lambda x: x and 'experience-item__meta-item' in x)
    location = "Unknown"
    if location_elem:
        location_text = location_elem.get_text().strip()
        # Skip if it's the date range
        if not any(word in location_text.lower() for word in ['present', 'month', 'year', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
            location = location_text
    
    # Extract description
    description_elem = first_item.find('div', {'data-section': 'currentPositions'})
    description = ""
    if description_elem:
        desc_text = description_elem.get_text().strip()
        # Clean up the description
        description = re.sub(r'\s+', ' ', desc_text)[:500]  # Limit to 500 chars
    
    return {
        'job_title': job_title,
        'company': company,
        'date_range': date_range,
        'start_date': start_date,
        'location': location,
        'description': description
    }

def parse_html_file(file_path):
    """Parse a single HTML file and extract profile information."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check if it's an auth wall or error page
        if is_auth_wall_or_error_page(soup):
            return None
        
        # Extract profile information
        profile_name = extract_profile_name(soup)
        most_recent_exp = extract_most_recent_experience(soup)
        
        # Extract LinkedIn URL from filename
        filename = os.path.basename(file_path)
        linkedin_url = filename.replace('.html', '').replace('_', '/').replace('linkedin.com/', 'https://linkedin.com/')
        if not linkedin_url.startswith('http'):
            linkedin_url = 'https://' + linkedin_url
        
        return {
            'filename': filename,
            'linkedin_url': linkedin_url,
            'profile_name': profile_name,
            'job_title': most_recent_exp['job_title'],
            'company': most_recent_exp['company'],
            'date_range': most_recent_exp['date_range'],
            'start_date': most_recent_exp['start_date'],
            'location': most_recent_exp['location'],
            'description': most_recent_exp['description']
        }
        
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
        return None

def main():
    """Main function to process all HTML files in the directory."""
    if not os.path.exists(HTML_DIR):
        print(f"Directory {HTML_DIR} does not exist!")
        return
    
    html_files = [f for f in os.listdir(HTML_DIR) if f.endswith('.html')]
    print(f"Found {len(html_files)} HTML files to process...")
    
    results = []
    processed = 0
    successful = 0
    
    for filename in html_files:
        file_path = os.path.join(HTML_DIR, filename)
        processed += 1
        
        if processed % 10 == 0:
            print(f"Processed {processed}/{len(html_files)} files...")
        
        result = parse_html_file(file_path)
        if result:
            results.append(result)
            successful += 1
    
    print(f"\nProcessing complete!")
    print(f"Total files processed: {processed}")
    print(f"Successful extractions: {successful}")
    print(f"Success rate: {successful/processed*100:.1f}%")
    
    if results:
        # Save to CSV
        fieldnames = ['filename', 'linkedin_url', 'profile_name', 'job_title', 'company', 'date_range', 'start_date', 'location', 'description']
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        # Save to JSON
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as jsonfile:
            json.dump(results, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to:")
        print(f"CSV: {OUTPUT_CSV}")
        print(f"JSON: {OUTPUT_JSON}")
        
        # Show sample results
        print(f"\nSample results:")
        for i, result in enumerate(results[:3]):
            print(f"\n{i+1}. {result['profile_name']}")
            print(f"   Job: {result['job_title']} at {result['company']}")
            print(f"   Date: {result['date_range']}")
            print(f"   Location: {result['location']}")
    else:
        print("No valid profiles found!")

if __name__ == "__main__":
    main() 