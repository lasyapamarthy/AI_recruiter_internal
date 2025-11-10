#!/usr/bin/env python3
"""
Test script to diagnose LinkedIn scraping issues
"""

import subprocess
import time
from pathlib import Path
import sys

def test_single_url(url: str, browser: str = "safari"):
    """Test scraping a single URL to diagnose issues"""
    
    print(f"\n{'='*60}")
    print(f"Testing URL: {url}")
    print(f"Browser: {browser}")
    print(f"{'='*60}\n")
    
    # Determine script path
    script_dir = Path(__file__).parent / "scripts"
    if browser == "chrome":
        script_path = script_dir / "save_batch_chrome_improved.applescript"
    elif browser == "firefox":
        script_path = script_dir / "save_gentle_firefox.applescript"
    else:
        script_path = script_dir / "save_batch_safari_improved.applescript"
    
    # Check if script exists
    if not script_path.exists():
        print(f"❌ AppleScript not found: {script_path}")
        return
    
    # Create test output file
    test_file = Path(f"test_profile_{int(time.time())}.html")
    
    # Call AppleScript
    cmd = ["osascript", str(script_path), url, str(test_file)]
    print(f"📞 Calling AppleScript...")
    print(f"   Command: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Elapsed time: {elapsed:.1f} seconds")
        
        if result.returncode == 0:
            print(f"✅ AppleScript executed successfully")
        else:
            print(f"❌ AppleScript failed with return code: {result.returncode}")
            
        if result.stdout:
            print(f"\n📤 STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\n📥 STDERR:\n{result.stderr}")
            
    except subprocess.TimeoutExpired:
        print(f"❌ AppleScript timed out after 60 seconds")
        return
    except Exception as e:
        print(f"❌ Error executing AppleScript: {e}")
        return
    
    # Check if file was created
    print(f"\n📁 Checking output file: {test_file}")
    
    if test_file.exists():
        file_size = test_file.stat().st_size
        print(f"✅ File created successfully")
        print(f"   Size: {file_size:,} bytes")
        
        # Read first 500 chars
        content = test_file.read_text(errors='ignore')[:500]
        print(f"\n📄 First 500 characters:")
        print("-" * 40)
        print(content)
        print("-" * 40)
        
        # Quick analysis
        if "auth_wall" in content:
            print(f"\n🔒 AUTH WALL DETECTED")
        elif "profile:first_name" in content:
            print(f"\n✅ PROFILE METADATA FOUND")
        elif file_size < 1000:
            print(f"\n⚠️  FILE TOO SMALL - likely an error")
        else:
            print(f"\n❓ UNKNOWN PAGE TYPE")
            
        # Clean up test file
        print(f"\n🗑️  Cleaning up test file...")
        test_file.unlink()
        
    else:
        print(f"❌ File was NOT created")
        print(f"   This indicates the AppleScript failed to save the content")


def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test URL
        url = "https://www.linkedin.com/in/williamhgates"
    
    if len(sys.argv) > 2:
        browser = sys.argv[2].lower()
    else:
        browser = "safari"
    
    test_single_url(url, browser)
    
    print(f"\n💡 Suggestions:")
    print(f"   - If file wasn't created, check AppleScript permissions")
    print(f"   - If auth wall detected, try logging into LinkedIn in the browser first")
    print(f"   - If file is too small, the page might not have loaded fully")
    print(f"   - Try both browsers to see if one works better")


if __name__ == "__main__":
    print("LinkedIn Scraper Diagnostic Tool")
    print("Usage: python test_scraper.py [URL] [browser]")
    print("Example: python test_scraper.py https://www.linkedin.com/in/johndoe chrome")
    main() 