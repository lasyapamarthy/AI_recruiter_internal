#!/usr/bin/env python3
"""
LinkedIn Safari Batch Scraper - Based on old working script
Opens 10 profiles simultaneously in Safari tabs for better anti-detection
"""
import os
import sys
import time
import subprocess
import random
import json
from tqdm import tqdm

# Configuration
BATCH_SIZE = 10  # Number of profiles to open simultaneously
WAIT_BETWEEN_BATCHES = (30, 60)  # 30-60 seconds between batches
MAX_HAMMER_ATTEMPTS = 10  # Number of times to retry auth pages
HAMMER_WAIT_TIME = (60, 120)  # Wait time between hammer attempts (longer delays)
DELAYED_RETRY_WAIT = (300, 600)  # 5-10 minutes before retrying auth pages
CLEAR_COOKIES_EVERY = 5  # Clear cookies every N batches
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_safari_progress.json"
HAMMER_LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/hammer_attempts.json"
AUTH_RETRY_QUEUE_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/auth_retry_queue.json"

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
    return filename

def get_processed_urls():
    """Get URLs that have been successfully processed."""
    processed_urls = set()
    
    try:
        if os.path.exists(OUTPUT_DIR):
            for html_file in os.listdir(OUTPUT_DIR):
                if html_file.endswith('.html'):
                    url_part = html_file[:-5]
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

def get_remaining_urls():
    """Get list of URLs that haven't been processed or failed yet."""
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

