---
name: okf-review
description: Independently and read-only review an OKF incorporation, remediation, consolidation transfer plan, or post-consolidation state. Use for “review the incorporation,” “verify OKF changes,” “approve the transfer plan,” or “post-consolidation review.” Compare against a captured baseline, run exhaustive deterministic checks plus declared semantic sampling, emit stable findings, and return Blocked, Needs remediation, Ready for consolidation, or Ready.
---

# Independent OKF review

Remain read-only. Do not fix, stage, commit, or reuse the builder’s private reasoning. Read `rules.md`, `okf.md`, the run manifest, and `.opencode/okf/schemas/review-findings.schema.json`.

## Establish scope and baseline

Record the baseline commit and hash the working tree before review. Categorize changed sources, concepts, global files, and unexpected files. Verify the manifest’s source hashes, destination hashes, claim/facet ownership, write sets, model capabilities, retries, and lifecycle state.

Run exhaustive deterministic checks over the declared changed cluster:

```bash
python3 .opencode/skills/okf-incorporate/scripts/validate.py
python3 .opencode/okf/okf_core.py analyze --base <baseline-commit> --include-sources
```

Compare the current finding set against a baseline captured from the baseline commit. Report new, resolved, and unchanged warnings separately. Unsupported “pre-existing” assertions are findings.

Check all changed files for citation integrity and source URLs, terminal section order, frontmatter, Unicode paths, link-label targets, source immutability, timestamps, and manifest completeness. Verify the repository hash after review matches the hash before review.

## Declare semantic sampling

State the deterministic scope, semantic strata selected, files/claims sampled, selection rationale, and limits. The minimum stratified sample covers:

- failed/recovered or retried work;
- coordinated shared-destination work;
- a high-fan-out source;
- each distinct model or modality;
- a narrow batch;
- every new concept.

For each sampled source, map material claims to source spans, destination facets, concept-specific implications, citation custody, omissions, unsupported additions, and redundant custody. Check raw sources directly. Treat conclusions as:

- **Observed** — deterministically or directly checked;
- **Sampled** — true only of the declared sample;
- **Inferred** — reasoned hypothesis with evidence and uncertainty.

Never generalize sampled semantic quality to the full corpus.

## Review transfer plans

For consolidation plans, inspect every transfer rather than sampling. Require a canonical claim home, retained concept-specific facets, removed copies, expected citations, resolved decision, and pre-edit hashes. Reject authority transfers outside the changed cluster unless explicitly justified. Validate with:

```bash
python3 .opencode/okf/okf_core.py contract transfer-plan <plan.json>
```

Approval must identify this independent review and bind to the exact plan hash. Approval authorizes automatic Pass 2 only for that hash and those transfers.

## Findings and verdict

Emit stable IDs with severity, evidence, basis (observed/sampled/inferred), affected source/claim/concept, required disposition, and resolution status. Validate the report:

```bash
python3 .opencode/okf/okf_core.py contract findings <findings.json>
```

Use:

- **Blocked** for invalid inputs, unreadable sources, repository mutation, or unsafe lifecycle state.
- **Needs remediation** for deterministic errors, new unexplained warnings, unsupported/lost claims, improper duplicate custody, or unresolved high findings.
- **Ready for consolidation** after incorporation/remediation clears all gates.
- **Ready** only for an independently approved post-consolidation state with no unresolved transfers or high candidates.

State what changes reopen review.
