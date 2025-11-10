#!/usr/bin/env python3
"""
scraper_emil_improved.py - Improved LinkedIn profile scraper with better error handling
"""

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
from tqdm import tqdm

# ───────────────────────────── USER-TUNABLE CONSTANTS ────────────────────────── #
BATCH_SIZE         = 5               # Reduced for better stability
SLEEP_RANGE        = (10, 20)        # Increased pause between batches
COFFEE_EVERY_N     = 20              # More frequent breaks
COFFEE_RANGE       = (180, 360)      # seconds
MAX_RETRIES        = 3               # Increased retries
SCRIPT_DIR         = Path(__file__).resolve().parent / "scripts"
SAFARI_SCRIPT      = SCRIPT_DIR / "save_batch_safari_improved.applescript"
CHROME_SCRIPT      = SCRIPT_DIR / "save_batch_chrome_improved.applescript"
BROWSERS           = [               # ordered rotation
    ("safari", SAFARI_SCRIPT),
    ("chrome", CHROME_SCRIPT),
]
# ─────────────────────────────────────────────────────────────────────────────── #


def load_urls(path: Path) -> list[str]:
    txt = path.read_text(encoding="utf-8").splitlines()
    urls = [u.strip() for u in txt if u.strip()]
    urls = [u if u.startswith("http") else f"https://{u}" for u in urls]
    urls = [u.replace("pl.linkedin.com/", "linkedin.com/").replace("/mwlite/", "/") for u in urls]
    return list(dict.fromkeys(urls))


def filename_from_url(url: str) -> str:
    stem = url.rstrip("/").split("/")[-1] or "profile"
    return stem.split("?")[0] + ".html"


def analyze_html_content(html_path: Path) -> dict:
    """Enhanced profile analysis with detailed debugging info"""
    if not html_path.exists():
        return {"status": "file_not_found", "details": "File was not created"}
    
    try:
        text = html_path.read_text(errors="ignore")
        file_size = len(text)
        
        if file_size < 1000:  # Too small to be a real profile
            return {"status": "empty_file", "details": f"File size: {file_size} bytes"}
        
        soup = BeautifulSoup(text, "html.parser")
        
        # Check for auth wall
        key = soup.find("meta", attrs={"name": "pageKey"})
        if key and "auth_wall" in key.get("content", ""):
            return {"status": "auth_wall", "details": "Auth wall detected"}
        
        # Check for various profile indicators
        indicators = {
            "profile:first_name": soup.find("meta", attrs={"property": "profile:first_name"}),
            "profile:last_name": soup.find("meta", attrs={"property": "profile:last_name"}),
            "og:title": soup.find("meta", attrs={"property": "og:title"}),
            "title": soup.find("title"),
        }
        
        # Check for Person schema in JSON-LD
        person_found = False
        for tag in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(tag.string or "")
                graphs = (
                    data.get("@graph", []) if isinstance(data, dict) else []
                ) + ([data] if isinstance(data, dict) else [])
                if any(isinstance(n, dict) and n.get("@type") == "Person" for n in graphs):
                    person_found = True
                    break
            except Exception:
                continue
        
        # Check if it's a public profile page (even if limited)
        is_public_profile = any([
            indicators["profile:first_name"],
            person_found,
            (indicators["og:title"] and "LinkedIn" in indicators["og:title"].get("content", "")),
            (indicators["title"] and "LinkedIn" in indicators["title"].string),
        ])
        
        if is_public_profile:
            return {"status": "ok", "details": "Profile detected"}
        else:
            # Save debugging info
            debug_info = {
                "file_size": file_size,
                "has_profile_meta": bool(indicators["profile:first_name"]),
                "has_person_schema": person_found,
                "title": indicators["title"].string[:100] if indicators["title"] else "No title",
            }
            return {"status": "unknown_page", "details": json.dumps(debug_info)}
            
    except Exception as e:
        return {"status": "parse_error", "details": str(e)[:200]}


def write_log(log_path: Path, rows: list[dict]):
    first = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ts", "url", "file", "status", "details", "browser", "retry_count"])
        if first:
            w.writeheader()
        w.writerows(rows)


def call_applescript(script_path: Path, pair_list: list[str | Path]) -> tuple[bool, str]:
    """Call AppleScript and return (success, error_message)"""
    cmd = ["osascript", str(script_path)] + [str(x) for x in pair_list]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        error_msg = e.output[:500] if e.output else "Unknown error"
        tqdm.write(f"❌ AppleScript error: {error_msg}")
        return False, error_msg


def create_debug_report(out_dir: Path, processed_stats: dict):
    """Create a summary report of the scraping session"""
    report_path = out_dir / f"scraping_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with report_path.open("w") as f:
        f.write("LinkedIn Scraping Session Report\n")
        f.write("=" * 50 + "\n\n")
        
        for status, count in processed_stats.items():
            f.write(f"{status}: {count}\n")
        
        f.write(f"\nTotal URLs processed: {sum(processed_stats.values())}\n")
        f.write(f"Success rate: {processed_stats.get('ok', 0) / max(sum(processed_stats.values()), 1) * 100:.1f}%\n")


