#!/usr/bin/env python3
"""OKF bundle structural validator.

Checks every .md file outside sources/ and _site/ for:
  1. Frontmatter validity (required fields present per file role)
  2. Citation integrity (every [N] body ref has a matching [N] entry)
  3. Cross-link integrity ({{ site.baseurl }}/path.html -> path.md exists)
  4. Timestamp freshness (optionally check touched files have today's date)

Usage:
  python3 validate.py                    # full bundle scan
  python3 validate.py --touched          # only files in git diff
  python3 validate.py --today YYYY-MM-DD # check touched files have this date

Exit code: 0 if clean, 1 if issues found.
"""

import os
import re
import sys
import subprocess
from pathlib import Path

# --- Config -------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]  # scripts/ -> okf-incorporate/ -> skills/ -> .opencode/ -> repo root

EXCLUDE_DIRS = {"sources", "_site", "node_modules", ".git", ".opencode", "vendor"}
VALID_TYPES = {"Actor", "Conflict", "Region", "Theme", "Event"}
INDEX_FILES = {"README.md", "index.md", "log.md"}
# Reference docs at repo root — not OKF concepts, have frontmatter for Jekyll nav only
REFERENCE_DOCS = {"okf.md", "rules.md"}
TODAY_DEFAULT = None  # set by --today flag

# Tiered body sections, in the order rules.md section 7 requires them to appear.
SECTION_ORDER = [
    "Background",
    "Key Dynamics",
    "Current Situation",
    "Recent Developments",
    "Chronology",
    "Analysis",
    "Citations",
]
# Headings that are legitimate but carry no ordering constraint.
FREE_SECTIONS = {"Event", "Participants"}

SOURCE_KEY = re.compile(r"\[((?:isw|ref):[A-Za-z0-9][A-Za-z0-9._-]*)\]")
TOP_HEADING = re.compile(r"^#\s+(\S.*?)\s*$", re.MULTILINE)
PERIOD_HEADING = re.compile(
    r"^###\s+([A-Z][a-z]+)\s+(\d{1,2})\s*[–-]\s*(?:([A-Z][a-z]+)\s+)?(\d{1,2}),\s*(\d{4})\s+—\s+(\S.*)$"
)
MONTHS = {
    name: number
    for number, name in enumerate(
        ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"],
        start=1,
    )
}

# --- Frontmatter parser -------------------------------------------------

def parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file. Returns (frontmatter_dict, body_str) or ({}, full_text)."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return None, str(e)

    if not text.startswith("---"):
        return {}, text

    # Find closing ---
    lines = text.split("\n")
    if len(lines) < 2:
        return {}, text

    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        return {}, text

    fm_text = "\n".join(lines[1:close_idx])
    body = "\n".join(lines[close_idx + 1:])

    # Simple YAML key:value parser (no nested structures needed for our checks)
    fm = {}
    current_key = None
    current_list = None
    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # List item under a key
        if stripped.startswith("- ") and current_key:
            val = stripped[2:].strip().strip('"').strip("'")
            if current_list is None:
                current_list = []
            current_list.append(val)
            fm[current_key] = current_list
            continue
        # Inline list: key: [a, b, c]
        m = re.match(r'^(\w+):\s*\[(.*)\]', stripped)
        if m:
            key, val = m.group(1), m.group(2)
            fm[key] = [v.strip().strip('"').strip("'") for v in val.split(",") if v.strip()]
            current_key = key
            current_list = fm[key]
            continue
        # Block scalar (>)
        m = re.match(r'^(\w+):\s*>\s*$', stripped)
        if m:
            current_key = m.group(1)
            current_list = None
            fm[current_key] = ""  # will be filled by continuation lines
            continue
        # Simple key: value
        m = re.match(r'^(\w+):\s*(.*)', stripped)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # Strip quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            if val:
                fm[key] = val
            else:
                fm[key] = ""
            current_key = key
            current_list = None
        # Continuation of block scalar
        elif current_key and fm.get(current_key) == "" and stripped:
            if fm[current_key]:
                fm[current_key] += " " + stripped
            else:
                fm[current_key] = stripped

    return fm, body


