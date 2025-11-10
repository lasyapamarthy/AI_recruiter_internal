#!/usr/bin/env python3
"""
Script to:
1. Consolidate all HTML files from three directories into one
2. Filter out files without experience data
3. Prepare for parsing
"""
import os
import shutil
import pathlib
from bs4 import BeautifulSoup
import re

def has_experience_data(html_file_path):
    """Check if an HTML file contains experience data."""
    try:
        with open(html_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check if this is actually a LinkedIn profile page
        title = soup.find('title')
        if not title or 'LinkedIn' not in title.get_text():
            return False
        
        # Check for auth wall or sign-in pages
        if 'sign in' in html.lower() or 'authwall' in html.lower():
            return False
        
        # Look for experience section
        experience_section = soup.find('section', {'data-section': 'experience'})
        if experience_section:
            experience_items = experience_section.find_all('li', class_='experience-item')
            if experience_items:
                return True
        
        # Check for JSON-LD data with work experience
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string or '{}')
                if isinstance(data, dict) and '@graph' in data:
                    data = data['@graph']
                if not isinstance(data, list):
                    data = [data]
                
                for obj in data:
                    if obj.get('@type') == 'Person':
                        works_for = obj.get('worksFor', [])
                        if works_for:
                            return True
            except:
                continue
        
        # Check meta description for job/company info
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')
            # Look for patterns like "Title at Company"
            if re.search(r'\w+\s+at\s+\w+', desc) or 'Experience:' in desc:
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking {html_file_path}: {e}")
        return False

def main():
    """Main function to consolidate and filter HTML files."""
    
    # Define source directories
    source_directories = [
        "data/linkedin/output/collected_htmls",
        "data/linkedin/output/htmls",
        "data/linkedin/output/safari_htmls"
    ]
    
    # Define target directory
    target_dir = "data/linkedin/output/consolidated_htmls"
    
    # Create target directory
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"Consolidating HTML files into {target_dir}")
    
    total_files = 0
    copied_files = 0
    files_with_experience = 0
    processed_urls = set()  # To avoid duplicates
    
    # Step 1: Copy all HTML files to consolidated directory
    for source_dir in source_directories:
        if not os.path.exists(source_dir):
            print(f"Directory does not exist: {source_dir}")
            continue
        
        html_files = list(pathlib.Path(source_dir).glob("*.html"))
        print(f"\nProcessing {len(html_files)} files from {source_dir}")
        
        for html_file in html_files:
            total_files += 1
            
            # Create unique filename to avoid conflicts
            source_name = pathlib.Path(source_dir).name
            new_filename = f"{source_name}_{html_file.name}"
            target_path = os.path.join(target_dir, new_filename)
            
            # Check for duplicates based on filename content
            if new_filename not in processed_urls:
                processed_urls.add(new_filename)
                
                # Copy file
                shutil.copy2(html_file, target_path)
                copied_files += 1
                
                if copied_files % 100 == 0:
                    print(f"  Copied {copied_files} files...")
    
    print(f"\nStep 1 Complete:")
    print(f"Total files found: {total_files}")
    print(f"Unique files copied: {copied_files}")
    
    # Step 2: Filter out files without experience data
    print(f"\nStep 2: Filtering files with experience data...")
    
    consolidated_files = list(pathlib.Path(target_dir).glob("*.html"))
    files_to_remove = []
    
    for i, html_file in enumerate(consolidated_files, 1):
        if i % 50 == 0:
            print(f"  Checking {i}/{len(consolidated_files)}: {html_file.name}")
        
        if has_experience_data(html_file):
            files_with_experience += 1
        else:
            files_to_remove.append(html_file)
    
    # Remove files without experience data
    print(f"\nRemoving {len(files_to_remove)} files without experience data...")
    for file_to_remove in files_to_remove:
        os.remove(file_to_remove)
    
    print(f"\nStep 2 Complete:")
    print(f"Files with experience data: {files_with_experience}")
    print(f"Files removed (no experience): {len(files_to_remove)}")
    
    # Final summary
    remaining_files = list(pathlib.Path(target_dir).glob("*.html"))
    print(f"\nFinal Summary:")
    print(f"Total files in consolidated directory: {len(remaining_files)}")
    print(f"All files should have experience data")
    print(f"Ready for parsing with linkedin_safari_parser.py")
    
    # Show breakdown by source directory
    print(f"\nBreakdown by source directory:")
    for source_dir in source_directories:
        source_name = pathlib.Path(source_dir).name
        source_files = [f for f in remaining_files if f.name.startswith(f"{source_name}_")]
        print(f"  {source_name}: {len(source_files)} files")

if __name__ == "__main__":
    main() 