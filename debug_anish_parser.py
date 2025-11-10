#!/usr/bin/env python3
"""Debug script to understand why the Anish Peshwe profile isn't being parsed correctly."""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

def debug_anish_profile():
    # Try different possible locations
    file_paths = [
        Path("data/linkedin/urls_528/Anish Peshwe _ LinkedIn.html"),
        Path("data/linkedin/manual_html_v1/Anish Peshwe _ LinkedIn.html"),
        Path("data/linkedin/htmls_1/anish-peshwe-89a562222.html")
    ]
    
    valid_file = None
    for path in file_paths:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "Error: Could not retrieve page content" not in content and len(content) > 1000:
                valid_file = path
                break
    
    if not valid_file:
        print("Could not find a valid Anish Peshwe profile file")
        return
    
    content = valid_file.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(content, "html.parser")
    
    print("=== DEBUGGING ANISH PESHWE PROFILE ===")
    print(f"File: {valid_file}")
    print(f"File size: {len(content)} characters")
    
    # Check for profile meta tags
    print("\n1. Checking for profile meta tags:")
    first_name = soup.find("meta", attrs={"property": "profile:first_name"})
    last_name = soup.find("meta", attrs={"property": "profile:last_name"})
    print(f"   profile:first_name: {'Found: ' + first_name.get('content', 'No content') if first_name else 'NOT FOUND'}")
    print(f"   profile:last_name: {'Found: ' + last_name.get('content', 'No content') if last_name else 'NOT FOUND'}")
    
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
    
    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            if "@type" in data and data["@type"] == "Person":
                print(f"\n   Found Person data in JSON-LD script {i}:")
                print(f"   Name: {data.get('name', 'Not found')}")
                print(f"   Works For: {data.get('worksFor', 'Not found')}")
        except:
            pass
    
    # Look for May 2025 specifically
    print("\n4. Searching for 'May 2025' in content:")
    may_2025_indices = [m.start() for m in re.finditer(r'May\s+2025', content, re.IGNORECASE)]
    print(f"   Found 'May 2025' {len(may_2025_indices)} times")
    if may_2025_indices:
        # Show context around first occurrence
        first_idx = may_2025_indices[0]
        context_start = max(0, first_idx - 200)
        context_end = min(len(content), first_idx + 200)
        print(f"   Context around first occurrence: ...{content[context_start:context_end]}...")
    
    # Search for any job dates
    print("\n5. Searching for job-related date patterns:")
    date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
    matches = re.findall(date_pattern, content)
    if matches:
        print(f"   Found {len(matches)} date patterns")
        print(f"   First few dates: {matches[:10]}")
    
    # Look for embedded data with Anish
    print("\n6. Looking for embedded profile data:")
    scripts = soup.find_all("script")
    for i, script in enumerate(scripts):
        if script.string and "Anish" in script.string and ("position" in script.string.lower() or "experience" in script.string.lower()):
            print(f"\n   Found potential profile data in script {i}:")
            # Find the context around "Anish"
            anish_idx = script.string.find("Anish")
            sample_start = max(0, anish_idx - 300)
            sample_end = min(len(script.string), anish_idx + 300)
            sample = script.string[sample_start:sample_end]
            print(f"   Sample: ...{sample}...")
            break
    
    # Check page type
    print("\n7. Checking page type:")
    title = soup.find("title")
    if title:
        print(f"   Title tag: {title.text}")
    
    # Look for data in code blocks or embedded JSON
    print("\n8. Looking for embedded JSON data:")
    code_blocks = soup.find_all("code")
    for i, code in enumerate(code_blocks[:5]):  # Check first 5 code blocks
        if "Anish" in code.text or "2025" in code.text:
            print(f"   Found relevant data in code block {i}: {code.text[:200]}...")

if __name__ == "__main__":
    debug_anish_profile() 