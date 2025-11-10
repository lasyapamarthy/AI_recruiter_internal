#!/usr/bin/env python3
"""
Extract the current (latest) professional experience from a batch of
locally saved LinkedIn HTML files.

The script
----------
1. Skips "auth-wall" / broken pages.
2. Detects real public profiles via `profile:first_name` meta or JSON-LD.
3. Pulls the latest job (title, company, start date) from JSON-LD, or
   falls back to the `og:title` meta tag.
4. Captures the canonical LinkedIn URL.
5. Writes a CSV:

   file, linkedin_url, name, job_title, company, start_date

Usage
-----
python linkedin_latest_experience.py /path/to/html_folder \
       --out my_experience_dump.csv
"""

import argparse
import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def is_plain_text_profile(content: str) -> bool:
    """Check if the content is a plain text LinkedIn profile (from Firefox text mode)."""
    # Look for patterns that indicate plain text profile
    content_lower = content.lower()
    
    # Must NOT have HTML tags
    if "<html" in content_lower or "<!doctype" in content_lower:
        return False
    
    # Check for plain text profile indicators
    indicators = [
        "degree connection" in content_lower,
        "connections" in content_lower and not content_lower.startswith("error:"),
        any(section in content_lower for section in ["education", "experience", "skills", "licenses & certifications"]),
        bool(re.search(r'\d+ followers', content_lower)),
    ]
    
    return sum(indicators) >= 2


