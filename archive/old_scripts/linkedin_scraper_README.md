# LinkedIn Profile Scraper

A Python tool that scrapes LinkedIn profiles from a CSV list of URLs, handling LinkedIn's blocking mechanisms by using incognito mode, cookie management, and retry logic.

## Features

- Reads LinkedIn profile URLs from a CSV file
- Opens Chrome in incognito mode for each URL
- Implements retry mechanism when LinkedIn blocks the request
- Saves HTML content of successfully scraped profiles
- Manages cookies to improve success rate
- Rotates user agents to avoid detection
- Handles errors gracefully

## Prerequisites

- Python 3.6+
- Chrome browser installed

## Installation

1. Clone this repository or download the script files
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Configuration

The script contains several configuration variables that you can modify:

- `CSV_FILE_PATH`: Path to your CSV file containing LinkedIn URLs
- `OUTPUT_DIR`: Directory where scraped HTML files will be saved
- `COOKIES_DIR`: Directory where cookie files will be stored
- `MAX_RETRIES`: Maximum number of retry attempts for each URL
- `WAIT_BETWEEN_RETRIES_SECONDS`: Range of seconds to wait between retries
- `WAIT_AFTER_SUCCESS_SECONDS`: Range of seconds to wait after successful scraping
- `USER_AGENTS`: List of user agents to rotate between

## Usage

Simply run the script:

```bash
python linkedin_scraper.py
```

The script will:
1. Create the output and cookies directories if they don't exist
2. Read the CSV file and extract LinkedIn URLs
3. Initialize the Chrome driver in incognito mode
4. Try to load any existing cookies
5. Process each LinkedIn URL with retries if needed
6. Save the HTML content of successfully scraped profiles
7. Save cookies after successful scrapes

## CSV File Format

The script expects a CSV file with a column named "Linkedin" containing the LinkedIn profile URLs.

Example:
```
name,job_title,Linkedin
John Doe,Software Engineer,https://www.linkedin.com/in/johndoe/
Jane Smith,Data Scientist,https://www.linkedin.com/in/janesmith/
```

## Tips for Avoiding LinkedIn Blocks

- Run the script with reasonable delays between requests
- Consider using a VPN or proxy service (not implemented in this script)
- Try logging into LinkedIn manually and then copying the cookies to the cookies directory
- Run the script during off-peak hours

## Troubleshooting

- If LinkedIn consistently blocks your requests, try increasing the wait times
- Check that your Chrome browser is up to date
- Make sure you have the correct version of ChromeDriver installed (handled by webdriver-manager)
- Consider using a proxy service to rotate IP addresses

## Legal Disclaimer

This script is provided for educational purposes only. Scraping LinkedIn may violate their Terms of Service. Use at your own risk and responsibility.

## License

This project is open source and available under the MIT License. 