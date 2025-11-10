#!/usr/bin/env python3
import pandas as pd
import os

# Path to the CSV file
CSV_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin_jobs_emil.csv"
OUTPUT_FILE = "/Users/emilpalikot/Research/AI-Recruiter/linkedin_urls.txt"

def main():
    try:
        # Read the CSV file with different encodings to handle special characters
        try:
            df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(CSV_FILE_PATH, encoding='latin-1')
            except UnicodeDecodeError:
                df = pd.read_csv(CSV_FILE_PATH, encoding='cp1252')
        
        # Check if 'Linkedin' column exists
        if 'Linkedin' not in df.columns:
            print(f"CSV file does not contain a 'Linkedin' column. Available columns: {df.columns.tolist()}")
            return
        
        # Filter out rows with missing LinkedIn URLs
        df = df[df['Linkedin'].notna()]
        
        # Filter out any invalid URLs
        linkedin_urls = [url for url in df['Linkedin'] if isinstance(url, str) and "linkedin.com" in url]
        
        # Save to file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(linkedin_urls))
        
        print(f"Successfully extracted {len(linkedin_urls)} LinkedIn URLs to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 