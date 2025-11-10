#!/usr/bin/env python3
import os
import time
import random
import json
import pickle
import csv
import re
import glob
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, SessionNotCreatedException
from selenium.webdriver.common.keys import Keys

# Configuration
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/linkedin_urls.txt"
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
COOKIES_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/cookies"
EXPERIENCES_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/linkedin_experiences.csv"
PROCESSED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/processed_urls.txt"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/failed_urls.txt"
ATTEMPTED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/attempted_urls.txt"
MAX_RETRIES = 10  # Reduced retries to avoid endless loops
RETRIES_BEFORE_LONG_PAUSE = 5  # Take a long pause after this many retries
LONG_PAUSE_DURATION = 30  # Wait 30 seconds
WAIT_BETWEEN_RETRIES_SECONDS = [3, 5]  # Slightly longer wait times
WAIT_AFTER_SUCCESS_SECONDS = [2, 3]  # Moderate wait times
PROFILES_BEFORE_BREAK = 5  # More frequent breaks
BREAK_DURATION = 45  # Longer break duration
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

def setup_driver():
    """Configure and return Chrome webdriver with incognito mode."""
    chrome_options = Options()
    chrome_options.add_argument("--incognito")  # Back to incognito mode
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Additional anti-detection measures
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 1,
    })
    
    # Use a random user agent
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    try:
        # Initialize Chrome driver with retry logic
        max_driver_attempts = 3
        for attempt in range(max_driver_attempts):
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)  # Back to longer timeout
                
                # Spoof webdriver to avoid detection
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                return driver
            except Exception as e:
                print(f"Failed to create driver (attempt {attempt + 1}/{max_driver_attempts}): {e}")
                try:
                    if 'driver' in locals():
                        driver.quit()
                except:
                    pass
                
                if attempt < max_driver_attempts - 1:
                    time.sleep(5)
                else:
                    raise
    except Exception as e:
        print(f"Fatal error creating driver: {e}")
        raise

def get_html_filename(profile_url):
    """Create a valid filename from the URL."""
    # Remove URL parameters
    clean_url = profile_url.split('?')[0]
    filename = clean_url.replace("https://", "").replace("www.", "").replace("/", "_")
    filename = f"{filename}.html"
    return filename

def save_html(profile_url, html_content):
    """Save HTML content to a file."""
    os.makedirs(HTML_DIR, exist_ok=True)
    
    # Create a valid filename from the URL
    filename = get_html_filename(profile_url)
    file_path = os.path.join(HTML_DIR, filename)
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Add to processed URLs list
        add_to_processed_urls(profile_url)
        
        print(f"Successfully saved HTML to {file_path}")
        return file_path
    except Exception as e:
        print(f"Error saving HTML file: {e}")
        return None

def save_cookies(driver, name="linkedin_cookies"):
    """Save cookies from the current session."""
    try:
        os.makedirs(COOKIES_DIR, exist_ok=True)
        cookies_path = os.path.join(COOKIES_DIR, f"{name}.pkl")
        
        cookies = driver.get_cookies()
        
        # Only save if we have cookies
        if cookies:
            with open(cookies_path, "wb") as f:
                pickle.dump(cookies, f)
            print(f"Cookies saved to {cookies_path}")
            
            # Also save in JSON format for inspection
            json_path = os.path.join(COOKIES_DIR, f"{name}.json")
            with open(json_path, "w") as f:
                json.dump(cookies, f, indent=4)
            print(f"Cookies also saved as JSON to {json_path}")
    except Exception as e:
        print(f"Error saving cookies: {e}")

def load_cookies(driver, name="linkedin_cookies"):
    """Load cookies into the current session."""
    cookies_path = os.path.join(COOKIES_DIR, f"{name}.pkl")
    
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, "rb") as f:
                cookies = pickle.load(f)
            
            # Make sure we're on LinkedIn domain before adding cookies
            driver.get("https://www.linkedin.com/")
            time.sleep(2)  # Wait for page to load
            
            # Add cookies
            for cookie in cookies:
                # Handle browser compliance issues with sameSite
                if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = 'None'
                
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Error adding cookie: {e}")
            
            print(f"Loaded cookies from {cookies_path}")
            return True
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return False
    else:
        print(f"No cookies found at {cookies_path}")
        return False

