#!/usr/bin/env python3
"""
Check AppleScript permissions for Safari and Chrome
"""

import subprocess
import sys

def check_browser_control(browser: str):
    """Check if we can control a browser via AppleScript"""
    
    print(f"\n🔍 Checking {browser} control permissions...")
    
    # Simple AppleScript to test browser control
    if browser.lower() == "safari":
        script = '''
        tell application "Safari"
            return "Safari is controllable"
        end tell
        '''
    else:
        script = '''
        tell application "Google Chrome"
            return "Chrome is controllable"
        end tell
        '''
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ {browser} can be controlled via AppleScript")
            return True
        else:
            print(f"❌ Cannot control {browser}")
            if "not allowed assistive access" in result.stderr:
                print(f"   → Need to grant Accessibility permissions")
            else:
                print(f"   → Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout trying to control {browser}")
        return False
    except Exception as e:
        print(f"❌ Error checking {browser}: {e}")
        return False


def check_file_write():
    """Check if we can write files"""
    print(f"\n🔍 Checking file write permissions...")
    
    try:
        test_file = "test_write_permission.txt"
        with open(test_file, "w") as f:
            f.write("test")
        
        import os
        os.remove(test_file)
        print(f"✅ Can write files in current directory")
        return True
    except Exception as e:
        print(f"❌ Cannot write files: {e}")
        return False


def main():
    print("LinkedIn Scraper Permission Checker")
    print("=" * 40)
    
    issues = []
    
    # Check Safari
    if not check_browser_control("Safari"):
        issues.append("Safari control")
    
    # Check Chrome
    if not check_browser_control("Chrome"):
        issues.append("Chrome control")
    
    # Check file writing
    if not check_file_write():
        issues.append("File writing")
    
    print(f"\n{'='*40}")
    print("Summary:")
    print(f"{'='*40}")
    
    if not issues:
        print("✅ All permissions OK! The scraper should work.")
    else:
        print(f"❌ Permission issues found:")
        for issue in issues:
            print(f"   - {issue}")
        
        print(f"\n📋 How to fix:")
        print(f"   1. Open System Preferences → Security & Privacy → Privacy")
        print(f"   2. Click on 'Accessibility' in the left sidebar")
        print(f"   3. Click the lock icon and authenticate")
        print(f"   4. Add Terminal (or your IDE) to the list")
        print(f"   5. Ensure the checkbox is checked")
        print(f"   6. You may need to restart Terminal/IDE")


if __name__ == "__main__":
    main() 