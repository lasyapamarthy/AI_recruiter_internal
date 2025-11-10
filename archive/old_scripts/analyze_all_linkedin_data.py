#!/usr/bin/env python3
"""
Comprehensive analysis of all LinkedIn profile parsing results.
"""
import pandas as pd
import sys
from collections import Counter
import os

def analyze_all_linkedin_data():
    """Analyze all LinkedIn profile parsing results."""
    
    print("LinkedIn Profile Parsing - Comprehensive Analysis")
    print("=" * 60)
    
    # Load all available CSV files
    csv_files = {
        'Original (All directories)': 'linkedin_experiences_parsed.csv',
        'Enhanced (All directories)': 'linkedin_experiences_enhanced.csv', 
        'Safari HTML only': 'safari_htmls_experiences_parsed.csv',
        'Manual Collection only': 'manual_collection_experiences_parsed.csv'
    }
    
    results = {}
    
    for name, filename in csv_files.items():
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                results[name] = df
                print(f"✓ Loaded {name}: {len(df)} records")
            except Exception as e:
                print(f"✗ Failed to load {name}: {e}")
        else:
            print(f"✗ File not found: {filename}")
    
    if not results:
        print("No CSV files found to analyze!")
        return
    
    print("\n" + "=" * 60)
    
    # Analyze each dataset
    for name, df in results.items():
        print(f"\n{name.upper()} ANALYSIS:")
        print("-" * 40)
        
        total_profiles = len(df)
        successful_profiles = len(df[df['profile_empty'] == False])
        profiles_with_experience = len(df[df['experience_empty'] == False])
        
        print(f"Total profiles: {total_profiles}")
        print(f"Successful profiles: {successful_profiles} ({successful_profiles/total_profiles*100:.1f}%)")
        print(f"Profiles with experience: {profiles_with_experience} ({profiles_with_experience/total_profiles*100:.1f}%)")
        
        if 'source_directory' in df.columns:
            print(f"\nBreakdown by source directory:")
            source_breakdown = df.groupby('source_directory').agg({
                'profile_empty': lambda x: (x == False).sum(),
                'experience_empty': lambda x: (x == False).sum()
            }).rename(columns={'profile_empty': 'successful_profiles', 'experience_empty': 'with_experience'})
            
            for source, row in source_breakdown.iterrows():
                source_total = len(df[df['source_directory'] == source])
                print(f"  {source}: {source_total} total, {row['successful_profiles']} successful, {row['with_experience']} with experience")
        
        # Show top companies
        if profiles_with_experience > 0:
            companies = df[df['experience_empty'] == False]['company'].value_counts().head(10)
            if len(companies) > 0:
                print(f"\nTop 10 companies:")
                for company, count in companies.items():
                    if company and len(str(company).strip()) > 0:
                        print(f"  {company}: {count}")
        
        # Show sample successful extractions
        successful_samples = df[df['experience_empty'] == False].head(5)
        if len(successful_samples) > 0:
            print(f"\nSample successful extractions:")
            for _, row in successful_samples.iterrows():
                job_title = row.get('job_title', '')
                company = row.get('company', '')
                start_date = row.get('start_date', '')
                if job_title or company:
                    print(f"  {job_title} at {company} ({start_date})")
    
    # Compare datasets if we have multiple
    if len(results) > 1:
        print(f"\n{'COMPARISON SUMMARY':=^60}")
        
        comparison_data = []
        for name, df in results.items():
            total = len(df)
            with_exp = len(df[df['experience_empty'] == False])
            success_rate = with_exp/total*100 if total > 0 else 0
            
            comparison_data.append({
                'Dataset': name,
                'Total Profiles': total,
                'With Experience': with_exp,
                'Success Rate (%)': f"{success_rate:.1f}%"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        print(comparison_df.to_string(index=False))
    
    # Recommendations
    print(f"\n{'RECOMMENDATIONS':=^60}")
    
    if 'Safari HTML only' in results:
        safari_df = results['Safari HTML only']
        safari_success_rate = len(safari_df[safari_df['experience_empty'] == False]) / len(safari_df) * 100
        
        if safari_success_rate > 10:
            print("✓ Safari HTML files show good success rate for experience extraction")
            print("  Recommendation: Focus on collecting more Safari HTML files")
        else:
            print("⚠ Safari HTML files have low success rate")
    
    # Check for authwall issues
    if 'Safari HTML only' in results:
        safari_df = results['Safari HTML only']
        authwall_count = len(safari_df[safari_df['linkedin_url'].str.contains('/authwall', na=False)])
        if authwall_count > 0:
            print(f"⚠ Found {authwall_count} authwall pages in Safari HTML files")
            print("  Recommendation: Ensure you're logged in when collecting Safari HTML files")
    
    print(f"\n{'NEXT STEPS':=^60}")
    print("1. Focus on Safari HTML collection as it shows the best results")
    print("2. Ensure proper authentication when collecting profiles")
    print("3. Consider implementing additional fallback parsing methods")
    print("4. Filter out authwall and invalid pages before processing")

if __name__ == "__main__":
    analyze_all_linkedin_data() 