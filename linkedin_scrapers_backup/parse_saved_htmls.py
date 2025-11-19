#!/usr/bin/env python3
import os
import csv
import re
from bs4 import BeautifulSoup

HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
OUTPUT_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/extracted_experiences.csv"

def extract_name_from_html(soup):
    """Extract profile name from HTML content."""
    name = None
    # Try title tag first
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.text
        name_match = re.match(r'^([^-|]+)', title_text)
        if name_match:
            name = name_match.group(1).strip()
    
    # If name not found in title, try other common selectors
    if not name:
        name_selectors = [
            {'class': 'top-card-layout__title'},
            {'class': 'text-heading-xlarge'},
            {'class': 'pv-text-details__left-panel'},
            {'id': 'name'},
        ]
        for selector in name_selectors:
            name_elem = soup.find(['h1', 'div', 'span'], selector)
            if name_elem:
                name = name_elem.get_text().strip()
                break
    
    return name

def is_profile_empty(soup):
    """Check if a profile is empty (no experience and no education)."""
    # Check for experience section
    has_experience = False
    for selector in [
        {'data-section': 'experience'},
        {'id': 'experience-section'},
        {'class': 'experience-section'},
        {'class': 'pvs-list__outer-container'},
        {'class': 'pvs-entity'}
    ]:
        section = soup.find(['section', 'div', 'ul'], selector)
        if section and section.find(['li', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['experience-item', 'pvs-list__item', 'pvs-entity'])):
            has_experience = True
            break
    
    # Check for education section
    has_education = False
    for selector in [
        {'data-section': 'education'},
        {'id': 'education-section'},
        {'class': 'education-section'},
        {'class': 'pvs-list__outer-container'},
        {'class': 'pvs-entity'}
    ]:
        section = soup.find(['section', 'div', 'ul'], selector)
        if section and section.find(['li', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['education-item', 'pvs-list__item', 'pvs-entity'])):
            has_education = True
            break
    
    return not (has_experience or has_education)

def extract_experiences(html_content, profile_url):
    """Extract experience information from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    name = extract_name_from_html(soup)
    
    if not name:
        print(f"Could not find name for profile: {profile_url}")
        name = "Unknown"
    
    # Check if profile is empty
    is_empty = is_profile_empty(soup)
    
    # Find experience section
    experience_section = None
    for selector in [
        {'data-section': 'experience'},
        {'id': 'experience-section'},
        {'class': 'experience-section'},
        {'class': 'pvs-list__outer-container'},
        {'class': 'pvs-entity'}
    ]:
        section = soup.find(['section', 'div', 'ul'], selector)
        if section:
            experience_section = section
            break
    
    # If no experience section found, return a single blank experience entry
    if not experience_section:
        print(f"No experience section found for {name} ({profile_url})")
        return [{
            'name': name,
            'linkedin_url': profile_url,
            'title': '',
            'company': '',
            'start_date': '',
            'end_date': '',
            'duration': '',
            'location': '',
            'description': '',
            'is_empty_profile': is_empty
        }]
    
    experiences = []
    experience_items = experience_section.find_all(['li', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['experience-item', 'pvs-list__item', 'pvs-entity']))
    
    # If no experience items found in the section, return blank experience
    if not experience_items:
        print(f"No experience items found for {name} ({profile_url})")
        return [{
            'name': name,
            'linkedin_url': profile_url,
            'title': '',
            'company': '',
            'start_date': '',
            'end_date': '',
            'duration': '',
            'location': '',
            'description': '',
            'is_empty_profile': is_empty
        }]
    
    for item in experience_items:
        # Extract job details
        title = ''
        company = ''
        start_date = ''
        end_date = ''
        duration = ''
        location = ''
        description = ''
        
        # Try to extract title
        title_elem = item.find(['h3', 'span', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['experience-item__title', 't-16', 'job-title']))
        if title_elem:
            title = title_elem.get_text().strip()
        
        # Try to extract company
        company_elem = item.find(['p', 'span', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['experience-item__subtitle', 'company-name']))
        if company_elem:
            company = company_elem.get_text().strip()
        
        # Try to extract dates
        date_elem = item.find(['span', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['date-range', 'experience-item__duration']))
        if date_elem:
            date_text = date_elem.get_text().strip()
            # Try to parse start and end dates
            date_match = re.search(r'(\w+ \d{4})\s*(?:-|–)\s*(\w+ \d{4}|Present)', date_text)
            if date_match:
                start_date = date_match.group(1)
                end_date = date_match.group(2)
        
        # Try to extract duration
        duration_pattern = re.compile(r'(\d+\s+(?:yr|year|mo|month)s?\s*(?:\d+\s+(?:yr|year|mo|month)s?)?)')
        for text in item.stripped_strings:
            duration_match = duration_pattern.search(text)
            if duration_match:
                duration = duration_match.group(0)
                break
        
        # Try to extract location
        location_elem = item.find(['span', 'div'], class_=lambda x: x and any(pattern in str(x) for pattern in ['location', 'experience-item__location']))
        if location_elem:
            location = location_elem.get_text().strip()
        
        # Try to extract description
        desc_elem = item.find(['div', 'p'], class_=lambda x: x and any(pattern in str(x) for pattern in ['description', 'show-more-less-text']))
        if desc_elem:
            description = desc_elem.get_text().strip()
        
        experiences.append({
            'name': name,
            'linkedin_url': profile_url,
            'title': title,
            'company': company,
            'start_date': start_date,
            'end_date': end_date,
            'duration': duration,
            'location': location,
            'description': description,
            'is_empty_profile': is_empty
        })
    
    return experiences

def main():
    """Process all HTML files and extract experiences."""
    print(f"Scanning directory: {HTML_DIR}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    # Get list of HTML files
    html_files = [f for f in os.listdir(HTML_DIR) if f.endswith('.html')]
    print(f"Found {len(html_files)} HTML files")
    
    all_experiences = []
    processed_profiles = 0
    profiles_with_experiences = 0
    
    # Process each HTML file
    for i, html_file in enumerate(html_files, 1):
        file_path = os.path.join(HTML_DIR, html_file)
        
        try:
            # Convert filename back to URL
            profile_url = html_file.replace('_', '/').replace('linkedin.com', 'linkedin.com/')
            profile_url = profile_url[:-5]  # Remove .html extension
            if not profile_url.startswith('http'):
                profile_url = 'https://' + profile_url
            
            # Read and parse HTML file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract experiences
            experiences = extract_experiences(html_content, profile_url)
            
            if experiences:
                all_experiences.extend(experiences)
                if any(exp['title'] or exp['company'] for exp in experiences):
                    profiles_with_experiences += 1
                print(f"Extracted {len(experiences)} experiences from {html_file}")
            
            processed_profiles += 1
            
            # Show progress every 10 files
            if i % 10 == 0:
                print(f"Processed {i}/{len(html_files)} files...")
        
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
    
    # Save all experiences to CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'linkedin_url', 'title', 'company', 'start_date', 'end_date', 'duration', 'location', 'description', 'is_empty_profile']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_experiences)
    
    print("\nProcessing complete!")
    print(f"Processed {processed_profiles} HTML files")
    print(f"Extracted {len(all_experiences)} experiences from {profiles_with_experiences} profiles")
    print(f"Saved to {OUTPUT_CSV}")

if __name__ == '__main__':
    main() 