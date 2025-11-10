# AI Recruiter Research Project

This repository contains research tools and scripts for analyzing AI-powered recruiting processes, with a focus on LinkedIn profile scraping and candidate evaluation.

## 🍎 LinkedIn Profile Scraper (Production Ready)

The main feature is a robust LinkedIn profile scraper optimized for Safari with excellent anti-detection capabilities.

### Quick Start

1. **Setup Safari:**
   ```bash
   sudo safaridriver --enable
   ```
   Enable: Safari → Develop → Allow Remote Automation

2. **Run the scraper:**
   ```bash
   cd src/linkedin
   python linkedin_scraper_safari_batch.py
   ```

3. **Monitor progress (in another terminal):**
   ```bash
   python linkedin_monitor.py
   ```

### Features
- **Batch processing:** 10 profiles simultaneously in Safari tabs
- **Anti-detection:** Uses Safari's natural browsing patterns  
- **Smart validation:** Only saves real profiles (>200KB with content)
- **Auto-cleanup:** Immediately deletes auth wall pages
- **Real-time monitoring:** Live progress tracking and statistics
- **Resume capability:** Can restart from where it left off

## 📁 Project Structure

```
/
├── src/
│   └── linkedin/
│       ├── linkedin_scraper_safari_batch.py  # 🍎 Main Safari scraper (RECOMMENDED)
│       ├── linkedin_monitor.py               # 📊 Real-time progress monitor
│       ├── parse_saved_htmls.py             # 🔧 Extract structured data
│       ├── linkedin_profile_parser.py       # 🔧 Parse individual profiles
│       ├── safari_batch_download.applescript # 🍎 Safari automation
│       ├── archive/                         # 📦 Old/experimental scrapers
│       └── README_SCRAPERS.md               # 📖 Detailed scraper documentation
│
└── data/
    ├── other_groups_linkedin_urls.txt       # 📋 Input URLs (861 profiles)
    └── linkedin/
        ├── output/
        │   └── safari_htmls/                # 💾 Saved HTML profiles
        └── profiles/
            └── safari_failed_urls.txt       # ❌ Failed URLs log
```

## 📈 Performance Results

The Safari batch scraper has achieved:
- **400+ high-quality profiles** captured successfully
- **200-280KB average file size** (real profiles, not auth walls)
- **Excellent anti-detection** - no blocking issues
- **~50% success rate** with automatic retry for failed URLs

## 🔧 Additional Tools

### Data Analysis Scripts
- `resume_vetting_experiment.py` - Resume evaluation experiments
- `ai_interview_quality.py` - AI interview analysis
- `candidate_nps_with_lee_bounds.py` - NPS analysis with statistical bounds

### R Analysis Scripts (src/)
- `ate.R` - Average Treatment Effect analysis
- `embeds_analysis.R` - Embedding analysis
- `skill_vetting.R` - Skill assessment analysis

## 📊 Research Data

The repository includes various datasets for research:
- LinkedIn profile data and embeddings
- Resume vetting experiment results  
- AI vs human interview comparisons
- Candidate satisfaction (NPS) data

## 🚀 Getting Started

1. **Clone the repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Setup Safari for scraping** (see Quick Start above)
4. **Run the LinkedIn scraper** to collect profile data
5. **Use analysis scripts** to process and analyze the data

## 📖 Documentation

- **LinkedIn Scrapers:** See `src/linkedin/README_SCRAPERS.md` for detailed documentation
- **Individual scripts:** Each script contains docstrings and usage examples

## ⚠️ Important Notes

- **Safari is much more effective** than Chrome for LinkedIn scraping
- **The scraper respects rate limits** with 30-60 second delays between batches
- **All scraped data is for research purposes** - ensure compliance with LinkedIn's terms
- **The scraper can be safely interrupted** and resumed without losing progress

## 🔍 Troubleshooting

If you encounter issues:
1. Check that Safari Remote Automation is enabled
2. Ensure `safaridriver` is running (`sudo safaridriver --enable`)
3. Monitor progress with `linkedin_monitor.py` for real-time diagnostics
4. Check the detailed documentation in `src/linkedin/README_SCRAPERS.md`
