#!/usr/bin/env python3
import subprocess
import os

# Test with a single URL
test_url = "https://www.linkedin.com/in/hitanshu-shah-21272017a"
output_dir = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/safari_scraped"
filename = os.path.join(output_dir, "test_profile")

print(f"Testing Safari save with URL: {test_url}")
print(f"Output file: {filename}.html")

# Simple AppleScript to test saving
applescript = f'''
tell application "Safari"
    activate
    
    -- Create new private window
    make new document
    set privateWindow to window 1
    
    -- Open URL
    set URL of current tab of privateWindow to "{test_url}"
    
    -- Wait for page to load
    delay 10
    
    -- Get page source
    set pageSource to source of current tab of privateWindow
    
    -- Log info
    log "Page source length: " & (length of pageSource)
    
    -- Save to file
    set filePath to POSIX file "{filename}.html"
    try
        set fileHandle to open for access filePath with write permission
        set eof fileHandle to 0
        write pageSource to fileHandle as «class utf8»
        close access fileHandle
        log "File saved successfully"
    on error errMsg
        log "Error saving: " & errMsg
        try
            close access filePath
        end try
    end try
    
    -- Close window
    close privateWindow
end tell

return "done"
'''

print("Running AppleScript...")
try:
    result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, timeout=30)
    print(f"Return code: {result.returncode}")
    print(f"Output: {result.stdout}")
    print(f"Errors: {result.stderr}")
    
    # Check if file was created
    if os.path.exists(f"{filename}.html"):
        file_size = os.path.getsize(f"{filename}.html")
        print(f"✅ File created successfully! Size: {file_size} bytes")
    else:
        print("❌ File was not created")
        
except Exception as e:
    print(f"Error: {e}") 