# --- Checks -------------------------------------------------------------

def get_md_files(touched_only=False):
    """Walk the repo and return all .md files outside excluded dirs."""
    if touched_only:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True, text=True, check=True
            )
            touched = set()
            for line in result.stdout.strip().split("\n"):
                if line.endswith(".md"):
                    touched.add(REPO_ROOT / line)
            return sorted(touched)
        except Exception:
            pass

    files = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # Exclude dirs in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if fname.endswith(".md"):
                files.append(Path(dirpath) / fname)
    return sorted(files)


def check_frontmatter(filepath, fm):
    """Check required frontmatter fields. Returns (errors, warnings) lists."""
    errors = []
    warnings = []
    filename = filepath.name
    rel = str(filepath.relative_to(REPO_ROOT))

    # Reference docs (okf.md, rules.md) — have Jekyll nav frontmatter but are not concepts
    if filename in REFERENCE_DOCS:
        return errors, warnings

    if filename in INDEX_FILES:
        # Index files: need title (except log.md which has title in frontmatter too)
        if filename == "log.md":
            if "title" not in fm:
                errors.append(f"{rel}: index/log file missing 'title'")
        elif not fm.get("title"):
            errors.append(f"{rel}: index file missing 'title'")
        # README.md at root or in dirs should have nav stuff if it's an index
        # But not all README.md are indexes - we check has_children presence
        return errors, warnings

    # Concept files
    if not fm:
        errors.append(f"{rel}: no frontmatter found")
        return errors, warnings

    if "type" not in fm:
        errors.append(f"{rel}: concept file missing required 'type' field")
    elif fm["type"] not in VALID_TYPES:
        errors.append(f"{rel}: type '{fm['type']}' not in {VALID_TYPES}")

    if not fm.get("title"):
        errors.append(f"{rel}: concept file missing required 'title' field")

    if not fm.get("parent"):
        errors.append(f"{rel}: concept file missing required 'parent' field")

    return errors, warnings


def check_citations(filepath, body):
    """Check that every [N] reference in the body has a matching [N] entry in Citations."""
    issues = []
    rel = str(filepath.relative_to(REPO_ROOT))

    # Skip log.md — its [N] references are log entries, not citations
    if filepath.name == "log.md":
        return issues
    # Skip reference docs
    if filepath.name in REFERENCE_DOCS:
        return issues

    # Find all [N] references in the body (not in the Citations section itself)
    # Split at # Citations heading
    citations_match = re.search(r'^#\s+Citations?\s*$', body, re.MULTILINE)
    if not citations_match:
        # No citations section - check if there are any [N] refs
        refs = set(int(n) for n in re.findall(r'\[(\d+)\]', body))
        if refs:
            issues.append(f"{rel}: has [N] references but no '# Citations' section")
        return issues

    body_before = body[:citations_match.start()]
    citations_section = body[citations_match.end():]

    # Find references in the body (before Citations)
    body_refs = set(int(n) for n in re.findall(r'\[(\d+)\]', body_before))

    # Find citation entries: lines starting with [N]
    citation_entries = set()
    for line in citations_section.split("\n"):
        m = re.match(r'^\[(\d+)\]', line.strip())
        if m:
            citation_entries.add(int(m.group(1)))

    # Check each body ref has an entry
    missing = body_refs - citation_entries
    if missing:
        issues.append(f"{rel}: body references {sorted(missing)} with no matching citation entry")

    # Check for gaps in numbering (informational)
    if citation_entries:
        expected = set(range(1, max(citation_entries) + 1))
        gaps = expected - citation_entries
        if gaps:
            issues.append(f"{rel}: citation numbering has gaps at {sorted(gaps)}")

    return issues


