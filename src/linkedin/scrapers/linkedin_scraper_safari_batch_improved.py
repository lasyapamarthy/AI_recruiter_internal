#!/usr/bin/env python3
"""
LinkedIn Safari Batch Scraper - Improved Version
Ensures all profiles are properly saved with better error handling
"""
import os
import sys
import time
import subprocess
import random
import json
from datetime import datetime
from tqdm import tqdm

# Configuration
BATCH_SIZE = 10  # Number of profiles to open simultaneously
WAIT_BETWEEN_BATCHES = (30, 60)  # 30-60 seconds between batches
PAGE_LOAD_WAIT = 20  # Wait time for pages to load (increased from 10)
SAVE_WAIT_PER_TAB = 3  # Wait time between saving each tab
MAX_RETRY_ATTEMPTS = 3  # Number of times to retry failed saves
CLEAR_COOKIES_EVERY = 5  # Clear cookies every N batches

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/safari_scraper_progress.json"
SAVE_LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/save_verification_log.json"

# Get current script directory
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

def clean_linkedin_url(url):
    """Clean and standardize LinkedIn URLs."""
    if not url or url.lower() == 'na':
        return None
    
    url = url.strip()
    url = url.replace(' ', '')
    
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Handle regional LinkedIn domains
    if 'pl.linkedin.com' in url:
        url = url.replace('pl.linkedin.com', 'linkedin.com')
    
    # Remove mobile lite version
    if '/mwlite/' in url:
        url = url.replace('/mwlite/', '/')
    
    # Ensure www
    if 'linkedin.com' in url and 'www.' not in url:
        url = url.replace('linkedin.com', 'www.linkedin.com')
    
    # Remove trailing slash and parameters
    url = url.rstrip('/').split('?')[0]
    
    return url

def get_html_filename(profile_url):
    """Create a valid filename from the URL."""
    clean_url = profile_url.split('?')[0]
    filename = clean_url.replace("https://", "").replace("www.", "").replace("/", "_")
    return filename + ".html"

def verify_html_file(filepath):
    """Verify that an HTML file was saved correctly and contains content."""
    try:
        if not os.path.exists(filepath):
            return False, "File does not exist"
        
        file_size = os.path.getsize(filepath)
        if file_size < 1000:  # Less than 1KB is suspicious
            return False, f"File too small ({file_size} bytes)"
        
        # Try to read the file to ensure it's not corrupted
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)  # Read first 1000 chars
            if not content or len(content) < 100:
                return False, "File appears empty or corrupted"
        
        return True, "File verified successfully"
    except Exception as e:
        return False, f"Verification error: {str(e)}"

def get_processed_urls():
    """Get URLs that have been successfully processed and verified."""
    processed_urls = set()
    
    try:
        if os.path.exists(OUTPUT_DIR):
            for html_file in os.listdir(OUTPUT_DIR):
                if html_file.endswith('.html'):
                    filepath = os.path.join(OUTPUT_DIR, html_file)
                    # Only count files that pass verification
                    is_valid, _ = verify_html_file(filepath)
                    if is_valid:
                        # Extract URL from filename
                        url_part = html_file[:-5]  # Remove .html
                        if '_in_' in url_part:
                            parts = url_part.split('_in_')
                            if len(parts) >= 2:
                                username = parts[-1].rstrip('_').strip()
                                if username:
                                    standardized_url = f'https://www.linkedin.com/in/{username}'
                                    processed_urls.add(standardized_url)
        return processed_urls
    except Exception as e:
        print(f"Error getting processed URLs: {e}")
        return set()

def get_failed_urls():
    """Get URLs that have failed."""
    failed_urls = set()
    try:
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                failed_urls.update(url.strip() for url in f.readlines() if url.strip())
        return failed_urls
    except Exception as e:
        print(f"Error getting failed URLs: {e}")
        return set()

