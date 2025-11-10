#!/usr/bin/env python3
"""
LinkedIn Scraper Monitor V2 - Streamlined Real-time Dashboard
Advanced monitoring with visual progress, trends, and smart alerts
"""
import os
import time
import datetime
import json
import subprocess
import pathlib
from collections import deque
import statistics

# Configuration
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"
AUTH_RETRY_QUEUE_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/auth_retry_queue.json"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_safari_progress.json"
PARSER_SCRIPT = "/Users/emilpalikot/Research/AI-Recruiter/linkedin_safari_parser.py"
PARSER_OUTPUT = "/Users/emilpalikot/Research/AI-Recruiter/collected_htmls_experiences_parsed.csv"

REFRESH_INTERVAL = 30  # 30 seconds for more responsive monitoring
TREND_WINDOW = 20  # Keep last 20 data points for trends

class ScrapingMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.data_history = deque(maxlen=TREND_WINDOW)
        self.last_file_count = 0
        self.last_check_time = time.time()
        
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_basic_stats(self):
        """Get basic collection statistics."""
        try:
            # Total URLs
            with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
                total_urls = len([url.strip() for url in f.readlines() if url.strip()])
            
            # Collected files
            collected_count = 0
            total_size = 0
            if os.path.exists(OUTPUT_DIR):
                html_files = list(pathlib.Path(OUTPUT_DIR).glob("*.html"))
                collected_count = len(html_files)
                total_size = sum(f.stat().st_size for f in html_files)
            
            # Failed URLs
            failed_count = 0
            if os.path.exists(FAILED_URLS_FILE):
                with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                    failed_count = len([url.strip() for url in f.readlines() if url.strip()])
            
            # Retry queue
            retry_queue = []
            if os.path.exists(AUTH_RETRY_QUEUE_FILE):
                with open(AUTH_RETRY_QUEUE_FILE, 'r') as f:
                    retry_queue = json.load(f)
            
            return {
                'total_urls': total_urls,
                'collected': collected_count,
                'failed': failed_count,
                'retry_queue': len(retry_queue),
                'remaining': total_urls - collected_count - failed_count,
                'total_size_mb': total_size / (1024 * 1024),
                'retry_queue_data': retry_queue
            }
        except Exception as e:
            print(f"Error getting basic stats: {e}")
            return None
    
    def get_session_info(self):
        """Get current session information."""
        try:
            if os.path.exists(PROGRESS_FILE):
                with open(PROGRESS_FILE, 'r') as f:
                    progress = json.load(f)
                return progress
            return None
        except Exception as e:
            return None
    
    def run_parser_analysis(self):
        """Run parser and get experience data."""
        try:
            result = subprocess.run(['python', PARSER_SCRIPT], 
                                  capture_output=True, text=True, 
                                  cwd='/Users/emilpalikot/Research/AI-Recruiter',
                                  timeout=60)
            
            if result.returncode != 0:
                return None
            
            # Count profiles with experience from CSV
            experience_count = 0
            if os.path.exists(PARSER_OUTPUT):
                with open(PARSER_OUTPUT, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[1:]  # Skip header
                    experience_count = len([line for line in lines if 'False,False' in line])
            
            return experience_count
        except Exception as e:
            return None
    
    def calculate_trends(self, current_stats):
        """Calculate collection trends and rates."""
        current_time = time.time()
        
        # Add current data point
        self.data_history.append({
            'time': current_time,
            'collected': current_stats['collected'],
            'failed': current_stats['failed']
        })
        
        if len(self.data_history) < 2:
            return None
        
        # Calculate rates
        time_diff = current_time - self.data_history[0]['time']
        collected_diff = current_stats['collected'] - self.data_history[0]['collected']
        
        if time_diff > 0:
            profiles_per_hour = (collected_diff / time_diff) * 3600
            
            # Estimate completion time
            remaining = current_stats['remaining']
            if profiles_per_hour > 0:
                hours_remaining = remaining / profiles_per_hour
                eta = datetime.datetime.now() + datetime.timedelta(hours=hours_remaining)
            else:
                eta = None
            
            return {
                'profiles_per_hour': profiles_per_hour,
                'eta': eta,
                'trend_direction': 'up' if collected_diff > 0 else 'stable'
            }
        
        return None
    
    def create_progress_bar(self, current, total, width=40, label=""):
        """Create a visual progress bar."""
        if total == 0:
            percentage = 0
        else:
            percentage = (current / total) * 100
        
        filled = int(width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)
        
        return f"{label}[{bar}] {percentage:5.1f}% ({current:,}/{total:,})"
    
    def get_retry_queue_analysis(self, retry_queue_data):
        """Analyze retry queue for insights."""
        if not retry_queue_data:
            return None
        
        current_time = time.time()
        ready_count = 0
        avg_attempts = 0
        oldest_item = None
        
        for item in retry_queue_data:
            # Check if ready for retry (5+ minutes old)
            if current_time - item.get('added_time', 0) >= 300:
                ready_count += 1
            
            # Track attempts
            avg_attempts += item.get('retry_attempts', 0)
            
            # Find oldest item
            if oldest_item is None or item.get('added_time', 0) < oldest_item.get('added_time', 0):
                oldest_item = item
        
        avg_attempts = avg_attempts / len(retry_queue_data) if retry_queue_data else 0
        
        return {
            'ready_count': ready_count,
            'avg_attempts': avg_attempts,
            'oldest_age_minutes': (current_time - oldest_item.get('added_time', current_time)) / 60 if oldest_item else 0
        }
    
    def display_dashboard(self):
        """Display the main monitoring dashboard."""
        self.clear_screen()
        
        # Header
        uptime = time.time() - self.start_time
        uptime_str = f"{int(uptime//3600):02d}:{int((uptime%3600)//60):02d}:{int(uptime%60):02d}"
        
        print("🍎 LinkedIn Scraper Monitor V2 - Live Dashboard")
        print("=" * 80)
        print(f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ⏱️  Uptime: {uptime_str} | 🔄 Refresh: {REFRESH_INTERVAL}s")
        print()
        
        # Get current data
        stats = self.get_basic_stats()
        if not stats:
            print("❌ Error loading statistics")
            return
        
        session_info = self.get_session_info()
        trends = self.calculate_trends(stats)
        
        # Main Progress Section
        print("📊 COLLECTION PROGRESS")
        print("-" * 50)
        
        # Overall progress bar
        overall_progress = self.create_progress_bar(
            stats['collected'], stats['total_urls'], 50, "Overall: "
        )
        print(f"  {overall_progress}")
        
        # Success rate progress bar
        attempted = stats['collected'] + stats['failed']
        if attempted > 0:
            success_rate = (stats['collected'] / attempted) * 100
            success_bar = self.create_progress_bar(
                stats['collected'], attempted, 50, "Success: "
            )
            print(f"  {success_bar}")
        
        print()
        
        # Key Metrics
        print("📈 KEY METRICS")
        print("-" * 30)
        print(f"  📁 Total URLs:      {stats['total_urls']:,}")
        print(f"  ✅ Collected:       {stats['collected']:,} ({stats['total_size_mb']:.1f} MB)")
        print(f"  ❌ Failed:          {stats['failed']:,}")
        print(f"  📋 Remaining:       {stats['remaining']:,}")
        print(f"  🔄 In Retry Queue:  {stats['retry_queue']:,}")
        
        if attempted > 0:
            print(f"  📈 Success Rate:    {success_rate:.1f}%")
        
        print()
        
        # Performance & Trends
        if trends:
            print("⚡ PERFORMANCE")
            print("-" * 25)
            print(f"  🚀 Rate:            {trends['profiles_per_hour']:.1f} profiles/hour")
            if trends['eta']:
                print(f"  🎯 ETA:             {trends['eta'].strftime('%Y-%m-%d %H:%M')}")
            print(f"  📊 Trend:           {trends['trend_direction'].upper()}")
            print()
        
        # Current Session
        if session_info:
            print("🔄 CURRENT SESSION")
            print("-" * 30)
            print(f"  📦 Current Batch:   {session_info.get('batch', 'N/A')}")
            print(f"  ✅ Session Saved:   {session_info.get('profiles_scraped', 0):,}")
            print(f"  ❌ Session Failed:  {session_info.get('profiles_failed', 0):,}")
            
            if 'timestamp' in session_info:
                last_batch = datetime.datetime.fromtimestamp(session_info['timestamp'])
                time_since = datetime.datetime.now() - last_batch
                print(f"  🕒 Last Activity:   {time_since.total_seconds()/60:.0f} min ago")
            print()
        
        # Retry Queue Analysis
        retry_analysis = self.get_retry_queue_analysis(stats['retry_queue_data'])
        if retry_analysis:
            print("🔄 RETRY QUEUE STATUS")
            print("-" * 35)
            print(f"  ⏰ Ready for Retry: {retry_analysis['ready_count']:,}")
            print(f"  📊 Avg Attempts:    {retry_analysis['avg_attempts']:.1f}")
            print(f"  ⏳ Oldest Item:     {retry_analysis['oldest_age_minutes']:.0f} min ago")
            print()
        
        # Experience Analysis (run every few cycles to avoid slowdown)
        if int(time.time()) % 120 < REFRESH_INTERVAL:  # Every 2 minutes
            print("🔍 Running experience analysis...")
            experience_count = self.run_parser_analysis()
            if experience_count is not None:
                exp_rate = (experience_count / stats['collected'] * 100) if stats['collected'] > 0 else 0
                print(f"  🎯 Profiles with Experience: {experience_count:,} ({exp_rate:.1f}%)")
            print()
        
        # Smart Alerts
        alerts = []
        if trends and trends['profiles_per_hour'] < 5:
            alerts.append("⚠️  Low collection rate detected")
        if stats['retry_queue'] > 100:
            alerts.append("⚠️  Large retry queue building up")
        if session_info and 'timestamp' in session_info:
            inactive_time = time.time() - session_info['timestamp']
            if inactive_time > 600:  # 10 minutes
                alerts.append("⚠️  Scraper appears inactive")
        
        if alerts:
            print("🚨 ALERTS")
            print("-" * 15)
            for alert in alerts:
                print(f"  {alert}")
            print()
        
        # Footer
        print("💡 Press Ctrl+C to stop monitoring")
        print(f"🔄 Next update in {REFRESH_INTERVAL} seconds...")
    
    def run(self):
        """Main monitoring loop."""
        print("🍎 LinkedIn Scraper Monitor V2 Starting...")
        print("🚀 Enhanced dashboard with real-time metrics")
        print()
        
        try:
            while True:
                self.display_dashboard()
                time.sleep(REFRESH_INTERVAL)
        except KeyboardInterrupt:
            self.clear_screen()
            print("🛑 LinkedIn Scraper Monitor V2 Stopped")
            print("📊 Final Statistics:")
            
            stats = self.get_basic_stats()
            if stats:
                print(f"   ✅ Total Collected: {stats['collected']:,}")
                print(f"   📈 Success Rate: {(stats['collected']/(stats['collected']+stats['failed'])*100):.1f}%")
                print(f"   ⏱️  Monitor Uptime: {(time.time()-self.start_time)/3600:.1f} hours")
            
            print("👋 Thanks for monitoring!")

if __name__ == "__main__":
    monitor = ScrapingMonitor()
    monitor.run() 