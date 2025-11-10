# AI-Recruiter Scraping Tasks Reorganization Summary

## Date: May 27, 2024

### Overview
This document summarizes the reorganization of the AI-Recruiter project's scraping tasks, parsers, and data files to improve project structure and maintainability.

## Directory Structure Changes

### 1. Archive Directory Created
Created `archive/` with subdirectories:
- `archive/old_csv_files/` - Contains deprecated CSV outputs
- `archive/deprecated_scrapers/` - Contains old scraper implementations
- `archive/deprecated_parsers/` - Contains old parser implementations
- `archive/old_scripts/` - Contains miscellaneous old scripts

### 2. Experiments Directory Created
Created `experiments/` with subdirectories:
- `experiments/resume_vetting/` - Resume vetting experiment files
- `experiments/ai_interviews/` - AI interview analysis files
- `experiments/embeddings/` - Embedding analysis files

### 3. LinkedIn Source Code Reorganization
Reorganized `src/linkedin/` into:
- `src/linkedin/scrapers/` - Active scraper implementations
- `src/linkedin/parsers/` - Active parser implementations
- `src/linkedin/utils/` - Utility scripts
- `src/linkedin/applescripts/` - AppleScript automation files
- `src/linkedin/archive/` - Deprecated LinkedIn-specific code

## Files Moved

### Moved to archive/deprecated_scrapers/:
- `linkedin_scraper.py`
- `linkedin_scraper_from_list.py`

### Moved to archive/deprecated_parsers/:
- `linkedin_profile_parser.py`
- `linkedin_safari_parser.py`
- `linkedin_manual_collection_parser.py`
- `linkedin_profile_parser_enhanced.py`

### Moved to archive/old_scripts/:
- `consolidate_and_filter_htmls.py`
- `consolidate_and_filter_htmls_v2.py`
- `simple_consolidate.py`
- `parse_consolidated_htmls.py`
- `parse_all_directories.py`
- `append_new_profiles.py`
- `append_collected_to_combined.py`
- `combine_safari_htmls_data.py`
- `analyze_all_linkedin_data.py`
- `analyze_parsed_profiles.py`
- `linkedin_scraper_README.md`
- `README_LIST_SCRAPER.md`

### Moved to archive/old_csv_files/:
- `collected_htmls_experiences_parsed.csv`
- `consolidated_profiles_parsed.csv`
- `consolidated_profiles_with_experience.csv`
- `safari_htmls_experiences_parsed.csv`
- `manual_collection_experiences_parsed.csv`
- `linkedin_experiences_enhanced.csv`
- `linkedin_experiences_parsed.csv`

### Moved to experiments/:
- Resume vetting files → `experiments/resume_vetting/`
- AI interview files → `experiments/ai_interviews/`
- Embedding analysis files → `experiments/embeddings/`

### LinkedIn Code Organization:
- Active scrapers → `src/linkedin/scrapers/`
- Active parsers → `src/linkedin/parsers/`
- Utility scripts → `src/linkedin/utils/`
- AppleScripts → `src/linkedin/applescripts/`

## Current Active Components

### Active Scrapers:
- `linkedin_scraper_safari_batch.py` - Main Safari-based batch scraper
- `linkedin_monitor.py` & `linkedin_monitor_v2.py` - Scraping progress monitors

### Active Parsers:
- `unified_linkedin_parser.py` & `unified_linkedin_parser_v2.py` - Unified parsing approach
- `parse_all_htmls_robust.py` - Robust HTML parsing
- `parse_htmls_directory.py` - Directory-based parsing

### Utility Scripts:
- `filter_and_extract_profiles.py`
- `extract_most_recent_jobs.py`
- `scrape_remaining_safari.py`
- `create_remaining_urls_csv.py`
- `extract_linkedin_urls.py`

## Data Organization
- All LinkedIn-related CSV data files are now in `data/linkedin/`
- Experiment-specific data is in respective `experiments/` subdirectories
- Archive contains all deprecated outputs for reference

## Benefits of Reorganization
1. **Clearer Structure**: Separation of active vs deprecated code
2. **Better Maintainability**: Organized by functionality (scrapers, parsers, utils)
3. **Preserved History**: All old files archived rather than deleted
4. **Experiment Isolation**: Research experiments separated from scraping infrastructure
5. **Easier Navigation**: Logical grouping makes finding relevant code easier

## Next Steps Recommendations
1. Update any scripts that reference moved files
2. Consider creating a unified entry point for scraping operations
3. Document the purpose and usage of each active component
4. Set up automated tests for active scrapers and parsers
5. Consider version control for data outputs 