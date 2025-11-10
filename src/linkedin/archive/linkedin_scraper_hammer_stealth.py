#!/usr/bin/env python3
"""
LinkedIn Hammer + Stealth Scraper for Other Groups Dataset
Combines multiple attempts per profile with anti-detection features
"""
import os
import time
import random
import json
import re
import shutil
import tempfile
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.keys import Keys

# Hammering Configuration
ATTEMPTS_PER_PROFILE = 20  # Number of attempts on the SAME profile
WAIT_BETWEEN_HAMMER_ATTEMPTS = (2, 5)  # 2-5 seconds between attempts
WAIT_AFTER_LOAD_ATTEMPT = (1, 3)  # 1-3 seconds after page load
PROFILES_PER_SESSION = 3  # Fewer profiles per session for stealth
BREAK_BETWEEN_SESSIONS = (180, 300)  # 3-5 minutes between sessions
LONG_BREAK_AFTER_FAILURES = (300, 600)  # 5-10 minute break if failures
PAGE_LOAD_TIMEOUT = 25
HTML_MIN_LENGTH_THRESHOLD = 2500

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/"
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/other_groups_htmls"
TEMP_HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/temp_htmls"
FAILED_URLS_FILE = os.path.join(OUTPUT_DIR, "other_groups_failed_urls.txt")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "hammer_stealth_progress.json")

# Enhanced user agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

