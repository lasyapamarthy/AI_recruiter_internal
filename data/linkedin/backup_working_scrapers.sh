#!/bin/bash

# Backup Working LinkedIn Scrapers
# This script creates a backup of the production-ready scraper files

BACKUP_DIR="linkedin_scrapers_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating backup directory: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

# Copy the working scraper files
echo "Backing up working scraper files..."
cp src/linkedin/linkedin_scraper_safari_batch.py "$BACKUP_DIR/"
cp src/linkedin/linkedin_monitor.py "$BACKUP_DIR/"
cp src/linkedin/safari_batch_download.applescript "$BACKUP_DIR/"
cp src/linkedin/safari_simple_batch.applescript "$BACKUP_DIR/"
cp src/linkedin/parse_saved_htmls.py "$BACKUP_DIR/"
cp src/linkedin/linkedin_profile_parser.py "$BACKUP_DIR/"

# Copy documentation
cp src/linkedin/README_SCRAPERS.md "$BACKUP_DIR/"
cp README.md "$BACKUP_DIR/"

# Copy requirements
cp requirements.txt "$BACKUP_DIR/"

echo "Backup completed successfully!"
echo "Files backed up to: $BACKUP_DIR"
echo ""
echo "Working scraper files:"
echo "- linkedin_scraper_safari_batch.py (Main Safari scraper)"
echo "- linkedin_monitor.py (Real-time monitor)"
echo "- safari_batch_download.applescript (Safari automation)"
echo "- parse_saved_htmls.py (Data extraction)"
echo "- linkedin_profile_parser.py (Profile parsing)"
echo ""
echo "To restore, copy these files back to src/linkedin/" 