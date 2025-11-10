#!/usr/bin/env python3
"""
LinkedIn Scraper Monitor - Real-time Progress Tracking
Monitors scraping progress every 30 seconds without interrupting the main process
"""
import os
import sys
import time
import json
from datetime import datetime, timedelta
import subprocess

# Configuration
MONITOR_INTERVAL = 30  # seconds
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_safari_progress.json"
AUTH_RETRY_QUEUE_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/auth_retry_queue.json"
SAVE_LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/save_verification_log.json"

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_file_count_and_size(directory):
    """Get count and total size of HTML files in directory."""
    if not os.path.exists(directory):
        return 0, 0
    
    try:
        html_files = [f for f in os.listdir(directory) if f.endswith('.html')]
        total_size = 0
        for html_file in html_files:
            try:
                file_path = os.path.join(directory, html_file)
                total_size += os.path.getsize(file_path)
            except:
                pass
        return len(html_files), total_size
    except Exception as e:
        return 0, 0

def get_total_urls():
    """Get total number of URLs to process."""
    try:
        if os.path.exists(URLS_FILE_PATH):
            with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
                return len([line.strip() for line in f.readlines() if line.strip()])
        return 0
    except:
        return 0

def get_failed_count():
    """Get number of failed URLs."""
    try:
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                return len([line.strip() for line in f.readlines() if line.strip()])
        return 0
    except:
        return 0

def get_retry_queue_stats():
    """Get retry queue statistics."""
    try:
        if os.path.exists(AUTH_RETRY_QUEUE_FILE):
            with open(AUTH_RETRY_QUEUE_FILE, 'r') as f:
                queue = json.load(f)
                
                current_time = time.time()
                ready_count = 0
                total_attempts = 0
                
                for item in queue:
                    total_attempts += item.get('retry_attempts', 0)
                    time_since_added = current_time - item.get('added_time', 0)
                    if time_since_added >= 300:  # 5 minutes
                        ready_count += 1
                
                return len(queue), ready_count, total_attempts
        return 0, 0, 0
    except:
        return 0, 0, 0

def get_last_progress():
    """Get last progress information."""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                progress = json.load(f)
                return progress
        return None
    except:
        return None

def get_recent_save_failures():
    """Get recent save failures from log."""
    try:
        if os.path.exists(SAVE_LOG_FILE):
            with open(SAVE_LOG_FILE, 'r') as f:
                log_data = json.load(f)
                
                # Get failures from last hour
                one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                recent_failures = [
                    entry for entry in log_data 
                    if not entry.get('is_valid', True) and entry.get('timestamp', '') > one_hour_ago
                ]
                return len(recent_failures), recent_failures[-5:] if recent_failures else []
        return 0, []
    except:
        return 0, []

def check_scraper_running():
    """Check if the scraper is currently running."""
    try:
        # Check for Python processes running the scraper
        result = subprocess.run(['pgrep', '-f', 'linkedin_scraper_safari_batch'], 
                              capture_output=True, text=True)
        return len(result.stdout.strip().split('\n')) > 0 if result.stdout.strip() else False
    except:
        return False

def format_time_ago(timestamp):
    """Format timestamp as time ago."""
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        now = datetime.now()
        if dt.tzinfo:
            now = now.replace(tzinfo=dt.tzinfo)
        
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds//3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds//60}m ago"
        else:
            return f"{diff.seconds}s ago"
    except:
        return "unknown"

def calculate_rate(saved_count, failed_count, time_elapsed_hours):
    """Calculate scraping rate per hour."""
    if time_elapsed_hours <= 0:
        return 0
    return (saved_count + failed_count) / time_elapsed_hours

def estimate_completion_time(remaining_count, current_rate):
    """Estimate completion time based on current rate."""
    if current_rate <= 0:
        return "unknown"
    
    hours_remaining = remaining_count / current_rate
    
    if hours_remaining < 1:
        return f"{int(hours_remaining * 60)}m"
    elif hours_remaining < 24:
        return f"{hours_remaining:.1f}h"
    else:
        days = hours_remaining / 24
        return f"{days:.1f}d"

