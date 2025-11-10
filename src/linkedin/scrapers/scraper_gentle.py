#!/usr/bin/env python3
"""
scraper_gentle.py - Gentle LinkedIn scraper for logged-in sessions
- Uses regular browser windows (not private/incognito)
- Processes one profile at a time
- 30+ second delays between profiles
- Designed to look like human browsing
"""

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
from tqdm import tqdm

# ───────────────────────────── GENTLE CONSTANTS ────────────────────────── #
DELAY_BETWEEN_PROFILES = (30, 45)    # 30-45 seconds between profiles
COFFEE_EVERY_N = 50                  # Take a break every 50 profiles
COFFEE_RANGE = (300, 600)            # 5-10 minute breaks
PAGE_LOAD_WAIT = 10                  # Wait 10 seconds after page loads
SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
SAFARI_SCRIPT = SCRIPT_DIR / "save_gentle_safari.applescript"
CHROME_SCRIPT = SCRIPT_DIR / "save_gentle_chrome.applescript"
FIREFOX_SCRIPT = SCRIPT_DIR / "save_gentle_firefox.applescript"
DEFAULT_BROWSER = "firefox"          # Use Firefox by default
# ─────────────────────────────────────────────────────────────────────────────── #


def load_urls(path: Path) -> list[str]:
    txt = path.read_text(encoding="utf-8").splitlines()
    urls = [u.strip() for u in txt if u.strip()]
    urls = [u if u.startswith("http") else f"https://{u}" for u in urls]
    urls = [u.replace("pl.linkedin.com/", "linkedin.com/").replace("/mwlite/", "/") for u in urls]
    urls = list(dict.fromkeys(urls))
    # Reverse the list to process from last to first
    urls.reverse()
    return urls


def filename_from_url(url: str) -> str:
    stem = url.rstrip("/").split("/")[-1] or "profile"
    return stem.split("?")[0] + ".html"


def analyze_html_content(html_path: Path) -> dict:
    """Analyze content to determine if it's a valid profile (works with both HTML and text)"""
    if not html_path.exists():
        return {"status": "file_not_found", "details": "File was not created"}
    
    try:
        text = html_path.read_text(errors="ignore")
        file_size = len(text)
        
        if file_size < 500:
            return {"status": "empty_file", "details": f"File size: {file_size} bytes"}
        
        # Check for error messages
        if text.startswith("Error:"):
            return {"status": "error", "details": text[:200]}
        
        # For Firefox text content, look for profile indicators
        text_lower = text.lower()
        
        # Check for auth/login indicators
        if "sign in" in text_lower and "join now" in text_lower:
            return {"status": "auth_wall", "details": "Login page detected"}
        
        # Look for profile indicators in text
        profile_indicators = [
            "experience" in text_lower,
            "education" in text_lower,
            any(job_title in text_lower for job_title in ["manager", "engineer", "developer", "director", "analyst", "consultant"]),
            "degree connection" in text_lower,
            any(company_indicator in text_lower for company_indicator in ["at ", "company", "corporation", "inc", "llc", "ltd"]),
        ]
        
        # Check if it looks like a profile
        if sum(profile_indicators) >= 2:
            # Try to find recent experience
            experience_hint = ""
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if any(keyword in line.lower() for keyword in ["experience", "current", "present", " at "]):
                    experience_hint = f"Found: {line.strip()[:100]}"
                    break
            
            return {"status": "ok", "details": f"Profile captured. {experience_hint}"}
        
        # For HTML content (Safari/Chrome), check HTML structure
        if "<html" in text or "<!DOCTYPE" in text:
            soup = BeautifulSoup(text, "html.parser")
            
            # Check for auth wall
            key = soup.find("meta", attrs={"name": "pageKey"})
            if key and "auth_wall" in key.get("content", ""):
                return {"status": "auth_wall", "details": "Auth wall detected (not logged in?)"}
            
            # Check for profile indicators
            indicators = {
                "profile:first_name": soup.find("meta", attrs={"property": "profile:first_name"}),
                "og:title": soup.find("meta", attrs={"property": "og:title"}),
            }
            
            if any(indicators.values()):
                return {"status": "ok", "details": "HTML profile captured successfully"}
        
        return {"status": "unknown_page", "details": f"Content type unclear (size: {file_size})"}
            
    except Exception as e:
        return {"status": "parse_error", "details": str(e)[:200]}


def write_log(log_path: Path, row: dict):
    """Write a single row to the log file"""
    first = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ts", "url", "file", "status", "details", "browser"])
        if first:
            w.writeheader()
        w.writerow(row)


def call_applescript(script_path: Path, url: str, output_file: Path) -> tuple[bool, str]:
    """Call AppleScript for a single URL"""
    cmd = ["osascript", str(script_path), url, str(output_file)]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=60)
        return True, ""
    except subprocess.CalledProcessError as e:
        error_msg = e.output[:500] if e.output else "Unknown error"
        return False, error_msg
    except subprocess.TimeoutExpired:
        return False, "Timeout after 60 seconds"


