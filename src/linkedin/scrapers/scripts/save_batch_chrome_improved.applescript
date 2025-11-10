#!/usr/bin/osascript
-- Improved Chrome AppleScript for LinkedIn profile scraping
-- Uses JavaScript execution instead of View Source for better reliability

on run argv
    set pairCount to (count of argv) div 2
    if pairCount = 0 then return
    
    tell application "Google Chrome"
        activate
        delay 1
        set win to make new window with properties {mode:"incognito"}
    end tell
    
    repeat with i from 1 to pairCount
        set theURL to item (i * 2 - 1) of argv
        set theFile to item (i * 2) of argv
        
        try
            -- Open URL in new tab
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
            
            -- Enhanced wait for page load
            set maxWait to 30 -- 30 seconds max
            set waitCount to 0
            repeat while waitCount < maxWait
                delay 1
                set waitCount to waitCount + 1
                
                try
                    tell application "Google Chrome"
                        -- Check if page is loaded and is LinkedIn
                        set jsCheck to execute tabRef javascript "
                            (function() {
                                if (!window.location.href.includes('linkedin.com')) return 'not_linkedin';
                                if (document.readyState !== 'complete') return 'loading';
                                
                                // Check for profile indicators
                                var hasProfile = (
                                    document.querySelector('meta[property=\"profile:first_name\"]') ||
                                    document.querySelector('script[type=\"application/ld+json\"]') ||
                                    document.querySelector('.pv-top-card') ||
                                    document.querySelector('.profile-top-card') ||
                                    document.title.includes('LinkedIn')
                                );
                                
                                // Check for auth wall
                                var pageKey = document.querySelector('meta[name=\"pageKey\"]');
                                if (pageKey && pageKey.content.includes('auth_wall')) {
                                    return 'auth_wall';
                                }
                                
                                return hasProfile ? 'ready' : 'waiting';
                            })();
                        "
                        
                        if jsCheck is "ready" or jsCheck is "auth_wall" then
                            exit repeat
                        else if jsCheck is "not_linkedin" then
                            -- URL redirect or error
                            exit repeat
                        end if
                    end tell
                on error
                    -- JavaScript execution failed, continue waiting
                end try
            end repeat
            
            -- Additional wait for dynamic content
            delay 3
            
            -- Get full HTML using JavaScript (more reliable than View Source)
            set pageSource to ""
            try
                tell application "Google Chrome"
                    set pageSource to execute tabRef javascript "document.documentElement.outerHTML"
                end tell
            on error errMsg
                -- Fallback: try to get body HTML at least
                try
                    tell application "Google Chrome"
                        set pageSource to execute tabRef javascript "document.body.outerHTML"
                    end tell
                on error
                    set pageSource to "Error: Could not retrieve page content - " & errMsg
                end try
            end try
            
            -- Save to file
            do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
            
            -- Close tab
            delay 0.5
            try
                tell application "Google Chrome" to close tabRef
            end try
            
        on error errMsg
            -- Save error information
            try
                do shell script "echo 'Error processing " & theURL & ": " & errMsg & "' > " & quoted form of theFile
            end try
        end try
    end repeat
    
    -- Close the incognito window
    delay 1
    try
        tell application "Google Chrome" to close win
    end try
end run 