def add_to_failed_urls(profile_url):
    """Add a URL to the failed URLs file."""
    try:
        os.makedirs(os.path.dirname(FAILED_URLS_FILE), exist_ok=True)
        with open(FAILED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(profile_url + '\n')
    except Exception as e:
        print(f"Error adding URL to failed list: {e}")

def save_progress(batch_num, profiles_saved, profiles_failed, verification_stats):
    """Save detailed progress including verification statistics."""
    progress = {
        "batch": batch_num,
        "profiles_saved": profiles_saved,
        "profiles_failed": profiles_failed,
        "verification_stats": verification_stats,
        "timestamp": datetime.now().isoformat()
    }
    try:
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        print(f"Error saving progress: {e}")

def log_save_verification(batch_num, url, filepath, is_valid, message):
    """Log detailed save verification results."""
    log_entry = {
        "batch": batch_num,
        "url": url,
        "filepath": filepath,
        "is_valid": is_valid,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        os.makedirs(os.path.dirname(SAVE_LOG_FILE), exist_ok=True)
        
        # Load existing log
        if os.path.exists(SAVE_LOG_FILE):
            with open(SAVE_LOG_FILE, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = []
        
        # Add new entry
        log_data.append(log_entry)
        
        # Keep only last 1000 entries
        if len(log_data) > 1000:
            log_data = log_data[-1000:]
        
        # Save updated log
        with open(SAVE_LOG_FILE, 'w') as f:
            json.dump(log_data, f, indent=2)
    except Exception as e:
        print(f"Error logging save verification: {e}")

def create_improved_applescript():
    """Create an improved AppleScript with better error handling and verification."""
    applescript_content = '''
on run argv
    set urlList to {}
    set filenameList to {}
    set saveResults to {}
    
    -- Parse arguments (alternating URLs and filenames)
    repeat with i from 1 to count of argv by 2
        set end of urlList to item i of argv
        if i + 1 <= count of argv then
            set end of filenameList to item (i + 1) of argv
        end if
    end repeat
    
    tell application "Safari"
        activate
        
        -- Close existing tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
        -- Open all URLs in new tabs
        repeat with i from 1 to count of urlList
            if i = 1 then
                set URL of document 1 to item i of urlList
            else
                tell window 1 to make new tab with properties {URL:item i of urlList}
            end if
        end repeat
        
        -- Wait longer for pages to load
        delay 20
        
        -- Additional wait to ensure all pages are loaded
        repeat with i from 1 to count of urlList
            set current tab of window 1 to tab i of window 1
            delay 1
            
            -- Check if page is still loading
            repeat 5 times
                try
                    set pageState to do JavaScript "document.readyState" in current tab of window 1
                    if pageState is "complete" then
                        exit repeat
                    end if
                on error
                    -- Page might not be ready for JavaScript yet
                end try
                delay 2
            end repeat
        end repeat
        
        -- Save each tab with verification
        repeat with i from 1 to count of urlList
            set saveSuccess to false
            set retryCount to 0
            
            repeat while retryCount < 3 and not saveSuccess
                try
                    set current tab of window 1 to tab i of window 1
                    delay 3
                    
                    -- Get the page source
                    set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
                    
                    -- Verify we got actual content
                    if length of pageSource > 1000 then
                        set filename to item i of filenameList
                        
                        -- Write to file with error handling
                        try
                            set fileRef to open for access filename with write permission
                            set eof of fileRef to 0  -- Clear existing content
                            write pageSource to fileRef as «class utf8»
                            close access fileRef
                            set saveSuccess to true
                            set end of saveResults to "SUCCESS: " & filename
                        on error writeErr
                            try
                                close access fileRef
                            end try
                            set end of saveResults to "WRITE_ERROR: " & filename & " - " & writeErr
                        end try
                    else
                        set end of saveResults to "EMPTY_CONTENT: " & item i of filenameList
                    end if
                    
                on error jsErr
                    set end of saveResults to "JS_ERROR: " & item i of filenameList & " - " & jsErr
                end try
                
                if not saveSuccess then
                    set retryCount to retryCount + 1
                    if retryCount < 3 then
                        delay 2
                    end if
                end if
            end repeat
            
            if not saveSuccess then
                set end of saveResults to "FAILED_AFTER_RETRIES: " & item i of filenameList
            end if
        end repeat
        
        -- Close all tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
    end tell
    
    -- Return save results
    return saveResults
end run
'''
    
    applescript_path = os.path.join(SCRIPT_PATH, "../applescripts/safari_batch_download_improved.applescript")
    os.makedirs(os.path.dirname(applescript_path), exist_ok=True)
    
    with open(applescript_path, 'w') as f:
        f.write(applescript_content)
    
    return applescript_path

def process_batch_with_verification(urls_batch, batch_num):
    """Process a batch of URLs with detailed verification and retry logic."""
    print(f"\n🍎 Processing batch {batch_num} with {len(urls_batch)} URLs")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create filenames for this batch
    url_to_filepath = {}
    args = []
    
    for url in urls_batch:
        filename = get_html_filename(url)
        filepath = os.path.join(OUTPUT_DIR, filename)
        url_to_filepath[url] = filepath
        args.extend([url, filepath])
    
    # Create improved AppleScript
    applescript_path = create_improved_applescript()
    
    try:
        # Execute AppleScript
        command = ['osascript', applescript_path] + args
        print(f"  📱 Opening {len(urls_batch)} tabs in Safari...")
        print(f"  ⏳ Waiting for pages to load and save...")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        
        # Parse AppleScript results
        if result.returncode == 0 and result.stdout:
            save_results = result.stdout.strip().split(", ")
            print(f"  📄 AppleScript completed with {len(save_results)} results")
        else:
            save_results = []
            print(f"  ⚠️ AppleScript may have encountered issues")
        
        # Verify each file was saved correctly
        verification_stats = {
            "verified": 0,
            "failed": 0,
            "retried": 0,
            "details": []
        }
        
        successful_saves = []
        failed_saves = []
        
        for i, (url, filepath) in enumerate(url_to_filepath.items()):
            print(f"    {i+1}. Verifying: {url[:50]}{'...' if len(url) > 50 else ''}")
            
            # Check AppleScript result if available
            applescript_result = save_results[i] if i < len(save_results) else "NO_RESULT"
            
            # Verify the file
            is_valid, message = verify_html_file(filepath)
            
            if is_valid:
                print(f"       ✅ Saved and verified ({os.path.getsize(filepath)/1024:.1f} KB)")
                successful_saves.append(url)
                verification_stats["verified"] += 1
            else:
                print(f"       ❌ Save failed: {message}")
                print(f"       📝 AppleScript result: {applescript_result}")
                failed_saves.append(url)
                verification_stats["failed"] += 1
                
                # Log the failure
                log_save_verification(batch_num, url, filepath, False, f"{message} | AS: {applescript_result}")
                
                # Clean up failed file if it exists
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
            
            verification_stats["details"].append({
                "url": url,
                "valid": is_valid,
                "message": message,
                "applescript": applescript_result
            })
        
        # Summary
        print(f"\n  📊 BATCH {batch_num} VERIFICATION RESULTS:")
        print(f"     ✅ Successfully saved and verified: {verification_stats['verified']}")
        print(f"     ❌ Failed to save properly: {verification_stats['failed']}")
        
        return successful_saves, failed_saves, verification_stats
        
    except subprocess.TimeoutExpired:
        print(f"  ⏰ Batch timed out after 3 minutes")
        return [], urls_batch, {"verified": 0, "failed": len(urls_batch), "details": []}
    except Exception as e:
        print(f"  💥 Error processing batch: {e}")
        return [], urls_batch, {"verified": 0, "failed": len(urls_batch), "details": []}

def get_remaining_urls():
    """Get list of URLs that haven't been processed yet."""
    try:
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            all_urls = [url.strip() for url in f.readlines()]
        
        valid_urls = []
        for url in all_urls:
            cleaned_url = clean_linkedin_url(url)
            if cleaned_url and 'linkedin.com' in cleaned_url:
                valid_urls.append(cleaned_url)
        
        processed_urls = get_processed_urls()
        failed_urls = get_failed_urls()
        
        remaining_urls = [url for url in valid_urls if url not in processed_urls and url not in failed_urls]
        
        print(f"📊 Status: {len(valid_urls)} total | {len(processed_urls)} processed | {len(failed_urls)} failed | {len(remaining_urls)} remaining")
        return remaining_urls
    except Exception as e:
        print(f"Error getting remaining URLs: {e}")
        return []

def clear_safari_cookies():
    """Clear Safari cookies and website data."""
    try:
        print("    🧹 Clearing Safari cookies...")
        
        # Simple cookie clearing via menu automation
        applescript_content = '''
tell application "Safari"
    activate
    delay 1
    
    tell application "System Events"
        tell process "Safari"
            -- Open Safari menu and clear history
            keystroke "y" using {command down, shift down}
            delay 2
            
            -- Click Clear History button
            try
                click button "Clear History" of sheet 1 of window 1
            end try
            delay 1
        end tell
    end tell
end tell
'''
        
        temp_script = os.path.join(SCRIPT_PATH, "clear_cookies_simple.applescript")
        with open(temp_script, 'w') as f:
            f.write(applescript_content)
        
        subprocess.run(['osascript', temp_script], capture_output=True, text=True, timeout=10)
        
        # Clean up
        try:
            os.remove(temp_script)
        except:
            pass
        
        print("    ✅ Safari cookies cleared")
        time.sleep(5)  # Wait after clearing
            
    except Exception as e:
        print(f"    ⚠️ Cookie clearing may have failed: {e}")

def main():
    """Main scraping function with improved verification."""
    print("🍎 LinkedIn Safari Batch Scraper - Improved Version")
    print(f"Strategy: {BATCH_SIZE} profiles per batch, {PAGE_LOAD_WAIT}s page load wait")
    print(f"Features: File verification, detailed logging, retry logic")
    print("=" * 85)
    
    # Get remaining URLs
    remaining_urls = get_remaining_urls()
    
    if not remaining_urls:
        print("🎉 All URLs have been processed!")
        return
    
    session_profiles_saved = 0
    session_profiles_failed = 0
    batch_num = 1
    
    # Process URLs in batches
    for i in tqdm(range(0, len(remaining_urls), BATCH_SIZE), desc="Processing batches"):
        batch_urls = remaining_urls[i:i+BATCH_SIZE]
        
        print(f"\n📦 BATCH {batch_num}: Processing {len(batch_urls)} URLs")
        
        # Clear cookies periodically
        if batch_num % CLEAR_COOKIES_EVERY == 0:
            clear_safari_cookies()
        
        # Process the batch with verification
        successful_saves, failed_saves, verification_stats = process_batch_with_verification(batch_urls, batch_num)
        
        session_profiles_saved += len(successful_saves)
        session_profiles_failed += len(failed_saves)
        
        # Add failed URLs to failed list
        for failed_url in failed_saves:
            add_to_failed_urls(failed_url)
        
        # Save detailed progress
        save_progress(batch_num, session_profiles_saved, session_profiles_failed, verification_stats)
        
        # Show session progress
        print(f"\n📊 SESSION PROGRESS:")
        print(f"   ✅ Total saved this session: {session_profiles_saved}")
        print(f"   ❌ Total failed this session: {session_profiles_failed}")
        if session_profiles_saved + session_profiles_failed > 0:
            success_rate = (session_profiles_saved / (session_profiles_saved + session_profiles_failed)) * 100
            print(f"   📈 Session success rate: {success_rate:.1f}%")
        
        # Wait between batches
        if i + BATCH_SIZE < len(remaining_urls):
            wait_time = random.uniform(*WAIT_BETWEEN_BATCHES)
            print(f"\n💤 Waiting {wait_time:.1f} seconds before next batch...")
            time.sleep(wait_time)
        
        batch_num += 1
    
    # Final summary
    print(f"\n🏁 SCRAPING SESSION COMPLETED!")
    print(f"=" * 50)
    print(f"📊 FINAL SUMMARY:")
    print(f"   ✅ Profiles saved: {session_profiles_saved}")
    print(f"   ❌ Profiles failed: {session_profiles_failed}")
    
    # Show verification log summary
    try:
        if os.path.exists(SAVE_LOG_FILE):
            with open(SAVE_LOG_FILE, 'r') as f:
                log_data = json.load(f)
                recent_failures = [entry for entry in log_data[-100:] if not entry['is_valid']]
                if recent_failures:
                    print(f"\n📋 Recent save failures:")
                    for failure in recent_failures[-5:]:
                        print(f"   - {failure['url'][:50]}... : {failure['message']}")
    except:
        pass

if __name__ == "__main__":
    main() 