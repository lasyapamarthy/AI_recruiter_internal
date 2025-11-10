#!/usr/bin/env python3
"""
Enhanced LinkedIn profile parser that handles both public profile pages and 
logged-in web app pages with embedded JSON data.

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

def parse_webapp_json_data(html_content):
    """Parse LinkedIn web app JSON data for profile information."""
    try:
        # Look for the main data script tag
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find script tags that might contain profile data
        for script in soup.find_all('script'):
            if script.string and 'profileCard' in script.string:
                script_content = script.string
                
                # Try to extract JSON data
                # Look for patterns like "profileCard":{"data":{...}}
                json_match = re.search(r'"profileCard":\s*({[^}]+})', script_content)
                if json_match:
                    try:
                        profile_data = json.loads(json_match.group(1))
                        return profile_data
                    except:
                        continue
                
                # Alternative: look for experience card data
                exp_match = re.search(r'"experienceCard":\s*({[^}]+})', script_content)
                if exp_match:
                    try:
                        exp_data = json.loads(exp_match.group(1))
                        return exp_data
                    except:
                        continue
                        
                # Look for member profile data
                member_match = re.search(r'"member":\s*({[^}]+})', script_content)
                if member_match:
                    try:
                        member_data = json.loads(member_match.group(1))
                        return member_data
                    except:
                        continue
        
        # If no structured JSON found, try to extract from meta tags
        title_tag = soup.find('title')
        if title_tag and 'LinkedIn' in title_tag.get_text():
            title_text = title_tag.get_text()
            # Extract name and title from page title
            # Pattern: "Name - Title - Company | LinkedIn"
            title_match = re.match(r'([^-]+)\s*-\s*([^-]+)\s*-\s*([^|]+)', title_text)
            if title_match:
                return {
                    'name': title_match.group(1).strip(),
                    'title': title_match.group(2).strip(),
                    'company': title_match.group(3).strip()
                }
        
        return None
        
    except Exception as e:
        print(f"Error parsing webapp JSON data: {e}")
        return None

def extract_experience_from_webapp_json(json_data):
    """Extract experience information from webapp JSON data."""
    if not json_data:
        return None
    
    try:
        # Try different JSON structure patterns
        
        # Pattern 1: Direct experience data
        if 'experience' in json_data:
            exp_data = json_data['experience']
            if isinstance(exp_data, list) and exp_data:
                latest = exp_data[0]  # Assume first is most recent
                return {
                    'title': latest.get('title', ''),
                    'company': latest.get('company', ''),
                    'startDate': latest.get('startDate', '')
                }
        
        # Pattern 2: Profile card with experience
        if 'data' in json_data and 'experience' in json_data['data']:
            exp_data = json_data['data']['experience']
            if isinstance(exp_data, list) and exp_data:
                latest = exp_data[0]
                return {
                    'title': latest.get('title', ''),
                    'company': latest.get('company', ''),
                    'startDate': latest.get('startDate', '')
                }
        
        # Pattern 3: From title extraction
        if 'title' in json_data and 'company' in json_data:
            return {
                'title': json_data['title'],
                'company': json_data['company'],
                'startDate': ''
            }
        
        return None
        
    except Exception as e:
        print(f"Error extracting experience from JSON: {e}")
        return None

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

    # ---- Determine if this is a webapp page or public profile ----
    is_webapp = 'manual_collection' in source_dir or 'voyager' in html or 'ember-cli' in html
    
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

    latest = None
    
    # ---- Handle webapp pages with JSON data ----
    if is_webapp:
        json_data = parse_webapp_json_data(html)
        latest = extract_experience_from_webapp_json(json_data)
        
        # If JSON parsing didn't work, try to extract from page title
        if not latest and title:
            title_text = title.get_text()
            # Pattern: "Name - Title - Company | LinkedIn" or "Name | LinkedIn"
            if ' - ' in title_text and ' | LinkedIn' in title_text:
                parts = title_text.replace(' | LinkedIn', '').split(' - ')
                if len(parts) >= 3:
                    latest = {
                        'title': parts[1].strip(),
                        'company': parts[2].strip(),
                        'startDate': ''
                    }
                elif len(parts) == 2:
                    # Try to determine if second part is title or company
                    second_part = parts[1].strip()
                    if any(word in second_part.lower() for word in ['engineer', 'developer', 'manager', 'analyst', 'specialist', 'coordinator', 'director', 'lead']):
                        latest = {
                            'title': second_part,
                            'company': '',
                            'startDate': ''
                        }
                    else:
                        latest = {
                            'title': '',
                            'company': second_part,
                            'startDate': ''
                        }

    # ---- Handle public profile pages (original logic) ----
    if not latest:
        # ---- try JSON-LD first (fast & reliable when present) -----------------
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

def main(out_csv='linkedin_experiences_enhanced.csv'):
    """Main function to process all directories and create CSV output."""
    
    # Define the three directories
    directories = [
        ('/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls', 'htmls'),
        ('/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/safari_htmls', 'safari_htmls'),
        ('/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/manual_collection', 'manual_collection')
    ]
    
    all_rows = []
    
    print("Starting Enhanced LinkedIn profile parsing...")
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
    print(f"Enhanced parsing complete!")
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
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'linkedin_experiences_enhanced.csv'
    main(output_file) 