def create_session_report(out_dir: Path, processed_stats: dict, start_time: float):
    """Create a summary report of the scraping session"""
    report_path = out_dir / f"gentle_scraping_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    duration = time.time() - start_time
    total = sum(processed_stats.values())
    
    with report_path.open("w") as f:
        f.write("Gentle LinkedIn Scraping Session Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Duration: {duration/60:.1f} minutes\n")
        f.write(f"Total URLs processed: {total}\n")
        f.write(f"Average time per profile: {duration/max(total, 1):.1f} seconds\n\n")
        
        for status, count in sorted(processed_stats.items()):
            f.write(f"{status}: {count}\n")
        
        f.write(f"\nSuccess rate: {processed_stats.get('ok', 0) / max(total, 1) * 100:.1f}%\n")


def main(url_file: Path, out_dir: Path, log_csv: Path, browser: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if script exists
    if browser == "safari":
        script_path = SAFARI_SCRIPT
    elif browser == "chrome":
        script_path = CHROME_SCRIPT
    else:  # firefox
        script_path = FIREFOX_SCRIPT
    
    if not script_path.exists():
        print(f"⚠️  Warning: {script_path} not found. Creating it now...")
    
    urls = load_urls(url_file)
    print(f"🌱 Gentle LinkedIn Scraper")
    print(f"📋 Loaded {len(urls)} unique URLs")
    print(f"🔄 Processing in REVERSE order (last to first)")
    print(f"🌐 Using {browser.title()} (logged-in session)")
    print(f"⏱️  Processing one profile every 30-45 seconds")
    print(f"☕ Coffee breaks every {COFFEE_EVERY_N} profiles\n")
    
    processed_stats = {"ok": 0, "auth_wall": 0, "empty_file": 0, "unknown_page": 0, "error": 0}
    start_time = time.time()
    
    with tqdm(total=len(urls), desc="Gently scraping profiles") as pbar:
        for idx, url in enumerate(urls):
            # Take coffee break if needed
            if idx > 0 and idx % COFFEE_EVERY_N == 0:
                pause = random.uniform(*COFFEE_RANGE)
                tqdm.write(f"\n☕ Coffee break #{idx//COFFEE_EVERY_N} - Resting for {pause/60:.1f} minutes...")
                time.sleep(pause)
            
            # Process single URL
            file_path = out_dir / filename_from_url(url)
            original_position = len(urls) - idx  # Calculate original position (counting from end)
            tqdm.write(f"\n🔍 Profile {idx+1}/{len(urls)} (original position: {original_position}): {url.split('/')[-1]}")
            
            # Skip if already processed successfully
            if file_path.exists() and not file_path.name.endswith("_AUTHWALL"):
                analysis = analyze_html_content(file_path)
                if analysis["status"] == "ok":
                    tqdm.write(f"   ✓ Already captured successfully, skipping...")
                    processed_stats["ok"] += 1
                    pbar.update(1)
                    continue
            
            # Call AppleScript
            script_ok, error_msg = call_applescript(script_path, url, file_path)
            
            # Wait for file to be written
            time.sleep(2)
            
            # Analyze result
            analysis = analyze_html_content(file_path)
            status = analysis["status"]
            
            # Handle different statuses
            if status == "ok":
                tqdm.write(f"   ✅ Profile saved successfully!")
                processed_stats["ok"] += 1
            elif status == "auth_wall":
                # Unexpected if logged in
                new_path = file_path.with_stem(file_path.stem + "_AUTHWALL")
                if file_path.exists():
                    file_path.rename(new_path)
                tqdm.write(f"   🔒 Auth wall encountered (check if still logged in)")
                processed_stats["auth_wall"] += 1
            elif status in ["empty_file", "file_not_found"]:
                tqdm.write(f"   ❌ Failed to capture: {analysis['details']}")
                if error_msg:
                    tqdm.write(f"      Error: {error_msg}")
                processed_stats["error"] += 1
            else:
                tqdm.write(f"   ❓ {status}: {analysis['details']}")
                processed_stats[status] = processed_stats.get(status, 0) + 1
            
            # Log the result
            write_log(log_csv, {
                "ts": int(time.time()),
                "url": url,
                "file": file_path.name,
                "status": status,
                "details": analysis["details"],
                "browser": browser,
            })
            
            pbar.update(1)
            
            # Wait before next profile (except for last one)
            if idx < len(urls) - 1:
                delay = random.uniform(*DELAY_BETWEEN_PROFILES)
                tqdm.write(f"   💤 Waiting {delay:.0f}s before next profile...")
                time.sleep(delay)
    
    # Final report
    print("\n" + "="*50)
    print("GENTLE SCRAPING COMPLETE")
    print("="*50)
    create_session_report(out_dir, processed_stats, start_time)
    print(f"Log saved to: {log_csv}")
    print(f"Report saved to: {out_dir}/gentle_scraping_report_*.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gentle LinkedIn scraper for logged-in sessions")
    ap.add_argument("url_file", type=Path, help="TXT file with LinkedIn URLs")
    ap.add_argument("output_dir", type=Path, help="Directory to save HTML files")
    ap.add_argument(
        "--log",
        type=Path,
        default=Path("linkedin_gentle_scraper.csv"),
        help="CSV log file (default: linkedin_gentle_scraper.csv)",
    )
    ap.add_argument(
        "--browser",
        choices=["safari", "chrome", "firefox"],
        default=DEFAULT_BROWSER,
        help=f"Browser to use (default: {DEFAULT_BROWSER})",
    )
    args = ap.parse_args()
    
    main(args.url_file, args.output_dir, args.log, args.browser) 