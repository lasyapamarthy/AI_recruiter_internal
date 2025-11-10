#!/usr/bin/env python3
"""
Analyze the parsed LinkedIn profile data and provide insights.
"""
import pandas as pd
import sys
from collections import Counter

def analyze_profiles(csv_file='linkedin_experiences_parsed.csv'):
    """Analyze the parsed LinkedIn profile data."""
    
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: File {csv_file} not found!")
        return
    
    print("LinkedIn Profile Parsing Analysis")
    print("=" * 50)
    
    # Basic statistics
    total_profiles = len(df)
    successful_profiles = len(df[df['profile_empty'] == False])
    profiles_with_experience = len(df[df['experience_empty'] == False])
    
    print(f"Total profiles processed: {total_profiles}")
    print(f"Successful profiles: {successful_profiles} ({successful_profiles/total_profiles*100:.1f}%)")
    print(f"Profiles with experience: {profiles_with_experience} ({profiles_with_experience/total_profiles*100:.1f}%)")
    print()
    
    # Breakdown by source directory
    print("Breakdown by Source Directory:")
    print("-" * 30)
    source_stats = df.groupby('source_directory').agg({
        'profile_empty': lambda x: (x == False).sum(),
        'experience_empty': lambda x: (x == False).sum(),
        'linkedin_url': 'count'
    }).rename(columns={
        'profile_empty': 'successful_profiles',
        'experience_empty': 'with_experience',
        'linkedin_url': 'total_files'
    })
    
    for source in source_stats.index:
        stats = source_stats.loc[source]
        print(f"{source}:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Successful profiles: {stats['successful_profiles']} ({stats['successful_profiles']/stats['total_files']*100:.1f}%)")
        print(f"  With experience: {stats['with_experience']} ({stats['with_experience']/stats['total_files']*100:.1f}%)")
        print()
    
    # Top companies
    print("Top 10 Companies:")
    print("-" * 20)
    companies = df[df['company'] != '']['company'].value_counts().head(10)
    for i, (company, count) in enumerate(companies.items(), 1):
        print(f"{i:2d}. {company}: {count} profiles")
    print()
    
    # Top job titles
    print("Top 10 Job Titles:")
    print("-" * 20)
    job_titles = df[df['job_title'] != '']['job_title'].value_counts().head(10)
    for i, (title, count) in enumerate(job_titles.items(), 1):
        print(f"{i:2d}. {title}: {count} profiles")
    print()
    
    # Start date analysis
    print("Start Date Analysis:")
    print("-" * 20)
    start_dates = df[df['start_date'] != '']['start_date']
    if len(start_dates) > 0:
        # Extract years from start dates
        years = []
        for date in start_dates:
            try:
                if '-' in str(date):
                    year = str(date).split('-')[0]
                    if year.isdigit() and len(year) == 4:
                        years.append(int(year))
                elif str(date).isdigit() and len(str(date)) == 4:
                    years.append(int(date))
            except:
                continue
        
        if years:
            year_counts = Counter(years)
            recent_years = sorted(year_counts.items(), key=lambda x: x[0], reverse=True)[:5]
            print("Most recent start years:")
            for year, count in recent_years:
                print(f"  {year}: {count} profiles")
        else:
            print("  No valid start years found")
    else:
        print("  No start dates available")
    print()
    
    # Error analysis
    if 'error' in df.columns:
        errors = df[df['error'].notna()]
        if len(errors) > 0:
            print("Error Analysis:")
            print("-" * 15)
            error_types = errors['error'].value_counts()
            for error, count in error_types.items():
                print(f"  {error}: {count} files")
            print()
    
    # Data quality insights
    print("Data Quality Insights:")
    print("-" * 25)
    
    # Profiles with both job title and company
    complete_experience = df[(df['job_title'] != '') & (df['company'] != '')]
    print(f"Profiles with both job title and company: {len(complete_experience)} ({len(complete_experience)/total_profiles*100:.1f}%)")
    
    # Profiles with start dates
    with_dates = df[df['start_date'] != '']
    print(f"Profiles with start dates: {len(with_dates)} ({len(with_dates)/total_profiles*100:.1f}%)")
    
    # Profiles with LinkedIn URLs
    with_urls = df[df['linkedin_url'].str.contains('linkedin.com', na=False)]
    print(f"Profiles with valid LinkedIn URLs: {len(with_urls)} ({len(with_urls)/total_profiles*100:.1f}%)")
    
    print("\nAnalysis complete!")

if __name__ == '__main__':
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'linkedin_experiences_parsed.csv'
    analyze_profiles(csv_file) 