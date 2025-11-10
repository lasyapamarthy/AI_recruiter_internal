#!/usr/bin/env python3
"""
rotating_scraper.py   ·   Safari & Chrome LinkedIn profile downloader
─────────────────────────────────────────────────────────────────────
• Reads a plain-text list of LinkedIn profile URLs.
• Downloads in batches, round-robin between Safari & Chrome.
• Calls AppleScript helpers that open private windows, save HTML.
• After each batch fast-parses the HTML and flags auth-wall pages.
• Retries failed/auth-wall URLs up to MAX_RETRIES times.

→  python3 rotating_scraper.py urls.txt output_dir  [--log log.csv]

AppleScript helpers
-------------------
Place these next to this Python file (paths are configurable below):

    scripts/save_batch_safari.applescript
    scripts/save_batch_chrome.applescript

Both must accept CLI arguments:
    osascript  save_batch_⟨browser⟩.applescript  url1 file1 url2 file2 …

They open all URLs in PRIVATE mode, wait ~4 s each, dump outerHTML
into the requested file and close the tab.  A minimal Chrome script
is included after this Python code block.

Dependencies:  pip install beautifulsoup4 pandas tqdm
"""

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

# ───────────────────────────── USER-TUNABLE CONSTANTS ────────────────────────── #
BATCH_SIZE         = 8
SLEEP_RANGE        = (7, 15)         # seconds between batches
COFFEE_EVERY_N     = 25              # big pause after these many batches
COFFEE_RANGE       = (180, 360)      # seconds
MAX_RETRIES        = 2               # auth-wall / error retries
SCRIPT_DIR         = Path(__file__).resolve().parent / "scripts"
SAFARI_SCRIPT      = SCRIPT_DIR / "save_batch_safari.applescript"
CHROME_SCRIPT      = SCRIPT_DIR / "save_batch_chrome.applescript"
BROWSERS           = [               # ordered rotation
    ("safari", SAFARI_SCRIPT),
    ("chrome", CHROME_SCRIPT),
]
# ─────────────────────────────────────────────────────────────────────────────── #


def chunk(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def load_urls(path: Path) -> list[str]:
    txt = path.read_text(encoding="utf-8").splitlines()
    urls = [u.strip() for u in txt if u.strip()]
    urls = [u if u.startswith("http") else f"https://{u}" for u in urls]
    urls = [u.replace("pl.linkedin.com/", "linkedin.com/").replace("/mwlite/", "/") for u in urls]
    return list(dict.fromkeys(urls))


def filename_from_url(url: str) -> str:
    stem = url.rstrip("/").split("/")[-1] or "profile"
    return stem.split("?")[0] + ".html"


# ────────────────────────────── QUICK AUTH-WALL TEST ─────────────────────────── #
def is_profile(html_path: Path) -> bool:
    text = html_path.read_text(errors="ignore")
    soup = BeautifulSoup(text, "html.parser")
    key = soup.find("meta", attrs={"name": "pageKey"})
    if key and "auth_wall" in key.get("content", ""):
        return False
    if soup.find("meta", attrs={"property": "profile:first_name"}):
        return True
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        graphs = (
            data.get("@graph", []) if isinstance(data, dict) else []
        ) + ([data] if isinstance(data, dict) else [])
        if any(isinstance(n, dict) and n.get("@type") == "Person" for n in graphs):
            return True
    return False
# ─────────────────────────────────────────────────────────────────────────────── #


def write_log(log_path: Path, rows: list[dict]):
    first = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ts", "url", "file", "status", "browser"])
        if first:
            w.writeheader()
        w.writerows(rows)


def call_applescript(script_path: Path, pair_list: list[str | Path]) -> bool:
    cmd = ["osascript", str(script_path)] + [str(x) for x in pair_list]
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        tqdm.write(f"❌ AppleScript error: {e.output.decode(errors='ignore')[:200]}")
        return False


def main(url_file: Path, out_dir: Path, log_csv: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    urls = load_urls(url_file)

    status_counter = defaultdict(int)  # url → retries
    queue = urls.copy()
    processed_ok = set()

    batch_idx = 0
    browser_cycle = iter(BROWSERS)

    while queue:
        # rotate browser
        try:
            browser_name, script_path = next(browser_cycle)
        except StopIteration:
            browser_cycle = iter(BROWSERS)
            browser_name, script_path = next(browser_cycle)

        batch = queue[:BATCH_SIZE]
        queue = queue[BATCH_SIZE:]

        files = [out_dir / filename_from_url(u) for u in batch]
        arglist = [item for pair in zip(batch, files) for item in pair]

        ok = call_applescript(script_path, arglist)
        ts = int(time.time())
        log_rows = []

        for url, file_path in zip(batch, files):
            if ok and file_path.exists():
                if is_profile(file_path):
                    status = "ok"
                    processed_ok.add(url)
                else:
                    # rename problematic file for inspection
                    file_path.rename(file_path.with_stem(file_path.stem + "_AUTHWALL"))
                    status = "auth_wall"
                    if status_counter[url] < MAX_RETRIES:
                        status_counter[url] += 1
                        queue.append(url)  # retry later
            else:
                status = "error"
                if status_counter[url] < MAX_RETRIES:
                    status_counter[url] += 1
                    queue.append(url)

            log_rows.append(
                {
                    "ts": ts,
                    "url": url,
                    "file": file_path.name,
                    "status": status,
                    "browser": browser_name,
                }
            )

        write_log(log_csv, log_rows)

        batch_idx += 1
        if batch_idx % COFFEE_EVERY_N == 0:
            pause = random.uniform(*COFFEE_RANGE)
            tqdm.write(f"☕ coffee break for {pause/60:.1f} min")
        else:
            pause = random.uniform(*SLEEP_RANGE)
        time.sleep(pause)

    print(f"Done.  {len(processed_ok)} profiles saved OK.")
    print(f"Log saved to {log_csv}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url_file", type=Path, help="TXT with LinkedIn URLs")
    ap.add_argument("output_dir", type=Path, help="Folder to save *.html")
    ap.add_argument(
        "--log",
        type=Path,
        default=Path("linkedin_rotating_log.csv"),
        help="CSV log (default: linkedin_rotating_log.csv)",
    )
    args = ap.parse_args()

    # sanity-check helper scripts
    for name, p in BROWSERS:
        if not p.exists():
            sys.exit(f"Missing AppleScript for {name}: {p}")

    main(args.url_file, args.output_dir, args.log)
