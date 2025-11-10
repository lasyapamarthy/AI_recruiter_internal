#!/usr/bin/env python3
"""
LinkedIn Scraper Monitor - Real-time progress tracking
Monitors the Safari scraper progress and shows live statistics
"""
import os
import time
import datetime
from pathlib import Path

# Configuration - match the main scraper paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/other_groups_linkedin_urls.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/safari_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/safari_failed_urls.txt"
REFRESH_INTERVAL = 30  # seconds

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_original_urls():
    """Get set of original URLs to process."""
    try:
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            return set(url.strip() for url in f.readlines() if url.strip())
    except Exception as e:
        print(f"Error reading URLs file: {e}")
        return set()

def get_total_urls():
    """Get total number of URLs to process."""
    return len(get_original_urls())

def get_failed_count():
    """Get number of failed URLs that are in the original list."""
    try:
        original_urls = get_original_urls()
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                failed_urls = [url.strip() for url in f.readlines() if url.strip()]
                # Only count failed URLs that are in the original list
                return len([url for url in failed_urls if url in original_urls])
        return 0
    except Exception as e:
        print(f"Error reading failed URLs: {e}")
        return 0

def get_saved_profiles_info():
    """Get information about saved profiles that correspond to original URLs."""
    try:
        if not os.path.exists(OUTPUT_DIR):
            return [], 0, 0
        
        original_urls = get_original_urls()
        html_files = []
        total_size = 0
        
        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith('.html'):
                filepath = os.path.join(OUTPUT_DIR, filename)
                try:
                    # Convert filename back to URL format to check if it's in original list
                    url_part = filename.replace('.html', '')
                    
                    # Handle different URL formats in filenames
                    if url_part.startswith('http:__'):
                        url = url_part.replace('http:__', 'https://').replace('_', '/')
                    elif url_part.startswith('ae.linkedin.com'):
                        url = 'https://' + url_part.replace('_', '/')
                    else:
                        # Try to reconstruct URL
                        url = 'https://' + url_part.replace('_', '/')
                    
                    # Only count files that correspond to original URLs
                    if url in original_urls:
                        stat = os.stat(filepath)
                        file_size = stat.st_size
                        modified_time = stat.st_mtime
                        
                        html_files.append({
                            'filename': filename,
                            'size': file_size,
                            'modified_time': modified_time,
                            'modified_datetime': datetime.datetime.fromtimestamp(modified_time)
                        })
                        total_size += file_size
                except:
                    continue
        
        # Sort by modification time (newest first)
        html_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return html_files, len(html_files), total_size
    except Exception as e:
        print(f"Error getting saved profiles: {e}")
        return [], 0, 0

def format_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def format_time_ago(timestamp):
    """Format how long ago a file was modified."""
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return f"{int(diff)}s ago"
    elif diff < 3600:
        return f"{int(diff/60)}m ago"
    elif diff < 86400:
        return f"{int(diff/3600)}h ago"
    else:
        return f"{int(diff/86400)}d ago"

def extract_profile_name(filename):
    """Extract profile name from filename."""
    # Remove .html extension and linkedin.com prefix
    name = filename.replace('.html', '').replace('linkedin.com_in_', '')
    # Replace underscores with spaces and limit length
    name = name.replace('_', ' ').replace('-', ' ')
    if len(name) > 30:
        name = name[:27] + "..."
    return name

def display_stats():
    """Display current statistics."""
    clear_screen()
    
    # Get current data
    total_urls = get_total_urls()
    failed_count = get_failed_count()
    saved_files, saved_count, total_size = get_saved_profiles_info()
    
    # Calculate percentages
    total_processed = saved_count + failed_count
    saved_percentage = (saved_count / total_urls * 100) if total_urls > 0 else 0
    failed_percentage = (failed_count / total_urls * 100) if total_urls > 0 else 0
    processed_percentage = (total_processed / total_urls * 100) if total_urls > 0 else 0
    
    # Header
    print("🍎 LinkedIn Safari Scraper - Live Monitor")
    print("=" * 60)
    print(f"📅 Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔄 Refreshes every {REFRESH_INTERVAL} seconds")
    print()
    
    # Main statistics
    print("📊 OVERALL PROGRESS:")
    print(f"   📁 Total profiles to collect: {total_urls:,}")
    print(f"   ✅ Total saved: {saved_count:,} ({saved_percentage:.1f}%)")
    print(f"   ❌ Total failed: {failed_count:,} ({failed_percentage:.1f}%)")
    print(f"   🔄 Total processed: {total_processed:,} ({processed_percentage:.1f}%)")
    print(f"   📋 Remaining: {total_urls - total_processed:,}")
    print()
    
    # File statistics
    print("📁 FILE STATISTICS:")
    print(f"   💾 Total size: {format_size(total_size)}")
    if saved_count > 0:
        avg_size = total_size / saved_count
        print(f"   📏 Average file size: {format_size(avg_size)}")
    print()
    
    # Success rate
    if total_processed > 0:
        success_rate = (saved_count / total_processed * 100)
        print(f"📈 SUCCESS RATE: {success_rate:.1f}%")
        print()
    
    # Progress bar
    if total_urls > 0:
        progress = processed_percentage / 100
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"📊 PROGRESS: [{bar}] {processed_percentage:.1f}%")
        print()
    
    # Last 5 saved profiles
    print("🕒 LAST 5 PROFILES SAVED:")
    if saved_files:
        for i, file_info in enumerate(saved_files[:5], 1):
            profile_name = extract_profile_name(file_info['filename'])
            size_str = format_size(file_info['size'])
            time_ago = format_time_ago(file_info['modified_time'])
            timestamp = file_info['modified_datetime'].strftime('%H:%M:%S')
            
            print(f"   {i}. {profile_name}")
            print(f"      📅 {timestamp} ({time_ago}) | 📏 {size_str}")
    else:
        print("   No profiles saved yet...")
    
    print()
    print("💡 Press Ctrl+C to stop monitoring")
    print("🔄 Next refresh in 30 seconds...")

def main():
    """Main monitoring loop."""
    print("🍎 LinkedIn Scraper Monitor Starting...")
    print("🔄 Monitoring scraper progress...")
    print()
    
    try:
        while True:
            display_stats()
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        clear_screen()
        print("🛑 LinkedIn Scraper Monitor Stopped")
        print("👋 Thanks for monitoring!")

if __name__ == "__main__":
    main() 