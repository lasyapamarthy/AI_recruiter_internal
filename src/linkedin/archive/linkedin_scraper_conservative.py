#!/usr/bin/env python3
import os
import time
import random
import json
import pickle
import csv
import re
import glob
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, SessionNotCreatedException
from selenium.webdriver.common.keys import Keys

# Hammering Configuration (Chrome)
ATTEMPTS_PER_PROFILE = 30  # Number of quick hits on the SAME profile
WAIT_BETWEEN_HAMMER_ATTEMPTS = (1, 3)  # 1-3 seconds wait between these hits
WAIT_AFTER_LOAD_ATTEMPT = (1, 2) # 1-2 seconds after a page load attempt
PROFILES_PER_SESSION = 5     # Number of unique profiles to process per browser session
BREAK_BETWEEN_SESSIONS = (300, 480)  # 5-8 minutes break between browser sessions
LONG_BREAK_AFTER_FAILURES = (600, 900) # 10-15 minute break if multiple profiles fail consecutively
PAGE_LOAD_TIMEOUT = 20 # Shorter page load for faster attempts
HTML_MIN_LENGTH_THRESHOLD = 2500 # Min bytes for a potentially valid profile HTML

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/"
PROCESSED_URLS_FILE = os.path.join(OUTPUT_DIR, "processed_urls.txt") # Not directly used by save_html anymore, but good for tracking
FAILED_URLS_FILE = os.path.join(OUTPUT_DIR, "failed_urls.txt")
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
TEMP_HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/temp_htmls" # For temporary saves
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "scraper_progress.json")

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

def setup_driver():
    """Configure and return Chrome webdriver with fresh incognito session."""
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="linkedin_scraper_chrome_") # Unique prefix
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_settings.popups": 0,
    })
    
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print(f"✓ Fresh Chrome incognito session created (User Agent: {user_agent})")
        return driver, temp_dir
    except Exception as e:
        print(f"✗ Error creating Chrome driver: {e}")
        # Attempt to cleanup temp_dir if driver creation fails
        if 'temp_dir' in locals() and temp_dir:
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as ce:
                print(f"    Could not cleanup temp_dir {temp_dir}: {ce}")
        raise

def clean_linkedin_url(url):
    """Clean and standardize LinkedIn URLs."""
    if not url or url.lower() == 'na':
        return None
    
    url = url.lstrip('@')
    
    if not url.startswith('https://'):
        url = 'https://' + url.replace('http://', '')
    
    url = re.sub(r'https://([a-z]{2}\.)(www\.)?linkedin\.com', r'https://www.linkedin.com', url)
    
    if 'www.' not in url:
        url = url.replace('linkedin.com', 'www.linkedin.com')
    
    url = url.rstrip('/').split('?')[0]
    return url

def get_html_filename(profile_url):
    """Create a valid filename from the URL."""
    clean_url = profile_url.split('?')[0]
    filename = clean_url.replace("https://", "").replace("www.", "").replace("/", "_")
    return f"{filename}.html"

def get_processed_urls():
    """Get URLs that have been successfully processed (have HTML files)."""
    processed_urls = set()
    
    try:
        if os.path.exists(HTML_DIR):
            for html_file in os.listdir(HTML_DIR):
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
    """Get URLs that have failed after max retries."""
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

def save_html(profile_url, html_content):
    """Save HTML content to a file."""
    os.makedirs(HTML_DIR, exist_ok=True)
    
    filename = get_html_filename(profile_url)
    file_path = os.path.join(HTML_DIR, filename)
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return file_path
    except Exception as e:
        print(f"Error saving HTML file: {e}")
        return None