def check_orphaned_citations(filepath, body):
    """Check for citation entries with no matching body [N] reference.
    Returns warnings — orphaned citations are a quality issue, not a structural error."""
    warnings = []
    rel = str(filepath.relative_to(REPO_ROOT))

    if filepath.name == "log.md" or filepath.name in REFERENCE_DOCS:
        return warnings

    citations_match = re.search(r'^#\s+Citations?\s*$', body, re.MULTILINE)
    if not citations_match:
        return warnings

    body_before = body[:citations_match.start()]
    citations_section = body[citations_match.end():]

    body_refs = set(int(n) for n in re.findall(r'\[(\d+)\]', body_before))
    citation_entries = set()
    for line in citations_section.split("\n"):
        m = re.match(r'^\[(\d+)\]', line.strip())
        if m:
            citation_entries.add(int(m.group(1)))

    orphaned = citation_entries - body_refs
    if orphaned:
        warnings.append(f"{rel}: orphaned citation entries {sorted(orphaned)} (no body reference)")

    return warnings


def check_source_keys(filepath, body):
    """Source keys must be resolved to numbers before commit.

    Authors cite as [isw:2025-01-18]; citations.py rewrites those to [N] and
    regenerates # Citations. A key surviving into a committed file means
    normalize was never run, and the citation would render as literal text.
    """
    issues = []
    if filepath.name == "log.md" or filepath.name in REFERENCE_DOCS:
        return issues
    keys = sorted(set(SOURCE_KEY.findall(body)))
    if keys:
        rel = str(filepath.relative_to(REPO_ROOT))
        shown = ", ".join(keys[:5]) + (" …" if len(keys) > 5 else "")
        issues.append(
            f"{rel}: unresolved source keys ({shown}) — "
            f"run: python3 .opencode/okf/citations.py normalize {rel}"
        )
    return issues


def check_sections(filepath, body):
    """Check the tiered section vocabulary and ordering from rules.md section 7."""
    errors = []
    warnings = []
    rel = str(filepath.relative_to(REPO_ROOT))

    if filepath.name in INDEX_FILES or filepath.name in REFERENCE_DOCS:
        return errors, warnings

    headings = TOP_HEADING.findall(body)
    if not headings:
        return errors, warnings

    for heading in headings:
        if heading not in SECTION_ORDER and heading not in FREE_SECTIONS:
            warnings.append(f"{rel}: unrecognized top-level section '# {heading}'")

    if "Citations" in headings and headings[-1] != "Citations":
        errors.append(f"{rel}: '# Citations' must be the final top-level section")

    ranked = [(SECTION_ORDER.index(h), h) for h in headings if h in SECTION_ORDER]
    for (rank, name), (prev_rank, prev_name) in zip(ranked[1:], ranked):
        if rank < prev_rank:
            errors.append(
                f"{rel}: section '# {name}' must come before '# {prev_name}' (see rules.md section 7)"
            )

    return errors, warnings


def check_periods(filepath, body):
    """Tier-2 period headings must be well-formed, ordered and non-overlapping."""
    errors = []
    rel = str(filepath.relative_to(REPO_ROOT))

    match = re.search(r"^#\s+Chronology\s*$", body, re.MULTILINE)
    if not match:
        return errors
    rest = body[match.end():]
    nxt = re.search(r"^#\s+\S", rest, re.MULTILINE)
    section = rest[: nxt.start()] if nxt else rest

    spans = []
    for line in section.split("\n"):
        line = line.strip()
        if not line.startswith("### "):
            continue
        period = PERIOD_HEADING.match(line)
        if not period:
            errors.append(
                f"{rel}: malformed period heading '{line}' "
                f"(expected '### January 7–18, 2025 — Name')"
            )
            continue
        start_month, start_day, end_month, end_day, year, _name = period.groups()
        end_month = end_month or start_month
        if start_month not in MONTHS or end_month not in MONTHS:
            errors.append(f"{rel}: unknown month in period heading '{line}'")
            continue
        start = (int(year), MONTHS[start_month], int(start_day))
        end = (int(year), MONTHS[end_month], int(end_day))
        if end < start:
            errors.append(f"{rel}: period '{line}' ends before it starts")
            continue
        spans.append((start, end, line))

    for (start, _end, line), (_prev_start, prev_end, prev_line) in zip(spans[1:], spans):
        if start <= prev_end:
            errors.append(f"{rel}: period '{line}' overlaps or precedes '{prev_line}'")

    return errors


