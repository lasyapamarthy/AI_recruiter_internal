# LinkedIn Scrapers - Final Working Versions

This directory contains the final, production-ready LinkedIn scrapers that have been tested and optimized for reliability and anti-detection.

## 🍎 Safari Batch Scraper (RECOMMENDED)

**File:** `linkedin_scraper_safari_batch.py`

This is the **primary, production-ready scraper** that works excellently with Safari for anti-detection.

### Features:
- **Batch processing:** Opens 10 profiles simultaneously in Safari tabs
- **Anti-detection:** Uses Safari's natural browsing patterns
- **Smart validation:** Only saves real profiles (>200KB with profile content)
- **Auto-cleanup:** Immediately deletes auth wall pages
- **Progress tracking:** Detailed logging and statistics
- **Resume capability:** Can restart from where it left off

### Usage:
```bash
python linkedin_scraper_safari_batch.py
```

### Requirements:
- Safari with Remote Automation enabled
- `sudo safaridriver --enable` (run once)
- URLs file: `data/other_groups_linkedin_urls.txt`

### Output:
- **HTML files:** `data/linkedin/output/safari_htmls/`
- **Failed URLs:** `data/linkedin/profiles/safari_failed_urls.txt`

## 📊 Real-time Monitor

**File:** `linkedin_monitor.py`

Provides real-time monitoring of scraper progress with accurate statistics.

### Features:
- **Live statistics:** Total progress, success rates, file counts
- **Recent activity:** Last 5 profiles saved with timestamps
- **File analysis:** Size statistics and validation
- **Accurate counting:** Only counts URLs from the current task

### Usage:
```bash
python linkedin_monitor.py
```

## 🔧 Utility Scripts

### AppleScript Helpers
- `safari_batch_download.applescript` - Core Safari automation
- `safari_simple_batch.applescript` - Simplified batch processing

### Analysis Tools
- `parse_saved_htmls.py` - Extract structured data from saved profiles
- `linkedin_profile_parser.py` - Parse individual profile data

## 📈 Performance Results

The Safari batch scraper has achieved:
- **125+ high-quality profiles** captured successfully
- **200-280KB average file size** (real profiles)
- **Excellent anti-detection** - no blocking issues
- **30-60 second delays** between batches for safety

## 🗂️ Archived Scrapers

The following scrapers are kept for reference but are not recommended for production use:

### Chrome-based Scrapers (Less Effective)
- `linkedin_scraper_stealth_chrome.py` - Chrome with stealth mode
- `linkedin_scraper_persistent_hammer.py` - Aggressive Chrome scraper
- `linkedin_scraper_hammer_stealth.py` - Enhanced stealth Chrome

### Experimental Versions
- `linkedin_scraper_hybrid.py` - Early batch processing attempt
- `linkedin_scraper_safari.py` - Single-profile Safari scraper
- `linkedin_scraper_conservative.py` - Conservative approach
- `linkedin_scraper_complete.py` - Feature-complete but complex

### Legacy/Test Files
- `linkedin_scraper_test.py` - Testing framework
- `linkedin_scraper_other_groups.py` - Chrome version for other groups
- `linkedin_scraper_safari_other_groups.py` - Safari version for other groups

## 🚀 Quick Start

1. **Setup Safari:**
   ```bash
   sudo safaridriver --enable
   ```

2. **Enable Safari Remote Automation:**
   - Safari → Develop → Allow Remote Automation

3. **Run the scraper:**
   ```bash
   cd src/linkedin
   python linkedin_scraper_safari_batch.py
   ```

4. **Monitor progress (in another terminal):**
   ```bash
   python linkedin_monitor.py
   ```

## 📋 Data Flow

```
other_groups_linkedin_urls.txt (861 URLs)
           ↓
linkedin_scraper_safari_batch.py
           ↓
safari_htmls/ (HTML files) + safari_failed_urls.txt
           ↓
linkedin_monitor.py (real-time stats)
```

## ⚠️ Important Notes

- **Safari is much more effective** than Chrome for LinkedIn scraping
- **Batch processing** (10 profiles at once) is key for efficiency
- **File validation** prevents saving auth walls as profiles
- **Progress tracking** is now accurate and doesn't double-count
- **The scraper can be safely interrupted** and resumed

## 🔍 Troubleshooting

If you see negative remaining counts in the monitor, it means there are old files from previous runs. The monitor now only counts files that correspond to URLs in the current task list. 