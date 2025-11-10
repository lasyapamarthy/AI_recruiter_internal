#!/bin/bash

# LinkedIn Scraper Progress Monitor
# This script shows the current progress of the parallel scraping

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/Users/emilpalikot/Research/AI-Recruiter"

echo -e "${BLUE}LinkedIn Scraper Progress Monitor${NC}"
echo "================================="

# Change to project directory
cd "$PROJECT_DIR"

# Count HTML files
html_count=$(find data/linkedin/output/htmls -name "*.html" 2>/dev/null | wc -l | tr -d ' ')

# Count failed URLs
failed_count=0
if [ -f "data/linkedin/profiles/failed_urls.txt" ]; then
    failed_count=$(wc -l < data/linkedin/profiles/failed_urls.txt | tr -d ' ')
fi

# Count processed URLs
processed_count=0
if [ -f "data/linkedin/profiles/processed_urls.txt" ]; then
    processed_count=$(wc -l < data/linkedin/profiles/processed_urls.txt | tr -d ' ')
fi

# Total URLs (from previous run)
total_urls=572
remaining_urls=304

# Calculate progress
completed=$((html_count))
remaining=$((remaining_urls - completed - failed_count))
if [ $remaining -lt 0 ]; then
    remaining=0
fi

progress_percent=0
if [ $remaining_urls -gt 0 ]; then
    progress_percent=$(( (completed * 100) / remaining_urls ))
fi

echo ""
echo -e "${GREEN}📊 Current Progress:${NC}"
echo "==================="
echo -e "Total URLs to process: ${BLUE}$remaining_urls${NC}"
echo -e "Successfully scraped:  ${GREEN}$html_count${NC} HTML files"
echo -e "Failed URLs:           ${RED}$failed_count${NC}"
echo -e "Remaining:             ${YELLOW}$remaining${NC}"
echo -e "Progress:              ${GREEN}$progress_percent%${NC}"

# Progress bar
bar_length=50
filled_length=$(( (progress_percent * bar_length) / 100 ))
bar=$(printf "%*s" $filled_length | tr ' ' '█')
empty=$(printf "%*s" $((bar_length - filled_length)) | tr ' ' '░')
echo -e "Progress bar:          [${GREEN}$bar${NC}${YELLOW}$empty${NC}] $progress_percent%"

echo ""

# Check if workers are running
worker_processes=$(pgrep -f "linkedin_scraper_parallel" | wc -l | tr -d ' ')
echo -e "${BLUE}🔧 Worker Status:${NC}"
echo "================="
if [ $worker_processes -gt 0 ]; then
    echo -e "Active workers: ${GREEN}$worker_processes${NC}"
    echo ""
    echo -e "${YELLOW}Running processes:${NC}"
    pgrep -f "linkedin_scraper_parallel" | while read pid; do
        ps -p $pid -o pid,command | tail -n +2
    done
else
    echo -e "Active workers: ${RED}0${NC} (No workers running)"
fi

echo ""

# Show recent activity (last 5 HTML files)
echo -e "${BLUE}📁 Recent Activity:${NC}"
echo "=================="
if [ $html_count -gt 0 ]; then
    echo -e "${YELLOW}Last 5 scraped profiles:${NC}"
    find data/linkedin/output/htmls -name "*.html" -type f -exec ls -lt {} + 2>/dev/null | head -5 | while read line; do
        filename=$(echo "$line" | awk '{print $NF}' | sed 's/.*\///')
        timestamp=$(echo "$line" | awk '{print $6, $7, $8}')
        echo "  $timestamp - $filename"
    done
else
    echo "No HTML files found yet."
fi

echo ""

# Show estimated completion time
if [ $worker_processes -gt 0 ] && [ $remaining -gt 0 ]; then
    # Rough estimate: assume 30 seconds per profile with 4 workers
    seconds_per_profile=30
    estimated_seconds=$(( (remaining * seconds_per_profile) / worker_processes ))
    
    hours=$((estimated_seconds / 3600))
    minutes=$(( (estimated_seconds % 3600) / 60 ))
    
    echo -e "${BLUE}⏱️  Estimated Completion:${NC}"
    echo "========================"
    if [ $hours -gt 0 ]; then
        echo -e "Approximately ${YELLOW}${hours}h ${minutes}m${NC} remaining"
    else
        echo -e "Approximately ${YELLOW}${minutes}m${NC} remaining"
    fi
fi

echo ""
echo -e "${BLUE}💡 Commands:${NC}"
echo "============"
echo "Monitor continuously: watch -n 30 ./src/linkedin/monitor_progress.sh"
echo "Stop all workers:     pkill -f 'linkedin_scraper_parallel'"
echo "View worker logs:     tail -f /tmp/chrome_user_data_worker_*/chrome_debug.log"
echo "" 