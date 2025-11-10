#!/usr/bin/env python3
"""
Quick Status Checker for LinkedIn Scraper
Shows current progress without the full monitoring interface
"""
import os
import subprocess

# File paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"

def get_stats():
    """Get current statistics."""
    # Total URLs
    try:
        with open(URLS_FILE_PATH, 'r') as f:
            total_urls = len([line.strip() for line in f.readlines() if line.strip()])
    except:
        total_urls = 0
    
    # Saved files
    try:
        if os.path.exists(OUTPUT_DIR):
            html_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')]
            saved_count = len(html_files)
            
            total_size = 0
            for html_file in html_files:
                try:
                    file_path = os.path.join(OUTPUT_DIR, html_file)
                    total_size += os.path.getsize(file_path)
                except:
                    pass
        else:
            saved_count = 0
            total_size = 0
    except:
        saved_count = 0
        total_size = 0
    
    # Failed URLs
    try:
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r') as f:
                failed_count = len([line.strip() for line in f.readlines() if line.strip()])
        else:
            failed_count = 0
    except:
        failed_count = 0
    
    # Check if scraper is running
    try:
        result = subprocess.run(['pgrep', '-f', 'linkedin_scraper_safari_batch'], 
                              capture_output=True, text=True)
        scraper_running = len(result.stdout.strip().split('\n')) > 0 if result.stdout.strip() else False
    except:
        scraper_running = False
    
    return {
        'total_urls': total_urls,
        'saved_count': saved_count,
        'failed_count': failed_count,
        'total_size': total_size,
        'remaining': max(0, total_urls - saved_count - failed_count),
        'scraper_running': scraper_running
    }

def main():
    """Display quick status."""
    stats = get_stats()
    
    print("🔍 LinkedIn Scraper Quick Status")
    print("=" * 40)
    
    # Status indicator
    status_icon = "🟢" if stats['scraper_running'] else "🔴"
    status_text = "RUNNING" if stats['scraper_running'] else "STOPPED"
    print(f"{status_icon} Scraper: {status_text}")
    print()
    
    # Progress
    print(f"📁 Total URLs: {stats['total_urls']:,}")
    print(f"✅ Saved: {stats['saved_count']:,} ({stats['total_size']/1024/1024:.1f} MB)")
    print(f"❌ Failed: {stats['failed_count']:,}")
    print(f"📋 Remaining: {stats['remaining']:,}")
    
    if stats['total_urls'] > 0:
        completion_pct = ((stats['saved_count'] + stats['failed_count']) / stats['total_urls']) * 100
        success_rate = (stats['saved_count'] / (stats['saved_count'] + stats['failed_count'])) * 100 if (stats['saved_count'] + stats['failed_count']) > 0 else 0
        print(f"📈 Completion: {completion_pct:.1f}%")
        print(f"🎯 Success rate: {success_rate:.1f}%")
    
    # Progress bar
    if stats['total_urls'] > 0:
        progress = (stats['saved_count'] + stats['failed_count']) / stats['total_urls']
        bar_length = 30
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"\nProgress: [{bar}] {progress*100:.1f}%")

if __name__ == "__main__":
    main() 