#!/usr/bin/env python3
import os
import csv
import time
import subprocess
from datetime import datetime

# Paths
INPUT_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/uncollected_profiles.csv"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/scraped_profiles"
TEMP_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/temp_scraped"
LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/scraping_log.txt"

# File size threshold (100KB)
SIZE_THRESHOLD = 100 * 1024  # 100KB in bytes

# Delay between requests (seconds)
DELAY_MIN = 3
DELAY_MAX = 7

def setup_directories():
    """Create necessary directories."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

def log_message(message):
    """Log message to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + "\n")

def save_safari_page(url, filename):
    """Save current Safari page as HTML using AppleScript in private browsing mode."""
    # Create temp file path
    temp_path = os.path.join(TEMP_DIR, filename)
    
    applescript = f'''
    tell application "Safari"
        activate
        
        -- Create new private window
        make new document
        set privateWindow to window 1
        
        -- Open URL in the private window
        tell privateWindow
            set URL of current tab to "{url}"
        end tell
        
        -- Wait for page to load
        delay 5
        
        -- Additional wait for dynamic content
        repeat with i from 1 to 10
            delay 1
            set pageSource to source of document 1
            if length of pageSource > 50000 then
                exit repeat
            end if
        end repeat
        
        -- Get the page source
        set pageSource to source of document 1
        
        -- Close the private window
        close privateWindow
    end tell
    
    -- Write to file
    set filePath to POSIX file "{temp_path}"
    try
        set fileHandle to open for access filePath with write permission
        set eof fileHandle to 0
        write pageSource to fileHandle as «class utf8»
        close access fileHandle
    on error
        try
            close access filePath
        end try
    end try
    
    return "done"
    '''
    
    try:
        # Run AppleScript
        result = subprocess.run(['osascript', '-e', applescript], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            log_message(f"❌ AppleScript error: {result.stderr}")
            return False
        
        # Check if file was created and has content
        if os.path.exists(temp_path):
            file_size = os.path.getsize(temp_path)
            
            if file_size >= SIZE_THRESHOLD:
                # Move to output directory
                final_path = os.path.join(OUTPUT_DIR, filename)
                os.rename(temp_path, final_path)
                log_message(f"✅ Saved: {filename} ({file_size / 1024:.1f}KB)")
                return True
            else:
                # Remove small file (likely auth page)
                os.remove(temp_path)
                log_message(f"⚠️  Skipped (too small): {filename} ({file_size / 1024:.1f}KB) - likely auth page")
                return False
        else:
            log_message(f"❌ File not created: {filename}")
            return False
            
    except subprocess.TimeoutExpired:
        log_message(f"❌ Timeout while scraping: {url}")
        return False
    except Exception as e:
        log_message(f"❌ Error scraping {url}: {str(e)}")
        return False

def main():
    """Main scraping function."""
    log_message("🚀 Starting Safari scraper for uncollected profiles...")
    log_message("🔒 Using private browsing mode (incognito)")
    log_message(f"📏 File size threshold: {SIZE_THRESHOLD / 1024:.0f}KB")
    
    # Setup directories
    setup_directories()
    
    # Read CSV file
    if not os.path.exists(INPUT_CSV):
        log_message(f"❌ CSV file not found: {INPUT_CSV}")
        return
    
    profiles = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        profiles = list(reader)
    
    total_count = len(profiles)
    log_message(f"📋 Found {total_count} profiles to scrape")
    
    if total_count == 0:
        log_message("❌ No profiles found in CSV!")
        return
    
    # Check existing files to avoid re-scraping
    existing_files = set(os.listdir(OUTPUT_DIR))
    profiles_to_scrape = []
    
    for profile in profiles:
        if profile['filename'] not in existing_files:
            profiles_to_scrape.append(profile)
    
    skip_count = total_count - len(profiles_to_scrape)
    if skip_count > 0:
        log_message(f"⏭️  Skipping {skip_count} already scraped profiles")
    
    log_message(f"🎯 Will scrape {len(profiles_to_scrape)} new profiles")
    
    if len(profiles_to_scrape) == 0:
        log_message("✅ All profiles already scraped!")
        return
    
    # Confirm before starting
    print("\n⚠️  This will open Safari in private browsing mode and scrape profiles automatically.")
    print("   Note: You will NOT be logged into LinkedIn in private mode.")
    print("   The script will only save files larger than 100KB (real profiles).")
    response = input("   Continue? (y/n): ")
    
    if response.lower() != 'y':
        log_message("❌ Scraping cancelled by user")
        return
    
    # Start scraping
    success_count = 0
    fail_count = 0
    
    log_message("\n🔄 Starting scraping process...")
    
    for i, profile in enumerate(profiles_to_scrape):
        log_message(f"\n[{i+1}/{len(profiles_to_scrape)}] Scraping: {profile['profile_name']}")
        log_message(f"   URL: {profile['linkedin_url']}")
        
        success = save_safari_page(profile['linkedin_url'], profile['filename'])
        
        if success:
            success_count += 1
        else:
            fail_count += 1
        
        # Progress update
        if (i + 1) % 10 == 0:
            log_message(f"\n📊 Progress: {i+1}/{len(profiles_to_scrape)} profiles")
            log_message(f"   Success: {success_count}, Failed: {fail_count}")
        
        # Delay between requests (except for last one)
        if i < len(profiles_to_scrape) - 1:
            delay = DELAY_MIN + (hash(profile['linkedin_url']) % (DELAY_MAX - DELAY_MIN))
            log_message(f"   Waiting {delay} seconds...")
            time.sleep(delay)
    
    # Final summary
    log_message("\n🎉 Scraping complete!")
    log_message(f"📊 Final results:")
    log_message(f"   Total attempted: {len(profiles_to_scrape)}")
    log_message(f"   Successfully scraped: {success_count} (files > 100KB)")
    log_message(f"   Failed/Skipped: {fail_count} (auth pages or errors)")
    log_message(f"   Output directory: {OUTPUT_DIR}")
    
    # Count final files
    final_files = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')])
    log_message(f"   Total profiles saved: {final_files}")

if __name__ == "__main__":
    main() 