def try_bypass_login_wall(driver):
    """Try various techniques to bypass LinkedIn login wall"""
    print("Attempting to bypass login wall...")
    
    # Wait for page to load
    time.sleep(3)
    
    # Try pressing Escape key to dismiss popups
    try:
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
    except Exception as e:
        print(f"Error sending Escape key: {e}")
    
    # Try clicking the X button on modals if present
    try:
        close_button_selectors = [
            "button.modal__dismiss",
            "button.artdeco-modal__dismiss", 
            "button.close-button",
            "button[aria-label='Dismiss']",
            "button.sign-in-modal__dismiss-btn"
        ]
        
        for selector in close_button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed():
                        print(f"Found close button ({selector}), clicking it")
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
            except:
                continue
    except Exception as e:
        print(f"Error finding/clicking close buttons: {e}")
    
    # Try removing the login overlay via JavaScript
    try:
        driver.execute_script("""
            // Remove any modal overlays
            var elements = document.querySelectorAll('.modal-wormhole, .artdeco-modal-overlay, .authentication-outlet, .global-nav__login');
            elements.forEach(e => e.remove());
            
            // Remove body class that prevents scrolling
            document.body.classList.remove('overflow-hidden');
            document.documentElement.classList.remove('overflow-hidden');
            
            // Remove blur effect
            document.body.style.filter = 'none';
            document.body.style.opacity = '1';
            
            // Reset overflow
            document.documentElement.style.overflow = 'auto';
            document.body.style.overflow = 'auto';
            document.body.style.position = 'static';
        """)
        time.sleep(2)
    except Exception as e:
        print(f"Error executing JavaScript to remove overlay: {e}")
    
    # Check if bypass was successful
    try:
        current_url = driver.current_url
        if "authwall" in current_url or "login" in current_url or "checkpoint" in current_url:
            print("Bypass unsuccessful, still at login/auth page")
            return False
        
        # Additional check for profile content
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-background-image, .pv-top-card, .core-rail, .scaffold-layout__main"))
            )
            print("Profile elements found - bypass appears successful!")
            return True
        except TimeoutException:
            print("Profile elements not found after waiting")
            return False
            
    except Exception as e:
        print(f"Error checking bypass success: {e}")
        return False

def get_processed_urls():
    """Get a list of URLs that have actually been successfully processed (have HTML files)."""
    processed_urls = set()
    
    try:
        # Check the HTML directory for existing files - this is the source of truth
        if os.path.exists(HTML_DIR):
            for html_file in os.listdir(HTML_DIR):
                if html_file.endswith('.html'):
                    # Remove .html extension
                    url_part = html_file[:-5]
                    
                    # Extract the username from various filename formats
                    username = None
                    
                    # Handle different filename patterns
                    if '_in_' in url_part:
                        # Extract username after '_in_'
                        parts = url_part.split('_in_')
                        if len(parts) >= 2:
                            username = parts[-1]  # Take the last part after '_in_'
                            
                            # Clean up the username - remove trailing underscores and other artifacts
                            username = username.rstrip('_')
                            username = username.strip()
                    
                    if username:
                        # Create standardized URL
                        standardized_url = f'https://www.linkedin.com/in/{username}'
                        processed_urls.add(standardized_url)
                        
                        # Also add the cleaned version to catch any variations
                        cleaned_url = clean_linkedin_url(standardized_url)
                        if cleaned_url:
                            processed_urls.add(cleaned_url)
        
        print(f"Found {len(processed_urls)} URLs with actual HTML files")
        return processed_urls
    except Exception as e:
        print(f"Error getting processed URLs: {e}")
        return set()

