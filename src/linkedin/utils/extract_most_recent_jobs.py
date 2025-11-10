#!/usr/bin/env python3
import os
import csv
import pandas as pd
from datetime import datetime
import re

# Configuration
EXPERIENCES_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/extracted_experiences.csv"
OUTPUT_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/most_recent_jobs.csv"
OUTPUT_EXCEL = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/most_recent_jobs.xlsx"

def clean_text(text):
    """Clean text by removing non-printable characters and extra spaces."""
    if not text or pd.isna(text):
        return ""
    
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E]', '', str(text))
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove asterisks (often used for censoring)
    text = re.sub(r'\*+\s*\w+\s*\*+', '', text)
    
    return text

def parse_date(date_str):
    """Parse date string into a datetime object for comparison."""
    if not date_str or pd.isna(date_str) or date_str == 'Present':
        return datetime.now()  # Default to now for 'Present' or empty dates
    
    # Clean the date string
    date_str = str(date_str).strip()
    
    # List of date formats to try
    formats = [
        '%b %Y',           # Jan 2020
        '%B %Y',           # January 2020
        '%b %d, %Y',       # Jan 1, 2020
        '%B %d, %Y',       # January 1, 2020
        '%m/%d/%Y',        # 01/01/2020
        '%d/%m/%Y',        # 01/01/2020
        '%Y-%m-%d',        # 2020-01-01
        '%Y/%m/%d'         # 2020/01/01
    ]
    
    # Try each format
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try more advanced regex-based parsing
    try:
        # Try to extract month and year with regex
        match = re.search(r'(\w+)\s+(\d{4})', date_str)
        if match:
            month, year = match.groups()
            # Convert month name to number (Jan -> 1, etc.)
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month_num = month_map.get(month.lower()[:3], 1)  # Default to January if not found
            return datetime(int(year), month_num, 1)
    except:
        pass
    
    # Just try to extract year as a last resort
    try:
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            return datetime(int(year_match.group(1)), 1, 1)  # Default to January 1st of the year
    except:
        pass
    
    # If all parsing attempts fail, return a very old date
    return datetime(1900, 1, 1)

