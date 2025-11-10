#!/bin/zsh

# LinkedIn Scraper Continuous Monitor for zsh
# Usage: ./src/linkedin/watch_scraper.sh

PROJECT_DIR="/Users/emilpalikot/Research/AI-Recruiter"
cd "$PROJECT_DIR"

echo "🚀 Starting continuous monitoring of LinkedIn scraper..."
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    # Clear screen
    clear
    
    # Show current time
    echo "Last updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Run the monitor script
    ./src/linkedin/monitor_progress.sh
    
    # Show refresh info
    echo ""
    echo "🔄 Auto-refreshing every 30 seconds..."
    echo "Press Ctrl+C to stop monitoring"
    
    # Wait 30 seconds
    sleep 30
done 