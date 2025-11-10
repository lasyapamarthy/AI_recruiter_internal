#!/usr/bin/osascript
-- Save a batch of LinkedIn profiles in ONE Safari Private window (tabs)
-- Usage:  osascript save_batch_safari.applescript url1 file1 url2 file2 …

on run argv
    set pairCount to (count of argv) div 2
    if pairCount = 0 then return
    
    tell application "Safari"
        activate
        delay 1
        
        -- Create a new private window
        tell application "System Events" to keystroke "n" using {command down, shift down}
        delay 2
        
        set win to front window
    end tell
    
    repeat with i from 1 to pairCount
        set theURL to item (i * 2 - 1) of argv
        set theFile to item (i * 2) of argv
        
        try
            if i = 1 then
                tell application "Safari"
                    set URL of current tab of win to theURL
                    set tabRef to current tab of win
                end tell
            else
                tell application "Safari"
                    set tabRef to make new tab at end of tabs of win
                    set current tab of win to tabRef
                    set URL of tabRef to theURL
                end tell
            end if
            
            -- Wait for page to load
            repeat 15 times
                delay 0.5
                try
                    tell application "Safari"
                        set curURL to URL of tabRef
                        if curURL contains "linkedin.com" then exit repeat
                    end tell
                end try
            end repeat
            delay 2
            
            -- Get page source
            set pageSource to ""
            try
                tell application "Safari"
                    set pageSource to source of tabRef
                end tell
            end try
            
            -- Save to file
            do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
            
            -- Close tab
            try
                tell application "Safari" to close tabRef
            end try
            
        on error errMsg
            -- If there's an error, just continue to next URL
            try
                do shell script "echo 'Error processing " & theURL & ": " & errMsg & "' > " & quoted form of theFile
            end try
        end try
    end repeat
    
    -- Close the private window
    try
        tell application "Safari" to close win
    end try
end run
