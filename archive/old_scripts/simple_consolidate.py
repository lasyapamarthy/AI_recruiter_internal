#!/usr/bin/env python3
"""
Simple script to consolidate all HTML files from three directories
without any filtering - just copy everything.
"""
import os
import shutil
import pathlib

def main():
    """Main function to consolidate HTML files without filtering."""
    
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
    processed_filenames = set()  # To avoid duplicates
    
    # Copy all HTML files to consolidated directory
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
            
            # Check for duplicates based on filename
            if new_filename not in processed_filenames:
                processed_filenames.add(new_filename)
                
                # Copy file
                shutil.copy2(html_file, target_path)
                copied_files += 1
                
                if copied_files % 100 == 0:
                    print(f"  Copied {copied_files} files...")
            else:
                print(f"  Skipping duplicate: {new_filename}")
    
    print(f"\nConsolidation Complete:")
    print(f"Total files found: {total_files}")
    print(f"Unique files copied: {copied_files}")
    
    # Final summary
    remaining_files = list(pathlib.Path(target_dir).glob("*.html"))
    print(f"Total files in consolidated directory: {len(remaining_files)}")
    
    # Show breakdown by source directory
    print(f"\nBreakdown by source directory:")
    for source_dir in source_directories:
        source_name = pathlib.Path(source_dir).name
        source_files = [f for f in remaining_files if f.name.startswith(f"{source_name}_")]
        print(f"  {source_name}: {len(source_files)} files")
    
    # Check a few file sizes to understand what we're working with
    print(f"\nSample file sizes:")
    for i, file_path in enumerate(remaining_files[:5]):
        size = os.path.getsize(file_path)
        print(f"  {file_path.name}: {size:,} bytes")

if __name__ == "__main__":
    main() 