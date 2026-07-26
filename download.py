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
from urllib.parse import urlparse

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


def date_from_url(url: str) -> str | None:
    match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"-(\d{1,2})-(\d{4})",
        url.lower(),
    )
    if not match:
        return None
    month, day, year = match.groups()
    return f"{year}-{MONTHS[month]:02d}-{int(day):02d}"


def date_from_page(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return meta["content"][:10]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="ISW assessment URL")
    args = parser.parse_args()

    response = requests.get(args.url, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    date = date_from_url(args.url)
    if date:
        filename = f"{date}.md"
    else:
        date = date_from_page(soup)
        if not date:
            sys.exit(
                f"error: no date in URL slug and no article:published_time meta tag on page: {args.url}"
            )
        slug = urlparse(args.url).path.rstrip("/").rsplit("/", 1)[-1]
        filename = f"{date}-{slug}.md"
    content = soup.find("div", class_="dynamic-entry-content")
    if content is None:
        print("warning: content div not found, converting full page", file=sys.stderr)
        content = soup

    converter = html2text.HTML2Text(baseurl=args.url)
    converter.body_width = 0
    markdown = converter.handle(str(content)).strip() + "\n"

    title = soup.title.get_text().split("|")[0].strip() if soup.title else None
    header = f"# {title}\n\n" if title and not markdown.startswith("#") else ""

    out_path = Path(__file__).parent / "sources" / "isw" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + markdown, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
