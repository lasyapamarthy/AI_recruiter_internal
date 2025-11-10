
on run argv
    set urlList to {}
    set filenameList to {}
    
    -- Parse arguments (alternating URLs and filenames)
    repeat with i from 1 to count of argv by 2
        set end of urlList to item i of argv
        if i + 1 <= count of argv then
            set end of filenameList to item (i + 1) of argv
        end if
    end repeat
    
    tell application "Safari"
        activate
        
        -- Close existing tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
        -- Open all URLs in new tabs
        repeat with i from 1 to count of urlList
            if i = 1 then
                set URL of document 1 to item i of urlList
            else
                tell window 1 to make new tab with properties {URL:item i of urlList}
            end if
        end repeat
        
        -- Wait for pages to load
        delay 10
        
        -- Save each tab
        repeat with i from 1 to count of urlList
            try
                set current tab of window 1 to tab i of window 1
                delay 2
                
                -- Get the page source and save it
                set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
                set filename to item i of filenameList & ".html"
                
                set fileRef to open for access filename with write permission
                write pageSource to fileRef
                close access fileRef
                
            on error errMsg
                -- If there's an error, just continue to next tab
                try
                    close access fileRef
                end try
            end try
        end repeat
        
        -- Close all tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
    end tell
end run
