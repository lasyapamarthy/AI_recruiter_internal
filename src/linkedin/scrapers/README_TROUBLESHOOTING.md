# LinkedIn Scraper Troubleshooting Guide

## Common Issues and Solutions

### 1. Files Not Being Created (Status: "error")

**Symptoms:**
- Log shows all entries with status "error"
- No HTML files are created
- AppleScript returns errors

**Possible Causes & Solutions:**

1. **AppleScript Permissions**
   - Go to System Preferences → Security & Privacy → Privacy → Accessibility
   - Ensure Terminal (or your IDE) has permission to control Safari/Chrome
   - Add Terminal to the allowed apps if not present

2. **Browser Not Installed/Accessible**
   - Ensure Safari and/or Chrome are installed
   - Try running the test script: `python test_scraper.py`

3. **Path Issues**
   - Check that the AppleScript files exist in the `scripts/` directory
   - Ensure write permissions on the output directory

### 2. Auth Walls Being Captured

**Symptoms:**
- Files are created but renamed with `_AUTHWALL` suffix
- HTML contains "Sign Up | LinkedIn" or auth wall content

**Solutions:**

1. **Login to LinkedIn**
   - Open Safari/Chrome manually
   - Log into LinkedIn
   - Keep the browser open while running the scraper
   - LinkedIn might still show auth walls for automated access

2. **Use Cookies**
   - The improved scripts use incognito/private mode which doesn't have cookies
   - Consider modifying scripts to use regular windows (remove incognito mode)

3. **Reduce Batch Size**
   - Use smaller batches (3-5 URLs) to appear less automated
   - Increase delays between batches

### 3. Incomplete Profile Captures

**Symptoms:**
- Files are created but marked as "unknown_page"
- HTML is captured but doesn't contain profile data

**Solutions:**

1. **Increase Load Times**
   - LinkedIn profiles load content dynamically
   - Modify the `maxWait` variable in AppleScripts (currently 30 seconds)
   - Increase the additional delay after page load (currently 3 seconds)

2. **Check for Different Profile Formats**
   - LinkedIn has multiple profile layouts
   - Some profiles might use different HTML structure
   - The improved `analyze_html_content()` function checks for multiple indicators

### 4. Performance Issues

**Symptoms:**
- Scraper is very slow
- Browser windows hang or crash

**Solutions:**

1. **Reduce Batch Size**
   - Use `BATCH_SIZE = 3` instead of 5 or 8
   - Process fewer URLs at once

2. **Increase Delays**
   - Longer delays between batches reduce detection risk
   - Use `SLEEP_RANGE = (15, 30)` for more natural behavior

3. **Monitor System Resources**
   - Chrome/Safari can use significant memory
   - Close other applications while scraping

## Testing Individual URLs

Use the diagnostic script to test individual URLs:

```bash
# Test with Safari (default)
python test_scraper.py https://www.linkedin.com/in/username

# Test with Chrome
python test_scraper.py https://www.linkedin.com/in/username chrome
```

## Debugging AppleScript Issues

1. **Run AppleScript Manually**
   ```bash
   osascript scripts/save_batch_safari_improved.applescript \
     "https://www.linkedin.com/in/test" "test.html"
   ```

2. **Check Console Logs**
   - Open Console.app
   - Filter for "Safari" or "Chrome"
   - Look for JavaScript errors

3. **Verbose Output**
   - The improved scripts capture error messages
   - Check the HTML files for error messages starting with "Error:"

## Recommended Settings for Better Success

```python
# In scraper_emil_improved.py
BATCH_SIZE = 3          # Small batches
SLEEP_RANGE = (15, 30)  # Longer delays
MAX_RETRIES = 3         # More retries for auth walls
```

## Alternative Approaches

If automation continues to fail:

1. **Manual Login First**
   - Log into LinkedIn in both browsers
   - Keep browsers open during scraping
   - Remove incognito/private mode from scripts

2. **Use Different User Agents**
   - Modify AppleScripts to set custom user agents
   - Rotate between different browser profiles

3. **Consider API or Licensed Solutions**
   - LinkedIn has strict anti-scraping measures
   - Official APIs or licensed data providers might be more reliable

## Log Analysis

The improved scraper creates detailed logs with:
- `status`: The result of each URL
- `details`: Specific error messages or debug info
- `retry_count`: Number of attempts for each URL

Use this data to identify patterns and adjust your approach. 