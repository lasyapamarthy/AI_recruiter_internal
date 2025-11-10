#!/usr/bin/env python3
"""
Combine LinkedIn profile parsing results from safari_html and htmls directories
into a single CSV file with the best quality data.
"""
import pandas as pd
import sys
import os

def combine_safari_htmls_data():
    """Combine data from safari_html and htmls directories."""
    
    print("Combining Safari HTML and HTMLs Directory Data")
    print("=" * 50)
    
    # Load the main parsing results (contains all directories)
    main_file = 'linkedin_experiences_parsed.csv'
    safari_file = 'safari_htmls_experiences_parsed.csv'
    
    combined_data = []
    
    # Load main file and filter for htmls directory
    if os.path.exists(main_file):
        print(f"Loading {main_file}...")
        main_df = pd.read_csv(main_file)
        
        # Filter for htmls directory only
        htmls_df = main_df[main_df['source_directory'] == 'htmls'].copy()
        print(f"Found {len(htmls_df)} profiles from htmls directory")
        
        # Add to combined data
        combined_data.append(htmls_df)
    else:
        print(f"Warning: {main_file} not found")
    
    # Load safari HTML results
    if os.path.exists(safari_file):
        print(f"Loading {safari_file}...")
        safari_df = pd.read_csv(safari_file)
        
        # Filter out authwall pages for cleaner data
        valid_safari_df = safari_df[~safari_df['linkedin_url'].str.contains('/authwall', na=False)].copy()
        print(f"Found {len(safari_df)} total safari profiles, {len(valid_safari_df)} valid (non-authwall)")
        
        # Add to combined data
        combined_data.append(valid_safari_df)
    else:
        print(f"Warning: {safari_file} not found")
    
    if not combined_data:
        print("No data found to combine!")
        return
    
    # Combine all dataframes
    combined_df = pd.concat(combined_data, ignore_index=True)
    
    print(f"\nCombined dataset statistics:")
    print(f"Total profiles: {len(combined_df)}")
    
    # Calculate statistics
    total_profiles = len(combined_df)
    successful_profiles = len(combined_df[combined_df['profile_empty'] == False])
    profiles_with_experience = len(combined_df[combined_df['experience_empty'] == False])
    
    print(f"Successful profiles: {successful_profiles} ({successful_profiles/total_profiles*100:.1f}%)")
    print(f"Profiles with experience: {profiles_with_experience} ({profiles_with_experience/total_profiles*100:.1f}%)")
    
    # Breakdown by source
    print(f"\nBreakdown by source directory:")
    source_breakdown = combined_df.groupby('source_directory').agg({
        'profile_empty': lambda x: (x == False).sum(),
        'experience_empty': lambda x: (x == False).sum()
    }).rename(columns={'profile_empty': 'successful_profiles', 'experience_empty': 'with_experience'})
    
    for source, row in source_breakdown.iterrows():
        source_total = len(combined_df[combined_df['source_directory'] == source])
        print(f"  {source}: {source_total} total, {row['successful_profiles']} successful, {row['with_experience']} with experience")
    
    # Show top companies
    if profiles_with_experience > 0:
        companies = combined_df[combined_df['experience_empty'] == False]['company'].value_counts().head(15)
        if len(companies) > 0:
            print(f"\nTop 15 companies:")
            for company, count in companies.items():
                if company and len(str(company).strip()) > 0 and str(company) != 'nan':
                    print(f"  {company}: {count}")
    
    # Show sample successful extractions
    successful_samples = combined_df[combined_df['experience_empty'] == False].head(10)
    if len(successful_samples) > 0:
        print(f"\nSample successful extractions:")
        for _, row in successful_samples.iterrows():
            job_title = row.get('job_title', '')
            company = row.get('company', '')
            start_date = row.get('start_date', '')
            source = row.get('source_directory', '')
            if job_title or company:
                print(f"  [{source}] {job_title} at {company} ({start_date})")
    
    # Save combined data
    output_file = 'combined_safari_htmls_experiences.csv'
    combined_df.to_csv(output_file, index=False)
    
    print(f"\nCombined data saved to: {output_file}")
    
    # Create a high-quality subset with only profiles that have experience data
    quality_df = combined_df[combined_df['experience_empty'] == False].copy()
    quality_output_file = 'high_quality_linkedin_experiences.csv'
    quality_df.to_csv(quality_output_file, index=False)
    
    print(f"High-quality subset (with experience) saved to: {quality_output_file}")
    print(f"High-quality subset contains {len(quality_df)} profiles")
    
    # Show data quality metrics
    print(f"\nData Quality Metrics:")
    print(f"Overall success rate: {profiles_with_experience/total_profiles*100:.1f}%")
    
    # Calculate success rate by source
    for source in combined_df['source_directory'].unique():
        source_df = combined_df[combined_df['source_directory'] == source]
        source_success = len(source_df[source_df['experience_empty'] == False])
        source_total = len(source_df)
        print(f"{source} success rate: {source_success/source_total*100:.1f}% ({source_success}/{source_total})")

if __name__ == "__main__":
    combine_safari_htmls_data() 