def extract_from_plain_text(content: str, file_path: Path) -> dict | None:
    """Extract profile data from plain text LinkedIn profile."""
    lines = content.strip().split('\n')
    
    # Initialize fields
    name = ""
    job_title = ""
    company = ""
    location = ""
    start_date = ""
    
    # Try to find name - it usually appears early and often
    # Look for repeated names (name appears multiple times in these files)
    name_candidates = {}
    for i, line in enumerate(lines[:50]):  # Check first 50 lines
        line = line.strip()
        # Skip common non-name lines
        if (not line or len(line) < 3 or len(line) > 50 or 
            any(skip in line.lower() for skip in ['notifications', 'home', 'network', 'jobs', 'messaging', 'activity', 'nav'])):
            continue
        
        # Look for patterns like "Name Name" repeated
        if line in name_candidates:
            name_candidates[line] += 1
        else:
            # Check if it could be a name (2-4 words, title case)
            words = line.split()
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                name_candidates[line] = 1
    
    # Get the most repeated name
    if name_candidates:
        name = max(name_candidates.items(), key=lambda x: x[1])[0]
    
    # First, try to find current job (with "Present" or "current")
    current_job_found = False
    for i, line in enumerate(lines):
        # Look for date patterns with Present/current
        if re.search(r'(Present|present|Current|current)', line):
            # Check if this line contains a date range
            date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[-–]\s*(Present|present|Current|current)', line)
            if not date_match:
                date_match = re.search(r'\d{4}\s*[-–]\s*(Present|present|Current|current)', line)
            if not date_match:
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*to\s*(Present|present|Current|current)', line)
            
            if date_match:
                # Extract start date
                start_date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', line)
                if start_date_match:
                    start_date = start_date_match.group(0)
                else:
                    year_match = re.search(r'(\d{4})', line)
                    if year_match:
                        start_date = year_match.group(0)
                
                # Look for company name in the same line or nearby lines
                # Companies often appear doubled (e.g., "Gray AnchorGray Anchor")
                # Check current line first
                line_before_date = line[:date_match.start()].strip()
                
                # Pattern for doubled company names
                doubled_pattern = re.findall(r'([A-Z][^A-Z]*(?:[A-Z][^A-Z]*)*)', line_before_date)
                if len(doubled_pattern) >= 2:
                    # Check if first half equals second half (doubled company name)
                    half_len = len(doubled_pattern) // 2
                    first_half = ''.join(doubled_pattern[:half_len])
                    second_half = ''.join(doubled_pattern[half_len:half_len*2])
                    if first_half == second_half:
                        company = first_half
                        current_job_found = True
                
                # If not found in current line, check previous lines
                if not company and i > 0:
                    for j in range(max(0, i-5), i):
                        prev_line = lines[j].strip()
                        if prev_line and not any(skip in prev_line.lower() for skip in ['degree connection', 'contact info', 'followers']):
                            # Check for doubled company pattern
                            if len(prev_line) < 100:
                                words = prev_line.split()
                                if len(words) >= 2:
                                    # Simple check: if line has repeated text
                                    half = len(prev_line) // 2
                                    if prev_line[:half] == prev_line[half:half*2]:
                                        company = prev_line[:half]
                                        current_job_found = True
                                        break
                
                if current_job_found:
                    break
    
    # If no current job found, fall back to original logic
    if not current_job_found:
        # Find job title - usually appears after name and before location
        job_title_found = False
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Common job title keywords
            job_keywords = [
                "engineer", "developer", "manager", "analyst", "designer", "consultant",
                "director", "lead", "architect", "specialist", "coordinator", "executive",
                "scientist", "researcher", "intern", "associate", "administrator"
            ]
            
            if any(keyword in line.lower() for keyword in job_keywords):
                # Check it's not part of education or other sections
                if not any(section in line.lower() for section in ['degree', 'bachelor', 'master', 'university', 'college']):
                    # Also check it's not too long (avoid descriptions)
                    if len(line) < 100 and "at " not in line.lower():
                        job_title = line
                        job_title_found = True
                        
                        # Try to find company and dates in the next few lines
                        for j in range(i+1, min(i+10, len(lines))):
                            next_line = lines[j].strip()
                            if next_line and len(next_line) < 150:
                                # Check for date patterns
                                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', next_line)
                                if date_match and not start_date:
                                    start_date = date_match.group(0)
                                
                                # Check for location pattern (City, State, Country)
                                elif re.search(r'[A-Za-z]+,\s*[A-Za-z]+', next_line):
                                    location = next_line
                                    if job_title_found and not company:
                                        # Previous non-date, non-location line might be company
                                        for k in range(i+1, j):
                                            candidate = lines[k].strip()
                                            if candidate and not re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', candidate):
                                                company = candidate
                                                break
                                    break
                                # Otherwise might be company
                                elif not any(skip in next_line.lower() for skip in ['degree connection', 'contact info', 'full-time', 'part-time', 'contract', 'freelance']):
                                    if not company and not re.search(r'\d{4}', next_line):  # Avoid date lines
                                        company = next_line
                        break
        
        # Try to extract from "at Company" patterns with dates
        if not company or not start_date:
            for i, line in enumerate(lines):
                if " at " in line:
                    parts = line.split(" at ")
                    if len(parts) == 2:
                        potential_title = parts[0].strip()
                        potential_company = parts[1].strip()
                        if len(potential_company) < 50:  # Reasonable company name length
                            if not job_title:
                                job_title = potential_title
                            if not company:
                                company = potential_company
                            
                            # Look for dates in surrounding lines
                            if not start_date:
                                for j in range(max(0, i-3), min(i+3, len(lines))):
                                    date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', lines[j])
                                    if date_match:
                                        start_date = date_match.group(0)
                                        break
                            break
    
    # Try to find job title from the profile summary/headline if not found
    if not job_title and name:
        # Look for lines after the name that might be the headline
        name_index = -1
        for i, line in enumerate(lines):
            if line.strip() == name:
                name_index = i
                break
        
        if name_index >= 0:
            # Check next few lines for potential job title
            for j in range(name_index + 1, min(name_index + 5, len(lines))):
                candidate = lines[j].strip()
                if candidate and len(candidate) < 100:
                    # Skip connection info and location lines
                    if not any(skip in candidate.lower() for skip in ['degree connection', 'connections', 'contact info']) and not re.search(r'[A-Za-z]+,\s*[A-Za-z]+', candidate):
                        job_title = candidate
                        break
    
    # If we found at least a name or job title, return the data
    if name or job_title:
        # Reconstruct LinkedIn URL from filename
        # Remove .html extension and any leading dashes
        profile_id = file_path.stem.lstrip('-')
        linkedin_url = f"https://www.linkedin.com/in/{profile_id}/" if profile_id else ""
        
        return {
            "file": file_path.name,
            "linkedin_url": linkedin_url,
            "name": name,
            "job_title": job_title,
            "company": company,
            "start_date": start_date,
        }
    
    return None


def is_profile(soup: BeautifulSoup) -> bool:
    """Return True when the page looks like a real public profile."""
    page_key = soup.find("meta", attrs={"name": "pageKey"})
    if page_key and "auth_wall" in page_key.get("content", ""):
        return False  # sign-up / auth-wall splash

    # Fast positive signals
    if soup.find("meta", attrs={"property": "profile:first_name"}):
        return True

    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue

        # Handle both a single dict and an @graph list
        graphs = (
            data.get("@graph", []) if isinstance(data, dict) else []
        ) + ([data] if isinstance(data, dict) else [])

        if any(
            isinstance(node, dict) and node.get("@type") == "Person"
            for node in graphs
        ):
            return True
    return False


