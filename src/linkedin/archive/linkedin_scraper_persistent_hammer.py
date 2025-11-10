#!/usr/bin/env python3
"""
LinkedIn Persistent Hammer Scraper for Other Groups Dataset
More aggressive hammering with 30 attempts per profile
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

# Hammering Configuration - More aggressive
ATTEMPTS_PER_PROFILE = 30  # Increased attempts
WAIT_BETWEEN_HAMMER_ATTEMPTS = (2, 3)  # 2-3 seconds as requested
WAIT_AFTER_LOAD_ATTEMPT = (1, 2)  # Quick wait after load
PROFILES_PER_SESSION = 10  # Process 10 profiles before break
BREAK_BETWEEN_SESSIONS = (120, 180)  # 2-3 minutes break after 10 profiles
LONG_BREAK_AFTER_FAILURES = (180, 300)  # 3-5 minute break if many failures
PAGE_LOAD_TIMEOUT = 20
HTML_MIN_LENGTH_THRESHOLD = 2000  # Slightly lower threshold

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/"
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/other_groups_htmls"
TEMP_HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/temp_htmls"
FAILED_URLS_FILE = os.path.join(OUTPUT_DIR, "other_groups_failed_urls.txt")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "persistent_hammer_progress.json")

# User agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

def setup_driver():
    """Configure Chrome with minimal detection features."""
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Basic stealth
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    
    # Random window size
    width = random.randint(1200, 1920)
    height = random.randint(800, 1080)
    chrome_options.add_argument(f"--window-size={width},{height}")
    
    # Don't block images - sometimes helps with detection
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })
    
    # Random user agent
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="linkedin_persistent_")
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print(f"✓ Chrome session created")
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
    """Strict validation to reject auth walls."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if len(html_content) < HTML_MIN_LENGTH_THRESHOLD:
            return False

        html_lower = html_content.lower()
        
        # STRICT AUTH WALL DETECTION - immediate rejection
        auth_wall_phrases = [
            'sign in to view',
            'join now to see',
            'sign up to see',
            'log in to see',
            'create account to see'
        ]
        
        for phrase in auth_wall_phrases:
            if phrase in html_lower:
                print(f"[AuthWall: '{phrase}']", end=" ")
                return False
        
        # Check for excessive sign-in prompts (auth walls have many)
        sign_in_count = html_lower.count('sign in')
        if sign_in_count > 5:  # Auth walls have many sign-in buttons
            print(f"[TooManySignIn: {sign_in_count}]", end=" ")
            return False
        
        # Check for auth-related URLs in content
        auth_url_indicators = [
            '/login?', '/uas/login', 'session_redirect', 'fromSignIn=true'
        ]
        
        auth_url_count = sum(1 for indicator in auth_url_indicators if indicator in html_content)
        if auth_url_count > 3:  # Auth walls have many login URLs
            print(f"[AuthURLs: {auth_url_count}]", end=" ")
            return False
        
        # Look for actual profile content indicators
        profile_indicators = [
            'pv-top-card',  # Profile top card
            'pv-entity',    # Profile entities
            'experience-item',  # Experience items
            'education-item',   # Education items
            'profile-section',  # Profile sections
            'artdeco-card',     # LinkedIn card components
        ]
        
        profile_structure_count = sum(1 for indicator in profile_indicators if indicator in html_content)
        
        # Must have actual profile structure, not just keywords
        if profile_structure_count < 2:
            print(f"[NoProfileStruct: {profile_structure_count}]", end=" ")
            return False
        
        # Additional check: look for profile-specific content
        profile_keywords = ['experience', 'education', 'skills', 'about', 'summary', 'background']
        profile_keyword_count = sum(1 for keyword in profile_keywords if keyword in html_lower)
        
        # Need both structure AND content
        if profile_structure_count >= 2 and profile_keyword_count >= 2:
            print(f"[Valid: Struct={profile_structure_count}, KW={profile_keyword_count}]", end=" ")
            return True
        
        print(f"[Reject: Struct={profile_structure_count}, KW={profile_keyword_count}]", end=" ")
        return False

    except Exception as e:
        print(f"[ValidErr: {str(e)[:20]}]", end=" ")
        return False

