#!/usr/bin/osascript
-- Improved Safari AppleScript for LinkedIn profile scraping
-- Enhanced page load detection and content verification

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
            -- Open URL in tab
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
            
            -- Enhanced wait for page load
            set maxWait to 30 -- 30 seconds max
            set waitCount to 0
            set pageLoaded to false
            
            repeat while waitCount < maxWait
                delay 1
                set waitCount to waitCount + 1
                
                try
                    tell application "Safari"
                        -- First check if URL contains linkedin
                        set currentURL to URL of tabRef
                        if currentURL does not contain "linkedin.com" then
                            exit repeat
                        end if
                        
                        -- Check page load status using JavaScript
                        set loadStatus to do JavaScript "
                            (function() {
                                if (document.readyState !== 'complete') return 'loading';
                                
                                // Check for profile indicators
                                var hasProfile = (
                                    document.querySelector('meta[property=\"profile:first_name\"]') ||
                                    document.querySelector('script[type=\"application/ld+json\"]') ||
                                    document.querySelector('.pv-top-card') ||
                                    document.querySelector('.profile-top-card') ||
                                    document.querySelector('[data-member-id]') ||
                                    (document.title && document.title.includes('LinkedIn'))
                                );
                                
                                // Check for auth wall
                                var pageKey = document.querySelector('meta[name=\"pageKey\"]');
                                if (pageKey && pageKey.content.includes('auth_wall')) {
                                    return 'auth_wall';
                                }
                                
                                // Check if it's a sign-in page
                                if (document.querySelector('.authwall-join-form') || 
                                    document.querySelector('.sign-in-form')) {
                                    return 'auth_wall';
                                }
                                
                                return hasProfile ? 'ready' : 'waiting';
                            })();
                        " in tabRef
                        
                        if loadStatus is "ready" or loadStatus is "auth_wall" then
                            set pageLoaded to true
                            exit repeat
                        end if
                    end tell
                on error
                    -- JavaScript execution failed, continue waiting
                end try
            end repeat
            
            -- Additional wait for dynamic content
            if pageLoaded then
                delay 3
            else
                delay 1 -- Short delay even if page didn't load properly
            end if
            
            -- Get page source
            set pageSource to ""
            try
                tell application "Safari"
                    -- Try to get full HTML with JavaScript first
                    set pageSource to do JavaScript "document.documentElement.outerHTML" in tabRef
                end tell
            on error
                -- Fallback to source property
                try
                    tell application "Safari"
                        set pageSource to source of tabRef
                    end tell
                on error errMsg
                    set pageSource to "Error: Could not retrieve page content - " & errMsg
                end try
            end try
            
            -- Save to file
            do shell script "printf %s " & quoted form of pageSource & " > " & quoted form of theFile
            
            -- Close tab
            delay 0.5
            try
                tell application "Safari" to close tabRef
            end try
            
        on error errMsg
            -- Save error information
            try
                do shell script "echo 'Error processing " & theURL & ": " & errMsg & "' > " & quoted form of theFile
            end try
        end try
    end repeat
    
    -- Close the private window
    delay 1
    try
        tell application "Safari" to close win
    end try
end run 