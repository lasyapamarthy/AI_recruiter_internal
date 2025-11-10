#!/usr/bin/env python3
"""
Extract latest professional-experience information from locally saved
LinkedIn profile HTML pages and write the results to a CSV file.

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

def first_time(tag):
    """Return the first <time> element's text inside *tag* or ''."""
    t = tag.find('time')
    return t.get_text(strip=True) if t else ''

def extract_url_from_filename(filename):
    """Extract LinkedIn URL from filename patterns."""
    # Handle different filename patterns
    if 'linkedin.com_in_' in filename:
        # Pattern: linkedin.com_in_username.html
        username = filename.replace('linkedin.com_in_', '').replace('.html', '').replace('_', '')
        return f"https://in.linkedin.com/in/{username}"
    elif 'linkedin.com_' in filename:
        # Pattern: linkedin.com_username.html
        username = filename.replace('linkedin.com_', '').replace('.html', '').replace('_', '')
        return f"https://linkedin.com/in/{username}"
    elif 'LinkedIn.html' in filename:
        # Pattern: "Name _ LinkedIn.html"
        name_part = filename.replace(' _ LinkedIn.html', '').replace(' ', '-').lower()
        return f"https://linkedin.com/in/{name_part}"
    else:
        return filename  # fallback to filename

def parse_profile(path: pathlib.Path, source_dir: str) -> dict:
    """Parse a LinkedIn profile HTML file and extract experience information."""
    try:
        html = path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"Error reading file {path}: {e}")
        return dict(
            linkedin_url=str(path), 
            profile_empty=True,
            experience_empty=True, 
            job_title='', 
            company='', 
            start_date='',
            source_directory=source_dir,
            file_path=str(path),
            error=f"File read error: {e}"
        )
    
    soup = BeautifulSoup(html, 'html.parser')

    # ---- basic URL / "profile not found" check ----------------------------
    canonical = soup.find('link', rel='canonical') or soup.find('meta', property='og:url')
    
    if canonical:
        url = canonical.get('href', '')
    else:
        # Try to extract from filename if no canonical URL found
        url = extract_url_from_filename(path.name)

    # Check if this is actually a LinkedIn profile page
    title = soup.find('title')
    if title and 'LinkedIn' not in title.get_text():
        return dict(
            linkedin_url=url,
            profile_empty=True,
            experience_empty=True, 
            job_title='', 
            company='', 
            start_date='',
            source_directory=source_dir,
            file_path=str(path),
            error="Not a LinkedIn profile page"
        )

    # ---- try JSON-LD first (fast & reliable when present) -----------------
    latest = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            # some pages wrap items inside "@graph"
            objs = data if isinstance(data, list) else data.get('@graph', [data])
            for obj in objs:
                if obj.get('@type') == 'Person':
                    works_for = obj.get('worksFor', [])
                    if isinstance(works_for, dict):
                        works_for = [works_for]
                    
                    for wf in works_for:
                        role = wf.get('member', {})
                        sd = role.get('startDate')
                        if not sd:
                            continue
                        # keep the *most recent* (largest ISO date)
                        if (latest is None) or (sd > latest.get('startDate', '')):
                            latest = dict(
                                startDate=sd,
                                company=wf.get('name', ''),
                                title=obj.get('jobTitle', [''])[0] if isinstance(obj.get('jobTitle', []), list) else obj.get('jobTitle', '')
                            )
        except Exception as e:
            print(f"Error parsing JSON-LD in {path}: {e}")
            continue

    # ---- fall back to scraping the Experience section ---------------------
    if latest is None:
        # Try multiple selectors for experience section
        exp_section = (
            soup.select_one('section[data-section="experience"]') or
            soup.select_one('.experience') or
            soup.select_one('[class*="experience"]')
        )
        
        if exp_section:
            # Try multiple selectors for position items
            positions = (
                exp_section.select('li.profile-section-card') or
                exp_section.select('.experience-item') or
                exp_section.select('[class*="experience-item"]') or
                exp_section.select('li[data-section*="Position"]')
            )
            
            if positions:
                first = positions[0]  # Reverse-chronological order
                
                # Extract title
                title_elem = (
                    first.select_one('.experience-item__title') or
                    first.select_one('[class*="title"]') or
                    first.select_one('h3') or
                    first.select_one('.t-16')
                )
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Extract company
                company_elem = (
                    first.select_one('.experience-item__subtitle') or
                    first.select_one('[class*="subtitle"]') or
                    first.select_one('[class*="company"]') or
                    first.select_one('.t-14')
                )
                company = company_elem.get_text(strip=True) if company_elem else ''
                
                # Extract start date
                start_date = first_time(first)
                
                latest = dict(
                    title=title,
                    company=company,
                    startDate=start_date
                )

    # ---- Additional fallback: try to extract from meta description --------
    if latest is None:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')
            # Look for patterns like "Title at Company"
            title_company_match = re.search(r'([^·]+?)\s+at\s+([^·]+?)(?:\s*·|$)', desc)
            if title_company_match:
                latest = dict(
                    title=title_company_match.group(1).strip(),
                    company=title_company_match.group(2).strip(),
                    startDate=''
                )

    # ---- flags ------------------------------------------------------------
    experience_empty = latest is None
    profile_empty = not bool(soup.find('title') and 'LinkedIn' in soup.find('title').get_text())

    return dict(
        linkedin_url=url,
        job_title='' if experience_empty else latest.get('title', ''),
        company='' if experience_empty else latest.get('company', ''),
        start_date='' if experience_empty else latest.get('startDate', ''),
        profile_empty=profile_empty,
        experience_empty=experience_empty,
        source_directory=source_dir,
        file_path=str(path)
    )

