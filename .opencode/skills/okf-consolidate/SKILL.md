---
name: okf-consolidate
description: Consolidate an OKF changed concept cluster by deterministic structural/similarity triage, a fully resolved claim transfer plan, independent review approval, automatic bounded execution, and mandatory post-state review. Use for “consolidate,” “refactor the bundle,” “clean up concept files,” or duplication/custody cleanup. Do not use to incorporate new sources or perform the independent review.
---

# OKF consolidation

Canonicalize detailed evidence while preserving distinct concept-specific semantic facets. Read `rules.md` sections 3, 8, and 9; `references/concept-type-authority.md`; and `.opencode/okf/schemas/transfer-plan.schema.json`.

## Bound the cluster

Start from concepts changed since the approved incorporation baseline. Expand only for an explicit authority transfer and list the reason. Do not inventory the whole corpus unless the user explicitly requests a whole-bundle survey.

Run deterministic triage before semantic reading:

```bash
python3 .opencode/skills/okf-incorporate/scripts/validate.py
python3 .opencode/okf/okf_core.py analyze --base <baseline-commit>
```

Rank candidates using terminal section/order defects, citation/link findings, repeated normalized sentences/paragraphs, high claim fan-out from the run manifest, source-organized headings, alternating stubs, and unusually dense cross-concept citation overlap. Read semantically only the ranked cluster.

## Pass 1: transfer plan

For every candidate claim record:

- stable claim ID and source;
- canonical detailed-evidence home under concept-type authority;
- distinct facet summary retained in every other concept;
- exact copies removed or rewritten;
- citations expected after transfer;
- pre-edit hashes for every file;
- decision: `retain`, `move`, `merge`, or `drop_unsupported`.

No decision may remain ambiguous. If ownership cannot be resolved, stop for user direction. A cross-link does not replace a facet that the concept must own.

Save the plan outside version control while pending. Ask `okf-review` to review every transfer independently. Record the review ID, exact plan SHA-256, and approval in the plan, then validate:

```bash
python3 .opencode/okf/okf_core.py contract transfer-plan <plan.json>
```

Do not execute without a valid independent approval. Once approved, execute the exact plan automatically; do not seek a second approval unless scope or hashes change.

## Pass 2: bounded execution

1. Recompute all pre-edit hashes. Stop and invalidate approval on any mismatch.
2. Process the highest-authority canonical homes first.
3. Weave evidence thematically, preserve attribution, and retain distinct actor/conflict/event/region/theme facets.
4. Move or renumber citations atomically with claims; keep `# Citations` terminal.
5. Refresh timestamps and coordinator-owned `log.md` only after content files pass validation.
6. Record result hashes and transfer dispositions.

Never add unsupported evidence, new sources, or new concepts during consolidation.

## Mandatory post-state review and rollback

Run deterministic validation, then invoke an independent `okf-review` over the full transfer set. Require:

- no lost claims or citations;
- all retained summaries remain concept-specific;
- zero deterministic errors and zero new unexplained warnings;
- no unresolved high findings or transfers;
- no new high-severity candidate in a second consolidation survey;
- an idempotence check showing a second planned pass has no transfers.

If a gate fails, restore the approved pre-state from the recorded hashes/patch, mark the run blocked, and return to Pass 1. Report before/after sections, transfers, retained facets, citations, validation delta, post-review ID, and idempotence result. Do not commit or publish.