def get_most_recent_jobs():
    """Extract the most recent job for each person from the CSV file."""
    # Read the CSV file into a pandas DataFrame
    try:
        df = pd.read_csv(EXPERIENCES_CSV)
        print(f"Successfully loaded {len(df)} experience records")
        print(f"Number of unique LinkedIn URLs: {df['linkedin_url'].nunique()}")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []
    
    # Clean up the data
    for col in df.columns:
        if df[col].dtype == 'object':  # Only clean text columns
            df[col] = df[col].apply(clean_text)
    
    # Group by linkedin_url (primary key) and name (secondary key)
    grouped = df.groupby('linkedin_url')
    most_recent_jobs = []
    
    # Process each profile
    for linkedin_url, group in grouped:
        if pd.isna(linkedin_url) or not linkedin_url.strip():
            print(f"Skipping empty LinkedIn URL")
            continue
            
        try:
            # Get the most common name for this URL (in case of variations)
            name = group['name'].mode().iloc[0] if not group['name'].empty else ""
            
            # Get is_empty_profile flag (should be same for all records of this profile)
            is_empty = group['is_empty_profile'].iloc[0]
            
            # Parse dates for comparison
            group['parsed_start_date'] = group['start_date'].apply(lambda x: parse_date(x) if not pd.isna(x) else parse_date(''))
            
            # Sort by parsed date in descending order (most recent first)
            sorted_group = group.sort_values('parsed_start_date', ascending=False)
            
            if not sorted_group.empty:
                most_recent = sorted_group.iloc[0]
                
                # Format profile URL for clickability
                profile_url = linkedin_url
                if profile_url and '?' in profile_url:
                    profile_url = profile_url.split('?')[0]  # Remove tracking parameters
                
                # Build the job record - use empty strings for missing values
                job_record = {
                    'name': name if name else "",
                    'linkedin_url': profile_url,
                    'current_job_title': most_recent['title'] if not pd.isna(most_recent['title']) else "",
                    'current_employer': most_recent['company'] if not pd.isna(most_recent['company']) else "",
                    'job_start_date': most_recent['start_date'] if not pd.isna(most_recent['start_date']) else "",
                    'job_end_date': most_recent['end_date'] if not pd.isna(most_recent['end_date']) else "",
                    'job_duration': most_recent['duration'] if not pd.isna(most_recent['duration']) else "",
                    'job_location': most_recent['location'] if not pd.isna(most_recent['location']) else "",
                    'is_empty_profile': is_empty
                }
                
                # Add all jobs, even if title/employer are empty
                most_recent_jobs.append(job_record)
                
                # Debug logging
                print(f"Processed URL: {profile_url}")
                print(f"  Name: {job_record['name']}")
                print(f"  Title: {job_record['current_job_title']}")
                print(f"  Start Date: {job_record['job_start_date']}")
                print(f"  Empty Profile: {is_empty}")
            else:
                print(f"No experiences found for URL: {linkedin_url}")
                
                # Add empty record to preserve the URL
                most_recent_jobs.append({
                    'name': name if name else "",
                    'linkedin_url': profile_url,
                    'current_job_title': "",
                    'current_employer': "",
                    'job_start_date': "",
                    'job_end_date': "",
                    'job_duration': "",
                    'job_location': "",
                    'is_empty_profile': is_empty
                })
        except Exception as e:
            print(f"Error processing profile for URL {linkedin_url}: {e}")
            # Still add an empty record to preserve the URL
            most_recent_jobs.append({
                'name': "",
                'linkedin_url': linkedin_url,
                'current_job_title': "",
                'current_employer': "",
                'job_start_date': "",
                'job_end_date': "",
                'job_duration': "",
                'job_location': "",
                'is_empty_profile': True  # Assume empty if we can't process it
            })
    
    print(f"Extracted {len(most_recent_jobs)} most recent jobs")
    return most_recent_jobs

def format_linkedin_url(url):
    """Format LinkedIn URL to make it clickable."""
    if not url or pd.isna(url):
        return ""
    
    # Clean URL
    url = str(url).strip()
    
    # Remove tracking parameters
    if '?' in url:
        url = url.split('?')[0]
    
    return url

def main():
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    # Get most recent jobs
    most_recent_jobs = get_most_recent_jobs()
    
    # Sort by name
    most_recent_jobs.sort(key=lambda x: x['name'])
    
    # Save to CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'name', 'linkedin_url', 'current_job_title', 'current_employer', 
            'job_start_date', 'job_end_date', 'job_duration', 'job_location',
            'is_empty_profile'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for job in most_recent_jobs:
            writer.writerow(job)
    
    print(f"Successfully saved most recent jobs to {OUTPUT_CSV}")
    
    # Also save as Excel with better formatting
    try:
        df = pd.DataFrame(most_recent_jobs)
        
        # Create a formatted version for Excel
        writer = pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Most Recent Jobs')
        
        # Get the workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Most Recent Jobs']
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + i)].width = min(max_length, 50)  # Excel cols are A, B, C...
        
        # Save the workbook
        writer.close()
        print(f"Successfully saved Excel file to {OUTPUT_EXCEL}")
    except Exception as e:
        print(f"Error saving Excel file: {e}")
    
    # Display a preview in the terminal
    try:
        df = pd.DataFrame(most_recent_jobs)
        print("\nPreview of most recent jobs table:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)  # Wider display
        pd.set_option('display.max_colwidth', 30)  # Truncate long values
        print(df.head(15))
        
        # Print counts by job title
        print("\nTop 10 job titles:")
        job_titles = df['current_job_title'].value_counts().head(10)
        for title, count in job_titles.items():
            print(f"{title}: {count}")
        
        # Print counts by employer
        print("\nTop 10 employers:")
        employers = df['current_employer'].value_counts().head(10)
        for employer, count in employers.items():
            print(f"{employer}: {count}")
        
    except Exception as e:
        print(f"Error displaying preview: {e}")

if __name__ == '__main__':
    main() 