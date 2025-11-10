#!/usr/bin/env python3
import subprocess
import os

output_dir = "/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/output/safari_scraped"
urls = [
    "https://www.linkedin.com/in/hitanshu-shah-21272017a",
    "https://www.linkedin.com/in/sharanya-menon-24baaa83"
]
filenames = [
    os.path.join(output_dir, "test_profile1"),
    os.path.join(output_dir, "test_profile2")
]

args = [item for pair in zip(urls, filenames) for item in pair]
script_path = os.path.dirname(os.path.realpath(__file__))
applescript_file = os.path.join(script_path, "safari_parallel_incognito_v2.applescript")

print(f"Running batch AppleScript with URLs: {urls}")
print(f"Output files: {filenames[0]}.html, {filenames[1]}.html")

command = ["osascript", applescript_file] + args

try:
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    print(f"Return code: {result.returncode}")
    print(f"Output: {result.stdout}")
    print(f"Errors: {result.stderr}")
    
    for fname in filenames:
        html_file = f"{fname}.html"
        if os.path.exists(html_file):
            file_size = os.path.getsize(html_file)
            print(f"✅ File created: {html_file} ({file_size} bytes)")
        else:
            print(f"❌ File not created: {html_file}")
except Exception as e:
    print(f"Error: {e}") 