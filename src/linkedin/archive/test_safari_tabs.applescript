tell application "Safari"
    activate
    
    -- Set first tab
    set URL of document 1 to "https://www.linkedin.com/in/md-nesad-30b5bb286"
    
    -- Create second tab
    tell window 1 to make new tab with properties {URL:"https://www.linkedin.com/in/saurabhsonde"}
    
    -- Create third tab
    tell window 1 to make new tab with properties {URL:"https://www.linkedin.com/in/tdhpatel"}
    
    -- Wait a bit
    delay 5
    
    -- Try to get page source from first tab
    set current tab of window 1 to tab 1 of window 1
    delay 2
    
    try
        set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
        set filename to "/Users/emilpalikot/Research/AI-Recruiter/test_output.html"
        
        set fileRef to open for access filename with write permission
        write pageSource to fileRef
        close access fileRef
        
        return "Success: Saved to " & filename
    on error errMsg
        return "Error: " & errMsg
    end try
    
end tell 