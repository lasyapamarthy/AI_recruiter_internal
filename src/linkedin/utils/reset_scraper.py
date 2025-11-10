#!/usr/bin/env python3
"""
Reset LinkedIn Scraper Progress
Clears all progress files and allows restarting from scratch
"""
import os
import sys
import shutil
from datetime import datetime

# File paths
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_safari_progress.json"
AUTH_RETRY_QUEUE_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/auth_retry_queue.json"
SAVE_LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/save_verification_log.json"
HAMMER_LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/hammer_attempts.json"
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"

def backup_existing_data():
    """Create a backup of existing data before reset."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/backup_{timestamp}"
    
    print(f"📦 Creating backup at: {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup HTML files
    if os.path.exists(OUTPUT_DIR):
        html_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]
        if html_files:
            backup_html_dir = os.path.join(backup_dir, "collected_htmls")
            os.makedirs(backup_html_dir, exist_ok=True)
            
            print(f"   📄 Backing up {len(html_files)} HTML files...")
            for html_file in html_files:
                src = os.path.join(OUTPUT_DIR, html_file)
                dst = os.path.join(backup_html_dir, html_file)
                shutil.copy2(src, dst)
    
    # Backup progress files
    progress_files = [
        FAILED_URLS_FILE,
        PROGRESS_FILE,
        AUTH_RETRY_QUEUE_FILE,
        SAVE_LOG_FILE,
        HAMMER_LOG_FILE
    ]
    
    for file_path in progress_files:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            dst = os.path.join(backup_dir, filename)
            shutil.copy2(file_path, dst)
            print(f"   📋 Backed up: {filename}")
    
    return backup_dir

def get_current_stats():
    """Get current statistics before reset."""
    stats = {}
    
    # Count HTML files
    if os.path.exists(OUTPUT_DIR):
        html_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]
        stats['html_files'] = len(html_files)
        
        total_size = 0
        for html_file in html_files:
            try:
                file_path = os.path.join(OUTPUT_DIR, html_file)
                total_size += os.path.getsize(file_path)
            except:
                pass
        stats['total_size_mb'] = total_size / 1024 / 1024
    else:
        stats['html_files'] = 0
        stats['total_size_mb'] = 0
    
    # Count failed URLs
    if os.path.exists(FAILED_URLS_FILE):
        with open(FAILED_URLS_FILE, 'r') as f:
            stats['failed_urls'] = len([line.strip() for line in f.readlines() if line.strip()])
    else:
        stats['failed_urls'] = 0
    
    # Count total URLs
    if os.path.exists(URLS_FILE_PATH):
        with open(URLS_FILE_PATH, 'r') as f:
            stats['total_urls'] = len([line.strip() for line in f.readlines() if line.strip()])
    else:
        stats['total_urls'] = 0
    
    return stats

def clear_progress_files():
    """Clear all progress tracking files."""
    files_to_clear = [
        FAILED_URLS_FILE,
        PROGRESS_FILE,
        AUTH_RETRY_QUEUE_FILE,
        SAVE_LOG_FILE,
        HAMMER_LOG_FILE
    ]
    
    print("🧹 Clearing progress files...")
    for file_path in files_to_clear:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"   ❌ Removed: {os.path.basename(file_path)}")
        else:
            print(f"   ⚪ Not found: {os.path.basename(file_path)}")

def clear_html_files():
    """Clear all collected HTML files."""
    if os.path.exists(OUTPUT_DIR):
        html_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]
        if html_files:
            print(f"🧹 Clearing {len(html_files)} HTML files...")
            for html_file in html_files:
                file_path = os.path.join(OUTPUT_DIR, html_file)
                os.remove(file_path)
            print("   ✅ All HTML files removed")
        else:
            print("   ⚪ No HTML files found")
    else:
        print("   ⚪ Output directory doesn't exist")

def verify_urls_file():
    """Verify the URLs file exists and show statistics."""
    if not os.path.exists(URLS_FILE_PATH):
        print(f"❌ URLs file not found: {URLS_FILE_PATH}")
        return False
    
    with open(URLS_FILE_PATH, 'r') as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"📋 URLs file verified: {len(urls)} URLs to process")
    
    # Show first few URLs as sample
    print("   Sample URLs:")
    for i, url in enumerate(urls[:3], 1):
        print(f"   {i}. {url}")
    if len(urls) > 3:
        print(f"   ... and {len(urls) - 3} more")
    
    return True

def main():
    """Main reset function."""
    print("🔄 LinkedIn Scraper Reset Tool")
    print("=" * 50)
    
    # Get current statistics
    print("📊 Current Status:")
    stats = get_current_stats()
    print(f"   📁 HTML files: {stats['html_files']} ({stats['total_size_mb']:.1f} MB)")
    print(f"   ❌ Failed URLs: {stats['failed_urls']}")
    print(f"   📋 Total URLs: {stats['total_urls']}")
    print()
    
    # Verify URLs file
    if not verify_urls_file():
        print("❌ Cannot proceed without URLs file")
        return
    print()
    
    # Confirm reset
    print("⚠️  This will:")
    print("   1. Create a backup of existing data")
    print("   2. Clear all progress tracking files")
    print("   3. Remove all collected HTML files")
    print("   4. Reset scraper to start from beginning")
    print()
    
    response = input("🤔 Do you want to proceed? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Reset cancelled")
        return
    
    print("\n🚀 Starting reset process...")
    
    # Create backup
    backup_dir = backup_existing_data()
    print(f"✅ Backup created: {backup_dir}")
    
    # Clear progress files
    clear_progress_files()
    print("✅ Progress files cleared")
    
    # Clear HTML files
    clear_html_files()
    print("✅ HTML files cleared")
    
    # Verify reset
    print("\n🔍 Verifying reset...")
    new_stats = get_current_stats()
    print(f"   📁 HTML files: {new_stats['html_files']}")
    print(f"   ❌ Failed URLs: {new_stats['failed_urls']}")
    print(f"   📋 URLs to process: {new_stats['total_urls']}")
    
    print("\n✅ Reset completed successfully!")
    print(f"📦 Backup saved to: {backup_dir}")
    print("\n🚀 You can now restart the scraper:")
    print("   python3 src/linkedin/scrapers/linkedin_scraper_safari_batch.py")
    print("\n📊 Monitor progress with:")
    print("   python3 src/linkedin/utils/scraper_monitor.py")

if __name__ == "__main__":
    main() 