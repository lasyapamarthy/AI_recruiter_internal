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
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/safari_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/safari_failed_urls.txt"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/safari_progress.json"

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

def is_valid_profile_html(html_file_path):
    """Strict validation to reject auth walls and ensure we only keep real profiles."""
    try:
        # Try multiple encodings to handle different file formats
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
            print(f"[EncodingErr: Could not decode file]", end=" ")
            return False

        # Check file size - auth walls are typically small (under 100KB)
        file_size = len(html_content)
        if file_size < 150000:  # 150KB minimum for real profiles
            print(f"[Size: {file_size//1000}KB - TOO SMALL]", end=" ")
            return False

        html_lower = html_content.lower()
        
        # Check for profile content indicators FIRST
        profile_indicators = [
            'experience',
            'education', 
            'skills',
            'about',
            'recommendations',
            'accomplishments',
            'profile-section-card',
            'experience__list',
            'education__list',
            'experience-item',
            'education-item'
        ]
        
        profile_score = sum(1 for indicator in profile_indicators if indicator in html_lower)
        
        # If we have strong profile indicators and good size, it's likely a real profile
        if file_size > 200000 and profile_score >= 5:  # 200KB+ with 5+ indicators = definitely real
            print(f"[ACCEPT: Strong profile - {profile_score} indicators, {file_size//1000}KB]", end=" ")
            return True
        
        # STRICT AUTH WALL DETECTION - but only for smaller/weaker profiles
        auth_wall_phrases = [
            'authwall-sign-in-form',
            'authentication-outlet', 
            'sign in with google',
            'continue to join or sign in',
            'join now to see',
            'sign up to see',
            'log in to see',
            'create account to see'
        ]
        
        auth_count = 0
        for phrase in auth_wall_phrases:
            if phrase in html_lower:
                auth_count += 1
                print(f"[Auth: '{phrase}']", end=" ")
        
        # Only reject if multiple strong auth indicators AND weak profile content
        if auth_count >= 2 and profile_score < 3:
            print(f"[REJECT: {auth_count} auth phrases, weak content]", end=" ")
            return False
        
        # Check for the specific "sign in to view" phrase - but be lenient if good content
        sign_in_view_count = html_lower.count('sign in to view')
        if sign_in_view_count > 0:
            if profile_score >= 4 and file_size > 180000:  # Good content overrides this phrase
                print(f"[ACCEPT: Good content despite 'sign in to view' - {profile_score} indicators, {file_size//1000}KB]", end=" ")
                return True
            elif sign_in_view_count > 3:  # Multiple instances = likely auth wall
                print(f"[REJECT: Multiple 'sign in to view' ({sign_in_view_count}), weak content]", end=" ")
                return False
        
        # Final check: need minimum profile content
        if profile_score < 3:
            print(f"[REJECT: Only {profile_score} profile indicators]", end=" ")
            return False
        
        print(f"[ACCEPT: {profile_score} profile indicators, {file_size//1000}KB]", end=" ")
        return True
        
    except Exception as e:
        print(f"[ValidErr: {str(e)[:30]}]", end=" ")
        return False

def create_applescript():
    """Create the AppleScript file for batch downloading."""
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
        
        -- Wait for pages to load
        delay 10
        
        -- Save each tab
        repeat with i from 1 to count of urlList
            try
                set current tab of window 1 to tab i of window 1
                delay 2
                
                -- Get the page source and save it
                set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
                set filename to item i of filenameList & ".html"
                
                set fileRef to open for access filename with write permission
                write pageSource to fileRef
                close access fileRef
                
            on error errMsg
                -- If there's an error, just continue to next tab
                try
                    close access fileRef
                end try
            end try
        end repeat
        
        -- Close all tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
    end tell
end run
'''
    
    applescript_path = os.path.join(SCRIPT_PATH, "safari_batch_download.applescript")
    with open(applescript_path, 'w') as f:
        f.write(applescript_content)
    
    return applescript_path

def process_batch(urls_batch, batch_num):
    """Process a batch of URLs using Safari."""
    print(f"\n🍎 Processing batch {batch_num} with {len(urls_batch)} URLs")
    
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
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"  📄 AppleScript completed, checking saved files...")
            
            # Track results for each URL individually
            valid_profiles_saved = 0
            auth_walls_deleted = 0
            not_saved_count = 0
            failed_urls = []
            
            for i, (url, filename) in enumerate(zip(urls_batch, filenames_batch), 1):
                print(f"    {i}. ", end="")
                if os.path.exists(filename):
                    if is_valid_profile_html(filename):
                        print(f" ✅ (valid profile)")
                        valid_profiles_saved += 1
                    else:
                        print(f" ❌ (auth wall - deleting)")
                        try:
                            os.remove(filename)  # Delete auth wall
                            auth_walls_deleted += 1
                        except:
                            pass
                        failed_urls.append(url)
                else:
                    print(f" ❌ (not saved)")
                    not_saved_count += 1
                    failed_urls.append(url)
            
            # Final count after validation and cleanup - this should match valid_profiles_saved
            files_after = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]) if os.path.exists(OUTPUT_DIR) else 0
            actual_new_files = files_after - files_before
            
            # Sanity check - actual_new_files should equal valid_profiles_saved
            if actual_new_files != valid_profiles_saved:
                print(f"  ⚠️  Warning: File count mismatch! Expected {valid_profiles_saved}, got {actual_new_files}")
            
            print(f"  📊 Results: {valid_profiles_saved} new valid profiles saved")
            print(f"  📊 Breakdown: {valid_profiles_saved} valid, {auth_walls_deleted} auth walls deleted, {not_saved_count} not saved")
            
            # Return the actual number of valid profiles saved, not the file count difference
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
    """Main scraping function using Safari batch approach."""
    print("🍎 LinkedIn Safari Batch Scraper")
    print(f"Strategy: {BATCH_SIZE} profiles per batch, {WAIT_BETWEEN_BATCHES[0]}-{WAIT_BETWEEN_BATCHES[1]}s between batches")
    print("=" * 70)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
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
    print()
    
    if not remaining_urls:
        print("🎉 All URLs have been processed!")
        return
    
    session_profiles_saved = 0
    session_profiles_failed = 0
    session_urls_tried = 0
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