def check_cross_links(filepath, body):
    """Check that {{ site.baseurl }}/path.html links point to existing .md files.
    Returns warnings (not errors) — OKF spec section 5.3 says broken links are tolerated."""
    warnings = []
    rel = str(filepath.relative_to(REPO_ROOT))

    # Skip reference docs (okf.md has example links to non-existent tables)
    if filepath.name in REFERENCE_DOCS:
        return warnings

    # Find all {{ site.baseurl }}/something.html links
    links = re.findall(r'\{\{\s*site\.baseurl\s*\}\}/([^\s\)]+)\.html', body)

    for link in links:
        # link is like "actors/countries/china" or "conflicts/us-iran-war-2026"
        target_md = REPO_ROOT / (link + ".md")
        if not target_md.exists():
            warnings.append(f"{rel}: broken link to '{link}.html' (no {link}.md found)")

    return warnings


def check_timestamp(filepath, fm, expected_date):
    """Check that a file's timestamp matches the expected date."""
    issues = []
    rel = str(filepath.relative_to(REPO_ROOT))
    if not expected_date:
        return issues
    ts = fm.get("timestamp", "")
    if ts and not ts.startswith(expected_date):
        issues.append(f"{rel}: timestamp '{ts}' does not match expected '{expected_date}'")
    return issues


# --- Main ----------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OKF bundle structural validator")
    parser.add_argument("--touched", action="store_true", help="Only check files in git diff")
    parser.add_argument("--today", type=str, default=None, help="Expected date (YYYY-MM-DD) for touched file timestamps")
    args = parser.parse_args()

    if args.today is None:
        from datetime import date
        args.today = date.today().isoformat()

    files = get_md_files(touched_only=args.touched)

    if not files:
        print("No .md files found to validate.")
        return 0

    all_errors = []
    all_warnings = []

    for filepath in files:
        fm, body = parse_frontmatter(filepath)
        if fm is None:
            all_errors.append(f"{filepath.relative_to(REPO_ROOT)}: ERROR reading file: {body}")
            continue

        errs, warns = check_frontmatter(filepath, fm)
        all_errors.extend(errs)
        all_warnings.extend(warns)

        all_errors.extend(check_citations(filepath, body))
        all_errors.extend(check_source_keys(filepath, body))
        all_errors.extend(check_periods(filepath, body))
        sec_errs, sec_warns = check_sections(filepath, body)
        all_errors.extend(sec_errs)
        all_warnings.extend(sec_warns)
        all_warnings.extend(check_cross_links(filepath, body))
        all_warnings.extend(check_orphaned_citations(filepath, body))

        if args.touched:
            all_errors.extend(check_timestamp(filepath, fm, args.today))

    # Report warnings first (informational), then errors (blocking)
    if all_warnings:
        print(f"\n{len(all_warnings)} warning(s) (broken links are tolerated per OKF spec 5.3):\n")
        for w in sorted(set(all_warnings)):
            print(f"  [WARN] {w}")

    if all_errors:
        print(f"\n{len(all_errors)} error(s) found:\n")
        for issue in all_errors:
            print(f"  [ERROR] {issue}")
        print()
        return 1

    if all_warnings and not all_errors:
        print(f"\n  All {len(files)} file(s) structurally valid. {len(all_warnings)} warning(s) (broken links, tolerated).\n")
        return 0

    if not all_warnings and not all_errors:
        print(f"\n  All {len(files)} file(s) valid. No issues found.\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
