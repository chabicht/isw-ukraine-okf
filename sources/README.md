# Sources

Raw source material. This directory is **not** part of the OKF bundle and is
excluded from the Jekyll build (`_config.yml`). Concepts cite sources by
their original URL, never by local file path (rules.md §14).

## Layout

* `isw/` — ISW articles as markdown, named `YYYY-MM-DD-<slug>.md` where the
  date is the publication date. Frontmatter carries `source:` (original URL),
  `title:`, `date:`, `publication: ISW`, `source_type:`
  (`daily-assessment` or `special-report`), and `authors:`. See rules.md
  §14.1 for the full convention.

Raw sources are immutable once saved — incorporation reads them, never edits
them.
