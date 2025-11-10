#!/usr/bin/osascript
-- Save a batch of LinkedIn profiles in ONE Google Chrome Incognito window (tabs)
-- Usage:  osascript save_batch_chrome.applescript url1 file1 url2 file2 …

on run argv
    set pairCount to (count of argv) div 2
    if pairCount = 0 then return
    
    --─────────────────────────────────────────────────────────────
    -- open incognito window
    tell application "Google Chrome"
        activate
        set win to make new window with properties {mode:"incognito"}
    end tell
    
    repeat with i from 1 to pairCount
        set theURL  to item (i * 2 - 1) of argv
        set theFile to item (i * 2) of argv
        
        -- first URL uses initial tab
        if i = 1 then
            tell application "Google Chrome"
                set tabRef to active tab of win
                set URL of tabRef to theURL
            end tell
        else
            tell application "Google Chrome"
                set tabRef to make new tab at end of tabs of win
                set URL of tabRef to theURL
            end tell
        end if
        
        -- wait until navigation completes (simple URL check)
        repeat 20 times
            delay 0.5
            try
                tell application "Google Chrome" to set curURL to URL of tabRef
                if curURL starts with theURL then exit repeat
            end try
        end repeat
        delay 1
        
        -- fetch HTML via JXA
        set jxa to "
            const chrome = Application('Google Chrome');
            const html = chrome.windows[0].activeTab.execute({
                javascript: 'document.documentElement.outerHTML'
            });
            console.log(html);
        "
        set pageSource to do shell script "osascript -l JavaScript <<'JS'\n" & jxa & "\nJS"
        
        do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
        
        tell application "Google Chrome" to close tabRef
    end repeat
    
    tell application "Google Chrome" to close win
end run