def get_failed_urls():
    """Get a list of URLs that have failed after max retries."""
    failed_urls = set()
    try:
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                failed_urls.update(url.strip() for url in f.readlines() if url.strip())
        print(f"Found {len(failed_urls)} failed URLs")
        return failed_urls
    except Exception as e:
        print(f"Error getting failed URLs: {e}")
        return set()

def get_attempted_urls():
    """Get a list of URLs that have been attempted (for tracking purposes)."""
    attempted_urls = set()
    try:
        if os.path.exists(ATTEMPTED_URLS_FILE):
            with open(ATTEMPTED_URLS_FILE, 'r', encoding='utf-8') as f:
                attempted_urls.update(url.strip() for url in f.readlines() if url.strip())
        print(f"Found {len(attempted_urls)} attempted URLs")
        return attempted_urls
    except Exception as e:
        print(f"Error getting attempted URLs: {e}")
        return set()

def add_to_processed_urls(profile_url):
    """Add a URL to the processed URLs file only after successful HTML save."""
    try:
        # Only add to processed list if HTML file actually exists
        filename = get_html_filename(profile_url)
        file_path = os.path.join(HTML_DIR, filename)
        
        if os.path.exists(file_path):
            os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
            with open(PROCESSED_URLS_FILE, 'a', encoding='utf-8') as f:
                f.write(profile_url + '\n')
            print(f"Added {profile_url} to processed list")
        else:
            print(f"HTML file not found, not adding {profile_url} to processed list")
    except Exception as e:
        print(f"Error adding URL to processed list: {e}")

