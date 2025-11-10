#!/usr/bin/env python3
"""
Script to:
1. Consolidate all HTML files from three directories into one
2. Filter out only obvious auth pages and completely empty files
3. Keep most files for parsing (let the parser handle experience detection)
"""
import os
import shutil
import pathlib
from bs4 import BeautifulSoup
import re

def is_auth_or_empty_page(html_file_path):
    """Check if an HTML file is an auth page or completely empty."""
    try:
        with open(html_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        
        # Check file size - very small files are likely empty or auth pages
        if len(html) < 1000:
            return True
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for obvious auth indicators
        auth_indicators = [
            'sign in to linkedin',
            'join linkedin',
            'authwall',
            'authentication-outlet',
            'sign in to view',
            'join to view',
            'please sign in',
            'login required'
        ]
        
        html_lower = html.lower()
        for indicator in auth_indicators:
            if indicator in html_lower:
                return True
        
        # Check title for auth indicators
        title = soup.find('title')
        if title:
            title_text = title.get_text().lower()
            if any(indicator in title_text for indicator in ['sign in', 'login', 'join linkedin']):
                return True
        
        # Check if page has very little content (likely auth page)
        body = soup.find('body')
        if body:
            text_content = body.get_text(strip=True)
            if len(text_content) < 500:  # Very little content
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking {html_file_path}: {e}")
        return True  # If we can't read it, consider it problematic

def main():
    """Main function to consolidate and lightly filter HTML files."""
    
    # Define source directories
    source_directories = [
        "data/linkedin/output/collected_htmls",
        "data/linkedin/output/htmls",
        "data/linkedin/output/safari_htmls"
    ]
    
    # Define target directory
    target_dir = "data/linkedin/output/consolidated_htmls"
    
    # Remove existing consolidated directory and recreate
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"Consolidating HTML files into {target_dir}")
    
    total_files = 0
    copied_files = 0
    auth_files_removed = 0
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
                
                # Copy file first
                shutil.copy2(html_file, target_path)
                copied_files += 1
                
                if copied_files % 100 == 0:
                    print(f"  Copied {copied_files} files...")
    
    print(f"\nStep 1 Complete:")
    print(f"Total files found: {total_files}")
    print(f"Unique files copied: {copied_files}")
    
    # Step 2: Remove only obvious auth pages and empty files
    print(f"\nStep 2: Removing only obvious auth pages and empty files...")
    
    consolidated_files = list(pathlib.Path(target_dir).glob("*.html"))
    files_to_remove = []
    
    for i, html_file in enumerate(consolidated_files, 1):
        if i % 50 == 0:
            print(f"  Checking {i}/{len(consolidated_files)}: {html_file.name}")
        
        if is_auth_or_empty_page(html_file):
            files_to_remove.append(html_file)
            auth_files_removed += 1
    
    # Remove auth/empty files
    print(f"\nRemoving {len(files_to_remove)} auth/empty files...")
    for file_to_remove in files_to_remove:
        os.remove(file_to_remove)
    
    print(f"\nStep 2 Complete:")
    print(f"Auth/empty files removed: {auth_files_removed}")
    
    # Final summary
    remaining_files = list(pathlib.Path(target_dir).glob("*.html"))
    print(f"\nFinal Summary:")
    print(f"Total files in consolidated directory: {len(remaining_files)}")
    print(f"Files kept for parsing: {len(remaining_files)}")
    print(f"Ready for parsing with parse_consolidated_htmls.py")
    
    # Show breakdown by source directory
    print(f"\nBreakdown by source directory:")
    for source_dir in source_directories:
        source_name = pathlib.Path(source_dir).name
        source_files = [f for f in remaining_files if f.name.startswith(f"{source_name}_")]
        print(f"  {source_name}: {len(source_files)} files")

if __name__ == "__main__":
    main() 