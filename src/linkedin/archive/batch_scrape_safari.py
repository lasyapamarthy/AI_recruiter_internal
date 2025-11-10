import pandas as pd
import os
import sys
import time
import subprocess
import random
from tqdm import tqdm

if len(sys.argv) < 3:
    print("usage: python3 batch_scrape_safari.py <path_to_links.csv> <output_dir>")
    sys.exit(0)

script_path = os.path.dirname(os.path.realpath(__file__))
input_file = sys.argv[1]
output_dir = sys.argv[2]
links = pd.read_csv(input_file)
result_log = pd.DataFrame(columns=['url', 'name'])

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_dir = os.path.abspath(output_dir)
print('Output directory:', output_dir)

batch_size = 5  # You can adjust this
applescript_file = os.path.join(script_path, 'batch_save_profiles.applescript')

for i in tqdm(range(0, len(links), batch_size)):
    links_batch = links.iloc[i:i+batch_size]['links'].tolist()
    if 'ids' in links.columns:
        filenames_batch = links.iloc[i:i+batch_size]['ids'].tolist()
        filenames_batch = [str(x) for x in filenames_batch]
    else:
        filenames_batch = [str(x) for x in range(i, i+len(links_batch))]
    filenames_batch = [os.path.join(output_dir, x) for x in filenames_batch]

    # Clean links
    for j, link in enumerate(links_batch):
        link = link.replace(' ', '')
        if not link.startswith('http'):
            link = 'https://' + link
        if 'pl.linkedin.com' in link:
            link = link.replace('pl.linkedin.com', 'linkedin.com')
        if '/mwlite/' in link:
            link = link.replace('/mwlite/', '/')
        links_batch[j] = link

    args = [item for pair in zip(links_batch, filenames_batch) for item in pair]
    command = ['osascript', applescript_file] + args
    try:
        subprocess.check_output(command, timeout=120)
        for url, filename in zip(links_batch, filenames_batch):
            result_log = pd.concat([result_log, pd.DataFrame({'url': [url], 'name': [filename + '.html']})], ignore_index=True)
    except Exception as e:
        print(f"Error processing batch {i//batch_size+1}: {e}")
        for url in links_batch:
            result_log = pd.concat([result_log, pd.DataFrame({'url': [url], 'name': ['error']})], ignore_index=True)

    # Save log every batch
    result_log.to_csv(os.path.join(output_dir, 'output_log.csv'), index=False)
    time.sleep(random.uniform(5, 15))

print("Batch scraping complete!") 