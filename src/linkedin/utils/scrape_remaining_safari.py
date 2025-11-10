import pandas as pd
import os
import sys
import time
import subprocess
import random
from tqdm import tqdm

# usage: python3 scrape_remaining_safari.py <path_to_links.csv> <path_to_output>
# print usage if not enough arguments
if len(sys.argv) < 3:
    print("usage: python3 scrape_remaining_safari.py <path_to_links.csv> <path_to_output>")
    print("example: python3 scrape_remaining_safari.py data/linkedin/remaining_urls_to_scrape.csv data/linkedin/output/safari_scraped")
    sys.exit(0)

# current script path
script_path = os.path.dirname(os.path.realpath(__file__))
print(f"Script path: {script_path}")

input_file = sys.argv[1]
output_dir = sys.argv[2]

# Read the CSV file
df = pd.read_csv(input_file)

# Filter for untried and failed URLs (both should be retried)
retry_df = df[(df['status'] == 'untried') | (df['status'] == 'failed')].copy()

# Create a new dataframe with the expected format
links = pd.DataFrame()
links['links'] = retry_df['url']
# Create IDs from the LinkedIn username (last part of URL)
links['ids'] = retry_df['url'].apply(lambda x: x.split('/')[-1].replace(',', '_'))

print(f"Found {len(links)} URLs to scrape (untried + failed)")

result_log = pd.DataFrame(columns=['url', 'name'])

# check if output directory exists
if not os.path.exists(output_dir):
    print('Creating output directory: ' + output_dir)
    os.makedirs(output_dir)

# Make sure output_dir is absolute path
output_dir = os.path.abspath(output_dir)
print('Output directory: ' + output_dir)

# Process each link to clean it up
for i in range(len(links)):
    link = links.iloc[i]['links']
    # check if link is empty
    if pd.isnull(link):
        continue
    # remove all spaces in the link
    link = link.replace(' ', '')
    if not link.startswith('http'):
        link = 'https://' + link
    # if link has pl.linkedin.com then replace with linkedin.com
    if 'pl.linkedin.com' in link:
        link = link.replace('pl.linkedin.com', 'linkedin.com')
    # if the link has a mwlite remove it
    if '/mwlite/' in link:
        link = link.replace('/mwlite/', '/')
    # Update the cleaned link
    links.at[i, 'links'] = link

# Process in batches of 10
batch_size = 10
total_batches = (len(links) + batch_size - 1) // batch_size

print(f"Will process {len(links)} URLs in {total_batches} batches of {batch_size}")
print("\nNote: This will open Safari in incognito mode and scrape profiles automatically.")
print("You will NOT be logged into LinkedIn in private mode.")
response = input("Continue? (y/n): ")

if response.lower() != 'y':
    print("Scraping cancelled by user")
    sys.exit(0)

# Start scraping
for batch_num in tqdm(range(0, len(links), batch_size), desc="Processing batches"):
    # Get the current batch
    batch_end = min(batch_num + batch_size, len(links))
    links_batch = links.iloc[batch_num:batch_end]['links'].tolist()
    filenames_batch = links.iloc[batch_num:batch_end]['ids'].tolist()
    filenames_batch = [str(x) for x in filenames_batch]
    
    # Add the output directory to the filenames
    filenames_batch = [os.path.join(output_dir, x) for x in filenames_batch]
    
    print(f"\nBatch {batch_num//batch_size + 1}/{total_batches}:")
    print(f"URLs: {links_batch}")
    print(f"Filenames: {filenames_batch}")
    
    try:
        # Prepare arguments for AppleScript (alternating URLs and filenames)
        args = [item for pair in zip(links_batch, filenames_batch) for item in pair]
        command = ['osascript', os.path.join(script_path, 'safari_parallel_incognito_v2.applescript')] + args
        
        # Run the AppleScript
        result = subprocess.check_output(command, timeout=120)  # 2 minute timeout per batch
        
        # Log successful saves
        for url, filename in zip(links_batch, filenames_batch):
            result_log = pd.concat([result_log, pd.DataFrame({'url': [url], 'name': [filename + '.html']})], ignore_index=True)
        
    except subprocess.TimeoutExpired:
        print(f"Timeout error for batch starting at index {batch_num}")
        # Log as errors
        for url in links_batch:
            result_log = pd.concat([result_log, pd.DataFrame({'url': [url], 'name': ['timeout_error']})], ignore_index=True)
    except Exception as e:
        print(f"Error processing batch: {str(e)}")
        # Log as errors
        for url in links_batch:
            result_log = pd.concat([result_log, pd.DataFrame({'url': [url], 'name': ['error']})], ignore_index=True)
    
    # Save log every 5 batches
    if (batch_num // batch_size + 1) % 5 == 0:
        result_log.to_csv(os.path.join(output_dir, 'scraping_log.csv'), index=False)
        print(f"Saved progress log ({len(result_log)} entries)")
    
    # Random delay between batches (except for the last one)
    if batch_end < len(links):
        delay = random.uniform(5, 15)
        print(f"Waiting {delay:.1f} seconds before next batch...")
        time.sleep(delay)

# Save final log
result_log.to_csv(os.path.join(output_dir, 'scraping_log.csv'), index=False)
print(f"\nScraping complete! Processed {len(result_log)} URLs")
print(f"Log saved to: {os.path.join(output_dir, 'scraping_log.csv')}")

# Count successful downloads
success_count = len(result_log[~result_log['name'].isin(['error', 'timeout_error'])])
print(f"Successfully scraped: {success_count}/{len(links)} profiles") 