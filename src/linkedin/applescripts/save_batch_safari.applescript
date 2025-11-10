#!/usr/bin/osascript
-- Save a batch of LinkedIn profiles in ONE Safari Private window (tabs)
-- Usage:  osascript save_batch_safari.applescript url1 file1 url2 file2 …

on run argv
    set pairCount to (count of argv) div 2
    if pairCount = 0 then return
    
    --─────────────────────────────────────────────────────────────
    -- open a new PRIVATE window
    tell application "Safari"
        activate
        -- Cmd-Shift-N produces a private window
        tell application "System Events" to keystroke "n" using {command down, shift down}
        delay 0.5
        set win to front window
    end tell
    
    repeat with i from 1 to pairCount
        set theURL  to item (i * 2 - 1) of argv
        set theFile to item (i * 2) of argv
        
        -- first URL: use existing empty tab; others: new tab
        if i = 1 then
            tell application "Safari" to set URL of current tab of win to theURL
            set tabRef to current tab of win
        else
            tell application "Safari"
                set tabRef to make new tab at end of tabs of win
                set current tab of win to tabRef
                set URL of tabRef to theURL
            end tell
        end if
        
        -- spin-wait until page reports target URL
        repeat 20 times
            delay 0.5
            try
                tell application "Safari" to set curURL to URL of tabRef
                if curURL starts with theURL then exit repeat
            end try
        end repeat
        delay 1
        
        -- grab full HTML
        set pageSource to ""
        try
            tell application "Safari" to set pageSource to source of tabRef
        end try
        
        do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
        
        -- close tab (keeps memory low)
        tell application "Safari" to close tabRef
    end repeat
    
    tell application "Safari" to close win
end run
