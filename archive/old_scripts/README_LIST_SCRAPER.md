# LinkedIn Profile Scraper (List Version)

A Python tool that scrapes LinkedIn profiles from a text file list of URLs, handling LinkedIn's blocking mechanisms by using incognito mode, cookie management, and retry logic.

## Overview

This version of the LinkedIn scraper reads LinkedIn profile URLs directly from a text file instead of a CSV. This approach is more straightforward and avoids potential CSV parsing issues with encoding.

## Files in this project

- `extract_linkedin_urls.py` - Script to extract LinkedIn URLs from CSV into a text file
- `linkedin_scraper_from_list.py` - Main scraper script that reads from the text file
- `linkedin_urls.txt` - Text file containing LinkedIn profile URLs
- `requirements.txt` - Required Python packages

## Prerequisites

- Python 3.6+
- Chrome browser installed

## Installation

1. Clone this repository or download the script files
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

### Step 1: Extract LinkedIn URLs from CSV (if not already done)

```bash
python extract_linkedin_urls.py
```

This will create a file called `linkedin_urls.txt` with one URL per line.

### Step 2: Run the scraper

```bash
python linkedin_scraper_from_list.py
```

The script will:
1. Read the URLs from the text file
2. Create the output and cookies directories if they don't exist
3. Initialize the Chrome driver in incognito mode
4. Try to load any existing cookies
5. Process each LinkedIn URL with retries if needed
6. Save the HTML content of successfully scraped profiles
7. Save cookies after successful scrapes

## Configuration

The script contains several configuration variables that you can modify:

- `URLS_FILE_PATH`: Path to your text file containing LinkedIn URLs
- `OUTPUT_DIR`: Directory where scraped HTML files will be saved
- `COOKIES_DIR`: Directory where cookie files will be stored
- `MAX_RETRIES`: Maximum number of retry attempts for each URL
- `WAIT_BETWEEN_RETRIES_SECONDS`: Range of seconds to wait between retries
- `WAIT_AFTER_SUCCESS_SECONDS`: Range of seconds to wait after successful scraping
- `USER_AGENTS`: List of user agents to rotate between

## Troubleshooting

- If LinkedIn consistently blocks your requests, try increasing the wait times
- Check that your Chrome browser is up to date
- Make sure you have the correct version of ChromeDriver installed (handled by webdriver-manager)
- Consider using a proxy service to rotate IP addresses (not implemented in this version)

## Legal Disclaimer

This script is provided for educational purposes only. Scraping LinkedIn may violate their Terms of Service. Use at your own risk and responsibility. 