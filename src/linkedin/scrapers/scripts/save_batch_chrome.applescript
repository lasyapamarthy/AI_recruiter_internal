#!/usr/bin/osascript
-- Save a batch of LinkedIn profiles in ONE Chrome Incognito window (tabs)
-- Usage:  osascript save_batch_chrome.applescript url1 file1 url2 file2 …

on run argv
    set pairCount to (count of argv) div 2
    if pairCount = 0 then return
    
    --─────────────────────────────────────────────────────────────
    -- open a new INCOGNITO window
    tell application "Google Chrome"
        activate
        delay 1
        set win to make new window with properties {mode:"incognito"}
    end tell
    
    repeat with i from 1 to pairCount
        set theURL to item (i * 2 - 1) of argv
        set theFile to item (i * 2) of argv
        
        try
            if i = 1 then
                tell application "Google Chrome"
                    set URL of active tab of win to theURL
                    set tabRef to active tab of win
                end tell
            else
                tell application "Google Chrome"
                    set tabRef to make new tab at end of tabs of win
                    set active tab index of win to (count of tabs of win)
                    set URL of tabRef to theURL
                end tell
            end if
            
            -- Wait for page to load
            repeat 15 times
                delay 0.5
                try
                    tell application "Google Chrome"
                        set curURL to URL of tabRef
                        if curURL contains "linkedin.com" then exit repeat
                    end tell
                end try
            end repeat
            delay 3
            
            -- Get page source using View Source
            tell application "Google Chrome" to activate
            tell application "System Events"
                keystroke "u" using {command down, option down}
                delay 2
                keystroke "a" using command down
                delay 0.5
                keystroke "c" using command down
                delay 0.5
                keystroke "w" using command down
            end tell
            
            set pageSource to the clipboard
            do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
            
            -- Close tab
            try
                tell application "Google Chrome" to close tabRef
            end try
            
        on error errMsg
            -- If there's an error, just continue to next URL
            try
                do shell script "echo 'Error processing " & theURL & ": " & errMsg & "' > " & quoted form of theFile
            end try
        end try
    end repeat
    
    -- Close the incognito window
    try
        tell application "Google Chrome" to close win
    end try
end run