def extract_from_jsonld(person_node: dict) -> tuple[str, str, str]:
    """Return (job_title, company, start_date) from a Person JSON-LD node."""
    title = company = start = ""
    works_for = person_node.get("worksFor", [])
    if isinstance(works_for, dict):
        works_for = [works_for]  # normalize to list

    if works_for:
        latest = works_for[0]  # first item = current employer
        company = latest.get("name", "")
        role = latest.get("member", {}) or latest.get("roleName", {})
        if isinstance(role, dict):
            title = role.get("description") or role.get("roleName", "")
            start = role.get("startDate", "")
        else:  # plain string
            title = role
    return title.strip(), company.strip(), start.strip()


def extract_latest_experience(html_path: Path) -> dict | None:
    """
    Parse one file. Return dict with extracted fields or None if not a profile.
    Now handles both HTML and plain text formats.
    """
    content = html_path.read_text(encoding="utf-8", errors="ignore")
    
    # Check if it's plain text format
    if is_plain_text_profile(content):
        return extract_from_plain_text(content, html_path)
    
    # Otherwise, parse as HTML
    soup = BeautifulSoup(content, "html.parser")

    if not is_profile(soup):
        return None

    # ---------- NAME ----------
    first = soup.find("meta", attrs={"property": "profile:first_name"})
    last = soup.find("meta", attrs={"property": "profile:last_name"})
    name = " ".join(
        tag["content"] for tag in (first, last) if tag and tag.get("content")
    ).strip()

    # ---------- URL ----------
    url_tag = soup.find("meta", property="og:url") or soup.find(
        "link", rel="canonical"
    )
    linkedin_url = (
        url_tag.get("content", "").strip() if url_tag else ""
    )

    # ---------- EXPERIENCE ----------
    job_title = company = start_date = ""

    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue

        graphs = (
            data.get("@graph", []) if isinstance(data, dict) else []
        ) + ([data] if isinstance(data, dict) else [])

        for node in graphs:
            if isinstance(node, dict) and node.get("@type") == "Person":
                job_title, company, start_date = extract_from_jsonld(node)
                break
        if job_title or company:
            break

    # Fallback:  "Name – Title – Company | LinkedIn" in og:title
    if not job_title or not company:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            parts = og["content"].split(" - ")
            if len(parts) >= 3:
                job_title = job_title or parts[1].strip()
                company = company or parts[2].split("|")[0].strip()
                if not name:
                    name = parts[0].strip()

    return {
        "file": html_path.name,
        "linkedin_url": linkedin_url,
        "name": name,
        "job_title": job_title,
        "company": company,
        "start_date": start_date,
    }


# --------------------------------------------------------------------------- #
# Main driver                                                                 #
# --------------------------------------------------------------------------- #
def run(indir: Path, outfile: Path) -> None:
    # Filter out AUTHWALL files
    html_files = [
        html_path for html_path in sorted(indir.rglob("*.html"))
        if "_AUTHWALL" not in html_path.name
    ]
    
    print(f"Found {len(list(indir.rglob('*.html')))} total HTML files")
    print(f"Processing {len(html_files)} files (filtered out AUTHWALL files)")
    
    # Process files and track format types
    html_count = 0
    text_count = 0
    rows = []
    
    for html_path in html_files:
        rec = extract_latest_experience(html_path)
        if rec:
            rows.append(rec)
            # Check format type for reporting
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            if is_plain_text_profile(content):
                text_count += 1
            else:
                html_count += 1
    
    print(f"Found {html_count} HTML profiles and {text_count} plain text profiles")

    if not rows:
        print("No valid LinkedIn profiles found.")
        return

    with outfile.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "file",
                "linkedin_url",
                "name",
                "job_title",
                "company",
                "start_date",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Saved {len(rows)} profiles to {outfile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Extract the latest professional experience from local "
            "LinkedIn profile HTML files."
        )
    )
    parser.add_argument(
        "indir",
        type=Path,
        help="Directory containing the *.html files (searched recursively)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("linkedin_latest_experience.csv"),
        help="Output CSV path (default: linkedin_latest_experience.csv)",
    )
    args = parser.parse_args()
    run(args.indir, args.out)
