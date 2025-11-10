#!/usr/bin/osascript
-- Gentle Chrome AppleScript for logged-in LinkedIn scraping
-- Uses regular windows (not incognito) to maintain login session

on run argv
    if (count of argv) < 2 then return
    
    set theURL to item 1 of argv
    set theFile to item 2 of argv
    
    tell application "Google Chrome"
        activate
        
        -- Open URL in a new tab in the front window (or create new window if needed)
        if (count of windows) = 0 then
            make new window
        end if
        
        set currentWindow to front window
        set tabRef to make new tab at end of tabs of currentWindow
        set active tab index of currentWindow to (count of tabs of currentWindow)
        
        set URL of tabRef to theURL
    end tell
    
    -- Wait for page to fully load (up to 45 seconds)
    set maxWait to 45
    set waitCount to 0
    set pageReady to false
    
    repeat while waitCount < maxWait
        delay 1
        set waitCount to waitCount + 1
        
        try
            tell application "Google Chrome"
                -- Check if we're still on LinkedIn
                set currentURL to URL of tabRef
                if currentURL does not contain "linkedin.com" then
                    exit repeat
                end if
                
                -- Check if page is loaded using JavaScript
                set loadStatus to execute tabRef javascript "
                    (function() {
                        if (document.readyState !== 'complete') return 'loading';
                        
                        // For logged-in profiles, check for more elements
                        var indicators = [
                            document.querySelector('meta[property=\"profile:first_name\"]'),
                            document.querySelector('.pv-top-card'),
                            document.querySelector('.profile-top-card'),
                            document.querySelector('[data-member-id]'),
                            document.querySelector('.pv-text-details__left-panel'),
                            document.querySelector('.scaffold-layout__main'),
                            document.querySelector('main.scaffold-layout__main'),
                            document.querySelector('section.artdeco-card')
                        ];
                        
                        var hasContent = indicators.some(function(el) { return el !== null; });
                        
                        // Also check if we have a reasonable amount of content
                        var bodyLength = document.body ? document.body.innerText.length : 0;
                        
                        if (hasContent || bodyLength > 1000) {
                            return 'ready';
                        } else {
                            return 'waiting';
                        }
                    })();
                "
                
                if loadStatus is "ready" then
                    set pageReady to true
                    exit repeat
                end if
            end tell
        on error
            -- Continue waiting if JavaScript fails
        end try
    end repeat
    
    -- Extra wait for dynamic content to fully render
    if pageReady then
        delay 10  -- 10 seconds for all dynamic content
    else
        delay 3   -- Short delay even if not ready
    end if
    
    -- Capture the page HTML
    set pageSource to ""
    try
        tell application "Google Chrome"
            -- Get full HTML using JavaScript
            set pageSource to execute tabRef javascript "document.documentElement.outerHTML"
        end tell
    on error errMsg
        -- If JavaScript fails, try getting at least something
        try
            tell application "Google Chrome"
                set pageSource to execute tabRef javascript "document.body.outerHTML"
            end tell
        on error
            set pageSource to "Error: Could not capture page content - " & errMsg
        end try
    end try
    
    -- Save to file
    do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
    
    -- Close the tab
    delay 1
    try
        tell application "Google Chrome" to close tabRef
    end try
end run 