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
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.keys import Keys

# Configuration
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/linkedin_urls.txt"
HTML_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/htmls"
COOKIES_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/cookies"
EXPERIENCES_CSV = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/linkedin_experiences_test.csv"
PROCESSED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/processed_urls.txt"
MAX_RETRIES = 50  # Increased to 50 attempts per profile
RETRIES_BEFORE_LONG_PAUSE = 10  # Take a long pause after this many retries
LONG_PAUSE_DURATION = 30  # Wait 30 seconds
WAIT_BETWEEN_RETRIES_SECONDS = [1, 3]  # Reduced to 1-3 seconds
WAIT_AFTER_SUCCESS_SECONDS = [1, 2]  # Reduced to 1-2 seconds
MAX_URLS_TO_PROCESS = 3  # Only process the first 3 URLs for testing
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

def setup_driver():
    """Configure and return Chrome webdriver with incognito mode."""
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Use a random user agent on each attempt
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    # Initialize Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Spoof webdriver to avoid detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def get_html_filename(profile_url):
    """Create a valid filename from the URL."""
    filename = profile_url.replace("https://", "").replace("www.", "").replace("/", "_")
    filename = f"{filename}.html"
    return filename

def save_html(profile_url, html_content):
    """Save HTML content to a file."""
    # Create a valid filename from the URL
    filename = get_html_filename(profile_url)
    file_path = os.path.join(HTML_DIR, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Add to processed URLs list
    add_to_processed_urls(profile_url)
    
    print(f"Successfully saved HTML to {file_path}")
    return file_path

def save_cookies(driver, name="linkedin_cookies"):
    """Save cookies from the current session."""
    os.makedirs(COOKIES_DIR, exist_ok=True)
    cookies_path = os.path.join(COOKIES_DIR, f"{name}.pkl")
    
    cookies = driver.get_cookies()
    
    # Only save if we have cookies
    if cookies:
        with open(cookies_path, "wb") as f:
            pickle.dump(cookies, f)
        print(f"Cookies saved to {cookies_path}")

def load_cookies(driver, name="linkedin_cookies"):
    """Load cookies into the current session."""
    cookies_path = os.path.join(COOKIES_DIR, f"{name}.pkl")
    
    if os.path.exists(cookies_path):
        with open(cookies_path, "rb") as f:
            cookies = pickle.load(f)
        
        # Make sure we're on LinkedIn domain before adding cookies
        driver.get("https://www.linkedin.com/")
        
        # Add cookies
        for cookie in cookies:
            try:
                if 'sameSite' in cookie:
                    if cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                        cookie['sameSite'] = 'None'
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie: {e}")
        
        print(f"Loaded cookies from {cookies_path}")
        return True
    else:
        print(f"No cookies found at {cookies_path}")
        return False

def try_bypass_login_wall(driver):
    """Try various techniques to bypass LinkedIn login wall"""
    print("Attempting to bypass login wall...")
    
    # Try pressing Escape key to dismiss popups
    try:
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
    except Exception as e:
        print(f"Error sending Escape key: {e}")
    
    # Try clicking the X button on modals if present
    try:
        close_buttons = driver.find_elements(By.CSS_SELECTOR, "button.modal__dismiss, button.artdeco-modal__dismiss, button.close-button")
        if close_buttons:
            for button in close_buttons:
                try:
                    print("Found close button, clicking it")
                    button.click()
                    time.sleep(1)
                except Exception as btn_error:
                    print(f"Error clicking button: {btn_error}")
    except Exception as e:
        print(f"Error finding close buttons: {e}")
    
    # Try removing the login overlay via JavaScript
    try:
        # Remove any modal overlays
        driver.execute_script("""
            // Remove any modal overlays
            var modals = document.querySelectorAll('.modal-wormhole, .artdeco-modal-overlay, .authentication-outlet');
            for(var i=0; i<modals.length; i++) {
                modals[i].remove();
            }
            
            // Remove body class that prevents scrolling
            document.body.classList.remove('overflow-hidden');
            
            // For any elements with fixed positioning overlay
            var overlays = document.querySelectorAll('.global-alert-banner, .authentication-outlet, .login-form, .join-form');
            for(var i=0; i<overlays.length; i++) {
                overlays[i].remove();
            }
            
            // Remove dimmer overlay
            var dimmers = document.querySelectorAll('.artdeco-modal-overlay');
            for(var i=0; i<dimmers.length; i++) {
                dimmers[i].remove();
            }
            
            // Set overflow back to auto
            document.documentElement.style.overflow = 'auto';
            document.body.style.overflow = 'auto';
            
            // Remove fixed positioning from body
            document.body.style.position = 'static';
        """)
        time.sleep(1)
    except Exception as e:
        print(f"Error executing JavaScript to remove overlay: {e}")
    
    # Try a different approach with more aggressive DOM manipulation
    try:
        driver.execute_script("""
            // Try to find the profile content area and make a clone of it
            var profileContainer = document.querySelector('.scaffold-layout__main, .core-rail');
            if (profileContainer) {
                // Clone it
                var clone = profileContainer.cloneNode(true);
                
                // Clear the body and add only our clone
                document.body.innerHTML = '';
                document.body.appendChild(clone);
                
                // Reset styles
                document.body.style = '';
                document.documentElement.style = '';
            }
        """)
        time.sleep(1)
    except Exception as e:
        print(f"Error with aggressive DOM manipulation: {e}")
    
    # Check if bypass was successful
    current_url = driver.current_url
    if "authwall" in current_url or "login" in current_url or "checkpoint" in current_url:
        print("Bypass unsuccessful, still at login/auth page")
        return False
    else:
        print("Possibly bypassed login wall, current URL:", current_url)
        
        # Additional check to see if we have profile content
        try:
            profile_elements = driver.find_elements(By.CSS_SELECTOR, ".profile-background-image, .pv-top-card, .core-rail, .scaffold-layout__main")
            if profile_elements:
                print("Profile elements found - bypass appears successful!")
                return True
        except:
            pass
            
        # If we're not on an auth page but don't see profile elements, let's try to be optimistic
        return True

def get_processed_urls():
    """Get a list of already processed URLs."""
    processed_urls = set()
    
    # First check the processed URLs file
    if os.path.exists(PROCESSED_URLS_FILE):
        with open(PROCESSED_URLS_FILE, 'r', encoding='utf-8') as f:
            processed_urls.update(url.strip() for url in f.readlines())
    
    # Then check the HTML directory for any files that might not be in the processed file
    html_files = glob.glob(os.path.join(HTML_DIR, "*.html"))
    for html_file in html_files:
        base_filename = os.path.basename(html_file)
        # Convert filename back to URL format (rough approximation)
        url_part = base_filename.replace("_", "/").replace(".html", "")
        if "linkedin.com" in url_part:
            # Reconstruct the URL
            if not url_part.startswith("https://"):
                if url_part.startswith("linkedin.com"):
                    url_part = "https://www." + url_part
                else:
                    url_part = "https://" + url_part
            processed_urls.add(url_part)
    
    return processed_urls

def add_to_processed_urls(profile_url):
    """Add a URL to the processed URLs file."""
    with open(PROCESSED_URLS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{profile_url}\n")

def scrape_profile(driver, profile_url):
    """Try to scrape a LinkedIn profile with retries."""
    print(f"Attempting to scrape: {profile_url}")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Close and reopen the browser every few attempts to clear any tracking
            if attempt > 1 and attempt % 5 == 0:
                print(f"Restarting browser for attempt {attempt}...")
                driver.quit()
                time.sleep(3)
                driver = setup_driver()
            
            # Load the page
            print(f"Attempt {attempt}/{MAX_RETRIES}: Loading profile...")
            driver.get(profile_url)
            
            # Wait for the page to load with a simple delay
            time.sleep(random.uniform(1, 3))  # Reduced wait time
            
            # Check if we got blocked or redirected to login
            current_url = driver.current_url.lower()
            page_source = driver.page_source.lower()
            
            # Check for various login walls and authentication barriers
            if ("authwall" in current_url or 
                "login" in current_url or 
                "checkpoint" in current_url or
                "sessionredirect" in current_url or
                "authwall" in page_source or
                "please log in to continue" in page_source or
                "sign in to continue" in page_source):
                
                print(f"Attempt {attempt}: LinkedIn is asking for login. Trying to bypass...")
                
                # Try bypass methods
                bypass_success = try_bypass_login_wall(driver)
                
                if not bypass_success:
                    # If we've tried multiple times and still hit a login wall, mark as inaccessible
                    if attempt >= 7:  # After several attempts
                        print(f"Profile appears to be consistently blocked by login wall after {attempt} attempts. Marking as inaccessible.")
                        add_to_processed_urls(profile_url)
                        return []
                    
                    # If bypass failed, take a pause and retry
                    if attempt % RETRIES_BEFORE_LONG_PAUSE == 0:
                        wait_time = LONG_PAUSE_DURATION
                        print(f"Taking a longer pause of {wait_time} seconds after {RETRIES_BEFORE_LONG_PAUSE} attempts...")
                    else:
                        wait_time = random.uniform(WAIT_BETWEEN_RETRIES_SECONDS[0], WAIT_BETWEEN_RETRIES_SECONDS[1])
                        print(f"Waiting {wait_time:.1f} seconds before retry...")
                    
                    time.sleep(wait_time)
                    continue
            
            # Check for private profile markers
            page_source = driver.page_source.lower()
            if (any(phrase in page_source for phrase in [
                "this profile is not available", 
                "this profile is private",
                "this profile is semi-private",
                "this linkedin member is not available",
                "page not found",
                "member profile unavailable",
                "the profile you're looking for isn't available",
                "we can't find that page",
                "this page doesn't exist",
                "this profile is private or does not exist",
                "we're unable to show you this profile"
            ])):
                
                # Extract profile ID from URL to make a better message
                profile_id = profile_url.split("/")[-1].strip()
                if not profile_id:
                    profile_id = profile_url.split("/")[-2].strip()
                
                print(f"The profile '{profile_id}' appears to be private or not available. Skipping...")
                
                # Add to processed URLs to avoid trying again
                add_to_processed_urls(profile_url)
                
                # Return empty list to continue to next profile
                return []
            
            # Try to identify if we've successfully loaded the profile page
            try:
                profile_elements = driver.find_elements(By.CSS_SELECTOR, ".profile-background-image, .pv-top-card, .core-rail, .scaffold-layout__main")
                
                if profile_elements:
                    print(f"Attempt {attempt}: Profile page elements found!")
                    # Get the page source
                    html_content = driver.page_source
                    
                    # Try to scroll down to load all content
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                        time.sleep(1)
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                        time.sleep(1)
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        # Get updated page source after scrolling
                        html_content = driver.page_source
                    except Exception as scroll_error:
                        print(f"Error scrolling: {scroll_error}")
                    
                    # Check if the HTML contains profile-related information
                    # (even without experience/education sections)
                    if any(term in html_content.lower() for term in ['profile', 'member', 'contact info', 'about']):
                        # Always save the HTML content regardless of experience section
                        html_file_path = save_html(profile_url, html_content)
                        print(f"HTML content saved to {html_file_path}")
                        
                        # Check for experience or education sections
                        if "experience" in html_content.lower() or "education" in html_content.lower():
                            print("Found profile content with experience or education sections")
                            
                            # Parse the HTML content for experience data
                            experiences = parse_html_content(html_content, profile_url)
                            
                            if experiences:
                                # Success - wait before moving to the next profile
                                wait_time = random.uniform(WAIT_AFTER_SUCCESS_SECONDS[0], WAIT_AFTER_SUCCESS_SECONDS[1])
                                print(f"Successfully extracted {len(experiences)} experiences. Waiting {wait_time:.1f} seconds before next profile...")
                                time.sleep(wait_time)
                                return experiences
                            else:
                                print("Experience section found but couldn't extract data, but HTML was saved")
                                # Return empty list to indicate success in loading the profile but no experiences extracted
                                return []
                        else:
                            print("Profile HTML saved but didn't contain experience or education sections")
                            # Return empty list to indicate success in loading the profile but no experiences extracted
                            return []
                    else:
                        print("Page loaded but doesn't appear to be a valid profile. Marking as processed to skip in future.")
                        add_to_processed_urls(profile_url)
                        return []
                else:
                    print(f"Attempt {attempt}: Profile page elements not found.")
                    
                    # Check if it appears to be a company page or other non-profile page
                    company_elements = driver.find_elements(By.CSS_SELECTOR, ".org-top-card, .company-hero-container")
                    if company_elements:
                        print("This appears to be a company page, not a personal profile. Marking as processed.")
                        add_to_processed_urls(profile_url)
                        return []
            except Exception as element_error:
                print(f"Error checking page elements: {element_error}")
            
            # If we got here but didn't return, the scrape wasn't successful
            print(f"Attempt {attempt}: Page loaded but didn't find expected content. Retrying...")
            time.sleep(random.uniform(WAIT_BETWEEN_RETRIES_SECONDS[0], WAIT_BETWEEN_RETRIES_SECONDS[1]))
            
        except Exception as e:
            print(f"Attempt {attempt}: Error: {e}")
            if attempt < MAX_RETRIES:
                # Take a longer pause after every RETRIES_BEFORE_LONG_PAUSE attempts
                if attempt % RETRIES_BEFORE_LONG_PAUSE == 0:
                    wait_time = LONG_PAUSE_DURATION
                    print(f"Taking a longer pause of {wait_time} seconds after {RETRIES_BEFORE_LONG_PAUSE} attempts...")
                else:
                    wait_time = random.uniform(WAIT_BETWEEN_RETRIES_SECONDS[0], WAIT_BETWEEN_RETRIES_SECONDS[1])
                    print(f"Waiting {wait_time:.1f} seconds before retry...")
                
                time.sleep(wait_time)
            else:
                print(f"Failed to scrape {profile_url} after {MAX_RETRIES} attempts")
                add_to_processed_urls(profile_url)  # Mark as processed even if it failed after all attempts
                return None
    
    print(f"Exhausted all {MAX_RETRIES} attempts for {profile_url}")
    add_to_processed_urls(profile_url)  # Mark as processed to avoid retrying in future runs
    return None

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
        
        # Limit to the first few URLs for testing
        test_urls = valid_urls[:MAX_URLS_TO_PROCESS]
        
        print(f"Loaded {len(test_urls)} LinkedIn URLs for testing from {URLS_FILE_PATH}")
        return test_urls
    except Exception as e:
        print(f"Error reading URLs file: {e}")
        return []

def main():
    # Create output directories if they don't exist
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(COOKIES_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
    
    # Get already processed URLs
    processed_urls = get_processed_urls()
    print(f"Found {len(processed_urls)} already processed URLs")
    
    # Read LinkedIn URLs from file
    linkedin_urls = read_linkedin_urls()
    
    if not linkedin_urls:
        print("No LinkedIn URLs found. Exiting.")
        return
    
    # Filter out already processed URLs
    linkedin_urls = [url for url in linkedin_urls if url not in processed_urls]
    print(f"After filtering already processed URLs, {len(linkedin_urls)} URLs remain to be scraped")
    
    if not linkedin_urls:
        print("All URLs have already been processed. Exiting.")
        return
    
    # For testing, limit to MAX_URLS_TO_PROCESS but select them randomly
    if len(linkedin_urls) > MAX_URLS_TO_PROCESS:
        # Randomly sample URLs for testing
        linkedin_urls = random.sample(linkedin_urls, MAX_URLS_TO_PROCESS)
        print(f"Randomly selected {MAX_URLS_TO_PROCESS} URLs for testing")
    
    all_experiences = []
    
    try:
        # Process each LinkedIn profile
        unprocessed_urls = linkedin_urls.copy()  # Create a copy to safely remove from
        total_profiles = len(unprocessed_urls)
        original_count = total_profiles
        success_count = 0
        
        print(f"Starting to scrape {total_profiles} LinkedIn profiles randomly for testing...")
        
        profile_count = 0
        while unprocessed_urls:
            # Randomly select a URL from the remaining unprocessed URLs
            profile_url = random.choice(unprocessed_urls)
            # Remove it from the list to avoid processing it again
            unprocessed_urls.remove(profile_url)
            
            profile_count += 1
            
            # Initialize the webdriver fresh for each profile
            print(f"Initializing Chrome driver for profile {profile_count}/{original_count} (random selection)...")
            print(f"{len(unprocessed_urls)} URLs remain in the queue")
            driver = setup_driver()
            
            try:
                experiences = scrape_profile(driver, profile_url)
                if experiences:
                    all_experiences.extend(experiences)
                    success_count += 1
                
                print(f"Progress: {profile_count}/{original_count} profiles processed, {success_count} with experiences")
            finally:
                # Close the driver after each profile to ensure clean state
                try:
                    driver.quit()
                    print(f"Chrome driver closed for profile {profile_count}")
                except:
                    print(f"Could not properly close driver for profile {profile_count}")
            
            # Add a pause between profiles
            if unprocessed_urls:  # Only pause if more profiles to process
                pause = random.uniform(8, 15)
                print(f"Pausing for {pause:.1f} seconds before next profile...")
                time.sleep(pause)
        
        print(f"Testing completed. Successfully scraped {success_count} out of {original_count} profiles.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    # Save experiences to CSV
    if all_experiences:
        with open(EXPERIENCES_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'profile_url', 'job_title', 'company', 'start_date', 'end_date', 'duration', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for exp in all_experiences:
                writer.writerow(exp)
        
        print(f"Successfully exported {len(all_experiences)} experiences to {EXPERIENCES_CSV}")
    else:
        print("No experiences were extracted from the profiles")

if __name__ == "__main__":
    main() 