def add_to_failed_urls(profile_url):
    """Add a URL to the failed URLs file."""
    try:
        os.makedirs(os.path.dirname(FAILED_URLS_FILE), exist_ok=True)
        with open(FAILED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(profile_url + '\n')
    except Exception as e:
        print(f"Error adding URL to failed list: {e}")

def save_progress(batch_num, profiles_scraped, profiles_failed):
    """Save progress to file."""
    progress = {
        "batch": batch_num,
        "profiles_scraped": profiles_scraped,
        "profiles_failed": profiles_failed,
        "timestamp": time.time()
    }
    try:
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except Exception as e:
        print(f"Error saving progress: {e}")

def load_hammer_attempts():
    """Load hammer attempt history."""
    try:
        if os.path.exists(HAMMER_LOG_FILE):
            with open(HAMMER_LOG_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading hammer attempts: {e}")
        return {}

def save_hammer_attempts(hammer_data):
    """Save hammer attempt history."""
    try:
        os.makedirs(os.path.dirname(HAMMER_LOG_FILE), exist_ok=True)
        with open(HAMMER_LOG_FILE, 'w') as f:
            json.dump(hammer_data, f, indent=2)
    except Exception as e:
        print(f"Error saving hammer attempts: {e}")

def load_auth_retry_queue():
    """Load auth retry queue."""
    try:
        if os.path.exists(AUTH_RETRY_QUEUE_FILE):
            with open(AUTH_RETRY_QUEUE_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading auth retry queue: {e}")
        return []

def save_auth_retry_queue(queue):
    """Save auth retry queue."""
    try:
        os.makedirs(os.path.dirname(AUTH_RETRY_QUEUE_FILE), exist_ok=True)
        with open(AUTH_RETRY_QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"Error saving auth retry queue: {e}")

def add_to_auth_retry_queue(url):
    """Add URL to auth retry queue with timestamp."""
    queue = load_auth_retry_queue()
    
    # Check if URL is already in queue
    for item in queue:
        if item['url'] == url:
            return  # Already in queue
    
    queue.append({
        'url': url,
        'added_time': time.time(),
        'retry_attempts': 0
    })
    
    save_auth_retry_queue(queue)
    print(f"    📋 Added to delayed retry queue")

def clear_safari_cookies():
    """Clear Safari cookies and website data."""
    try:
        print("    🧹 Clearing Safari cookies and website data...")
        
        # AppleScript to clear Safari data
        applescript_content = '''
tell application "Safari"
    activate
    
    -- Clear all website data
    tell application "System Events"
        tell process "Safari"
            keystroke "," using command down
            delay 2
            click button "Privacy" of toolbar 1 of window 1
            delay 1
            click button "Manage Website Data..." of group 1 of group 1 of window 1
            delay 2
            click button "Remove All" of sheet 1 of window 1
            delay 1
            click button "Remove Now" of sheet 1 of sheet 1 of window 1
            delay 2
            click button "Done" of sheet 1 of window 1
            delay 1
            keystroke "w" using command down
        end tell
    end tell
end tell
'''
        
        temp_script = os.path.join(SCRIPT_PATH, "clear_cookies.applescript")
        with open(temp_script, 'w') as f:
            f.write(applescript_content)
        
        result = subprocess.run(['osascript', temp_script], capture_output=True, text=True, timeout=30)
        
        # Clean up temp script
        try:
            os.remove(temp_script)
        except:
            pass
        
        if result.returncode == 0:
            print("    ✅ Safari cookies cleared successfully")
        else:
            print(f"    ⚠️ Cookie clearing may have failed: {result.stderr}")
            
    except Exception as e:
        print(f"    ❌ Error clearing cookies: {e}")

def clear_safari_state():
    """Clear Safari state between attempts."""
    try:
        print("      🧹 Clearing Safari state...")
        
        # Simple AppleScript to close all tabs and open a fresh one
        applescript_content = '''
tell application "Safari"
    activate
    
    -- Close all windows except one
    repeat while (count of windows) > 1
        close window 2
    end repeat
    
    -- Close all tabs except one in the remaining window
    if (count of windows) > 0 then
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
        -- Navigate to a neutral page
        set URL of document 1 to "about:blank"
        delay 2
    end if
end tell
'''
        
        temp_script = os.path.join(SCRIPT_PATH, "clear_state.applescript")
        with open(temp_script, 'w') as f:
            f.write(applescript_content)
        
        result = subprocess.run(['osascript', temp_script], capture_output=True, text=True, timeout=15)
        
        # Clean up temp script
        try:
            os.remove(temp_script)
        except:
            pass
        
        if result.returncode == 0:
            print("      ✅ Safari state cleared")
        else:
            print(f"      ⚠️ State clearing may have failed")
            
    except Exception as e:
        print(f"      ❌ Error clearing state: {e}")

def get_ready_auth_retries():
    """Get auth URLs that are ready for retry (after delay period)."""
    queue = load_auth_retry_queue()
    current_time = time.time()
    ready_urls = []
    
    for item in queue:
        time_since_added = current_time - item['added_time']
        min_wait = DELAYED_RETRY_WAIT[0]
        
        if time_since_added >= min_wait and item['retry_attempts'] < MAX_HAMMER_ATTEMPTS:
            ready_urls.append(item)
    
    return ready_urls

def is_auth_page(html_file_path):
    """Enhanced detection specifically for auth pages."""
    try:
        html_content = None
        encodings_to_try = ['utf-8', 'iso-8859-1', 'latin-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                with open(html_file_path, 'r', encoding=encoding) as f:
                    html_content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if html_content is None:
            return True  # If we can't read it, treat as auth page
        
        html_lower = html_content.lower()
        file_size = len(html_content)
        
        # Strong auth page indicators
        auth_indicators = [
            'authwall-sign-in-form',
            'authentication-outlet',
            'sign in with google',
            'continue to join or sign in',
            'join now to see',
            'sign up to see',
            'log in to see',
            'create account to see',
            'sign in to linkedin',
            'join linkedin',
            'linkedin login'
        ]
        
        auth_count = sum(1 for indicator in auth_indicators if indicator in html_lower)
        
        # Check for multiple "sign in to view" occurrences
        sign_in_view_count = html_lower.count('sign in to view')
        
        # Auth page criteria:
        # 1. Small file size (< 150KB) OR
        # 2. Multiple auth indicators (>= 2) OR  
        # 3. Many "sign in to view" occurrences (> 3)
        if file_size < 150000 or auth_count >= 2 or sign_in_view_count > 3:
            return True
            
        return False
        
    except Exception as e:
        return True  # If error, treat as auth page

def is_valid_profile_html(html_file_path):
    """Check if HTML file contains a valid LinkedIn profile (not an auth page)."""
    return not is_auth_page(html_file_path)

def hammer_profile_delayed(url, filename, retry_item=None):
    """Hammer a single profile URL with delayed retry and state clearing."""
    
    if retry_item is None:
        # This is a new auth page, add to queue for later
        add_to_auth_retry_queue(url)
        return False, None
    
    # This is a delayed retry attempt
    print(f"    🔨 DELAYED RETRY: {url}")
    print(f"       Attempt {retry_item['retry_attempts'] + 1}/{MAX_HAMMER_ATTEMPTS}")
    
    # Clear Safari state before attempt
    clear_safari_state()
    
    # Wait a bit after clearing state
    time.sleep(5)
    
    # Create single-URL AppleScript with longer delays
    applescript_content = f'''
tell application "Safari"
    activate
    delay 2
    
    set URL of document 1 to "{url}"
    delay 15
    
    set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
    
    set fileRef to open for access "{filename}" with write permission
    write pageSource to fileRef
    close access fileRef
end tell
'''
    
    # Write and execute AppleScript
    temp_script = os.path.join(SCRIPT_PATH, f"delayed_retry_{retry_item['retry_attempts']}.applescript")
    try:
        with open(temp_script, 'w') as f:
            f.write(applescript_content)
        
        result = subprocess.run(['osascript', temp_script], capture_output=True, text=True, timeout=90)
        
        # Clean up temp script
        try:
            os.remove(temp_script)
        except:
            pass
        
        if result.returncode == 0 and os.path.exists(filename):
            if is_valid_profile_html(filename):
                print(f"       ✅ DELAYED RETRY SUCCESS!")
                
                # Remove from retry queue
                queue = load_auth_retry_queue()
                queue = [item for item in queue if item['url'] != url]
                save_auth_retry_queue(queue)
                
                return True, None
            else:
                print(f"       ❌ Still auth page after delayed retry")
                # Delete auth page
                try:
                    os.remove(filename)
                except:
                    pass
        else:
            print(f"       ❌ Failed to save during delayed retry")
        
        # Update retry attempts
        queue = load_auth_retry_queue()
        for item in queue:
            if item['url'] == url:
                item['retry_attempts'] += 1
                item['added_time'] = time.time()  # Reset timer for next attempt
                break
        save_auth_retry_queue(queue)
        
        return False, None
        
    except Exception as e:
        print(f"       💥 Error during delayed retry: {e}")
        return False, None

def process_delayed_retries():
    """Process URLs that are ready for delayed retry."""
    ready_retries = get_ready_auth_retries()
    
    if not ready_retries:
        return 0, 0
    
    print(f"\n🔄 PROCESSING {len(ready_retries)} DELAYED RETRIES")
    
    successes = 0
    failures = 0
    
    for retry_item in ready_retries:
        url = retry_item['url']
        filename = get_html_filename(url)
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        print(f"  🔄 Retrying: {url[:60]}{'...' if len(url) > 60 else ''}")
        
        success, _ = hammer_profile_delayed(url, filepath, retry_item)
        
        if success:
            successes += 1
        else:
            failures += 1
            
        # Wait between delayed retries
        if retry_item != ready_retries[-1]:  # Not the last one
            wait_time = random.uniform(*HAMMER_WAIT_TIME)
            print(f"       💤 Waiting {wait_time:.1f}s before next retry...")
            time.sleep(wait_time)
    
    print(f"  📊 Delayed retry results: {successes} successes, {failures} failures")
    return successes, failures

def create_applescript():
    """Create the AppleScript file for batch downloading."""
    # Use the more reliable AppleScript
    applescript_path = os.path.join(SCRIPT_PATH, "../applescripts/safari_batch_reliable.applescript")
    
    # If it doesn't exist, create it
    if not os.path.exists(applescript_path):
        os.makedirs(os.path.dirname(applescript_path), exist_ok=True)
        applescript_content = '''
on run argv
    set urlList to {}
    set filenameList to {}
    
    -- Parse arguments (alternating URLs and filenames)
    repeat with i from 1 to count of argv by 2
        set end of urlList to item i of argv
        if i + 1 <= count of argv then
            set end of filenameList to item (i + 1) of argv
        end if
    end repeat
    
    tell application "Safari"
        activate
        
        -- Make sure we have a window
        if (count of windows) = 0 then
            make new document
        end if
        
        -- Close all tabs except first
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
        -- Open all URLs in tabs
        repeat with i from 1 to count of urlList
            if i = 1 then
                -- Use the first tab
                set URL of document 1 to item i of urlList
            else
                -- Create new tabs for the rest
                tell window 1
                    make new tab with properties {URL:item i of urlList}
                end tell
            end if
            delay 0.5
        end repeat
        
        -- Wait for all pages to start loading
        delay 5
        
        -- Wait for each page to finish loading
        repeat with i from 1 to count of tabs of window 1
            set current tab of window 1 to tab i of window 1
            delay 1
            
            -- Wait for page to load (check multiple times)
            set loadAttempts to 0
            repeat while loadAttempts < 10
                try
                    -- Check if page is loaded
                    set pageURL to URL of current tab of window 1
                    set pageTitle to name of current tab of window 1
                    
                    -- If we can get URL and title, page is likely loaded
                    if pageURL is not missing value and pageTitle is not missing value then
                        if pageTitle does not contain "Loading" and pageTitle does not contain "Untitled" then
                            exit repeat
                        end if
                    end if
                on error
                    -- Ignore errors and keep waiting
                end try
                
                delay 2
                set loadAttempts to loadAttempts + 1
            end repeat
        end repeat
        
        -- Additional wait to ensure JavaScript is ready
        delay 5
        
        -- Now save each tab's content
        repeat with i from 1 to count of urlList
            try
                -- Switch to the tab
                set current tab of window 1 to tab i of window 1
                delay 2
                
                -- Try to get the page source multiple times
                set gotContent to false
                set attempts to 0
                
                repeat while attempts < 3 and not gotContent
                    try
                        -- Get page source using JavaScript
                        set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
                        
                        -- Check if we got real content
                        if length of pageSource > 500 then
                            set gotContent to true
                        else
                            delay 2
                        end if
                    on error
                        delay 2
                    end try
                    set attempts to attempts + 1
                end repeat
                
                -- Save the content if we got it
                if gotContent then
                    set filename to item i of filenameList & ".html"
                    
                    -- Write to file
                    try
                        -- Delete existing file if it exists
                        do shell script "rm -f " & quoted form of filename
                        
                        -- Create new file with content
                        set fileRef to open for access filename with write permission
                        write pageSource to fileRef as «class utf8»
                        close access fileRef
                        
                        log "Saved: " & filename
                    on error errMsg
                        log "Error saving " & filename & ": " & errMsg
                        try
                            close access fileRef
                        end try
                    end try
                else
                    log "No content for tab " & i
                end if
                
            on error errMsg
                log "Error processing tab " & i & ": " & errMsg
            end try
        end repeat
        
        -- Clean up - close all tabs except first
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
        -- Navigate first tab to blank page
        set URL of document 1 to "about:blank"
        
    end tell
    
    return "Batch processing complete"
end run
'''
        with open(applescript_path, 'w') as f:
            f.write(applescript_content)
    
    return applescript_path

def process_batch(urls_batch, batch_num):
    """Process a batch of URLs using Safari with delayed retry for auth pages."""
    print(f"\n🍎 Processing batch {batch_num} with {len(urls_batch)} URLs")
    
    # Clear cookies every N batches
    if batch_num % CLEAR_COOKIES_EVERY == 0:
        print(f"  🧹 Batch {batch_num}: Time to clear cookies!")
        clear_safari_cookies()
        time.sleep(10)  # Wait after clearing cookies
    
    # Count files before processing
    files_before = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]) if os.path.exists(OUTPUT_DIR) else 0
    
    # Create filenames for this batch
    filenames_batch = []
    for url in urls_batch:
        filename = get_html_filename(url)
        filepath = os.path.join(OUTPUT_DIR, filename)
        filenames_batch.append(filepath)
    
    # Create AppleScript if it doesn't exist
    applescript_path = create_applescript()
    
    try:
        # Prepare arguments for AppleScript (alternating URLs and filenames)
        args = []
        for url, filename in zip(urls_batch, filenames_batch):
            args.extend([url, filename])
        
        # Execute AppleScript
        command = ['osascript', applescript_path] + args
        print(f"  📱 Opening {len(urls_batch)} tabs in Safari...")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)  # Increased timeout
        
        if result.returncode == 0:
            print(f"  📄 AppleScript completed, checking saved files...")
            
            # Wait a bit to ensure files are written
            time.sleep(2)
            
            # Track results for each URL individually
            valid_profiles_saved = 0
            auth_pages_queued = 0
            not_saved_count = 0
            failed_urls = []
            
            for i, (url, filename) in enumerate(zip(urls_batch, filenames_batch), 1):
                print(f"    {i}. {url[:50]}{'...' if len(url) > 50 else ''}")
                
                if os.path.exists(filename):
                    # Verify file size and content
                    try:
                        file_size = os.path.getsize(filename)
                        if file_size < 1000:  # Less than 1KB is suspicious
                            print(f"       ❌ File too small ({file_size} bytes) - likely failed")
                            not_saved_count += 1
                            failed_urls.append(url)
                            try:
                                os.remove(filename)
                            except:
                                pass
                        elif is_valid_profile_html(filename):
                            print(f"       ✅ Valid profile saved ({file_size/1024:.1f} KB)")
                            valid_profiles_saved += 1
                        else:
                            print(f"       ❌ Auth page detected - queuing for delayed retry")
                            auth_pages_queued += 1
                            
                            # Delete the auth page first
                            try:
                                os.remove(filename)
                            except:
                                pass
                            
                            # Add to delayed retry queue (no immediate hammering)
                            add_to_auth_retry_queue(url)
                    except Exception as e:
                        print(f"       ❌ Error checking file: {e}")
                        not_saved_count += 1
                        failed_urls.append(url)
                else:
                    print(f"       ❌ File not saved")
                    not_saved_count += 1
                    failed_urls.append(url)
            
            # Final count after validation and cleanup
            files_after = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]) if os.path.exists(OUTPUT_DIR) else 0
            actual_new_files = files_after - files_before
            
            # Enhanced reporting
            print(f"  📊 BATCH RESULTS:")
            print(f"     ✅ Valid profiles saved: {valid_profiles_saved}")
            print(f"     📋 Auth pages queued for retry: {auth_pages_queued}")
            print(f"     ❌ Not saved: {not_saved_count}")
            print(f"     📁 Total new valid profiles: {valid_profiles_saved}")
            
            # Show retry queue status
            queue = load_auth_retry_queue()
            ready_retries = get_ready_auth_retries()
            print(f"     🔄 Total in retry queue: {len(queue)}")
            print(f"     ⏰ Ready for retry now: {len(ready_retries)}")
            
            # Sanity check
            if actual_new_files != valid_profiles_saved:
                print(f"     ⚠️  File count mismatch! Expected {valid_profiles_saved}, got {actual_new_files}")
            
            total_failed = len(failed_urls)
            return valid_profiles_saved, total_failed, failed_urls
        else:
            print(f"  ❌ AppleScript error: {result.stderr}")
            return 0, len(urls_batch), urls_batch  # All failed
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ Batch timed out")
        return 0, len(urls_batch), urls_batch
    except Exception as e:
        print(f"  💥 Error processing batch: {e}")
        return 0, len(urls_batch), urls_batch

