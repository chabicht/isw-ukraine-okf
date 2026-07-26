---
title: Rules & Conventions
nav_order: 7
permalink: /rules/
---

# ISW OKF Bundle — Rules & Conventions

This document captures all design decisions governing the structure, formatting,
and authoring of concepts in this OKF bundle. It is project governance, not an
OKF concept.

All agents and humans creating or editing concepts in this bundle MUST follow
these conventions.

---

## 1. Bundle Overview

- **Subject**: The Russia-Ukraine war, as covered by the Institute for the
  Study of War (ISW). The primary source stream is ISW's near-daily *Russian
  Offensive Campaign Assessment* series, supplemented by ISW special reports.
- **Format**: OKF v0.1 (see `okf.md` for the full specification).
- **Site**: Published via GitHub Pages using the [Just the Docs](https://github.com/just-the-docs/just-the-docs)
  Jekyll theme. Site config is in `_config.yml`; dependencies in `Gemfile`.
- **Bundle root**: The repository root. All top-level OKF directories are at the root.
- **Sources**: The `sources/` directory contains raw source material (clippings,
  articles, essays). It is NOT part of the OKF bundle and is excluded from the
  Jekyll build. Concepts cite sources by their original URL, not by local file path.
- **OKF version**: Declared in root `README.md` as `okf_version: "0.1"`.
- **Index files**: Named `README.md` (not `index.md`) so that GitHub
  automatically renders them when browsing a directory. This is a
  bundle-specific deviation from the OKF spec's `index.md` convention.

---

## 2. Directory Structure

```
isw-okf/
├── _config.yml           # Jekyll / Just the Docs site configuration
├── Gemfile               # Ruby dependencies (github-pages gem)
├── README.md             # Bundle root index (site home page)
├── log.md                # Bundle update log
├── rules.md              # This file (governance, not an OKF concept)
├── okf.md                # The OKF specification (reference, not a concept)
├── sources/              # Raw source material (not part of the OKF bundle, excluded from Jekyll)
├── actors/               # Countries, leaders, organizations, authors
├── conflicts/            # Wars, crises, sustained standoffs
├── regions/              # Geographic areas with independent dynamics
├── themes/               # Cross-cutting analytical topics and frameworks
└── events/               # Discrete occurrences
```

---

## 3. Type System

Five types, one per top-level directory. Types are flat — subcategories are
expressed via tags, not via subtyped `type` values.

| Directory | `type` value | Covers |
|-----------|-------------|--------|
| `actors/` | `Actor` | Countries, leaders, organizations, authors |
| `conflicts/` | `Conflict` | Wars, crises, sustained standoffs |
| `regions/` | `Region` | Geographic areas with independent dynamics |
| `themes/` | `Theme` | Cross-cutting topics, analytical frameworks |
| `events/` | `Event` | Discrete occurrences (explosions, summits, ceasefires) |

---

## 4. Frontmatter

All markdown files in the bundle (concepts, indexes, and reference documents)
have YAML frontmatter. The frontmatter serves both OKF metadata and Just the
Docs navigation.

### 4.1 Required fields (concept files)

```yaml
type: Actor              # REQUIRED — one of the 5 types
title: United States     # REQUIRED — used as sidebar label and page title
parent: Countries        # REQUIRED — the parent nav page (see §4.5)
```

### 4.2 Recommended fields (concept files)

```yaml
description: <one-line summary>
tags: [country, military, nuclear]
status: ongoing           # Lifecycle state (see §6)
timestamp: 2026-07-02T00:00:00Z  # ISO 8601 last-modified
```

### 4.3 Event-specific fields

Event concepts (`type: Event`) SHOULD include these additional fields:

```yaml
event_date: 2026-06-17     # ISO 8601 date when the event occurred (or is projected to occur)
actuality: actual           # "actual" (happened) or "hypothetical" (projected/speculative)
```

| Field | Purpose | Values |
|-------|---------|--------|
| `event_date` | When the event itself occurred — distinct from `timestamp` (last-modified) | ISO 8601 date (`YYYY-MM-DD`) |
| `actuality` | Whether the event is real or hypothetical | `actual`, `hypothetical` |

`event_date` captures the **event occurrence date**, not the file modification
date (that's `timestamp`). For ongoing situations without a single decisive
date, use the date the situation became notable or was first reported.

`actuality` is orthogonal to `status` (§6): `status` tracks whether a situation
is still evolving (`ongoing`/`concluded`), while `actuality` tracks whether it
happened at all (`actual`/`hypothetical`). A hypothetical event can be
`ongoing` (a projected scenario being actively discussed) or `concluded` (a
speculation that has been overtaken by events).

### 4.4 Extension fields

Producers MAY add any additional keys. Common extensions in this bundle:

```yaml
author: Christina Harward       # For author actor concepts
source_url: https://...         # For events sourced from a single article
```

### 4.5 Navigation fields (Just the Docs)

The sidebar tree is built from these frontmatter fields:

| Field | Used on | Purpose |
|-------|---------|---------|
| `title` | All pages | Sidebar label and page `<title>` |
| `parent` | All concept files | Name of the parent page (matches the parent's `title`) |
| `nav_order` | Top-level pages | Sort order in the sidebar (integer or string) |
| `has_children` | Index/section pages | `true` if this page has child pages in the tree |
| `permalink` | Index/reference pages | Custom URL (e.g. `/actors/countries/`) |

**Parent values** must exactly match the parent page's `title`. The current
parent hierarchy:

| Parent `title` | Files |
|----------------|-------|
| `Actors` | Leader concepts in `actors/` root, and all sub-index READMEs |
| `Countries` | `actors/countries/*.md` (non-README) |
| `Organizations` | `actors/organizations/*.md` (non-README) |
| `Authors & Analysts` | `actors/authors/*.md` (non-README) |
| `Conflicts` | `conflicts/*.md` (non-README) |
| `Regions` | `regions/*.md` (non-README) |
| `Themes` | `themes/*.md` (non-README) |
| `Events` | `events/*.md` (non-README) |

Leaf pages (concepts) sort alphabetically by `title` automatically. No
`nav_order` is needed on concept files.

---

## 5. Naming Conventions

- **Kebab-case, descriptive**: `united-states.md`, not `us.md` or `UnitedStates.md`.
- **Year suffix for time-bound concepts**: `kursk-incursion-2024.md`, not
  `2024-kursk-incursion.md`. The year goes at the end, not as a date prefix.
- **Full English names for countries**: `united-states`, `united-kingdom`,
  `south-korea`. Short forms (`us`, `usa`) may appear in tags for discoverability.
- **Full names for authors**: `christina-harward`, `kateryna-shymkiv`.
- **Concept IDs**: Derived from the file path with `.md` removed.
  E.g., `actors/united-states.md` → concept ID `actors/united-states`.

---

## 6. Status Field

A custom frontmatter field indicating the lifecycle state of the concept.

| Value | Meaning | Examples |
|-------|---------|----------|
| `ongoing` | Actively evolving situation | Russia-Ukraine War, the strike campaign, an active front axis |
| `concluded` | Situation has ended; recorded for context | A past ceasefire, a concluded offensive |
| `evergreen` | Structural/enduring knowledge | Black Sea geography, Russian energy-export fundamentals |
| `historical` | Past event recorded for historical context | Cold War, WWII |

For `ongoing` concepts, `timestamp` tracks the last update, and `log.md`
entries record what changed.

---

## 7. Body Section Conventions

The body uses standard markdown with conventional section headings:

| Heading | When to use |
|---------|-------------|
| `# Background` | Evergreen/structural context — geography, history, fundamentals. Always relevant. |
| `# Key Dynamics` | For regions/themes: the structural forces that shape the concept. |
| `# Current Situation` | Time-bound description of the present state. Rewritten by compaction. |
| `# Recent Developments` | **Tier 1.** Per-day paragraphs under `### <Month D, YYYY>` headings. Append-only. |
| `# Chronology` | **Tier 2.** Sealed, named periods: `### January 7–18, 2025 — The Refractory Plant Fight`. |
| `# Analysis` | **Tier 3.** Dissolved analytical content and rolled-up phase narratives (see §8). |
| `# Citations` | Numbered external sources. Always at the bottom of the document. |

Not all sections are required for every concept. Use what applies. Where several are
present they appear in the order listed above, and `# Citations` is always terminal.

### 7.1 Daily-cadence conventions

The primary source stream is near-daily. To keep concepts readable at that
cadence:

- **Region concepts mirror ISW's recurring operational sections.** One region
  concept per recurring axis in the daily assessments (e.g. the northern axis,
  the eastern-Ukraine main effort, the southern axis, Ukrainian operations in
  Russia, Belarus). The air/missile/drone campaign is a **theme**, not a
  region. This gives every daily operational claim an obvious, stable
  destination. Axis regions own sector-level operational state; the conflict
  concept owns the war-level arc (see
  `.opencode/skills/okf-consolidate/references/concept-type-authority.md`).
- **Resolution decays with age, and the two runs own different sections.**
  Daily incorporation is purely additive: it appends one dated paragraph under
  `# Recent Developments` and touches nothing else. A separate, manually
  triggered compaction run (`okf-compact`) owns every rewrite — folding aged
  Tier-1 days into named `# Chronology` periods, rolling accumulated periods up
  into `# Analysis` phase narratives, and refreshing `# Current Situation` to
  the present state. Concentrating all destructive edits in one gated run keeps
  every daily commit a clean pure-add diff, and keeps concept files bounded in
  size however long the bundle runs.
- **`# Current Situation` is built from the newest assessments.** Derive it from the
  most recent three to five reports, not by synthesizing the concept's whole
  history — the latest reports already describe current positions, and the
  wider synthesis is where staleness and geographic drift enter. Reuse the
  sources' own directional and place wording verbatim; silently relabelling a
  district moves the front line. `# Chronology` period headings are named
  descriptively for what was contested, never for an interpretation of what it
  meant, because a heading cannot carry a hedge.
- **A written `# Chronology` period is sealed.** Routine runs must not re-cut,
  rename, reword or merge it. Sealed text is re-summarized only by the
  deliberate rollup step, which prevents repeated lossy re-summarization from
  eroding the record. A stale `# Current Situation` between compaction runs is
  expected, not a defect.
- **Events are for discrete notable occurrences** (major strike waves,
  summits, ceasefires, leadership changes) — never one event per daily issue.
- **"No change" findings** (e.g. "Russian forces did not advance") update the
  concept's `timestamp` without prose churn; add a `log.md` entry only if the
  concept was otherwise untouched for an extended period.

---

## 8. Analysis Dissolution

There is no `analyses/` directory. Analytical content from source articles is
**dissolved into the concepts it describes**, under `# Analysis` sections.

### 8.1 Format

Analysis sections use **thematic subsections** (organized by topic, not by
author). Multiple authors' perspectives are woven together in prose within each
subsection. Attribution is inline. Citations appear after each attributed claim.

```markdown
# Analysis

### Economic Impact of the Strike Campaign
Ukraine's strikes on Russian refineries are producing cascading economic
damage. ISW assesses that fuel shortages now affect most of Russia's federal
subjects and are draining export revenue the Kremlin needs to finance the
war. [1]

### Air-Defense Trade-offs
ISW assesses that Russia cannot strengthen air defenses over both frontline
and rear areas simultaneously, suggesting Ukraine can sustain the deep-strike
campaign. [1][2]
```

### 8.2 Author tracking

Recurring authors (3+ sources, or anticipated to reach that threshold) get
**actor concepts** in `actors/` that serve as indexes.

For ISW material the threshold applies to the **institution, not each
byline**: ISW gets an organization actor concept
(`actors/organizations/institute-for-the-study-of-war.md`) describing its
analytical method and coverage, created at first incorporation. Individual
ISW analysts get author concepts only if they develop a distinct recurring
framework of their own.

Author actor concepts:

- Describe their analytical framework, worldview, recurring themes, and perspective.
- Link to all concepts where their analysis appears.

### 8.3 Frameworks that span multiple concepts

Analytical frameworks that apply broadly (e.g., "Ukraine's deep-strike campaign",
"energy is power") become **theme concepts** in `themes/`, where the framework
itself is the concept.

---

## 9. Cross-linking

- **Absolute links** use the `{{ site.baseurl }}` prefix and `.html` extension:
  `[Russia-Ukraine War]({{ site.baseurl }}/conflicts/russia-ukraine-war.html)`.
- **Relative links** within the same directory use bare filenames with `.html`:
  `[United States](united-states.html)`.
- Links to directory index pages use the permalink (no `.html`):
  `[Countries](countries/)` or `[Actors]({{ site.baseurl }}/actors/)`.
- Links express relationships; the kind of relationship is conveyed by
  surrounding prose, not by the link itself.
- **Broken links are tolerated** — they represent not-yet-written knowledge.
- Link generously: every concept should connect to related actors, conflicts,
  themes, regions, and events.

---

## 10. Citations

- Citations are numbered and listed under `# Citations` at the bottom of each
  document.
- The primary citation is the **original article URL** (from the source's
  `source:` frontmatter field).
- Citation format:

```markdown
# Citations

[1] [Russian Offensive Campaign Assessment, July 24, 2026](https://understandingwar.org/research/russia-ukraine/russian-offensive-campaign-assessment-july-24-2026/)
[2] [Ukraine's Strike Campaigns Will Likely Continue to Hurt Russia's Economy and Military Operations in Ukraine](https://understandingwar.org/research/russia-ukraine/ukraines-strike-campaigns-will-likely-continue-to-hurt-russias-economy-and-military-operations-in-ukraine/)
```

### 10.1 Authoring: cite by source key

The numbered form above is the **committed output**, generated by a script. Authoring
agents never write it by hand. Instead they mark claims with a stable source key derived
from the filename in `sources/isw/`:

```markdown
Russian forces seized the Refractory Plant.[isw:2025-01-18]
```

Third-party sources that have no file in `sources/` use a `ref:` key registered in
`.opencode/okf/sources.json` (for example `[ref:nato-relations-with-georgia]`).

```bash
python3 .opencode/okf/citations.py index                  # rebuild the key registry
python3 .opencode/okf/citations.py check  <paths…>        # report, never write
python3 .opencode/okf/citations.py normalize <paths…>     # keys -> numbers, rebuild list
```

**Cite per claim.** A citation marker means "this source supports this sentence". Where
a compacted `# Chronology` period must also record the full set of sources that fed it,
it does so once, in a closing provenance line — `Sources for this period: [13]–[21]` —
not by attaching every source to every paragraph. Spraying the full set inline destroys
the meaning of a citation and lets unsupported assertions inherit apparent support.

`normalize` assigns numbers in order of first appearance in the body and regenerates
`# Citations` from the markers actually present, so orphaned, gapped and duplicated
numbering cannot be produced. It refuses to write a file whose markers it cannot resolve
rather than guessing. **Never hand-edit a numbered citation list** — doing so is what
corrupted 20 files in commit `0d43e88`. Unreferenced entries are preserved by default so
provenance is never silently dropped; `--prune` removes them deliberately.

---

## 11. Tag Vocabulary

Tags are used for subcategorization and cross-cutting filtering. The following
starter vocabulary MUST be used where applicable. New tags may be added as the
bundle grows, but existing tags should not be fragmented (e.g., use `energy`,
not `energy-policy`).

### 11.1 Actor subtypes

| Tag | Used for |
|-----|----------|
| `country` | Nation-states |
| `leader` | Individual political/military leaders |
| `organization` | International orgs, alliances, agencies, companies |
| `author` | Analysts, writers, publications whose interpretive work is tracked |

### 11.2 Thematic tags

`energy`, `military`, `technology`, `ai`, `ideology`, `economics`,
`cognitive-warfare`, `drone-warfare`, `nuclear`, `cbrn`, `sanctions`, `trade`,
`demography`, `intelligence`, `critical-minerals`, `supply-chain`,
`naval`, `air-defense`, `missile`, `cyber`, `elections`, `strike-campaign`,
`occupation`, `mobilization`, `war-economy`, `fortifications`

### 11.3 Regional tags

`middle-east`, `indo-pacific`, `europe`, `eastern-europe`, `africa`,
`latin-america`, `central-asia`, `caucasus`, `sahel`, `baltic`, `black-sea`,
`crimea`

### 11.4 Conflict character tags

`kinetic`, `gray-zone`, `cold-war`, `proxy`, `insurgency`, `hybrid`

### 11.5 Source-type tags (context only, not on concepts)

`news`, `opinion`, `framework` — used informally when describing an author's
output, not as concept tags.

---

## 12. Index Files

Each top-level directory has a `README.md` with Just the Docs navigation
frontmatter (`title`, `nav_order`, `has_children`, `permalink`). Subdirectory
index files add `parent` pointing to their top-level parent. Index files list
all concepts in the directory grouped by section, with one-line descriptions.

The frontmatter for an index file looks like:

```yaml
---
title: Actors
nav_order: 1
has_children: true
permalink: /actors/
---
```

Subdirectory index:

```yaml
---
title: Countries
parent: Actors
nav_order: 1
has_children: true
permalink: /actors/countries/
---
```

> **Note:** The OKF spec uses `index.md` for directory listings. This bundle
> uses `README.md` instead so that GitHub automatically renders the listing
> when browsing a directory. The content and structure are identical; only
> the filename differs.

---

## 13. Log Files

`log.md` at the bundle root records the history of changes. Entries are
date-grouped, newest first, using ISO 8601 dates. The leading bold word
(`**Creation**`, `**Update**`, etc.) is a convention.

**Concept-file references must be Jekyll links** (§9, §16.4): use the
concept's display `title` as link text and `{{ site.baseurl }}/<path>.html` as
the target. Do not write bare backtick paths (`` `actors/foo.md` ``) for
concept files — only for non-concept repo files (e.g. `rules.md`,
`validate.py`) that have no Jekyll page.

---

## 14. Source Handling

- The `sources/` directory contains raw articles and essays. It is NOT part of
  the OKF bundle.
- Concepts cite sources by their **original URL**, not by local file path.
- When a source is referenced in a concept's `# Citations` section, the URL
  from the source's `source:` frontmatter field is used.
- Author actor concepts list the sources that inform them, linking to the
  original URLs.

### 14.1 ISW source conventions

- ISW articles are saved as markdown under `sources/isw/`, named
  `YYYY-MM-DD-<slug>.md` where the date is the **publication date**:
  `sources/isw/2026-07-24-russian-offensive-campaign-assessment.md`.
- Source-file frontmatter:

```yaml
source: https://understandingwar.org/research/russia-ukraine/russian-offensive-campaign-assessment-july-24-2026/
title: Russian Offensive Campaign Assessment, July 24, 2026
date: 2026-07-24
publication: ISW
source_type: daily-assessment    # or: special-report
authors: [Christina Harward, Kateryna Shymkiv]
```

- Concepts cite the **ISW article URL**. ISW's own endnotes (Telegram
  channels, media reports, etc.) are second-hand sources: they remain in the
  raw source file and are never re-cited in concepts.
- Daily assessments follow a fixed structure (key takeaways, then recurring
  operational sections per axis, the air/missile/drone campaign, and Belarus).
  Incorporation maps each operational section to its axis region concept per
  §7.1; toplines and cross-cutting analysis map to the conflict, theme, and
  actor concepts they concern.

---

## 15. Subdirectory Organization

Top-level directories MAY be split into subdirectories to manage clutter as
the bundle grows. Subdirectories are a purely organizational layer — they do
not affect the `type` field, which remains flat (see §3).

### 15.1 When to split

- **No hard threshold** triggers splitting a directory. The decision is left
  to author judgment, guided by how cluttered the directory has become.
- **Group threshold:** When a single tag group within a directory exceeds
  **20 concepts**, that group SHOULD be moved into its own subdirectory.
  Groups below this threshold stay at the directory root alongside any
  subdirectories.
- The threshold is a guideline, not a gate — authors MAY split earlier or
  later if it improves navigability.

### 15.2 Subdirectory naming

- Subdirectory names derive from the existing tag vocabulary (§11), not
  invented ad hoc.
- Use the pluralized tag name where natural: `countries/`, `authors/`,
  `leaders/`, `organizations/`.

### 15.3 Invariants

- **`type` stays flat.** A file in `actors/countries/china.md` still has
  `type: Actor`, not `type: Country`. Subdirectories are organizational,
  not typological.
- **Each subdirectory gets its own `README.md`** index file following the
  same conventions as top-level index files (§12).
- **Cross-links must be updated** when files move into subdirectories.
  Absolute links use `{{ site.baseurl }}/actors/countries/china.html` (with
  `.html` extension). A link-rewriting pass is part of any migration.

### 15.4 Concept IDs

Concept IDs are derived from the full file path (OKF §2). Moving a file
into a subdirectory changes its concept ID. Consumers that cache or index
by concept ID MUST be updated.

---

## 16. Jekyll / Just the Docs Integration

The bundle is published as a GitHub Pages site using the
[Just the Docs](https://github.com/just-the-docs/just-the-docs) theme.
This section captures the rules that ensure new content renders correctly.

### 16.1 Configuration

- `_config.yml` at the repo root sets `remote_theme`, `baseurl`, `url`,
  `exclude`, and theme options. Do not commit a `_config.yml` with a
  different `baseurl` unless the repo is renamed.
- `Gemfile` pins the `github-pages` gem for local development.
- `sources/` is in the `exclude` list and will not be processed by Jekyll.

### 16.2 Frontmatter for new concept files

Every new concept file MUST include `title` and `parent` in its frontmatter
(see §4). The `parent` value must match the parent page's `title` exactly.
Without these, the page will not appear in the sidebar navigation tree.

### 16.3 Frontmatter for new index files

When creating a new subdirectory (see §15), create a `README.md` with:

```yaml
---
title: <Section Name>
parent: <Parent Section Title>
nav_order: <integer>
has_children: true
permalink: /<path>/<subdir>/
---
```

### 16.4 Link format

- Cross-concept links use `.html` extension, not `.md`:
  `[China]({{ site.baseurl }}/actors/countries/china.html)` (absolute) or
  `[China](china.html)` (relative within the same directory).
- Links to index pages use the permalink path without `.html`:
  `[Countries](countries/)` or `[Countries]({{ site.baseurl }}/actors/countries/)`.
- The `{{ site.baseurl }}` variable is required for absolute links so they
  resolve correctly under the GitHub Pages subpath (`/isw-okf`).

### 16.5 Adding a new top-level section

To add a new top-level section to the sidebar (e.g. a new directory):

1. Create the directory with a `README.md` index file containing `nav_order`
   and `has_children: true`.
2. Add the directory to `_config.yml` if it needs special handling.
3. Update the root `README.md` to link to the new directory.
4. Choose a `nav_order` value that positions it correctly in the sidebar.
