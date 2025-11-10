#!/usr/bin/env python3
"""
LinkedIn profile parser  – **v0.3.1**
====================================
*Emergency patch after runtime feedback*

**What was fixed**
------------------
1. **Plain‑text fallback no longer crashes** when the “Present” line is too
   short (IndexError).  Now it just skips that variant.
2. Broader **text‑sweep regex**
   * now also matches patterns like `2022 – Present` (year‑only ranges)
   * tolerates en‑dashes, hyphens, em‑dashes and extra spaces.
3. Added a **generic HTML sweep** in case the DOM is stripped but `<html>` is
   still present – this was the source of most “empty” results you saw.

Try again with the same CLI; you should now see start‑dates for the majority of
those previously blank profiles.  Any single stubborn file → send it and we’ll
add that pattern.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import List, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

__all__ = ["extract_latest_experience"]

# ----------------------------------------------------------------------------
# Date helpers
# ----------------------------------------------------------------------------
_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
MONTHS_FULL = {m: i + 1 for i, m in enumerate(_MONTHS)}
_MONTHS_PATTERN = "|".join(_MONTHS)
MONTH_WORD_RE = re.compile(rf"(?P<mon>{_MONTHS_PATTERN})\s+(?P<yr>\d{{4}})")
YEAR_ONLY_RE = re.compile(r"\b(\d{4})\b")
ISO_RE = re.compile(r"(\d{4})-(\d{2})")


def parse_date(txt: str | None) -> str:
    """Return `YYYY-MM` (ISO) or ""."""
    if not txt:
        return ""

    txt = txt.strip()
    if (m := ISO_RE.search(txt)):
        y, mo = m.groups()
        return f"{int(y):04d}-{int(mo):02d}"
    if (m := MONTH_WORD_RE.search(txt)):
        month_num = MONTHS_FULL[m.group("mon")]
        return f"{int(m.group('yr')):04d}-{month_num:02d}"
    if (m := YEAR_ONLY_RE.search(txt)):
        return f"{int(m.group(1)):04d}-01"
    try:
        return dateparser.parse(txt, fuzzy=True).strftime("%Y-%m")
    except Exception:
        return ""

# ----------------------------------------------------------------------------
# Rank helper – prefer current job, else newest start
# ----------------------------------------------------------------------------

def _best(rows: List[Tuple[str, str, str, bool]]) -> Tuple[str, str, str]:
    rows.sort(key=lambda r: (r[3], r[2]), reverse=True)
    return rows[0][:3] if rows else ("", "", "")

# ----------------------------------------------------------------------------
# 1. JSON‑LD extractor
# ----------------------------------------------------------------------------

def _from_jsonld(soup: BeautifulSoup):
    roles = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        nodes = data.get("@graph", data)
        if isinstance(nodes, dict):
            nodes = [nodes]
        for n in nodes:
            if n.get("@type") != "OrganizationRole":
                continue
            roles.append((
                (n.get("roleName") or "").strip(),
                (n.get("worksFor", {}).get("name") or "").strip(),
                parse_date(n.get("startDate")),
                not n.get("endDate"),
            ))
    return _best(roles)

# ----------------------------------------------------------------------------
# 2. __NEXT_DATA__ extractor
# ----------------------------------------------------------------------------

def _from_next_data(soup: BeautifulSoup):
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return "", "", ""
    try:
        data = json.loads(tag.string)
    except Exception:
        return "", "", ""
    apollo = data.get("props", {}).get("pageProps", {}).get("apolloState", {})
    rows = []
    for v in apollo.values():
        if not isinstance(v, dict) or not v.get("$type", "").endswith("Position"):
            continue
        start_raw = v.get("dateRange", {}).get("start", {})
        rows.append((
            (v.get("title") or "").strip(),
            (v.get("companyName") or "").strip(),
            parse_date(f"{start_raw.get('month',1):02}-{start_raw.get('year','')}"),
            v.get("dateRange", {}).get("end") is None,
        ))
    return _best(rows)

# ----------------------------------------------------------------------------
# 3. DOM Experience extractor (modern & legacy)
# ----------------------------------------------------------------------------

def _from_experience_dom(soup: BeautifulSoup):
    date_pat = re.compile(rf"(({_MONTHS_PATTERN}) \d{{4}}|\d{{4}})\s*[–—-]\s*(Present|Current|{_MONTHS_PATTERN} \d{{4}}|\d{{4}})")
    node = soup.find(string=date_pat)
    if not node:
        return "", "", ""
    start = parse_date(date_pat.search(node)[1])

    # Bubble up for title/company text
    title = company = ""
    cur = node.parent
    for _ in range(4):
        if not cur:
            break
        txt = cur.get_text(" ", strip=True)
        if " · " in txt:
            title, company = [p.strip() for p in txt.split(" · ", 1)]
            break
        cur = cur.parent
    return title, company, start

# ----------------------------------------------------------------------------
# 4. Generic text sweep (HTML or plain text)
# ----------------------------------------------------------------------------

def _from_text(raw: str):
    date_pat = re.compile(rf"(({_MONTHS_PATTERN}) \d{{4}}|\d{{4}})\s*[–—-]\s*(Present|Current|{_MONTHS_PATTERN} \d{{4}}|\d{{4}})")
    m = date_pat.search(raw)
    if not m:
        return "", "", ""
    start = parse_date(m.group(1))

    pre = raw[max(0, m.start()-160):m.start()].splitlines()
    pre = [l.strip() for l in pre if l.strip()]
    guess = pre[-1] if pre else ""
    if " · " in guess:
        title, company = [p.strip() for p in guess.split(" · ", 1)]
    else:
        title, company = guess, pre[-2] if len(pre) >= 2 else ""
    return title, company, start

# ----------------------------------------------------------------------------
# Plain‑text specific (lynx dumps, etc.)
# ----------------------------------------------------------------------------

def _from_plain_text_lines(lines: List[str]):
    for i, line in enumerate(lines):
        if re.search(r"present$", line, re.I):
            parts = line.split()
            start = parse_date(" ".join(parts[:2])) if len(parts) >= 2 else ""
            title = lines[i-1] if i >= 1 else ""
            company = lines[i-2] if i >= 2 else ""
            return title, company, start
    return "", "", ""

# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def extract_latest_experience(path: str | Path) -> dict:
    raw = Path(path).read_text(errors="ignore")
    if "<html" not in raw.lower():
        title, company, start = _from_plain_text_lines([l.strip() for l in raw.splitlines() if l.strip()])
    else:
        soup = BeautifulSoup(raw, "html.parser")
        for fn in (_from_jsonld, _from_next_data, _from_experience_dom):
            title, company, start = fn(soup)
            if start:
                break
        else:
            title, company, start = _from_text(soup.get_text("\n", strip=True))
    return {"job_title": title, "company": company, "start_date": start}

# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _cli(argv=None):
    ap = argparse.ArgumentParser(description="LinkedIn → latest job extractor (robust)")
    ap.add_argument("files", nargs="+", help="Input profile files (supports globs)")
    ap.add_argument("--out", default="parsed_experience_robust.csv", help="Output CSV filename")
    args = ap.parse_args(argv)

    rows = []
    for f in args.files:
        rec = extract_latest_experience(f)
        rec["file"] = f
        print(f"{Path(f).name}: {rec['job_title']} @ {rec['company']} – {rec['start_date']}")
        rows.append(rec)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file", "job_title", "company", "start_date"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    _cli()