def get_current_stats():
    """Get current statistics of saved files."""
    try:
        if not os.path.exists(OUTPUT_DIR):
            return 0, 0
        
        html_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]
        total_files = len(html_files)
        
        # Calculate total size
        total_size = 0
        for html_file in html_files:
            file_path = os.path.join(OUTPUT_DIR, html_file)
            try:
                total_size += os.path.getsize(file_path)
            except:
                pass
        
        return total_files, total_size
    except Exception as e:
        print(f"Error getting stats: {e}")
        return 0, 0

def main():
    """Main scraping function using Safari batch approach with delayed retry."""
    print("🍎 LinkedIn Safari Batch Scraper with Delayed Retry")
    print(f"Strategy: {BATCH_SIZE} profiles per batch, {WAIT_BETWEEN_BATCHES[0]}-{WAIT_BETWEEN_BATCHES[1]}s between batches")
    print(f"Delayed Retry: {DELAYED_RETRY_WAIT[0]//60}-{DELAYED_RETRY_WAIT[1]//60} min delays, clear cookies every {CLEAR_COOKIES_EVERY} batches")
    print("=" * 85)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load retry queue statistics
    retry_queue = load_auth_retry_queue()
    ready_retries = get_ready_auth_retries()
    
    # Get comprehensive stats
    initial_files, initial_size = get_current_stats()
    
    # Get URL counts for progress tracking
    try:
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            total_urls_in_file = len([url.strip() for url in f.readlines() if url.strip()])
    except:
        total_urls_in_file = 0
    
    processed_urls = get_processed_urls()
    failed_urls = get_failed_urls()
    remaining_urls = get_remaining_urls()
    
    print(f"📊 OVERALL PROGRESS:")
    print(f"   📁 Total profiles to collect: {total_urls_in_file}")
    print(f"   ✅ Already collected: {len(processed_urls)} profiles ({initial_size/1024/1024:.1f} MB)")
    print(f"   ❌ Previously failed: {len(failed_urls)} profiles")
    print(f"   📋 Remaining to try: {len(remaining_urls)} profiles")
    print(f"   📈 Collection rate so far: {len(processed_urls)/total_urls_in_file*100:.1f}%")
    
    print(f"\n🔄 DELAYED RETRY QUEUE:")
    print(f"   📋 Total in retry queue: {len(retry_queue)}")
    print(f"   ⏰ Ready for retry now: {len(ready_retries)}")
    if len(retry_queue) > 0:
        avg_attempts = sum(item.get('retry_attempts', 0) for item in retry_queue) / len(retry_queue)
        print(f"   📈 Average retry attempts: {avg_attempts:.1f}")
    print()
    
    # Process delayed retries first if any are ready
    if ready_retries:
        print("🔄 PROCESSING DELAYED RETRIES FIRST...")
        retry_successes, retry_failures = process_delayed_retries()
        print(f"✅ Delayed retry session: {retry_successes} successes, {retry_failures} failures")
        print()
    
    if not remaining_urls:
        print("🎉 All URLs have been processed!")
        if retry_queue:
            print(f"📋 {len(retry_queue)} URLs still in retry queue - they will be retried when ready")
        return
    
    session_profiles_saved = 0
    session_profiles_failed = 0
    session_urls_tried = 0
    session_auth_queued = 0
    batch_num = 1
    
    # Process URLs in batches
    for i in tqdm(range(0, len(remaining_urls), BATCH_SIZE), desc="Processing batches"):
        batch_urls = remaining_urls[i:i+BATCH_SIZE]
        session_urls_tried += len(batch_urls)
        
        print(f"\n📦 BATCH {batch_num}: URLs {i+1}-{min(i+BATCH_SIZE, len(remaining_urls))}")
        for j, url in enumerate(batch_urls, 1):
            print(f"  {j}. {url}")
        
        # Process the batch
        profiles_saved, profiles_failed, failed_urls_list = process_batch(batch_urls, batch_num)
        session_profiles_saved += profiles_saved
        session_profiles_failed += profiles_failed
        
        # Add only the actually failed URLs to failed list
        for failed_url in failed_urls_list:
            add_to_failed_urls(failed_url)
        
        # Save progress (using session totals)
        save_progress(batch_num, session_profiles_saved, session_profiles_failed)
        
        # Get current file stats
        current_files, current_size = get_current_stats()
        total_collected_now = len(processed_urls) + session_profiles_saved
        total_failed_now = len(failed_urls) + session_profiles_failed
        
        print(f"\n📊 BATCH {batch_num} RESULTS:")
        print(f"   🆕 New profiles saved this batch: {profiles_saved}")
        print(f"   ❌ Failed this batch: {profiles_failed}")
        print(f"   📁 Total profiles on disk: {current_files} ({current_size/1024/1024:.1f} MB)")
        
        print(f"\n📊 SESSION PROGRESS:")
        print(f"   🔄 URLs tried this session: {session_urls_tried}")
        print(f"   ✅ Profiles saved this session: {session_profiles_saved}")
        print(f"   ❌ Profiles failed this session: {session_profiles_failed}")
        
        print(f"\n📊 OVERALL PROGRESS:")
        print(f"   📁 Total to collect: {total_urls_in_file}")
        print(f"   ✅ Total collected: {total_collected_now} ({total_collected_now/total_urls_in_file*100:.1f}%)")
        print(f"   ❌ Total failed: {total_failed_now} ({total_failed_now/total_urls_in_file*100:.1f}%)")
        print(f"   📋 Remaining: {len(remaining_urls) - session_urls_tried}")
        
        # Calculate and show success rates
        if session_profiles_saved + session_profiles_failed > 0:
            session_rate = (session_profiles_saved / (session_profiles_saved + session_profiles_failed)) * 100
            print(f"   📈 Session success rate: {session_rate:.1f}%")
        
        if total_collected_now + total_failed_now > 0:
            overall_rate = (total_collected_now / (total_collected_now + total_failed_now)) * 100
            print(f"   📈 Overall success rate: {overall_rate:.1f}%")
        
        # Wait between batches (except for the last one)
        if i + BATCH_SIZE < len(remaining_urls):
            wait_time = random.uniform(*WAIT_BETWEEN_BATCHES)
            print(f"\n💤 Waiting {wait_time:.1f} seconds before next batch...")
            
            # Check for ready delayed retries during wait time
            ready_retries = get_ready_auth_retries()
            if ready_retries:
                print(f"🔄 Found {len(ready_retries)} ready delayed retries during wait...")
                retry_successes, retry_failures = process_delayed_retries()
                session_profiles_saved += retry_successes
                session_profiles_failed += retry_failures
                print(f"✅ Processed delayed retries: {retry_successes} successes, {retry_failures} failures")
            
            time.sleep(wait_time)
        
        batch_num += 1
    
    # Final statistics
    final_files, final_size = get_current_stats()
    final_processed = len(get_processed_urls())
    final_failed = len(get_failed_urls())
    
    print(f"\n🏁 SAFARI SCRAPING SESSION COMPLETED!")
    print(f"=" * 50)
    print(f"📊 SESSION SUMMARY:")
    print(f"   🔄 URLs tried: {session_urls_tried}")
    print(f"   ✅ Profiles saved: {session_profiles_saved}")
    print(f"   ❌ Profiles failed: {session_profiles_failed}")
    
    print(f"\n📊 FINAL OVERALL STATUS:")
    print(f"   📁 Total profiles to collect: {total_urls_in_file}")
    print(f"   ✅ Total collected: {final_processed} ({final_processed/total_urls_in_file*100:.1f}%)")
    print(f"   ❌ Total failed: {final_failed} ({final_failed/total_urls_in_file*100:.1f}%)")
    print(f"   📁 Files on disk: {final_files} ({final_size/1024/1024:.1f} MB)")
    
    remaining_after = get_remaining_urls()
    print(f"   📋 Still remaining: {len(remaining_after)} profiles")
    
    if session_profiles_saved + session_profiles_failed > 0:
        session_success_rate = (session_profiles_saved / (session_profiles_saved + session_profiles_failed)) * 100
        print(f"   📈 Session success rate: {session_success_rate:.1f}%")
    
    if final_processed + final_failed > 0:
        overall_success_rate = (final_processed / (final_processed + final_failed)) * 100
        print(f"   📈 Overall success rate: {overall_success_rate:.1f}%")

if __name__ == "__main__":
    main() 