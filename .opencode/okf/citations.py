#!/usr/bin/env python3
"""Citation key tooling for the OKF bundle.

Authoring agents cite by **stable source key** — ``[isw:2025-01-18]`` — and never
touch numbers or the terminal ``# Citations`` block. This tool resolves keys to
sequential integers assigned in order of first appearance in the body, then
regenerates ``# Citations`` from the markers actually present. Orphaned, gapped
and duplicated numbering therefore cannot be produced by hand.

Subcommands:
  index      rebuild sources.json from sources/isw/ frontmatter + corpus citations
  check      report what normalize would do; never writes
  normalize  rewrite markers and regenerate # Citations

Exit code: 0 clean, 1 if any file could not be normalized.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = ROOT / "sources" / "isw"
REGISTRY = Path(__file__).resolve().parent / "sources.json"
CONCEPT_DIRS = ("actors", "conflicts", "regions", "themes", "events")

# A citation marker is either [12] or [isw:2025-01-18] / [ref:nato-georgia].
NUM_MARKER = re.compile(r"\[(\d+)\]")
KEY_MARKER = re.compile(r"\[((?:isw|ref):[A-Za-z0-9][A-Za-z0-9._-]*)\]")
ANY_MARKER = re.compile(r"\[(\d+|(?:isw|ref):[A-Za-z0-9][A-Za-z0-9._-]*)\]")
CITATIONS_HEADING = re.compile(r"^#\s+Citations?\s*$", re.MULTILINE)
ENTRY_LINE = re.compile(r"^\[(\d+)\]\s+(.*\S)\s*$")
ROCA_TITLE = re.compile(
    r"^Russian Offensive Campaign Assessment,\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})$"
)

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        start=1,
    )
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def split_citations(body: str) -> tuple[str, str] | None:
    """Return (text_before_heading, text_after_heading), or None if absent."""
    match = CITATIONS_HEADING.search(body)
    if not match:
        return None
    return body[: match.start()], body[match.end():]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if match:
            fm[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return fm


# --- registry -------------------------------------------------------------


def source_keys() -> dict[str, Path]:
    """Every file in sources/isw/ keyed as isw:<filename stem>."""
    if not SOURCES_DIR.is_dir():
        return {}
    return {f"isw:{p.stem}": p for p in sorted(SOURCES_DIR.glob("*.md"))}


def concept_files() -> list[Path]:
    files: list[Path] = []
    for directory in CONCEPT_DIRS:
        base = ROOT / directory
        if base.is_dir():
            files.extend(sorted(base.rglob("*.md")))
    return [f for f in files if f.name != "README.md"]


def key_for_citation(title: str, url: str, known: dict[str, Path]) -> str:
    """Map an existing '[N] [title](url)' entry back to a stable source key."""
    match = ROCA_TITLE.match(title)
    if match and match.group(1) in MONTHS:
        month, day, year = MONTHS[match.group(1)], int(match.group(2)), int(match.group(3))
        candidate = f"isw:{year:04d}-{month:02d}-{day:02d}"
        if candidate in known:
            return candidate
    # Special reports: match the URL's trailing slug against a source filename.
    url_slug = slugify(url.rstrip("/").rsplit("/", 1)[-1])
    if url_slug:
        for key, path in known.items():
            stem_slug = slugify(path.stem)
            # source stems carry a date prefix the URL slug lacks
            if stem_slug == url_slug or stem_slug.endswith("-" + url_slug):
                return key
    return f"ref:{slugify(title)[:60]}"


def build_registry() -> dict[str, dict[str, str]]:
    known = source_keys()
    votes: dict[str, Counter] = defaultdict(Counter)

    # Frontmatter is authoritative where download.py wrote it.
    for key, path in known.items():
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if fm.get("title") and fm.get("source"):
            votes[key][(fm["title"], fm["source"])] += 1000

    # Otherwise learn title/URL from how the corpus already cites the source.
    for path in concept_files():
        parts = split_citations(path.read_text(encoding="utf-8"))
        if not parts:
            continue
        for line in parts[1].split("\n"):
            entry = ENTRY_LINE.match(line.strip())
            if not entry:
                continue
            link = re.match(r"^\[([^\]]+)\]\(([^)]+)\)\s*$", entry.group(2))
            if not link:
                continue
            title, url = link.group(1), link.group(2)
            votes[key_for_citation(title, url, known)][(title, url)] += 1

    registry: dict[str, dict[str, str]] = {}
    for key, counter in votes.items():
        (title, url), _ = counter.most_common(1)[0]
        registry[key] = {"title": title, "url": url}

    # Sources never yet cited still deserve a key so authors can reference them.
    for key, path in known.items():
        if key in registry:
            continue
        stem = path.stem
        iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", stem)
        if iso:
            month = [m for m, i in MONTHS.items() if i == int(iso.group(2))][0]
            title = (
                f"Russian Offensive Campaign Assessment, "
                f"{month} {int(iso.group(3))}, {iso.group(1)}"
            )
            slug = slugify(title)
        else:
            title = stem
            slug = slugify(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem))
        registry[key] = {
            "title": title,
            "url": f"https://understandingwar.org/research/russia-ukraine/{slug}/",
            "unverified": "true",
        }

    return dict(sorted(registry.items()))


def load_registry() -> dict[str, dict[str, str]]:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {}


def render_entry(number: int, meta: dict[str, str]) -> str:
    return f"[{number}] [{meta['title']}]({meta['url']})"


# --- normalization --------------------------------------------------------


class Problem(Exception):
    pass


def normalize_text(body: str, registry: dict[str, dict[str, str]], prune: bool) -> tuple[str, list[str]]:
    """Return (new_body, notes). Raises Problem if the file cannot be normalized."""
    parts = split_citations(body)
    if parts is None:
        if KEY_MARKER.search(body) or NUM_MARKER.search(body):
            raise Problem("has citation markers but no '# Citations' section")
        return body, []

    head, tail = parts
    notes: list[str] = []

    # Existing entries are authoritative for this file's numeric markers.
    existing: dict[int, dict[str, str]] = {}
    order: list[int] = []
    for line in tail.split("\n"):
        entry = ENTRY_LINE.match(line.strip())
        if not entry:
            continue
        number = int(entry.group(1))
        link = re.match(r"^\[([^\]]+)\]\(([^)]+)\)\s*$", entry.group(2))
        meta = (
            {"title": link.group(1), "url": link.group(2)}
            if link
            else {"title": entry.group(2), "url": ""}
        )
        if number in existing and existing[number] != meta:
            notes.append(f"duplicate entry [{number}] with differing content; keeping first")
        else:
            existing.setdefault(number, meta)
            order.append(number)

    # Resolve every body marker, in order of first appearance, to an identity.
    identities: list[tuple[str, dict[str, str]]] = []
    seen: dict[str, int] = {}

    def identity_of(meta: dict[str, str]) -> str:
        return meta["url"] or "title:" + meta["title"]

    def register(meta: dict[str, str]) -> int:
        ident = identity_of(meta)
        if ident not in seen:
            seen[ident] = len(identities) + 1
            identities.append((ident, meta))
        return seen[ident]

    unresolved: list[str] = []
    for match in ANY_MARKER.finditer(head):
        token = match.group(1)
        if token.isdigit():
            meta = existing.get(int(token))
            if meta is None:
                unresolved.append(f"body references [{token}] with no matching citation entry")
                continue
        else:
            meta = registry.get(token)
            if meta is None:
                unresolved.append(f"unknown source key [{token}]")
                continue
        register(meta)

    if unresolved:
        raise Problem("; ".join(sorted(set(unresolved))))

    # Entries nobody references: keep them (provenance) unless explicitly pruned.
    dangling = [n for n in order if identity_of(existing[n]) not in seen]
    if dangling and not prune:
        for number in dangling:
            register(existing[number])
        notes.append(
            f"kept {len(dangling)} unreferenced entr{'y' if len(dangling) == 1 else 'ies'} "
            f"(originally {sorted(dangling)}); pass --prune to drop"
        )
    elif dangling:
        notes.append(f"pruned {len(dangling)} unreferenced entries (originally {sorted(dangling)})")

    # Rewrite body markers to their new numbers.
    def replace(match: re.Match) -> str:
        token = match.group(1)
        meta = existing[int(token)] if token.isdigit() else registry[token]
        return f"[{seen[identity_of(meta)]}]"

    new_head = ANY_MARKER.sub(replace, head)

    lines = [render_entry(i, meta) for i, (_, meta) in enumerate(identities, start=1)]
    new_body = new_head.rstrip("\n") + "\n\n# Citations\n\n" + "\n".join(lines) + "\n"
    return new_body, notes


def process(path: Path, registry: dict[str, dict[str, str]], write: bool, prune: bool) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("\n---", 3) + len("\n---")
        front, body = text[:end], text[end:]
    else:
        front, body = "", text

    rel = str(path.relative_to(ROOT))
    try:
        new_body, notes = normalize_text(body, registry, prune)
    except Problem as exc:
        return False, [f"[ERROR] {rel}: {exc}"]

    messages = [f"[WARN] {rel}: {n}" for n in notes]
    if new_body != body:
        messages.append(f"[{'FIXED' if write else 'WOULD FIX'}] {rel}")
        if write:
            path.write_text(front + new_body, encoding="utf-8")
    return True, messages


def resolve_targets(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(a).resolve() for a in argv]
    return concept_files()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="rebuild sources.json")
    for name in ("check", "normalize"):
        p = sub.add_parser(name, help=f"{name} citation markers")
        p.add_argument("paths", nargs="*", help="files to process (default: all concepts)")
        p.add_argument("--prune", action="store_true", help="drop unreferenced citation entries")

    args = parser.parse_args()

    if args.command == "index":
        registry = build_registry()
        REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        unverified = sum(1 for v in registry.values() if v.get("unverified"))
        print(f"wrote {REGISTRY.relative_to(ROOT)}: {len(registry)} keys ({unverified} unverified)")
        return 0

    registry = load_registry()
    if not registry:
        print("no sources.json — run: python3 .opencode/okf/citations.py index", file=sys.stderr)
        return 1

    failed = False
    for path in resolve_targets(args.paths):
        ok, messages = process(path, registry, write=args.command == "normalize", prune=args.prune)
        failed |= not ok
        for message in messages:
            print(message)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