def add_to_failed_urls(profile_url):
    """Add a URL to the failed URLs file."""
    try:
        os.makedirs(os.path.dirname(FAILED_URLS_FILE), exist_ok=True)
        with open(FAILED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(profile_url + '\n')
    except Exception as e:
        print(f"Error adding URL to failed list: {e}")

def is_valid_profile_html(html_file_path, original_url, current_url_on_load):
    """Analyzes a saved HTML file to determine if it's a valid profile. current_url_on_load is the URL captured immediately after driver.get()"""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if len(html_content) < HTML_MIN_LENGTH_THRESHOLD:
            print(f"[Check: 📄TinyHTML {len(html_content)}b]", end=" ")
            return False

        html_lower = html_content.lower()
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.title
        title_text_lower = title_tag.string.lower() if title_tag and title_tag.string else ""

        # Define auth keywords and profile markers
        auth_keywords_in_html = [
            'authwall', 'login', 'sign in', 'signin', 'checkpoint', 'challenge', 'verify',
            'unlock', 'join now', 'create account', 'access denied', 'session timed out',
            'not authorized', 'request blocked', 'are you human', 'prove you\'re human'
        ]
        profile_keywords_content = ['experience', 'education', 'recommendations', 'skills', 'accomplishments', 'about', 'projects', 'courses', 'licenses & certifications']
        profile_selectors_structural = [
            'div[class*="pv-top-card"]', 'section[class*="artdeco-card"][class*="pv-profile-section"]',
            'main[class*="scaffold-layout__main"]', 'h1[class*="text-heading-xlarge"]',
            'ul[class*="experience__list"]', 'ul[class*="education__list"]',
            'div#experience', 'div#education', 'div#licenses_and_certifications',
            'section[aria-label*="experience"]', 'section[aria-label*="education"]',
            'div[id*="ember"][class*="profile-content"]', '.profile-outlet'
        ]

        # --- Start of Checks ---

        # Check 1: Title Tag - strong indicator
        is_auth_title = any(auth_word in title_text_lower for auth_word in ['sign in', 'authwall', 'security verification', 'join linkedin', 'challenge'])
        is_generic_linkedin_title = title_text_lower == "linkedin"
        
        if is_auth_title:
            print(f"[Check: 🚫AuthTitle '{title_text_lower[:30]}...']", end=" ")
            return False

        # Check 2: Was the URL immediately after loading an authwall URL?
        auth_indicators_url = ["authwall", "login", "checkpoint", "challenge", "verify", "signin"]
        was_direct_auth_url = any(indicator in current_url_on_load.lower() for indicator in auth_indicators_url)

        # Check 3: Structural profile elements & Content keywords
        found_any_structural_selector = any(soup.select_one(sel) for sel in profile_selectors_structural)
        profile_keyword_score = sum(1 for pk in profile_keywords_content if pk in html_lower) 

        # Check 4: Auth keywords in HTML body
        auth_keyword_count_body = sum(1 for keyword in auth_keywords_in_html if keyword in html_lower)

        # --- Decision Logic ---

        # Scenario A: URL loaded was an authwall URL
        if was_direct_auth_url:
            if found_any_structural_selector and profile_keyword_score >= 2 and auth_keyword_count_body < 3:
                print(f"[Check: ✅OverrideAuthURL (Struct:{found_any_structural_selector}, KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body})]", end=" ")
                return True
            else:
                print(f"[Check: 🚫RetainAuthURL (Struct:{found_any_structural_selector}, KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body})]", end=" ")
                return False

        # Scenario B: URL loaded was NOT an authwall URL (e.g., /in/profile_name)
        if found_any_structural_selector and profile_keyword_score >= 1: # Require at least one content keyword if structure is found
            if auth_keyword_count_body <= 3: # Tolerate up to 3 auth keywords in body if good structure & some content words
                print(f"[Check: ✅GoodStruct (KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body})]", end=" ")
                return True
            else:
                print(f"[Check: 🤔GoodStructButHighAuth (KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body})]", end=" ")
                # Fall through, might be rejected by later checks
        
        if not found_any_structural_selector and profile_keyword_score >= 3 and auth_keyword_count_body <=1: # If no structure, but many profile KWs and few auth KWs
             print(f"[Check: ✅TextHeavyProfile (KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body})]", end=" ")
             return True

        if is_generic_linkedin_title and not found_any_structural_selector and profile_keyword_score < 2:
            print(f"[Check: 🚫GenericTitleLowMarkers (AuthBody:{auth_keyword_count_body})]", end=" ")
            return False
            
        if not found_any_structural_selector and profile_keyword_score < 2 and auth_keyword_count_body > 1:
            print(f"[Check: 🤔LowProfileMarkersHighAuthBody (AuthBody:{auth_keyword_count_body})]", end=" ")
            return False

        if profile_keyword_score == 0 and auth_keyword_count_body > 0:
             print(f"[Check: 🤔NoProfileKWsSomeAuth (AuthBody:{auth_keyword_count_body})]", end=" ")
             return False

        if profile_keyword_score >= 1 and auth_keyword_count_body <= 1: # More lenient if at least one profile KW and very few auth KWs
            print(f"[Check: ✅LenientPass (KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body})]", end=" ")
            return True

        print(f"[Check: DefaultReject (Struct:{found_any_structural_selector}, KWScore:{profile_keyword_score}, AuthBody:{auth_keyword_count_body}, Title:'{title_text_lower[:20]}...')]", end=" ")
        return False

    except Exception as e:
        print(f"[Check: 💥ErrValidating '{str(e)[:30]}...']", end=" ")
        return False

def scrape_profile(driver, profile_url):
    """Hammer the same profile, save HTML each time, then analyze."""
    print(f"  🔨 Hammering (save & check): {profile_url}")
    print(f"    (Will attempt {ATTEMPTS_PER_PROFILE} times, waits: {WAIT_BETWEEN_HAMMER_ATTEMPTS[0]}-{WAIT_BETWEEN_HAMMER_ATTEMPTS[1]}s)")
    
    os.makedirs(TEMP_HTML_DIR, exist_ok=True) # Ensure temp dir exists
    permanent_file_name = get_html_filename(profile_url)
    permanent_file_path = os.path.join(HTML_DIR, permanent_file_name)

    # Check if already successfully processed (e.g. from a previous run)
    if os.path.exists(permanent_file_path):
        print(f"    🟢 Already processed: {permanent_file_name}")
        return True

    for attempt in range(1, ATTEMPTS_PER_PROFILE + 1):
        print(f"      Attempt {attempt}/{ATTEMPTS_PER_PROFILE}...", end=" ")
        temp_file_name = f"temp_{permanent_file_name}_attempt_{attempt}.html"
        temp_file_path = os.path.join(TEMP_HTML_DIR, temp_file_name)

        try:
            driver.get(profile_url)
            time.sleep(random.uniform(*WAIT_AFTER_LOAD_ATTEMPT))
            
            current_url_on_load = driver.current_url
            # Initial quick check if we were immediately redirected to an obvious auth wall URL
            auth_indicators_url = ["authwall", "login", "checkpoint", "challenge", "verify", "signin"]
            if any(indicator in current_url_on_load.lower() for indicator in auth_indicators_url):
                print(f"[Load: 🚫AuthURL '{current_url_on_load.split('?')[0]}']", end=" ")
                # Still save it, analysis function will make final call, but this is a strong hint
            else:
                print(f"[Load: OK '{current_url_on_load.split('?')[0]}']", end=" ")

            html_content = driver.page_source
            with open(temp_file_path, 'w', encoding='utf-8') as f_temp:
                f_temp.write(html_content)
            print(f"[Save: TempOK]", end=" ")

            # DEBUGGING: Save a copy of the first attempt for alejo-end for manual inspection
            if "alejo-end" in profile_url and attempt == 1:
                debug_save_path = os.path.join(TEMP_HTML_DIR, f"DEBUG_alejo-end_attempt_1.html")
                try:
                    import shutil
                    shutil.copyfile(temp_file_path, debug_save_path)
                    print(f"[DEBUG: Copied to {debug_save_path}]", end=" ")
                except Exception as e_debug_copy:
                    print(f"[DEBUG: Copy FAILED {e_debug_copy}]", end=" ")

            if is_valid_profile_html(temp_file_path, profile_url, current_url_on_load):
                os.makedirs(HTML_DIR, exist_ok=True)
                os.rename(temp_file_path, permanent_file_path)
                print(f"✅ RENAMED to {permanent_file_name} - SUCCESS!")
                return True # Successfully scraped and saved
            else:
                try:
                    os.remove(temp_file_path)
                    print(f"[Del: TempOK]", end=" ")
                except OSError as oe:
                    print(f"[Del: TempFail '{oe.strerror}']", end=" ")
            
        except WebDriverException as wde:
            print(f"[DriverErr: {str(wde)[:30]}...] ", end="")
            if os.path.exists(temp_file_path): os.remove(temp_file_path) # Clean up temp if error
            if "disconnected" in str(wde).lower() or "target new" in str(wde).lower() or "session deleted" in str(wde).lower():
                print("Raising to restart session!")
                raise # Re-raise critical driver errors to restart session
        except Exception as e:
            print(f"[GenericErr: {str(e)[:30]}...] ", end="")
            if os.path.exists(temp_file_path): os.remove(temp_file_path) # Clean up temp if error
        
        print() # Newline for next attempt's log line
        if attempt < ATTEMPTS_PER_PROFILE:
            time.sleep(random.uniform(*WAIT_BETWEEN_HAMMER_ATTEMPTS))

    print(f"  ❌ Failed to get valid HTML for {profile_url} after {ATTEMPTS_PER_PROFILE} attempts.")
    return False

def cleanup_temp_dir(temp_dir):
    """Clean up temporary directory."""
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass

def save_progress(session_num, profiles_scraped, profiles_failed):
    """Save progress to file."""
    progress = {
        "session": session_num,
        "profiles_scraped": profiles_scraped,
        "profiles_failed": profiles_failed,
        "timestamp": time.time()
    }
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except:
        pass

def main():
    """Main scraping function with intelligent, adaptive approach."""
    print("🚀 LinkedIn Intelligent Scraper Starting (using Chrome)...")
    print(f"Strategy: {PROFILES_PER_SESSION} profiles per session, {ATTEMPTS_PER_PROFILE} smart attempts per profile.")
    print("=" * 50)
    
    session_num = 1
    total_scraped_overall = 0
    total_failed_overall = 0
    consecutive_profile_failures_in_session = 0
    
    while True:
        remaining_urls = get_remaining_urls()
        if not remaining_urls:
            print("🎉 All URLs have been processed!")
            break
        
        print(f"\n🔄 Session {session_num} - Attempting up to {PROFILES_PER_SESSION} profiles with Chrome")
        print("-" * 50)
        
        driver = None
        temp_dir = None
        profiles_scraped_this_session = 0
        profiles_failed_this_session = 0
        force_session_restart = False
        
        try:
            driver, temp_dir = setup_driver() # Fresh browser for the session, ignore temp_dir
            
            for i in range(min(PROFILES_PER_SESSION, len(remaining_urls))):
                if force_session_restart:
                    print("    ⚠️ Driver issue detected. Ending current session early.")
                    break 
                
                profile_url = remaining_urls[i]
                print(f"\n📄 Processing Profile {i+1}/{min(PROFILES_PER_SESSION, len(remaining_urls))}: {profile_url}")
                
                try:
                    success = scrape_profile(driver, profile_url)
                    if success:
                        profiles_scraped_this_session += 1
                        total_scraped_overall += 1
                        consecutive_profile_failures_in_session = 0
                        print(f"  ✅ Profile Scraped! (Session: {profiles_scraped_this_session}, Total: {total_scraped_overall})")
                    else:
                        profiles_failed_this_session += 1
                        total_failed_overall += 1
                        consecutive_profile_failures_in_session += 1
                        add_to_failed_urls(profile_url) # Add to global failed list
                        print(f"  ❌ Profile Failed! (Session: {profiles_failed_this_session}, Total: {total_failed_overall})")
                except WebDriverException as wde_main: # Catch driver death from scrape_profile
                    print(f"  💥 Main loop caught WebDriverException for {profile_url}: {str(wde_main)[:100]}...")
                    profiles_failed_this_session += 1
                    total_failed_overall += 1
                    consecutive_profile_failures_in_session += 1
                    add_to_failed_urls(profile_url)
                    force_session_restart = True # Signal to end session and get new driver
                    print("    Marking session for restart due to driver failure.")
                except Exception as e_main:
                    print(f"  💥 Main loop caught unexpected Exception for {profile_url}: {e_main}")
                    profiles_failed_this_session += 1
                    total_failed_overall += 1
                    consecutive_profile_failures_in_session += 1
                    add_to_failed_urls(profile_url)

                if i < min(PROFILES_PER_SESSION, len(remaining_urls)) - 1 and not force_session_restart:
                    time.sleep(random.uniform(5, 10)) 
            
            print(f"\n📊 Session {session_num} Summary:")
            print(f"  Scraped: {profiles_scraped_this_session}, Failed: {profiles_failed_this_session}")
            save_progress(session_num, total_scraped_overall, total_failed_overall)

        except KeyboardInterrupt:
            print("\n⏹️  Scraping interrupted by user.")
            break
        except Exception as e_session:
            print(f"\n💥 Major Session Error (e.g. driver setup): {e_session}")
            force_session_restart = True 
        finally:
            if driver:
                try:
                    driver.quit()
                    print("  🧹 Browser session closed.")
                except:
                    pass 
            if temp_dir:
                cleanup_temp_dir(temp_dir)
        
        session_num += 1
        if force_session_restart:
            print("Driver or session issue, taking a short break before new session...")
            time.sleep(random.uniform(60,120))
            consecutive_profile_failures_in_session = 0 
            continue 

        if consecutive_profile_failures_in_session >= 2 and PROFILES_PER_SESSION > 1: 
            print(f"\n⚠️  {consecutive_profile_failures_in_session} consecutive profile failures. Taking a long break...")
            time.sleep(random.uniform(*LONG_BREAK_AFTER_FAILURES))
            consecutive_profile_failures_in_session = 0 
        else:
            print(f"\n💤 Taking a {BREAK_BETWEEN_SESSIONS[0]//60}-{BREAK_BETWEEN_SESSIONS[1]//60} min break between sessions...")
            time.sleep(random.uniform(*BREAK_BETWEEN_SESSIONS))
    
    print(f"\n🏁 Intelligent Scraping Completed (Chrome)!")
    print(f"📊 Final Stats: {total_scraped_overall} scraped, {total_failed_overall} failed.")
    if total_scraped_overall + total_failed_overall > 0:
        success_rate = (total_scraped_overall / (total_scraped_overall + total_failed_overall)) * 100
        print(f"📈 Overall success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main() 