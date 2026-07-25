#!/usr/bin/env python3
"""Deterministic contracts and analyzers for the OKF knowledge lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
CONCEPT_DIRS = ("actors", "conflicts", "regions", "themes", "events")
GLOBAL_FILES = {"log.md", "rules.md", "okf.md", "_config.yml"}
VALID_STATUSES = {
    "planned", "extracting", "writing", "remediation", "review",
    "ready_for_consolidation", "consolidating", "post_review", "complete", "blocked",
}


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    rule: str
    path: str
    evidence: str
    observed: str = "observed"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(rule: str, path: str, evidence: str) -> str:
    digest = hashlib.sha256(f"{rule}\0{path}\0{evidence}".encode()).hexdigest()[:10]
    return f"OKF-{rule.upper().replace('_', '-')}-{digest}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def git_paths(base: str, head: str = "HEAD") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"], cwd=ROOT,
        check=True, capture_output=True, text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def concept_paths(paths: Iterable[str]) -> list[str]:
    return sorted(p for p in paths if p.endswith(".md") and p.split("/", 1)[0] in CONCEPT_DIRS)


def parse_citations(text: str) -> tuple[set[int], set[int], int | None]:
    matches = list(re.finditer(r"^# Citations\s*$", text, re.MULTILINE))
    if not matches:
        return set(map(int, re.findall(r"\[(\d+)\]", text))), set(), None
    marker = matches[0]
    refs = set(map(int, re.findall(r"\[(\d+)\]", text[: marker.start()])))
    entries = set(map(int, re.findall(r"^\[(\d+)\]", text[marker.end() :], re.MULTILINE)))
    return refs, entries, marker.start()


def markdown_links(text: str) -> Iterable[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(\{\{\s*site\.baseurl\s*\}\}/([^\s)]+)\.html\)", text)


def preferred_link_targets() -> dict[str, str]:
    """Infer stable label targets from corpus-wide usage without banning aliases."""
    usages: dict[str, list[str]] = {}
    for directory in CONCEPT_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for label, target in markdown_links(text):
                usages.setdefault(label.casefold(), []).append(target)
    preferred: dict[str, str] = {}
    for label, targets in usages.items():
        if len(set(targets)) < 2:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", label).strip("-")
        direct = [target for target in targets if target.rsplit("/", 1)[-1] == slug]
        if direct:
            preferred[label] = direct[0]
        else:
            preferred[label] = max(set(targets), key=targets.count)
    return preferred


def analyze(paths: Iterable[str], include_sources: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    preferred = preferred_link_targets()
    for rel in sorted(set(paths)):
        path = ROOT / rel
        if not path.is_file():
            continue
        if rel.startswith("sources/") and not include_sources:
            continue
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")

        if rel.startswith("sources/"):
            lines = [str(i) for i, line in enumerate(text.splitlines(), 1) if line.endswith((" ", "\t"))]
            if lines:
                evidence = f"raw source has trailing whitespace on lines {','.join(lines[:12])}"
                findings.append(Finding(stable_id("raw_source_whitespace", rel, evidence), "info", "raw_source_whitespace", rel, evidence))
            continue

        is_reference = rel in {"log.md", "rules.md", "okf.md"} or path.name in {"README.md", "index.md"}

        refs, entries, marker = parse_citations(text) if not is_reference else (set(), set(), None)
        if refs - entries:
            evidence = f"body refs lack entries: {sorted(refs - entries)}"
            findings.append(Finding(stable_id("missing_citation", rel, evidence), "error", "missing_citation", rel, evidence))
        if entries - refs:
            evidence = f"citation entries lack body refs: {sorted(entries - refs)}"
            findings.append(Finding(stable_id("orphan_citation", rel, evidence), "warning", "orphan_citation", rel, evidence))
        if entries and entries != set(range(1, max(entries) + 1)):
            evidence = f"non-contiguous citation entries: {sorted(entries)}"
            findings.append(Finding(stable_id("citation_sequence", rel, evidence), "error", "citation_sequence", rel, evidence))
        if marker is not None and re.search(r"^#{1,6}\s+", text[marker + 1 :], re.MULTILINE):
            evidence = "# Citations is not the terminal heading"
            findings.append(Finding(stable_id("citations_terminal", rel, evidence), "error", "citations_terminal", rel, evidence))

        for label, target in markdown_links(text):
            target_path = ROOT / f"{target}.md"
            if not target_path.exists():
                evidence = f"link label {label!r} targets missing {target}.md"
                findings.append(Finding(stable_id("broken_link", rel, evidence), "warning", "broken_link", rel, evidence))
            expected = preferred.get(label.casefold())
            expected_path = ROOT / f"{expected}.md" if expected else None
            if (expected and target != expected and expected.startswith("actors/countries/")
                    and target.startswith("actors/countries/") and not expected_path.exists()):
                evidence = f"link label {label!r} targets {target}.md but corpus usage resolves it to {expected}.md"
                findings.append(Finding(stable_id("link_label_target", rel, evidence), "error", "link_label_target", rel, evidence))
    return findings


def warning_keys(findings: Iterable[Finding]) -> set[tuple[str, str, str]]:
    return {(f.rule, f.path, f.evidence) for f in findings if f.severity in {"warning", "error"}}


def added_lines(base: str, head: str, rel: str) -> set[int]:
    result = subprocess.run(
        ["git", "diff", "--unified=0", f"{base}..{head}", "--", rel], cwd=ROOT,
        capture_output=True, text=True, check=True,
    )
    lines: set[int] = set()
    for start, count in re.findall(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", result.stdout, re.MULTILINE):
        amount = int(count or "1")
        lines.update(range(int(start), int(start) + amount))
    return lines


def similarity_clusters(paths: Iterable[str], threshold: float = 0.72, base: str | None = None, head: str = "HEAD") -> list[dict[str, Any]]:
    """Rank near-duplicate paragraph custody without semantic file inventories."""
    paragraphs: list[tuple[str, int, str, set[str], bool]] = []
    for rel in concept_paths(paths):
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "# Citations" in text:
            text = text.split("# Citations", 1)[0]
        changed = added_lines(base, head, rel) if base else set()
        offset = 1
        for number, paragraph in enumerate(re.split(r"\n\s*\n", text), 1):
            paragraph_lines = paragraph.count("\n") + 1
            is_added = not base or bool(changed & set(range(offset, offset + paragraph_lines)))
            offset += paragraph_lines + 1
            plain = re.sub(r"\[[^\]]+\]\([^\)]+\)|\[\d+\]|[#*_`]", " ", paragraph)
            words = re.findall(r"[a-z0-9]+", plain.casefold())
            if len(words) < 35:
                continue
            paragraphs.append((rel, number, paragraph.strip(), set(words), is_added))
    clusters: list[dict[str, Any]] = []
    for index, (left_path, left_no, left_text, left_words, left_added) in enumerate(paragraphs):
        for right_path, right_no, right_text, right_words, right_added in paragraphs[index + 1 :]:
            if left_path == right_path:
                continue
            if not (left_added or right_added):
                continue
            score = len(left_words & right_words) / max(1, len(left_words | right_words))
            if score >= threshold:
                clusters.append({
                    "score": round(score, 3),
                    "left": {"path": left_path, "paragraph": left_no, "preview": left_text[:180]},
                    "right": {"path": right_path, "paragraph": right_no, "preview": right_text[:180]},
                })
    return sorted(clusters, key=lambda item: (-item["score"], item["left"]["path"], item["right"]["path"]))


def validate_manifest(data: dict[str, Any]) -> list[str]:
    required = {
        "schema_version", "run_id", "baseline_hash", "sources", "model", "claims",
        "destinations", "worker_write_sets", "result_hashes", "validation_delta", "lifecycle_status",
    }
    errors = [f"missing {key}" for key in sorted(required - data.keys())]
    if data.get("lifecycle_status") not in VALID_STATUSES:
        errors.append("invalid lifecycle_status")
    owners: dict[str, str] = {}
    for worker, paths in data.get("worker_write_sets", {}).items():
        for path in paths:
            if path in owners:
                errors.append(f"overlapping write ownership for {path}: {owners[path]} and {worker}")
            owners[path] = worker
            if Path(path).name in GLOBAL_FILES and worker != "coordinator":
                errors.append(f"global file {path} must be coordinator-owned")
    if data.get("lifecycle_status") in {"planned", "writing", "remediation", "consolidating"}:
        for path, expected in data.get("pre_edit_hashes", {}).items():
            full = ROOT / path
            if full.exists() and sha256(full) != expected:
                errors.append(f"stale pre-edit hash for {path}")
    custody: dict[tuple[str, str], str] = {}
    for destination in data.get("destinations", []):
        claim_id = destination.get("claim_id")
        facet_id = destination.get("facet_id")
        concept = destination.get("concept")
        if not all((claim_id, facet_id, concept)):
            errors.append("destination missing claim_id, facet_id, or concept")
            continue
        key = (claim_id, facet_id)
        if key in custody and custody[key] != concept:
            errors.append(f"duplicate custody for {claim_id}/{facet_id}: {custody[key]} and {concept}")
        custody[key] = concept
    return errors


def validate_findings(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for item in data.get("findings", []):
        for key in ("id", "severity", "evidence", "affected", "required_disposition", "resolution_status"):
            if key not in item:
                errors.append(f"finding missing {key}")
        if item.get("id") in seen:
            errors.append(f"duplicate finding id {item.get('id')}")
        if item.get("basis") not in {"observed", "sampled", "inferred"}:
            errors.append(f"finding {item.get('id')} lacks observed/sampled/inferred basis")
        seen.add(item.get("id", ""))
    verdict = data.get("verdict")
    if verdict not in {"Blocked", "Needs remediation", "Ready for consolidation", "Ready"}:
        errors.append("invalid review verdict")
    if verdict in {"Ready for consolidation", "Ready"}:
        unresolved = [f.get("id") for f in data.get("findings", []) if f.get("severity") in {"high", "critical"} and f.get("resolution_status") != "resolved"]
        if unresolved:
            errors.append(f"ready verdict has unresolved high findings: {unresolved}")
    return errors


def validate_transfer_plan(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"schema_version", "plan_id", "baseline_hash", "scope", "transfers", "review"}
    errors.extend(f"missing {key}" for key in sorted(required - data.keys()))
    for transfer in data.get("transfers", []):
        for key in ("claim_id", "canonical_home", "retained_facets", "removed_copies", "expected_citations", "pre_edit_hashes", "decision"):
            if key not in transfer:
                errors.append(f"transfer {transfer.get('claim_id', '?')} missing {key}")
        if transfer.get("decision") not in {"retain", "move", "merge", "drop_unsupported"}:
            errors.append(f"transfer {transfer.get('claim_id', '?')} unresolved")
    review = data.get("review", {})
    if review.get("status") != "approved" or not review.get("independent"):
        errors.append("transfer plan lacks independent approval")
    return errors


def source_capability(path: Path, vision: bool) -> tuple[bool, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        for command in ("pdftotext", "mutool"):
            if subprocess.run(["sh", "-c", f"command -v {command}"], capture_output=True).returncode == 0:
                return True, command
        return False, "PDF extraction requires pdftotext or MuPDF"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"} and not vision:
        return False, "image source requires a vision-capable model or explicit handoff"
    return True, "text"


def command_analyze(args: argparse.Namespace) -> int:
    paths = git_paths(args.base, args.head) if args.base else [str(p.relative_to(ROOT)) for p in ROOT.rglob("*.md")]
    findings = analyze(paths, include_sources=args.include_sources)
    payload = {"scope": {"base": args.base, "head": args.head, "files": len(paths)}, "findings": [asdict(f) for f in findings]}
    print(dump_json(payload), end="")
    return 1 if any(f.severity == "error" for f in findings) else 0


def command_contract(args: argparse.Namespace) -> int:
    data = load_json(Path(args.path))
    validators = {"manifest": validate_manifest, "findings": validate_findings, "transfer-plan": validate_transfer_plan}
    errors = validators[args.kind](data)
    print(dump_json({"valid": not errors, "errors": errors}), end="")
    return bool(errors)


def command_hash(args: argparse.Namespace) -> int:
    print(dump_json({path: sha256(ROOT / path) for path in args.paths}), end="")
    return 0


def command_triage(args: argparse.Namespace) -> int:
    paths = git_paths(args.base, args.head)
    print(dump_json({"base": args.base, "head": args.head, "clusters": similarity_clusters(paths, args.threshold, args.base, args.head)}), end="")
    return 0


def command_capability(args: argparse.Namespace) -> int:
    ok, method = source_capability(ROOT / args.path, args.vision)
    print(dump_json({"supported": ok, "method": method}), end="")
    return 0 if ok else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("analyze")
    scan.add_argument("--base")
    scan.add_argument("--head", default="HEAD")
    scan.add_argument("--include-sources", action="store_true")
    scan.set_defaults(func=command_analyze)
    contract = sub.add_parser("contract")
    contract.add_argument("kind", choices=("manifest", "findings", "transfer-plan"))
    contract.add_argument("path")
    contract.set_defaults(func=command_contract)
    hashes = sub.add_parser("hash")
    hashes.add_argument("paths", nargs="+")
    hashes.set_defaults(func=command_hash)
    triage = sub.add_parser("triage")
    triage.add_argument("--base", required=True)
    triage.add_argument("--head", default="HEAD")
    triage.add_argument("--threshold", type=float, default=0.72)
    triage.set_defaults(func=command_triage)
    capability = sub.add_parser("capability")
    capability.add_argument("path")
    capability.add_argument("--vision", action="store_true")
    capability.set_defaults(func=command_capability)
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