def process_directory(directory_path: str, source_name: str) -> list:
    """Process all HTML files in a directory and return parsed results."""
    rows = []
    html_files = glob.glob(os.path.join(directory_path, "*.html"))
    
    print(f"Processing {len(html_files)} files from {source_name}...")
    
    for i, file_path in enumerate(html_files):
        if i % 50 == 0:  # Progress indicator
            print(f"  Processed {i}/{len(html_files)} files...")
        
        try:
            result = parse_profile(pathlib.Path(file_path), source_name)
            rows.append(result)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            rows.append(dict(
                linkedin_url=file_path,
                profile_empty=True,
                experience_empty=True,
                job_title='',
                company='',
                start_date='',
                source_directory=source_name,
                file_path=file_path,
                error=f"Processing error: {e}"
            ))
    
    print(f"  Completed {source_name}: {len(rows)} profiles processed")
    return rows

def main(out_csv='linkedin_experiences_parsed.csv'):
    """Main function to process all directories and create CSV output."""
    
    # Define the three directories
    directories = [
        ('/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls', 'htmls'),
        ('/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/safari_htmls', 'safari_htmls'),
        ('/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/manual_collection', 'manual_collection')
    ]
    
    all_rows = []
    
    print("Starting LinkedIn profile parsing...")
    print("=" * 50)
    
    for directory_path, source_name in directories:
        if os.path.exists(directory_path):
            rows = process_directory(directory_path, source_name)
            all_rows.extend(rows)
        else:
            print(f"Warning: Directory {directory_path} does not exist")
    
    if not all_rows:
        print("No profiles found to process!")
        return
    
    # Write to CSV
    fieldnames = [
        'linkedin_url', 'job_title', 'company', 'start_date', 
        'profile_empty', 'experience_empty', 'source_directory', 'file_path'
    ]
    
    # Add error field if any rows have errors
    if any('error' in row for row in all_rows):
        fieldnames.append('error')
    
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("=" * 50)
    print(f"Parsing complete!")
    print(f"Total profiles processed: {len(all_rows)}")
    print(f"Results written to: {out_csv}")
    
    # Print summary statistics
    successful_profiles = sum(1 for row in all_rows if not row.get('profile_empty', True))
    profiles_with_experience = sum(1 for row in all_rows if not row.get('experience_empty', True))
    
    print(f"Successful profiles: {successful_profiles}")
    print(f"Profiles with experience data: {profiles_with_experience}")
    
    # Print breakdown by source
    print("\nBreakdown by source:")
    for _, source_name in directories:
        source_count = sum(1 for row in all_rows if row.get('source_directory') == source_name)
        source_with_exp = sum(1 for row in all_rows 
                             if row.get('source_directory') == source_name and not row.get('experience_empty', True))
        print(f"  {source_name}: {source_count} total, {source_with_exp} with experience")

if __name__ == '__main__':
    # Allow custom output filename
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'linkedin_experiences_parsed.csv'
    main(output_file) 