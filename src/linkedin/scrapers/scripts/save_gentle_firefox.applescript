#!/usr/bin/osascript
-- Gentle Firefox AppleScript for logged-in LinkedIn scraping
-- Simplified version due to Firefox's limited AppleScript support

on run argv
    if (count of argv) < 2 then return
    
    set theURL to item 1 of argv
    set theFile to item 2 of argv
    
    -- Open URL in Firefox
    tell application "Firefox"
        activate
        open location theURL
    end tell
    
    -- Wait for page to load (Firefox requires longer delays)
    delay 15  -- Initial load time
    
    -- Additional wait for dynamic content
    delay 15  -- More time for JavaScript content
    
    -- Try to capture page content using keyboard shortcuts
    set pageSource to ""
    try
        tell application "System Events"
            tell process "Firefox"
                set frontmost to true
                delay 1
                
                -- Select all and copy page content
                -- First click in the page to ensure focus
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
        try
            set pageSource to the clipboard as text
        on error
            -- If direct text conversion fails, try getting string representation
            try
                set pageSource to (the clipboard as string)
            on error
                -- Last resort: get whatever we can
                set pageSource to "Error: Clipboard contained non-text data"
            end try
        end try
        
    on error errMsg
        set pageSource to "Error: Could not capture Firefox content - " & errMsg
    end try
    
    -- Save to file
    try
        -- Use a more robust method to save text content
        set fileHandle to open for access theFile with write permission
        set eof fileHandle to 0
        write pageSource to fileHandle as «class utf8»
        close access fileHandle
    on error
        -- Fallback to shell script if file operations fail
        try
            close access theFile
        end try
        do shell script "echo " & quoted form of pageSource & " > " & quoted form of theFile
    end try
    
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