
on run argv
    set urlList to {}
    set filenameList to {}
    set saveResults to {}
    
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
        
        -- Wait longer for pages to load
        delay 20
        
        -- Additional wait to ensure all pages are loaded
        repeat with i from 1 to count of urlList
            set current tab of window 1 to tab i of window 1
            delay 1
            
            -- Check if page is still loading
            repeat 5 times
                try
                    set pageState to do JavaScript "document.readyState" in current tab of window 1
                    if pageState is "complete" then
                        exit repeat
                    end if
                on error
                    -- Page might not be ready for JavaScript yet
                end try
                delay 2
            end repeat
        end repeat
        
        -- Save each tab with verification
        repeat with i from 1 to count of urlList
            set saveSuccess to false
            set retryCount to 0
            
            repeat while retryCount < 3 and not saveSuccess
                try
                    set current tab of window 1 to tab i of window 1
                    delay 3
                    
                    -- Get the page source
                    set pageSource to do JavaScript "document.documentElement.outerHTML" in current tab of window 1
                    
                    -- Verify we got actual content
                    if length of pageSource > 1000 then
                        set filename to item i of filenameList
                        
                        -- Write to file with error handling
                        try
                            set fileRef to open for access filename with write permission
                            set eof of fileRef to 0  -- Clear existing content
                            write pageSource to fileRef as «class utf8»
                            close access fileRef
                            set saveSuccess to true
                            set end of saveResults to "SUCCESS: " & filename
                        on error writeErr
                            try
                                close access fileRef
                            end try
                            set end of saveResults to "WRITE_ERROR: " & filename & " - " & writeErr
                        end try
                    else
                        set end of saveResults to "EMPTY_CONTENT: " & item i of filenameList
                    end if
                    
                on error jsErr
                    set end of saveResults to "JS_ERROR: " & item i of filenameList & " - " & jsErr
                end try
                
                if not saveSuccess then
                    set retryCount to retryCount + 1
                    if retryCount < 3 then
                        delay 2
                    end if
                end if
            end repeat
            
            if not saveSuccess then
                set end of saveResults to "FAILED_AFTER_RETRIES: " & item i of filenameList
            end if
        end repeat
        
        -- Close all tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
    end tell
    
    -- Return save results
    return saveResults
end run
