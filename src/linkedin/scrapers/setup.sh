#!/bin/bash
# Setup script for LinkedIn scraper

echo "LinkedIn Scraper Setup"
echo "====================="

# Make Python scripts executable
echo "Setting executable permissions on Python scripts..."
chmod +x scraper_emil.py
chmod +x scraper_emil_improved.py
chmod +x test_scraper.py
chmod +x check_permissions.py

# Make AppleScripts executable
echo "Setting executable permissions on AppleScripts..."
chmod +x scripts/*.applescript

# Check if directories exist
echo -e "\nChecking directory structure..."
if [ -d "scripts" ]; then
    echo "✅ scripts/ directory exists"
else
    echo "❌ scripts/ directory missing - creating it..."
    mkdir -p scripts
fi

# List AppleScript files
echo -e "\nAppleScript files found:"
ls -la scripts/*.applescript 2>/dev/null || echo "❌ No AppleScript files found in scripts/"

# Run permission checker
echo -e "\nChecking system permissions..."
python3 check_permissions.py

echo -e "\n====================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. If permission issues were found, follow the instructions above"
echo "2. Test with a single URL: python3 test_scraper.py"
echo "3. Run the improved scraper: python3 scraper_emil_improved.py urls.txt output_dir" 