def add_to_failed_urls(profile_url):
    """Add a URL to the failed URLs file."""
    try:
        os.makedirs(os.path.dirname(FAILED_URLS_FILE), exist_ok=True)
        with open(FAILED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(profile_url + '\n')
        print(f"Added {profile_url} to failed list")
    except Exception as e:
        print(f"Error adding URL to failed list: {e}")

def add_to_attempted_urls(profile_url):
    """Add a URL to the attempted URLs file."""
    try:
        os.makedirs(os.path.dirname(ATTEMPTED_URLS_FILE), exist_ok=True)
        with open(ATTEMPTED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(profile_url + '\n')
        print(f"Added {profile_url} to attempted list")
    except Exception as e:
        print(f"Error adding URL to attempted list: {e}")

def clean_linkedin_url(url):
    """Clean and standardize LinkedIn URLs."""
    if not url or url.lower() == 'na':
        return None
    
    # Remove any leading @ symbol
    url = url.lstrip('@')
    
    # Ensure URL starts with https://
    if not url.startswith('https://'):
        url = 'https://' + url.replace('http://', '')
    
    # Remove regional prefixes (al., fr., de., etc.) from LinkedIn URLs
    # Pattern: https://XX.www.linkedin.com or https://XX.linkedin.com
    url = re.sub(r'https://([a-z]{2}\.)(www\.)?linkedin\.com', r'https://www.linkedin.com', url)
    
    # Ensure www. is present
    if 'www.' not in url:
        url = url.replace('linkedin.com', 'www.linkedin.com')
    
    # Remove trailing slashes and clean up
    url = url.rstrip('/')
    
    # Remove any query parameters
    url = url.split('?')[0]
    
    return url

def get_remaining_urls():
    """Get list of URLs that haven't been processed or failed yet."""
    try:
        # Get all URLs
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            all_urls = [url.strip() for url in f.readlines()]
        
        # Clean and filter URLs
        valid_urls = []
        for url in all_urls:
            cleaned_url = clean_linkedin_url(url)
            if cleaned_url and 'linkedin.com' in cleaned_url:
                valid_urls.append(cleaned_url)
            else:
                print(f"Skipping invalid URL: {url}")
        
        # Get processed and failed URLs
        processed_urls = get_processed_urls()
        failed_urls = get_failed_urls()
        
        # Debug: Show sample URLs for comparison
        print(f"\nDEBUG - Sample processed URLs:")
        for i, url in enumerate(sorted(processed_urls)):
            if i < 3:  # Show first 3
                print(f"  Processed: {url}")
        
        print(f"\nDEBUG - Sample valid URLs:")
        for i, url in enumerate(valid_urls):
            if i < 3:  # Show first 3
                print(f"  Valid: {url}")
        
        # Filter out processed and failed URLs
        remaining_urls = [url for url in valid_urls if url not in processed_urls and url not in failed_urls]
        
        print(f"\nTotal valid URLs: {len(valid_urls)}")
        print(f"Successfully processed: {len(processed_urls)}")
        print(f"Failed URLs: {len(failed_urls)}")
        print(f"Remaining to process: {len(remaining_urls)}")
        return remaining_urls
    except Exception as e:
        print(f"Error getting remaining URLs: {e}")
        return []

def scrape_profile(driver, profile_url):
    """Attempt to scrape a single LinkedIn profile with improved error handling."""
    print(f"\nAttempting to scrape: {profile_url}")
    
    # Mark as attempted
    add_to_attempted_urls(profile_url)
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Attempt {attempt}/{MAX_RETRIES}: Loading profile...")
            
            # Check if driver is still responsive
            try:
                current_url = driver.current_url
            except Exception as e:
                print(f"Driver appears to be dead: {e}")
                try:
                    driver.quit()
                except:
                    pass
                driver = setup_driver()
            
            # Load the profile URL with better error handling
            try:
                driver.get(profile_url)
            except Exception as e:
                print(f"Error loading page: {e}")
                if any(error in str(e).lower() for error in ["connection refused", "invalid argument", "session deleted", "invalid session"]):
                    print("Driver session corrupted, recreating...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = setup_driver()
                    continue
                else:
                    # For other errors, just retry
                    continue
            
            time.sleep(3)  # Initial wait for page load
            
            # Check if we hit a login wall
            try:
                current_url = driver.current_url
                if any(x in current_url for x in ["authwall", "login", "checkpoint"]):
                    print(f"Attempt {attempt}: LinkedIn is asking for login. Trying to bypass...")
                    if not try_bypass_login_wall(driver):
                        wait_time = random.uniform(*WAIT_BETWEEN_RETRIES_SECONDS)
                        print(f"Waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                        
                        # After several failed attempts, try restarting the browser
                        if attempt % 3 == 0:
                            print("Restarting browser for attempt", attempt)
                            try:
                                driver.quit()
                            except:
                                pass
                            driver = setup_driver()
                        
                        continue
            except Exception as e:
                print(f"Error checking URL: {e}")
                try:
                    driver.quit()
                except:
                    pass
                driver = setup_driver()
                continue
            
            # Check if the page has loaded properly
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-background-image, .pv-top-card, .core-rail, .scaffold-layout__main"))
                )
            except TimeoutException:
                print(f"Attempt {attempt}: Profile page elements not found.")
                if attempt < MAX_RETRIES:
                    print("Page loaded but didn't find expected content. Retrying...")
                    continue
                else:
                    print("Failed to find profile content after max retries")
                    add_to_failed_urls(profile_url)
                    return False
            except Exception as e:
                print(f"Error waiting for elements: {e}")
                try:
                    driver.quit()
                except:
                    pass
                driver = setup_driver()
                continue
            
            print(f"Attempt {attempt}: Profile page elements found!")
            
            # Get the page source
            try:
                html_content = driver.page_source
            except Exception as e:
                print(f"Error getting page source: {e}")
                try:
                    driver.quit()
                except:
                    pass
                driver = setup_driver()
                continue
            
            # Check if the content seems valid
            if len(html_content) < 1000:  # Arbitrary minimum size for a valid profile
                print("Retrieved HTML content seems too small. Retrying...")
                continue
            
            # Save the HTML content
            file_path = save_html(profile_url, html_content)
            if not file_path:
                print("Failed to save HTML content")
                continue
            
            print(f"Successfully saved HTML to {file_path}")
            time.sleep(random.uniform(*WAIT_AFTER_SUCCESS_SECONDS))
            return True
            
        except Exception as e:
            print(f"Attempt {attempt}: Unexpected error: {e}")
            if attempt < MAX_RETRIES:
                # Always recreate driver on unexpected errors
                try:
                    driver.quit()
                except:
                    pass
                driver = setup_driver()
                wait_time = random.uniform(*WAIT_BETWEEN_RETRIES_SECONDS)
                print(f"Waiting {wait_time:.1f} seconds before retry...")
                time.sleep(wait_time)
            else:
                print("Failed to scrape profile after max retries")
                add_to_failed_urls(profile_url)
                return False
    
    # If we get here, all retries failed
    add_to_failed_urls(profile_url)
    return False

def parse_html_content(html_content, profile_url):
    """Parse LinkedIn profile HTML content to extract experience information."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get profile name
        name = None
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.text
            # Titles usually have format "Name - Job Title - Company | LinkedIn"
            name_match = re.match(r'^([^-]+)', title_text)
            if name_match:
                name = name_match.group(1).strip()
        
        # Find experience section using multiple potential selectors
        experience_section = None
        selectors = [
            {'data-section': 'experience'},
            {'id': 'experience-section'},
            {'class': 'experience-section'}
        ]
        
        for selector in selectors:
            section = soup.find('section', selector)
            if section:
                experience_section = section
                break
        
        # If still not found, try broader search
        if not experience_section:
            experience_divs = soup.find_all('div', string=lambda text: text and 'experience' in text.lower())
            if experience_divs:
                for div in experience_divs:
                    parent = div.parent
                    if parent:
                        experience_section = parent
                        break
        
        if not experience_section:
            print(f"No experience section found in profile: {profile_url}")
            return None
        
        experiences = []
        
        # Find all experience items (try multiple potential class patterns)
        experience_cards = []
        card_patterns = [
            re.compile(r'experience-item'),
            re.compile(r'experience-group-position'),
            re.compile(r'pv-entity'),
            re.compile(r'pv-position-entity')
        ]
        
        for pattern in card_patterns:
            cards = experience_section.find_all('li', {'class': pattern})
            if cards:
                experience_cards.extend(cards)
        
        # If still no cards found, try div elements
        if not experience_cards:
            for pattern in card_patterns:
                cards = experience_section.find_all('div', {'class': pattern})
                if cards:
                    experience_cards.extend(cards)
        
        for card in experience_cards:
            # Try multiple selectors for job title
            title_elem = None
            title_selectors = [
                {'class': 'experience-item__title'},
                {'class': 'pv-entity__title'},
                {'class': 't-16'}
            ]
            
            for selector in title_selectors:
                elem = card.find('span', selector) or card.find('h3', selector)
                if elem:
                    title_elem = elem
                    break
            
            if not title_elem:
                continue
            
            job_title = title_elem.text.strip()
            
            # Try multiple selectors for company
            company_elem = None
            company_selectors = [
                {'class': 'experience-item__subtitle'},
                {'class': 'pv-entity__company-name'},
                {'class': 'pv-entity__secondary-title'},
                {'class': 't-14'}
            ]
            
            for selector in company_selectors:
                elem = card.find('span', selector) or card.find('p', selector)
                if elem:
                    company_elem = elem
                    break
            
            company = company_elem.text.strip() if company_elem else None
            
            # Try multiple selectors for date range
            date_range_elem = None
            date_selectors = [
                {'class': 'date-range'},
                {'class': 'pv-entity__date-range'},
                {'class': 'experience-item__duration'}
            ]
            
            for selector in date_selectors:
                elem = card.find('span', selector) or card.find('div', selector)
                if elem:
                    date_range_elem = elem
                    break
                    
            if not date_range_elem:
                continue
                
            date_texts = date_range_elem.find_all('time')
            
            start_date = None
            end_date = "Present"
            
            if date_texts:
                start_date = date_texts[0].text.strip()
                if len(date_texts) > 1:
                    end_date = date_texts[1].text.strip()
            else:
                # Try parsing dates from text
                date_text = date_range_elem.text.strip()
                date_match = re.search(r'(\w+ \d{4})\s*(?:-|–)\s*(\w+ \d{4}|Present)', date_text)
                if date_match:
                    start_date = date_match.group(1)
                    end_date = date_match.group(2)
            
            # Extract duration using regex
            duration = None
            duration_pattern = re.compile(r'(\d+\s+years?,?\s*\d*\s*months?|\d+\s+months?)')
            duration_match = None
            
            for text in card.stripped_strings:
                match = duration_pattern.search(text)
                if match:
                    duration_match = match
                    break
            
            if duration_match:
                duration = duration_match.group(0).strip()
            
            # Extract description
            description = None
            description_selectors = [
                {'class': 'show-more-less-text'},
                {'class': 'pv-entity__description'},
                {'class': 'description'}
            ]
            
            for selector in description_selectors:
                elem = card.find('div', selector) or card.find('p', selector)
                if elem:
                    description = elem.get_text().strip()
                    break
            
            experiences.append({
                'name': name,
                'profile_url': profile_url,
                'job_title': job_title,
                'company': company,
                'start_date': start_date,
                'end_date': end_date,
                'duration': duration,
                'description': description
            })
        
        return experiences
    
    except Exception as e:
        print(f"Error parsing HTML content: {e}")
        return None

def read_linkedin_urls():
    """Read LinkedIn URLs from the text file."""
    try:
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            urls = [url.strip() for url in f.readlines()]
        
        # Filter out any empty lines or invalid URLs
        valid_urls = [url for url in urls if url and "linkedin.com" in url]
        
        print(f"Successfully loaded {len(valid_urls)} LinkedIn URLs from {URLS_FILE_PATH}")
        return valid_urls
    except Exception as e:
        print(f"Error reading URLs file: {e}")
        return []

def cleanup_chrome():
    """Simple Chrome process cleanup."""
    try:
        os.system("pkill -f chrome > /dev/null 2>&1")
        os.system("pkill -f chromedriver > /dev/null 2>&1")
        time.sleep(2)
    except:
        pass

def test_url_cleaning():
    """Test the URL cleaning function with various examples."""
    test_urls = [
        "@https://al.www.linkedin.com/in/donika-qela-0bb0ab1a4",
        "https://fr.linkedin.com/in/john-doe",
        "https://de.www.linkedin.com/in/jane-smith",
        "linkedin.com/in/test-user",
        "http://www.linkedin.com/in/another-user/",
        "https://www.linkedin.com/in/normal-user?param=value"
    ]
    
    print("Testing URL cleaning function:")
    for url in test_urls:
        cleaned = clean_linkedin_url(url)
        print(f"  {url} -> {cleaned}")
    print()

def reset_tracking_files():
    """Reset failed and attempted tracking files, but keep successfully processed URLs."""
    try:
        print("Resetting failed and attempted tracking files (keeping successfully processed URLs)...")
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
        
        # Only clear failed and attempted files, NOT the processed URLs file
        for file_path in [FAILED_URLS_FILE, ATTEMPTED_URLS_FILE]:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("")  # Empty file
        
        print("Failed and attempted tracking files have been reset")
        print("Successfully processed URLs are preserved")
        
    except Exception as e:
        print(f"Error resetting tracking files: {e}")

def rebuild_processed_urls_file():
    """Rebuild the processed URLs file based on actual HTML files."""
    try:
        print("Rebuilding processed URLs file based on actual HTML files...")
        
        # Get URLs that actually have HTML files
        processed_urls = get_processed_urls()
        
        # Rewrite the processed URLs file
        os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
        with open(PROCESSED_URLS_FILE, 'w', encoding='utf-8') as f:
            for url in sorted(processed_urls):
                f.write(url + '\n')
        
        print(f"Rebuilt processed URLs file with {len(processed_urls)} actual processed URLs")
        
    except Exception as e:
        print(f"Error rebuilding processed URLs file: {e}")

def debug_url_matching():
    """Debug function to see why URL matching isn't working."""
    print("\n=== DEBUGGING URL MATCHING ===")
    
    # Get a few HTML files and see what URLs they generate
    html_files = []
    if os.path.exists(HTML_DIR):
        html_files = [f for f in os.listdir(HTML_DIR) if f.endswith('.html')][:5]
    
    print(f"Sample HTML files and their reconstructed URLs:")
    for html_file in html_files:
        url_part = html_file[:-5]  # Remove .html
        username = None
        
        if '_in_' in url_part:
            parts = url_part.split('_in_')
            if len(parts) >= 2:
                raw_username = parts[-1]
                username = raw_username.rstrip('_').strip()  # Clean up username
                print(f"  {html_file}")
                print(f"    Raw username: '{raw_username}' -> Cleaned: '{username}'")
        
        if username:
            reconstructed_url = f'https://www.linkedin.com/in/{username}'
            print(f"    Final URL: {reconstructed_url}")
    
    # Get a few URLs from the input file and see what they look like after cleaning
    print(f"\nSample input URLs and their cleaned versions:")
    try:
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            input_urls = [url.strip() for url in f.readlines()][:5]
        
        for url in input_urls:
            cleaned = clean_linkedin_url(url)
            print(f"  {url} -> {cleaned}")
    except Exception as e:
        print(f"Error reading input URLs: {e}")
    
    print("=== END DEBUG ===\n")

def main():
    """Main execution function."""
    driver = None
    try:
        # Test URL cleaning function
        test_url_cleaning()
        
        # Reset tracking files to restart the count
        reset_tracking_files()
        
        # Rebuild processed URLs file to match actual HTML files
        rebuild_processed_urls_file()

        # Clean up any existing Chrome processes
        cleanup_chrome()
        
        # Create output directories
        os.makedirs(HTML_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
        
        # Get remaining URLs to process
        urls = get_remaining_urls()
        if not urls:
            print("No valid URLs to process")
            return
        
        print(f"Starting scraping of {len(urls)} profiles...")
        
        # Initialize the driver
        driver = setup_driver()
        
        # Process URLs
        for i, url in enumerate(urls, 1):
            # Clean the URL again to be safe
            cleaned_url = clean_linkedin_url(url)
            if not cleaned_url:
                print(f"Skipping invalid URL {i}/{len(urls)}: {url}")
                continue
                
            print(f"\nProcessing URL {i}/{len(urls)}: {cleaned_url}")
            
            try:
                success = scrape_profile(driver, cleaned_url)
                if success:
                    print(f"Successfully scraped profile {i}/{len(urls)}")
                else:
                    print(f"Failed to scrape profile {i}/{len(urls)}")
            except Exception as e:
                print(f"Error processing profile {i}: {e}")
                # Recreate driver on any error
                try:
                    driver.quit()
                except:
                    pass
                cleanup_chrome()  # Clean up before recreating
                driver = setup_driver()
            
            # Take breaks to avoid rate limiting
            if i % PROFILES_BEFORE_BREAK == 0 and i < len(urls):
                print(f"\nTaking a {BREAK_DURATION} second break...")
                time.sleep(BREAK_DURATION)
                # Recreate driver after break for fresh session
                try:
                    driver.quit()
                except:
                    pass
                cleanup_chrome()  # Clean up before recreating
                driver = setup_driver()
        
        # Clean up
        try:
            if driver:
                driver.quit()
        except:
            pass
        cleanup_chrome()
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        try:
            if driver:
                driver.quit()
        except:
            pass
        cleanup_chrome()
    except Exception as e:
        print(f"Error in main loop: {e}")
        try:
            if driver:
                driver.quit()
        except:
            pass
        cleanup_chrome()

if __name__ == "__main__":
    main() 