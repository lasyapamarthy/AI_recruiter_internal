#!/usr/bin/env python3
import os
import re
import csv
import glob
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
EXPERIENCES_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/linkedin_experiences.csv"

def parse_html_file(file_path):
    """Parse a LinkedIn profile HTML file to extract experience information."""
    print(f"Parsing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get profile name
        name = None
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.text
            # Titles usually have format "Name - Job Title - Company | LinkedIn"
            name_match = re.match(r'^([^-]+)', title_text)
            if name_match:
                name = name_match.group(1).strip()
        
        # Find experience section
        experience_section = soup.find('section', {'data-section': 'experience'})
        
        if not experience_section:
            print(f"No experience section found in {file_path}")
            return None
        
        experiences = []
        
        # Find all experience items
        experience_cards = experience_section.find_all('li', {'class': re.compile(r'experience-item|experience-group-position')})
        
        for card in experience_cards:
            # Extract job title
            title_elem = card.find('span', {'class': 'experience-item__title'})
            if not title_elem:
                continue
            
            job_title = title_elem.text.strip()
            
            # Extract company name
            company_elem = card.find('span', {'class': 'experience-item__subtitle'})
            company = company_elem.text.strip() if company_elem else None
            
            # Extract date range
            date_range_elem = card.find('span', {'class': 'date-range'})
            if not date_range_elem:
                continue
                
            date_texts = date_range_elem.find_all('time')
            
            start_date = None
            end_date = "Present"
            
            if date_texts:
                start_date = date_texts[0].text.strip()
                if len(date_texts) > 1:
                    end_date = date_texts[1].text.strip()
            
            # Extract duration
            duration = None
            if date_range_elem.find(string=re.compile(r'\d+\s+(year|month)')):
                duration_text = date_range_elem.find(string=re.compile(r'\d+\s+(year|month)'))
                duration = duration_text.strip() if duration_text else None
            
            # Extract description
            description = None
            desc_elem = card.find('div', {'class': 'show-more-less-text'})
            if desc_elem:
                description = desc_elem.get_text().strip()
            
            experiences.append({
                'name': name,
                'job_title': job_title,
                'company': company,
                'start_date': start_date,
                'end_date': end_date,
                'duration': duration,
                'description': description
            })
        
        return experiences
    
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None

def main():
    # Create a list of all HTML files in the profiles directory
    html_files = glob.glob(os.path.join(HTML_DIR, "*.html"))
    
    if not html_files:
        print(f"No HTML files found in {HTML_DIR}")
        return
    
    all_experiences = []
    
    # Process each HTML file
    for file_path in html_files:
        experiences = parse_html_file(file_path)
        if experiences:
            all_experiences.extend(experiences)
    
    if not all_experiences:
        print("No experience information found in any HTML file")
        return
    
    # Write results to CSV
    with open(EXPERIENCES_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'job_title', 'company', 'start_date', 'end_date', 'duration', 'description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for exp in all_experiences:
            writer.writerow(exp)
    
    print(f"Successfully exported {len(all_experiences)} experiences to {EXPERIENCES_CSV}")

if __name__ == "__main__":
    main() 