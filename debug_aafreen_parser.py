#!/usr/bin/env python3
"""Debug script to understand why the Aafreen profile isn't being parsed."""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

def debug_aafreen_profile():
    # Read the Aafreen profile
    file_path = Path("data/linkedin/urls_528/Aafreen 🌻 ✨ _ LinkedIn.html")
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(content, "html.parser")
    
    print("=== DEBUGGING AAFREEN PROFILE ===")
    print(f"File: {file_path}")
    print(f"File size: {len(content)} characters")
    
    # Check for profile meta tags
    print("\n1. Checking for profile meta tags:")
    first_name = soup.find("meta", attrs={"property": "profile:first_name"})
    last_name = soup.find("meta", attrs={"property": "profile:last_name"})
    print(f"   profile:first_name: {'Found' if first_name else 'NOT FOUND'}")
    print(f"   profile:last_name: {'Found' if last_name else 'NOT FOUND'}")
    
    # Check for og:title
    print("\n2. Checking for og:title:")
    og_title = soup.find("meta", property="og:title")
    if og_title:
        print(f"   og:title content: {og_title.get('content', 'No content')}")
    else:
        print("   og:title: NOT FOUND")
    
    # Check for JSON-LD
    print("\n3. Checking for JSON-LD scripts:")
    json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
    print(f"   Found {len(json_ld_scripts)} JSON-LD scripts")
    
    # Check for auth wall
    print("\n4. Checking for auth wall:")
    page_key = soup.find("meta", attrs={"name": "pageKey"})
    if page_key:
        content = page_key.get("content", "")
        print(f"   pageKey content: {content}")
        print(f"   Is auth wall: {'auth_wall' in content}")
    else:
        print("   No pageKey meta tag found")
    
    # Look for embedded data
    print("\n5. Looking for embedded data patterns:")
    
    # Search for profile data in scripts
    scripts = soup.find_all("script")
    for i, script in enumerate(scripts):
        if script.string and "firstName" in script.string and "Aafreen" in script.string:
            print(f"\n   Found potential profile data in script {i}:")
            # Extract a sample of the content
            sample = script.string[:500] + "..." if len(script.string) > 500 else script.string
            print(f"   Sample: {sample}")
            break
    
    # Look for data attributes or other patterns
    print("\n6. Looking for alternative data locations:")
    
    # Check for data in window variable assignments
    for script in scripts:
        if script.string and "window." in script.string:
            lines = script.string.split('\n')
            for line in lines:
                if "Aafreen" in line or "experience" in line.lower():
                    print(f"   Found in window assignment: {line[:200]}...")
                    break
    
    # Look for the actual job data
    print("\n7. Searching for job-related content:")
    
    # Search for date patterns that might indicate jobs
    date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
    matches = re.findall(date_pattern, content)
    if matches:
        print(f"   Found {len(matches)} date patterns")
        print(f"   First few dates: {matches[:5]}")
    
    # Search for "2025" specifically
    print("\n8. Searching for '2025' in content:")
    indices = [m.start() for m in re.finditer('2025', content)]
    print(f"   Found '2025' {len(indices)} times")
    if indices:
        # Show context around first occurrence
        first_idx = indices[0]
        context_start = max(0, first_idx - 100)
        context_end = min(len(content), first_idx + 100)
        print(f"   Context around first occurrence: ...{content[context_start:context_end]}...")

if __name__ == "__main__":
    debug_aafreen_profile() 