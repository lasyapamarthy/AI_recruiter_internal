on run argv
    tell application "Safari"
        activate
        
        -- Close existing tabs except the first one
        repeat while (count of tabs of window 1) > 1
            close tab 2 of window 1
        end repeat
        
        -- Open all URLs in new tabs
        repeat with i from 1 to count of argv
            if i = 1 then
                set URL of document 1 to item i of argv
            else
                tell window 1 to make new tab with properties {URL:item i of argv}
            end if
        end repeat
        
        -- Wait for pages to load
        delay 15
        
        return "Opened " & (count of argv) & " tabs in Safari"
        
    end tell
end run 