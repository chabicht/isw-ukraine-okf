#!/usr/bin/env python3
"""Download an ISW Russia-Ukraine assessment and store it as markdown.

Usage:
    python3 download.py https://understandingwar.org/research/russia-ukraine/russian-offensive-campaign-assessment-january-2-2025/

Writes sources/isw/<YYYY-MM-DD>.md (date taken from the URL slug).
"""

import argparse
import re
import sys
from pathlib import Path

import html2text
import requests
from bs4 import BeautifulSoup

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def date_from_url(url: str) -> str:
    match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"-(\d{1,2})-(\d{4})",
        url.lower(),
    )
    if not match:
        sys.exit(f"error: could not find a date like 'january-2-2025' in URL: {url}")
    month, day, year = match.groups()
    return f"{year}-{MONTHS[month]:02d}-{int(day):02d}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="ISW assessment URL")
    args = parser.parse_args()

    date = date_from_url(args.url)

    response = requests.get(args.url, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", class_="dynamic-entry-content")
    if content is None:
        print("warning: content div not found, converting full page", file=sys.stderr)
        content = soup

    converter = html2text.HTML2Text(baseurl=args.url)
    converter.body_width = 0
    markdown = converter.handle(str(content)).strip() + "\n"

    title = soup.title.get_text().split("|")[0].strip() if soup.title else None
    header = f"# {title}\n\n" if title and not markdown.startswith("#") else ""

    out_path = Path(__file__).parent / "sources" / "isw" / f"{date}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + markdown, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