def scrape_profile(driver, profile_url):
    """Persistent hammering with 30 attempts."""
    print(f"\n🔨 Hammering: {profile_url}")
    
    os.makedirs(TEMP_HTML_DIR, exist_ok=True)
    permanent_file_name = get_html_filename(profile_url)
    permanent_file_path = os.path.join(HTML_DIR, permanent_file_name)

    if os.path.exists(permanent_file_path):
        print(f"  ✅ Already processed")
        return True

    for attempt in range(1, ATTEMPTS_PER_PROFILE + 1):
        if attempt % 10 == 1:  # Print every 10 attempts
            print(f"  Attempts {attempt}-{min(attempt+9, ATTEMPTS_PER_PROFILE)}...", end="", flush=True)
        
        temp_file_name = f"temp_{permanent_file_name}_attempt_{attempt}.html"
        temp_file_path = os.path.join(TEMP_HTML_DIR, temp_file_name)

        try:
            driver.get(profile_url)
            time.sleep(random.uniform(*WAIT_AFTER_LOAD_ATTEMPT))
            
            current_url = driver.current_url
            
            # Quick scroll to trigger content loading
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, 0);")
            
            # Try to dismiss any popups
            try:
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            except:
                pass

            html_content = driver.page_source
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            if is_valid_profile_html(temp_file_path, profile_url, current_url):
                os.makedirs(HTML_DIR, exist_ok=True)
                os.rename(temp_file_path, permanent_file_path)
                print(f" ✅ SUCCESS at attempt {attempt}!")
                return True
            else:
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                if attempt % 10 == 0:
                    print(" ❌", end="", flush=True)
            
        except Exception as e:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            if attempt % 10 == 0:
                print(" ⚠️", end="", flush=True)
        
        # Wait between attempts
        if attempt < ATTEMPTS_PER_PROFILE:
            time.sleep(random.uniform(*WAIT_BETWEEN_HAMMER_ATTEMPTS))

    print(f"\n  ❌ Failed after {ATTEMPTS_PER_PROFILE} attempts")
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
    """Main scraping function with persistent hammering."""
    print("🔨 LinkedIn Persistent Hammer Scraper")
    print(f"Strategy: {ATTEMPTS_PER_PROFILE} attempts per profile, {PROFILES_PER_SESSION} profiles per session")
    print("=" * 50)
    
    session_num = 1
    total_scraped = 0
    total_failed = 0
    
    while True:
        remaining_urls = get_remaining_urls()
        if not remaining_urls:
            print("\n🎉 All URLs processed!")
            break
        
        print(f"\n🔄 Session {session_num}")
        print("-" * 50)
        
        driver = None
        temp_dir = None
        session_scraped = 0
        session_failed = 0
        
        try:
            driver, temp_dir = setup_driver()
            
            # Process batch of profiles
            for i in range(min(PROFILES_PER_SESSION, len(remaining_urls))):
                profile_url = remaining_urls[i]
                
                try:
                    success = scrape_profile(driver, profile_url)
                    if success:
                        session_scraped += 1
                        total_scraped += 1
                    else:
                        session_failed += 1
                        total_failed += 1
                        add_to_failed_urls(profile_url)
                except Exception as e:
                    print(f"  💥 Error: {str(e)[:50]}")
                    session_failed += 1
                    total_failed += 1
                    add_to_failed_urls(profile_url)
                
                # Small wait between profiles
                if i < min(PROFILES_PER_SESSION, len(remaining_urls)) - 1:
                    time.sleep(random.uniform(5, 10))
            
            print(f"\n📊 Session {session_num}: {session_scraped} scraped, {session_failed} failed")
            print(f"📊 Total: {total_scraped} scraped, {total_failed} failed")
            save_progress(session_num, total_scraped, total_failed)

        except KeyboardInterrupt:
            print("\n⏹️  Interrupted")
            break
        except Exception as e:
            print(f"\n💥 Session error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if temp_dir:
                cleanup_temp_dir(temp_dir)
        
        session_num += 1
        
        # Take break between sessions
        if remaining_urls and len(remaining_urls) > PROFILES_PER_SESSION:
            wait_time = random.uniform(*BREAK_BETWEEN_SESSIONS)
            print(f"\n💤 Taking {wait_time/60:.1f} minute break...")
            time.sleep(wait_time)
    
    print(f"\n🏁 Final: {total_scraped} scraped, {total_failed} failed")
    if total_scraped + total_failed > 0:
        success_rate = (total_scraped / (total_scraped + total_failed)) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main() 