def display_progress():
    """Display current progress information."""
    clear_screen()
    
    # Header
    print("🔍 LinkedIn Scraper Monitor")
    print("=" * 80)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Refreshing every {MONITOR_INTERVAL}s")
    print()
    
    # Check if scraper is running
    scraper_running = check_scraper_running()
    status_icon = "🟢" if scraper_running else "🔴"
    status_text = "RUNNING" if scraper_running else "STOPPED"
    print(f"{status_icon} Scraper Status: {status_text}")
    print()
    
    # Get current statistics
    total_urls = get_total_urls()
    saved_count, total_size = get_file_count_and_size(OUTPUT_DIR)
    failed_count = get_failed_count()
    remaining_count = max(0, total_urls - saved_count - failed_count)
    
    # Progress overview
    print("📊 PROGRESS OVERVIEW")
    print("-" * 40)
    print(f"📁 Total URLs to process: {total_urls:,}")
    print(f"✅ Successfully saved: {saved_count:,} ({total_size/1024/1024:.1f} MB)")
    print(f"❌ Failed: {failed_count:,}")
    print(f"📋 Remaining: {remaining_count:,}")
    
    if total_urls > 0:
        completion_pct = ((saved_count + failed_count) / total_urls) * 100
        success_rate = (saved_count / (saved_count + failed_count)) * 100 if (saved_count + failed_count) > 0 else 0
        print(f"📈 Completion: {completion_pct:.1f}%")
        print(f"🎯 Success rate: {success_rate:.1f}%")
    print()
    
    # Progress bar
    if total_urls > 0:
        progress = (saved_count + failed_count) / total_urls
        bar_length = 50
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"Progress: [{bar}] {progress*100:.1f}%")
        print()
    
    # Retry queue information
    queue_total, queue_ready, total_attempts = get_retry_queue_stats()
    if queue_total > 0:
        print("🔄 RETRY QUEUE")
        print("-" * 40)
        print(f"📋 Total in queue: {queue_total}")
        print(f"⏰ Ready for retry: {queue_ready}")
        print(f"🔨 Total retry attempts: {total_attempts}")
        print()
    
    # Last session information
    last_progress = get_last_progress()
    if last_progress:
        print("📈 LAST SESSION")
        print("-" * 40)
        print(f"🔢 Batch: {last_progress.get('batch', 'N/A')}")
        print(f"✅ Profiles saved: {last_progress.get('profiles_saved', 0)}")
        print(f"❌ Profiles failed: {last_progress.get('profiles_failed', 0)}")
        
        timestamp = last_progress.get('timestamp')
        if timestamp:
            print(f"⏰ Last update: {format_time_ago(timestamp)}")
        print()
    
    # Recent failures
    failure_count, recent_failures = get_recent_save_failures()
    if failure_count > 0:
        print("⚠️  RECENT FAILURES (Last Hour)")
        print("-" * 40)
        print(f"❌ Total failures: {failure_count}")
        if recent_failures:
            print("📋 Latest failures:")
            for failure in recent_failures:
                url = failure.get('url', 'Unknown')[:50]
                message = failure.get('message', 'Unknown error')[:30]
                print(f"   • {url}... - {message}...")
        print()
    
    # Rate calculation and ETA
    if last_progress and scraper_running:
        timestamp = last_progress.get('timestamp')
        if timestamp:
            try:
                if isinstance(timestamp, (int, float)):
                    session_start = datetime.fromtimestamp(timestamp)
                else:
                    session_start = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                time_elapsed = datetime.now() - session_start
                hours_elapsed = time_elapsed.total_seconds() / 3600
                
                if hours_elapsed > 0:
                    session_saved = last_progress.get('profiles_saved', 0)
                    session_failed = last_progress.get('profiles_failed', 0)
                    current_rate = calculate_rate(session_saved, session_failed, hours_elapsed)
                    
                    print("⚡ PERFORMANCE")
                    print("-" * 40)
                    print(f"📊 Current rate: {current_rate:.1f} profiles/hour")
                    
                    if remaining_count > 0 and current_rate > 0:
                        eta = estimate_completion_time(remaining_count, current_rate)
                        print(f"⏱️  ETA: {eta}")
                    print()
            except:
                pass
    
    # File system info
    try:
        statvfs = os.statvfs(OUTPUT_DIR)
        free_space = statvfs.f_frsize * statvfs.f_bavail
        print(f"💾 Free disk space: {free_space/1024/1024/1024:.1f} GB")
    except:
        pass
    
    print()
    print("Press Ctrl+C to stop monitoring")

def main():
    """Main monitoring loop."""
    print("🔍 Starting LinkedIn Scraper Monitor...")
    print(f"📊 Monitoring every {MONITOR_INTERVAL} seconds")
    print("Press Ctrl+C to stop")
    time.sleep(2)
    
    try:
        while True:
            display_progress()
            time.sleep(MONITOR_INTERVAL)
    except KeyboardInterrupt:
        clear_screen()
        print("🛑 Monitoring stopped")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main() 