def main(url_file: Path, out_dir: Path, log_csv: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    urls = load_urls(url_file)
    print(f"Loaded {len(urls)} unique URLs to process")
    
    retry_counter = defaultdict(int)  # url → retry count
    queue = urls.copy()
    processed_stats = defaultdict(int)
    
    batch_idx = 0
    browser_cycle = iter(BROWSERS)
    
    with tqdm(total=len(urls), desc="Processing profiles") as pbar:
        while queue:
            # Rotate browser
            try:
                browser_name, script_path = next(browser_cycle)
            except StopIteration:
                browser_cycle = iter(BROWSERS)
                browser_name, script_path = next(browser_cycle)
            
            batch = queue[:BATCH_SIZE]
            queue = queue[BATCH_SIZE:]
            
            tqdm.write(f"\n📋 Batch {batch_idx + 1} - Using {browser_name} for {len(batch)} URLs")
            
            files = [out_dir / filename_from_url(u) for u in batch]
            arglist = [item for pair in zip(batch, files) for item in pair]
            
            script_ok, script_error = call_applescript(script_path, arglist)
            ts = int(time.time())
            log_rows = []
            
            # Wait a bit for files to be written
            time.sleep(2)
            
            for url, file_path in zip(batch, files):
                analysis = analyze_html_content(file_path)
                status = analysis["status"]
                details = analysis["details"]
                
                if status in ["file_not_found", "empty_file", "parse_error"]:
                    # Serious error - retry if under limit
                    if retry_counter[url] < MAX_RETRIES:
                        retry_counter[url] += 1
                        queue.append(url)
                        tqdm.write(f"  ⚠️  {file_path.name}: {status} - will retry ({retry_counter[url]}/{MAX_RETRIES})")
                    else:
                        tqdm.write(f"  ❌ {file_path.name}: {status} - max retries exceeded")
                        processed_stats[status] += 1
                        pbar.update(1)
                elif status == "auth_wall":
                    # Auth wall - rename and maybe retry
                    new_path = file_path.with_stem(file_path.stem + "_AUTHWALL")
                    file_path.rename(new_path)
                    
                    if retry_counter[url] < MAX_RETRIES:
                        retry_counter[url] += 1
                        queue.append(url)
                        tqdm.write(f"  🔒 {file_path.name}: Auth wall - will retry ({retry_counter[url]}/{MAX_RETRIES})")
                    else:
                        tqdm.write(f"  🔒 {file_path.name}: Auth wall - max retries exceeded")
                        processed_stats[status] += 1
                        pbar.update(1)
                elif status == "ok":
                    tqdm.write(f"  ✅ {file_path.name}: Profile saved successfully")
                    processed_stats[status] += 1
                    pbar.update(1)
                else:  # unknown_page
                    tqdm.write(f"  ❓ {file_path.name}: {status} - {details[:50]}...")
                    processed_stats[status] += 1
                    pbar.update(1)
                
                log_rows.append({
                    "ts": ts,
                    "url": url,
                    "file": file_path.name,
                    "status": status,
                    "details": details,
                    "browser": browser_name,
                    "retry_count": retry_counter[url],
                })
            
            write_log(log_csv, log_rows)
            
            batch_idx += 1
            if batch_idx % COFFEE_EVERY_N == 0 and queue:
                pause = random.uniform(*COFFEE_RANGE)
                tqdm.write(f"\n☕ Coffee break for {pause/60:.1f} min to avoid detection...")
                time.sleep(pause)
            elif queue:
                pause = random.uniform(*SLEEP_RANGE)
                tqdm.write(f"💤 Sleeping {pause:.0f}s before next batch...")
                time.sleep(pause)
    
    # Final report
    print("\n" + "="*50)
    print("SCRAPING SESSION COMPLETE")
    print("="*50)
    for status, count in processed_stats.items():
        print(f"{status}: {count}")
    print(f"\nTotal processed: {sum(processed_stats.values())}")
    print(f"Success rate: {processed_stats.get('ok', 0) / max(sum(processed_stats.values()), 1) * 100:.1f}%")
    
    create_debug_report(out_dir, processed_stats)
    print(f"\nLog saved to: {log_csv}")
    print(f"Debug report saved to: {out_dir}/scraping_report_*.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url_file", type=Path, help="TXT with LinkedIn URLs")
    ap.add_argument("output_dir", type=Path, help="Folder to save *.html")
    ap.add_argument(
        "--log",
        type=Path,
        default=Path("linkedin_scraper_improved.csv"),
        help="CSV log (default: linkedin_scraper_improved.csv)",
    )
    args = ap.parse_args()
    
    # Sanity-check helper scripts
    for name, p in BROWSERS:
        if not p.exists():
            print(f"⚠️  Warning: Missing AppleScript for {name}: {p}")
            print("   Creating improved version...")
    
    main(args.url_file, args.output_dir, args.log) 