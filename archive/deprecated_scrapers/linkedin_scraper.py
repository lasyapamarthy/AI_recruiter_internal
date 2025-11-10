#!/usr/bin/env python3
import os
import time
import random
import json
import pickle
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configuration
CSV_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin_jobs_emil.csv"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/linkedin_profiles"
COOKIES_DIR = "/Users/emilpalikot/Research/AI-Recruiter/cookies"
MAX_RETRIES = 5
WAIT_BETWEEN_RETRIES_SECONDS = [5, 10]  # Random wait between min and max seconds
WAIT_AFTER_SUCCESS_SECONDS = [3, 7]  # Random wait between min and max seconds
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
    
    # Add random user agent
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    # Initialize Chrome driver with ChromeDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Spoof webdriver to avoid detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def save_html(profile_url, html_content):
    """Save HTML content to a file."""
    # Create a valid filename from the URL
    filename = profile_url.replace("https://", "").replace("www.", "").replace("/", "_")
    filename = f"{filename}.html"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
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
        
        # Also save in JSON format for inspection
        json_path = os.path.join(COOKIES_DIR, f"{name}.json")
        with open(json_path, "w") as f:
            json.dump(cookies, f, indent=4)
        print(f"Cookies also saved as JSON to {json_path}")

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
            # Handle browser compliance issues with sameSite
            if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                cookie['sameSite'] = 'None'
                
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie: {e}")
        
        print(f"Loaded cookies from {cookies_path}")
        return True
    else:
        print(f"No cookies found at {cookies_path}")
        return False

def rotate_proxy():
    """
    This is a placeholder for proxy rotation functionality.
    In a real-world scenario, you would add code here to switch between different proxies.
    """
    # Implement your proxy rotation logic here if you have access to proxies
    # This could involve selecting a different proxy from a list
    print("Rotating proxy (placeholder function)")
    pass

def scrape_profile(driver, profile_url):
    """Try to scrape a LinkedIn profile with retries."""
    print(f"Attempting to scrape: {profile_url}")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Load the page
            driver.get(profile_url)
            
            # Wait for the page to load - look for a common LinkedIn profile element
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".scaffold-layout__main, .core-rail, .profile-background-image"))
            )
            
            # Check if we got blocked or redirected to login
            if "authwall" in driver.current_url or "login" in driver.current_url:
                print(f"Attempt {attempt}: LinkedIn is asking for login. Retrying...")
                
                # Try loading cookies if it's the first attempt
                if attempt == 1:
                    load_cookies(driver)
                    continue
                
                # On subsequent attempts, try rotating proxies or user agents
                if attempt > 2:
                    rotate_proxy()
                
                wait_time = random.uniform(WAIT_BETWEEN_RETRIES_SECONDS[0], WAIT_BETWEEN_RETRIES_SECONDS[1])
                print(f"Waiting {wait_time:.1f} seconds before retry...")
                time.sleep(wait_time)
                continue
            
            # Get the page source
            html_content = driver.page_source
            
            # Save cookies from successful attempt
            save_cookies(driver, f"linkedin_cookies_{int(time.time())}")
            
            # Save the HTML content
            save_html(profile_url, html_content)
            
            # Success - wait before moving to the next profile
            wait_time = random.uniform(WAIT_AFTER_SUCCESS_SECONDS[0], WAIT_AFTER_SUCCESS_SECONDS[1])
            print(f"Success! Waiting {wait_time:.1f} seconds before next profile...")
            time.sleep(wait_time)
            return True
            
        except (TimeoutException, WebDriverException) as e:
            print(f"Attempt {attempt}: Error: {e}")
            if attempt < MAX_RETRIES:
                wait_time = random.uniform(WAIT_BETWEEN_RETRIES_SECONDS[0], WAIT_BETWEEN_RETRIES_SECONDS[1])
                print(f"Waiting {wait_time:.1f} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"Failed to scrape {profile_url} after {MAX_RETRIES} attempts")
                return False

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(COOKIES_DIR, exist_ok=True)
    
    # Read the CSV file
    try:
        df = pd.read_csv(CSV_FILE_PATH)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Check if 'Linkedin' column exists
    if 'Linkedin' not in df.columns:
        print(f"CSV file does not contain a 'Linkedin' column. Available columns: {df.columns.tolist()}")
        return
    
    # Filter out rows with missing LinkedIn URLs
    df = df[df['Linkedin'].notna()]
    
    # Initialize the webdriver
    driver = setup_driver()
    
    try:
        # Try to load cookies first
        load_cookies(driver)
        
        # Process each LinkedIn profile
        total_profiles = len(df)
        success_count = 0
        
        print(f"Starting to scrape {total_profiles} LinkedIn profiles...")
        
        for index, row in df.iterrows():
            profile_url = row['Linkedin']
            
            # Skip if not a valid LinkedIn URL
            if not isinstance(profile_url, str) or "linkedin.com" not in profile_url:
                print(f"Skipping invalid URL: {profile_url}")
                continue
            
            success = scrape_profile(driver, profile_url)
            if success:
                success_count += 1
            
            print(f"Progress: {index + 1}/{total_profiles} profiles processed")
            
            # Save a checkpoint after every 5 successful profiles
            if success_count > 0 and success_count % 5 == 0:
                save_cookies(driver, "linkedin_cookies_checkpoint")
        
        print(f"Scraping completed. Successfully scraped {success_count} out of {total_profiles} profiles.")
        
    finally:
        # Save final cookies before quitting
        save_cookies(driver, "linkedin_cookies_final")
        
        # Clean up
        driver.quit()

if __name__ == "__main__":
    main() 