#!/usr/bin/env python3
"""
Test script for Safari LinkedIn scraper
Tests with a small batch to ensure everything is working
"""
import os
import sys
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_scraper():
    """Test the Safari scraper with a small batch."""
    print("🧪 Testing Safari LinkedIn Scraper")
    print("=" * 50)
    
    # Check if URLs file exists
    urls_file = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"
    if not os.path.exists(urls_file):
        print(f"❌ URLs file not found: {urls_file}")
        return
    
    # Read first 3 URLs for testing
    with open(urls_file, 'r') as f:
        test_urls = [line.strip() for line in f.readlines()[:3] if line.strip()]
    
    if not test_urls:
        print("❌ No URLs found in file")
        return
    
    print(f"📋 Testing with {len(test_urls)} URLs:")
    for i, url in enumerate(test_urls, 1):
        print(f"   {i}. {url}")
    
    # Create a test URLs file
    test_urls_file = "/tmp/test_linkedin_urls.txt"
    with open(test_urls_file, 'w') as f:
        for url in test_urls:
            f.write(url + '\n')
    
    # Run the scraper with test configuration
    print("\n🚀 Running scraper...")
    
    # Modify the scraper to use test file
    scraper_path = os.path.join(os.path.dirname(__file__), "linkedin_scraper_safari_batch.py")
    
    # Create a temporary modified version
    with open(scraper_path, 'r') as f:
        scraper_content = f.read()
    
    # Replace the URLs file path temporarily
    test_scraper_content = scraper_content.replace(
        'URLS_FILE_PATH = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/linkedin_urls_to_collect.txt"',
        f'URLS_FILE_PATH = "{test_urls_file}"'
    )
    
    # Also reduce batch size for testing
    test_scraper_content = test_scraper_content.replace(
        'BATCH_SIZE = 10',
        'BATCH_SIZE = 3'
    )
    
    # Save temporary test scraper
    test_scraper_path = "/tmp/test_safari_scraper.py"
    with open(test_scraper_path, 'w') as f:
        f.write(test_scraper_content)
    
    # Make it executable
    os.chmod(test_scraper_path, 0o755)
    
    # Run the test scraper
    try:
        result = subprocess.run([sys.executable, test_scraper_path], 
                              capture_output=True, text=True)
        
        print("\n📊 Test Results:")
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        # Check if files were created
        output_dir = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/collected_htmls"
        if os.path.exists(output_dir):
            html_files = [f for f in os.listdir(output_dir) if f.endswith('.html')]
            print(f"\n✅ Found {len(html_files)} HTML files in output directory")
            
            # Check file sizes
            for html_file in html_files[-3:]:  # Last 3 files
                filepath = os.path.join(output_dir, html_file)
                size = os.path.getsize(filepath) / 1024  # KB
                print(f"   - {html_file}: {size:.1f} KB")
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
    
    finally:
        # Clean up
        try:
            os.remove(test_urls_file)
            os.remove(test_scraper_path)
        except:
            pass
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_scraper() 