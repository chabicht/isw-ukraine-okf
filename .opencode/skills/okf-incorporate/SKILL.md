---
name: okf-incorporate
description: Incorporate new sources into the OKF geopolitical bundle or remediate review findings. Use for “incorporate sources,” “process new sources,” “add sources to the OKF,” or “remediate OKF review findings.” Plan claim/facet custody, reserve write ownership, preserve raw sources, update concepts/authors/log, and emit a lifecycle manifest. Do not use for independent review or consolidation.
---

# OKF source incorporation

Incorporate evidence by claim and semantic facet, not by maximizing touched files. Read `rules.md`, `okf.md`, and `.opencode/okf/schemas/run-manifest.schema.json` before planning.

## Start or resume a run

1. Create transient state outside version control (for example `/tmp/okf-<run-id>/`).
2. Record the baseline commit, source paths and SHA-256 hashes, model ID/variant/capabilities, lifecycle status, and all pre-edit destination hashes in a run manifest.
3. On restart, load that manifest. Re-extract only incomplete claims and never append an already recorded facet or citation.
4. For remediation mode, accept only stable finding IDs from an independent review. Record each disposition as fixed, rejected with rationale, or deferred as blocking.

Discover sources with `git status --porcelain=v1 -z`; preserve Unicode and apostrophes byte-for-byte. Never edit `sources/`. Check each input with:

```bash
python3 .opencode/okf/okf_core.py capability '<source-path>'
```

Use `pdftotext` or MuPDF for PDFs and compare the original when layout affects meaning. Hand images to a vision-capable model; fail clearly if none is available.

## Extract claims before destinations

The analyzing worker must read the complete raw source. Assign stable claim IDs and, for every claim:

- source span and attribution;
- observed content versus inference;
- proposed semantic facets;
- one authoritative concept per facet;
- citations required at each destination;
- omissions or uncertainty.

Reuse across concepts is valid only for different facets (for example actor posture versus operational effect). Near-identical evidentiary custody in multiple concepts is a defect.

## Concurrency and ownership

Default to parallel read-only extraction followed by serialized writing by one coordinator. Parallel writing is allowed only when the manifest proves exclusive destination ownership.

- Reserve all destination write sets before editing.
- Give `log.md`, author concepts shared by sources, indexes, rules, and configuration exclusively to the coordinator.
- Reject overlapping write sets.
- Recompute every pre-edit hash immediately before a write; stop on a stale hash and re-plan from current content.
- Never allow source-owned workers to edit destinations opportunistically.

This policy follows the retained lifecycle experiment in `.opencode/okf/evidence/concurrency-policy.json`.

## Plan and approval

Present sources, claims/facets, destination ownership, citations, new concepts, omissions, model limitations, and write sets. Obtain user approval for a new incorporation plan. A user request that explicitly supplies approved review finding IDs authorizes only the bounded remediation described by those findings.

## Write

1. Process destinations in authority order: canonical concept, dependent facet summaries, author concepts, then `log.md`.
2. Synthesize; do not copy source prose.
3. Allocate and insert each citation in the same edit as its claim.
4. Keep thematic sections, correct Jekyll label/target pairs, and terminal `# Citations`.
5. Create a concept only for a substantial new entity and follow `rules.md` frontmatter and index rules.
6. Update timestamps for every meaningfully changed concept.
7. Store resulting hashes and validation deltas in the manifest.

## Validate and report

Run both analyzers:

```bash
python3 .opencode/skills/okf-incorporate/scripts/validate.py
python3 .opencode/okf/okf_core.py analyze --base <baseline-commit> --include-sources
python3 .opencode/okf/okf_core.py contract manifest <manifest.json>
```

Compare warnings to a captured baseline. Never call a warning “pre-existing” without showing it in the baseline result. Report processed claims, facet custody, files/hashes, validation delta, finding dispositions, skipped inputs, and lifecycle status. Do not commit or publish.
