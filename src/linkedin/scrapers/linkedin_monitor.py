#!/usr/bin/env python3
"""
LinkedIn Scraper Monitor - Real-time progress tracking with Safari parser analysis
Monitors the Safari scraper progress and runs parser analysis every minute
"""
import os
import time
import datetime
import subprocess
import pathlib
import glob
from pathlib import Path

# Configuration - match the main scraper paths
URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
OUTPUT_DIR = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
FAILED_URLS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_failed_urls.txt"
HAMMER_LOG_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/hammer_attempts.json"
PROGRESS_FILE = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/profiles/collected_safari_progress.json"
PARSER_SCRIPT = "/Users/emilpalikot/Research/AI-Recruiter/linkedin_safari_parser.py"
PARSER_OUTPUT = "/Users/emilpalikot/Research/AI-Recruiter/collected_htmls_experiences_parsed.csv"
REFRESH_INTERVAL = 60  # 1 minute

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_total_urls():
    """Get total number of URLs to process."""
    try:
        with open(URLS_FILE_PATH, 'r', encoding='utf-8') as f:
            return len([url.strip() for url in f.readlines() if url.strip()])
    except Exception as e:
        print(f"Error reading URLs file: {e}")
        return 0

def get_failed_count():
    """Get number of failed URLs."""
    try:
        if os.path.exists(FAILED_URLS_FILE):
            with open(FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
                return len([url.strip() for url in f.readlines() if url.strip()])
        return 0
    except Exception as e:
        print(f"Error reading failed URLs: {e}")
        return 0

def get_html_files_count():
    """Get count of HTML files collected."""
    try:
        if not os.path.exists(OUTPUT_DIR):
            return 0
        html_files = list(pathlib.Path(OUTPUT_DIR).glob("*.html"))
        return len(html_files)
    except Exception as e:
        print(f"Error counting HTML files: {e}")
        return 0

def get_hammer_stats():
    """Get hammer attempt statistics."""
    try:
        if not os.path.exists(HAMMER_LOG_FILE):
            return {'total_hammered': 0, 'successful_hammers': 0, 'failed_hammers': 0}
        
        import json
        with open(HAMMER_LOG_FILE, 'r') as f:
            hammer_data = json.load(f)
        
        stats = {
            'total_hammered': len(hammer_data),
            'successful_hammers': len([url for url, data in hammer_data.items() if data.get('success', False)]),
            'failed_hammers': len([url for url, data in hammer_data.items() if not data.get('success', False)])
        }
        return stats
    except Exception as e:
        print(f"Error reading hammer stats: {e}")
        return {'total_hammered': 0, 'successful_hammers': 0, 'failed_hammers': 0}

def get_progress_info():
    """Get current progress information from the scraper."""
    try:
        if not os.path.exists(PROGRESS_FILE):
            return None
        
        import json
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
        
        return progress
    except Exception as e:
        print(f"Error reading progress: {e}")
        return None

def run_parser_analysis():
    """Run the Safari parser and return results."""
    try:
        # Run the parser script
        result = subprocess.run(['python', PARSER_SCRIPT], 
                              capture_output=True, text=True, cwd='/Users/emilpalikot/Research/AI-Recruiter')
        
        if result.returncode != 0:
            return None, f"Parser error: {result.stderr}"
        
        # Parse the output to extract statistics
        output_lines = result.stdout.split('\n')
        stats = {}
        
        for line in output_lines:
            if 'Found' in line and 'HTML files' in line:
                stats['total_files'] = int(line.split()[1])
            elif 'Total profiles processed:' in line:
                stats['total_processed'] = int(line.split()[-1])
            elif 'Successful profiles:' in line:
                stats['successful'] = int(line.split()[-1])
            elif 'Profiles with experience:' in line:
                stats['with_experience'] = int(line.split()[-1])
            elif 'Success rate:' in line:
                stats['success_rate'] = float(line.split()[-1].replace('%', ''))
        
        return stats, None
    except Exception as e:
        return None, f"Error running parser: {str(e)}"

def get_experience_profiles():
    """Get list of profiles with experience data from CSV."""
    try:
        if not os.path.exists(PARSER_OUTPUT):
            return []
        
        profiles = []
        with open(PARSER_OUTPUT, 'r', encoding='utf-8') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                if 'False,False' in line:  # profile_empty=False, experience_empty=False
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        linkedin_url = parts[0]
                        job_title = parts[1]
                        company = parts[2]
                        start_date = parts[3]
                        profiles.append({
                            'url': linkedin_url,
                            'title': job_title,
                            'company': company,
                            'start_date': start_date
                        })
        return profiles
    except Exception as e:
        print(f"Error reading experience profiles: {e}")
        return []

def format_time_ago(timestamp):
    """Format how long ago something happened."""
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

def get_recent_files():
    """Get recently modified HTML files."""
    try:
        if not os.path.exists(OUTPUT_DIR):
            return []
        
        html_files = []
        for filepath in pathlib.Path(OUTPUT_DIR).glob("*.html"):
            stat = filepath.stat()
            html_files.append({
                'name': filepath.name,
                'modified_time': stat.st_mtime,
                'size': stat.st_size
            })
        
        # Sort by modification time (newest first)
        html_files.sort(key=lambda x: x['modified_time'], reverse=True)
        return html_files[:5]  # Return last 5
    except Exception as e:
        print(f"Error getting recent files: {e}")
        return []

def display_stats():
    """Display current statistics with parser analysis and hammer stats."""
    clear_screen()
    
    # Get current data
    total_urls = get_total_urls()
    failed_count = get_failed_count()
    html_count = get_html_files_count()
    hammer_stats = get_hammer_stats()
    progress_info = get_progress_info()
    
    # Header
    print("🍎 LinkedIn Safari Scraper - Live Monitor with Hammering Analysis")
    print("=" * 85)
    print(f"📅 Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔄 Refreshes every {REFRESH_INTERVAL} seconds")
    print()
    
    # Collection Progress
    collection_percentage = (html_count / total_urls * 100) if total_urls > 0 else 0
    print("📊 COLLECTION PROGRESS:")
    print(f"   📁 Total URLs to collect: {total_urls:,}")
    print(f"   📄 HTML files collected: {html_count:,} ({collection_percentage:.1f}%)")
    print(f"   ❌ Failed URLs: {failed_count:,}")
    print(f"   📋 Remaining: {total_urls - html_count - failed_count:,}")
    print()
    
    # Progress bar for collection
    if total_urls > 0:
        progress = collection_percentage / 100
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"📊 COLLECTION: [{bar}] {collection_percentage:.1f}%")
        print()
    
    # Hammer Statistics
    print("🔨 HAMMER STATISTICS:")
    print(f"   🎯 Total URLs hammered: {hammer_stats['total_hammered']:,}")
    print(f"   ✅ Successful hammers: {hammer_stats['successful_hammers']:,}")
    print(f"   ❌ Failed hammers: {hammer_stats['failed_hammers']:,}")
    if hammer_stats['total_hammered'] > 0:
        hammer_success_rate = (hammer_stats['successful_hammers'] / hammer_stats['total_hammered']) * 100
        print(f"   📈 Hammer success rate: {hammer_success_rate:.1f}%")
        
        # Hammer progress bar
        hammer_progress = hammer_success_rate / 100
        bar_length = 40
        filled_length = int(bar_length * hammer_progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"🔨 HAMMERING: [{bar}] {hammer_success_rate:.1f}%")
    else:
        print("   📈 No hammer attempts yet")
    print()
    
    # Current Session Progress (if available)
    if progress_info:
        print("📈 CURRENT SESSION:")
        print(f"   📦 Current batch: {progress_info.get('batch', 'N/A')}")
        print(f"   ✅ Profiles scraped this session: {progress_info.get('profiles_scraped', 0):,}")
        print(f"   ❌ Profiles failed this session: {progress_info.get('profiles_failed', 0):,}")
        
        # Session timestamp
        if 'timestamp' in progress_info:
            session_time = datetime.datetime.fromtimestamp(progress_info['timestamp'])
            print(f"   🕒 Last batch: {session_time.strftime('%H:%M:%S')}")
        print()
    
    # Run parser analysis
    print("🔍 RUNNING PARSER ANALYSIS...")
    parser_stats, parser_error = run_parser_analysis()
    
    if parser_error:
        print(f"❌ Parser Error: {parser_error}")
    elif parser_stats:
        print("✅ Parser Analysis Complete!")
        print()
        print("📋 PROFILE ANALYSIS RESULTS:")
        print(f"   📄 Total profiles processed: {parser_stats.get('total_processed', 0):,}")
        print(f"   ✅ Successful profiles: {parser_stats.get('successful', 0):,}")
        print(f"   🎯 Profiles with experience: {parser_stats.get('with_experience', 0):,}")
        print(f"   📈 Experience extraction rate: {parser_stats.get('success_rate', 0):.1f}%")
        
        # Overall success rate
        total_processed = parser_stats.get('total_processed', 0)
        with_experience = parser_stats.get('with_experience', 0)
        overall_success = (with_experience / total_urls * 100) if total_urls > 0 else 0
        print(f"   🌟 Overall success rate: {overall_success:.1f}% ({with_experience}/{total_urls})")
        print()
        
        # Progress bar for experience extraction
        if total_processed > 0:
            exp_progress = parser_stats.get('success_rate', 0) / 100
            bar_length = 40
            filled_length = int(bar_length * exp_progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            print(f"📊 EXPERIENCE: [{bar}] {parser_stats.get('success_rate', 0):.1f}%")
            print()
        
        # Get and display profiles with experience
        experience_profiles = get_experience_profiles()
        print(f"🎯 PROFILES WITH EXPERIENCE DATA ({len(experience_profiles)} total):")
        if experience_profiles:
            for i, profile in enumerate(experience_profiles, 1):
                # Clean up the display
                title = profile['title'].replace('*', '[Redacted]')
                company = profile['company'].replace('*', '[Redacted]')
                start_date = f" ({profile['start_date']})" if profile['start_date'] else ""
                
                print(f"   {i:2d}. {title} at {company}{start_date}")
                
                # Show URL domain for reference
                if 'linkedin.com' in profile['url']:
                    domain = profile['url'].split('/')[2] if '/' in profile['url'] else 'linkedin.com'
                    print(f"       🔗 {domain}")
        else:
            print("   No profiles with experience data found yet...")
        print()
    
    # Recent activity
    recent_files = get_recent_files()
    print("🕒 LAST 5 FILES COLLECTED:")
    if recent_files:
        for i, file_info in enumerate(recent_files, 1):
            time_ago = format_time_ago(file_info['modified_time'])
            size_kb = file_info['size'] // 1024
            timestamp = datetime.datetime.fromtimestamp(file_info['modified_time']).strftime('%H:%M:%S')
            
            # Extract profile name from filename
            name = file_info['name'].replace('linkedin.com_in_', '').replace('.html', '').replace('_', ' ')
            if len(name) > 30:
                name = name[:27] + "..."
            
            print(f"   {i}. {name}")
            print(f"      📅 {timestamp} ({time_ago}) | 📏 {size_kb}KB")
    else:
        print("   No files collected yet...")
    
    print()
    print("💡 Press Ctrl+C to stop monitoring")
    print(f"🔄 Next analysis in {REFRESH_INTERVAL} seconds...")

def main():
    """Main monitoring loop."""
    print("🍎 LinkedIn Scraper Monitor with Parser Analysis Starting...")
    print("🔄 Running parser analysis every minute...")
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