def setup_driver():
    """Configure Chrome with enhanced stealth settings."""
    chrome_options = Options()
    
    # Stealth arguments
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Additional stealth
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    
    # Random window size
    width = random.randint(1200, 1920)
    height = random.randint(800, 1080)
    chrome_options.add_argument(f"--window-size={width},{height}")
    
    # Disable images for faster loading
    prefs = {
        "profile.default_content_setting_values": {
            "images": 2,  # Block images
            "plugins": 2,  # Block plugins
            "popups": 2,  # Block popups
            "geolocation": 2,  # Block location
            "notifications": 2,  # Block notifications
            "media_stream": 2,  # Block media stream
        },
        "profile.managed_default_content_settings": {
            "images": 2
        }
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Random user agent
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="linkedin_hammer_chrome_")
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Enhanced stealth JavaScript
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({state: 'granted'})
                })
            });
        """)
        
        print(f"✓ Stealth Chrome session created (UA: {user_agent[:50]}...)")
        return driver, temp_dir
    except Exception as e:
        print(f"✗ Error creating Chrome driver: {e}")
        if 'temp_dir' in locals() and temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
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
    """Get URLs that have been successfully processed."""
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

def add_to_failed_urls(profile_url):
    """Add a URL to the failed URLs file."""
    try:
        os.makedirs(os.path.dirname(FAILED_URLS_FILE), exist_ok=True)
        with open(FAILED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(profile_url + '\n')
    except Exception as e:
        print(f"Error adding URL to failed list: {e}")

def is_valid_profile_html(html_file_path, original_url, current_url_on_load):
    """Check if HTML contains valid profile data."""
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

        # Auth keywords and profile markers
        auth_keywords_in_html = [
            'authwall', 'login', 'sign in', 'signin', 'checkpoint', 'challenge', 'verify',
            'unlock', 'join now', 'create account', 'access denied'
        ]
        profile_keywords_content = ['experience', 'education', 'skills', 'about', 'accomplishments']
        profile_selectors_structural = [
            'div[class*="pv-top-card"]', 'section[class*="artdeco-card"]',
            'main[class*="scaffold-layout__main"]', 'div#experience', 'div#education'
        ]

        # Check for auth title
        is_auth_title = any(auth_word in title_text_lower for auth_word in ['sign in', 'authwall', 'security verification'])
        if is_auth_title:
            print(f"[Check: 🚫AuthTitle]", end=" ")
            return False

        # Check URL redirect
        auth_indicators_url = ["authwall", "login", "checkpoint", "challenge", "verify", "signin"]
        was_direct_auth_url = any(indicator in current_url_on_load.lower() for indicator in auth_indicators_url)

        # Check structural elements
        found_any_structural_selector = any(soup.select_one(sel) for sel in profile_selectors_structural)
        profile_keyword_score = sum(1 for pk in profile_keywords_content if pk in html_lower)
        auth_keyword_count_body = sum(1 for keyword in auth_keywords_in_html if keyword in html_lower)

        # Decision logic
        if was_direct_auth_url:
            if found_any_structural_selector and profile_keyword_score >= 2 and auth_keyword_count_body < 3:
                print(f"[Check: ✅OverrideAuth]", end=" ")
                return True
            else:
                print(f"[Check: 🚫AuthURL]", end=" ")
                return False

        if found_any_structural_selector and profile_keyword_score >= 1:
            if auth_keyword_count_body <= 3:
                print(f"[Check: ✅Valid]", end=" ")
                return True

        if profile_keyword_score >= 3 and auth_keyword_count_body <= 1:
            print(f"[Check: ✅TextProfile]", end=" ")
            return True

        print(f"[Check: 🚫Invalid]", end=" ")
        return False

    except Exception as e:
        print(f"[Check: 💥Error]", end=" ")
        return False

def human_like_behavior(driver):
    """Add human-like scrolling and pauses."""
    try:
        # Random scroll
        for _ in range(random.randint(1, 3)):
            scroll_amount = random.randint(200, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.3, 0.8))
        
        # Sometimes scroll back up
        if random.random() < 0.3:
            driver.execute_script("window.scrollBy(0, -200);")
            time.sleep(random.uniform(0.2, 0.5))
    except:
        pass

def scrape_profile(driver, profile_url):
    """Hammer the profile with multiple attempts."""
    print(f"  🔨 Hammering: {profile_url}")
    print(f"    (Attempting {ATTEMPTS_PER_PROFILE} times)")
    
    os.makedirs(TEMP_HTML_DIR, exist_ok=True)
    permanent_file_name = get_html_filename(profile_url)
    permanent_file_path = os.path.join(HTML_DIR, permanent_file_name)

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
            
            # Add human-like behavior
            human_like_behavior(driver)
            
            current_url_on_load = driver.current_url
            auth_indicators_url = ["authwall", "login", "checkpoint", "challenge", "verify", "signin"]
            if any(indicator in current_url_on_load.lower() for indicator in auth_indicators_url):
                print(f"[Load: 🚫AuthURL]", end=" ")
                # Try to bypass
                try:
                    driver.execute_script("document.body.style.overflow = 'auto';")
                    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(1)
                except:
                    pass
            else:
                print(f"[Load: OK]", end=" ")

            html_content = driver.page_source
            with open(temp_file_path, 'w', encoding='utf-8') as f_temp:
                f_temp.write(html_content)
            print(f"[Save: TempOK]", end=" ")

            if is_valid_profile_html(temp_file_path, profile_url, current_url_on_load):
                os.makedirs(HTML_DIR, exist_ok=True)
                os.rename(temp_file_path, permanent_file_path)
                print(f"✅ SUCCESS!")
                return True
            else:
                try:
                    os.remove(temp_file_path)
                    print(f"[Del: TempOK]", end=" ")
                except:
                    pass
            
        except WebDriverException as wde:
            print(f"[DriverErr]", end="")
            if os.path.exists(temp_file_path): 
                os.remove(temp_file_path)
            if "disconnected" in str(wde).lower() or "session deleted" in str(wde).lower():
                print(" Raising!")
                raise
        except Exception as e:
            print(f"[Error]", end="")
            if os.path.exists(temp_file_path): 
                os.remove(temp_file_path)
        
        print()
        if attempt < ATTEMPTS_PER_PROFILE:
            time.sleep(random.uniform(*WAIT_BETWEEN_HAMMER_ATTEMPTS))

    print(f"  ❌ Failed after {ATTEMPTS_PER_PROFILE} attempts.")
    return False

def cleanup_temp_dir(temp_dir):
    """Clean up temporary directory."""
    try:
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
    """Main scraping function with hammering + stealth approach."""
    print("🔨 LinkedIn Hammer + Stealth Scraper Starting...")
    print(f"Strategy: {PROFILES_PER_SESSION} profiles per session, {ATTEMPTS_PER_PROFILE} attempts per profile")
    print("=" * 50)
    
    session_num = 1
    total_scraped_overall = 0
    total_failed_overall = 0
    consecutive_profile_failures = 0
    
    while True:
        remaining_urls = get_remaining_urls()
        if not remaining_urls:
            print("🎉 All URLs have been processed!")
            break
        
        print(f"\n🔄 Session {session_num} - Processing up to {PROFILES_PER_SESSION} profiles")
        print("-" * 50)
        
        driver = None
        temp_dir = None
        profiles_scraped_this_session = 0
        profiles_failed_this_session = 0
        force_session_restart = False
        
        try:
            driver, temp_dir = setup_driver()
            
            for i in range(min(PROFILES_PER_SESSION, len(remaining_urls))):
                if force_session_restart:
                    print("    ⚠️ Driver issue detected. Restarting session.")
                    break
                
                profile_url = remaining_urls[i]
                print(f"\n📄 Profile {i+1}/{min(PROFILES_PER_SESSION, len(remaining_urls))}: {profile_url}")
                
                try:
                    success = scrape_profile(driver, profile_url)
                    if success:
                        profiles_scraped_this_session += 1
                        total_scraped_overall += 1
                        consecutive_profile_failures = 0
                        print(f"  ✅ Scraped! (Session: {profiles_scraped_this_session}, Total: {total_scraped_overall})")
                    else:
                        profiles_failed_this_session += 1
                        total_failed_overall += 1
                        consecutive_profile_failures += 1
                        add_to_failed_urls(profile_url)
                        print(f"  ❌ Failed! (Session: {profiles_failed_this_session}, Total: {total_failed_overall})")
                except WebDriverException:
                    print(f"  💥 Driver error")
                    profiles_failed_this_session += 1
                    total_failed_overall += 1
                    consecutive_profile_failures += 1
                    add_to_failed_urls(profile_url)
                    force_session_restart = True
                
                if i < min(PROFILES_PER_SESSION, len(remaining_urls)) - 1 and not force_session_restart:
                    time.sleep(random.uniform(10, 20))
            
            print(f"\n📊 Session {session_num} Summary:")
            print(f"  Scraped: {profiles_scraped_this_session}, Failed: {profiles_failed_this_session}")
            save_progress(session_num, total_scraped_overall, total_failed_overall)

        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by user.")
            break
        except Exception as e:
            print(f"\n💥 Session Error: {e}")
            force_session_restart = True
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if temp_dir:
                cleanup_temp_dir(temp_dir)
        
        session_num += 1
        
        if consecutive_profile_failures >= 2:
            print(f"\n⚠️  Multiple failures. Taking a long break...")
            time.sleep(random.uniform(*LONG_BREAK_AFTER_FAILURES))
            consecutive_profile_failures = 0
        else:
            print(f"\n💤 Taking a {BREAK_BETWEEN_SESSIONS[0]//60}-{BREAK_BETWEEN_SESSIONS[1]//60} min break...")
            time.sleep(random.uniform(*BREAK_BETWEEN_SESSIONS))
    
    print(f"\n🏁 Scraping Completed!")
    print(f"📊 Final Stats: {total_scraped_overall} scraped, {total_failed_overall} failed")
    if total_scraped_overall + total_failed_overall > 0:
        success_rate = (total_scraped_overall / (total_scraped_overall + total_failed_overall)) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main() 