#!/usr/bin/osascript
-- Debug version of Gentle Firefox AppleScript for LinkedIn scraping

on run argv
    if (count of argv) < 2 then return
    
    set theURL to item 1 of argv
    set theFile to item 2 of argv
    
    -- Open URL in Firefox
    tell application "Firefox"
        activate
        open location theURL
    end tell
    
    -- Wait for page to load
    delay 15
    
    -- Additional wait for dynamic content
    delay 15
    
    -- Try to capture page content
    set pageSource to ""
    try
        tell application "System Events"
            tell process "Firefox"
                set frontmost to true
                delay 1
                
                -- Debug: Log window title
                set windowTitle to name of window 1
                do shell script "echo 'Window: " & windowTitle & "' >> /tmp/firefox_debug.log"
                
                -- Click in the page to ensure focus
                click at {500, 400}
                delay 1
                
                -- Select all
                keystroke "a" using command down
                delay 2
                
                -- Copy
                keystroke "c" using command down
                delay 2
            end tell
        end tell
        
        -- Get from clipboard
        set pageSource to the clipboard
        
        -- Debug: Log clipboard length
        do shell script "echo 'Clipboard length: " & (count of pageSource) & "' >> /tmp/firefox_debug.log"
        
    on error errMsg
        set pageSource to "Error: " & errMsg
        do shell script "echo 'Error: " & errMsg & "' >> /tmp/firefox_debug.log"
    end try
    
    -- If clipboard is empty, try alternative method
    if (count of pageSource) < 10 then
        do shell script "echo 'Clipboard was empty, trying view source' >> /tmp/firefox_debug.log"
        
        -- Try View Page Source approach
        try
            tell application "System Events"
                tell process "Firefox"
                    -- Open page source
                    keystroke "u" using command down
                    delay 5
                    
                    -- Select all in source window
                    keystroke "a" using command down
                    delay 1
                    
                    -- Copy source
                    keystroke "c" using command down
                    delay 1
                    
                    -- Close source window
                    keystroke "w" using command down
                    delay 1
                end tell
            end tell
            
            set pageSource to the clipboard
            do shell script "echo 'Source view clipboard length: " & (count of pageSource) & "' >> /tmp/firefox_debug.log"
            
        on error errMsg2
            do shell script "echo 'Source view error: " & errMsg2 & "' >> /tmp/firefox_debug.log"
        end try
    end if
    
    -- Save to file (ensure we write something, even if empty)
    if (count of pageSource) > 0 then
        do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
    else
        do shell script "echo 'No content captured' > " & quoted form of theFile
    end if
    
    -- Close the tab
    delay 1
    try
        tell application "System Events"
            tell process "Firefox"
                keystroke "w" using command down
            end tell
        end tell
    end try
end run 