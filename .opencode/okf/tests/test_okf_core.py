import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import okf_core as core


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root_patch = patch.object(core, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_terminal_citations_and_wrong_link_target(self):
        write(self.root / "actors/countries/saudi-arabia.md", "---\ntitle: Saudi Arabia\n---\n")
        write(self.root / "events/example.md", "[Bahrain]({{ site.baseurl }}/actors/countries/bahrain.html)\n")
        write(self.root / "actors/countries/canada.md", "Body [1]\n[Bahrain]({{ site.baseurl }}/actors/countries/saudi-arabia.html)\n# Citations\n[1] url\n## See Also\n")
        rules = {f.rule for f in core.analyze(["actors/countries/canada.md"])}
        self.assertIn("citations_terminal", rules)
        self.assertIn("link_label_target", rules)

    def test_citation_renumbering_gap(self):
        write(self.root / "themes/x.md", "Claim [2]\n# Citations\n[2] url\n")
        rules = {f.rule for f in core.analyze(["themes/x.md"])}
        self.assertIn("citation_sequence", rules)

    def test_unicode_apostrophe_source_and_trailing_space(self):
        rel = "sources/Understanding President Trump’s Tariffs.md"
        write(self.root / rel, "source line  \n")
        found = core.analyze([rel], include_sources=True)
        self.assertEqual(found[0].rule, "raw_source_whitespace")
        self.assertEqual(found[0].severity, "info")

    def test_analyzer_is_read_only_and_idempotent(self):
        rel = "themes/x.md"
        write(self.root / rel, "Claim [1]\n# Citations\n[1] url\n")
        before = hashlib.sha256((self.root / rel).read_bytes()).hexdigest()
        first = core.analyze([rel])
        second = core.analyze([rel])
        after = hashlib.sha256((self.root / rel).read_bytes()).hexdigest()
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_similarity_triage_finds_duplicate_claim_custody(self):
        shared = "Iran attacks allied infrastructure and raises political costs for host governments while demonstrating that security guarantees cannot protect regional partners. " * 4
        write(self.root / "actors/a.md", shared)
        write(self.root / "themes/b.md", shared.replace("partners", "allies"))
        clusters = core.similarity_clusters(["actors/a.md", "themes/b.md"], threshold=0.7)
        self.assertEqual(len(clusters), 1)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root_patch = patch.object(core, "ROOT", self.root)
        self.root_patch.start()
        write(self.root / "themes/x.md", "x")

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def manifest(self):
        return {
            "schema_version": "1.0", "run_id": "run", "baseline_hash": "abc",
            "sources": [], "model": {"id": "glm-5.2", "variant": "medium", "vision": False},
            "claims": [], "destinations": [], "worker_write_sets": {"coordinator": ["log.md"]},
            "pre_edit_hashes": {}, "result_hashes": {}, "validation_delta": {}, "lifecycle_status": "review",
        }

    def test_stale_hash_global_ownership_and_overlap(self):
        data = self.manifest()
        data["lifecycle_status"] = "writing"
        data["pre_edit_hashes"] = {"themes/x.md": "stale"}
        data["worker_write_sets"] = {"a": ["log.md", "themes/x.md"], "b": ["themes/x.md"]}
        errors = core.validate_manifest(data)
        self.assertTrue(any("stale" in e for e in errors))
        self.assertTrue(any("global" in e for e in errors))
        self.assertTrue(any("overlapping" in e for e in errors))

    def test_distinct_facets_are_reuse_but_duplicate_custody_is_rejected(self):
        data = self.manifest()
        data["destinations"] = [
            {"claim_id": "C1", "facet_id": "actor-posture", "concept": "actors/a.md"},
            {"claim_id": "C1", "facet_id": "operational-effect", "concept": "conflicts/c.md"},
        ]
        self.assertEqual(core.validate_manifest(data), [])
        data["destinations"].append({"claim_id": "C1", "facet_id": "actor-posture", "concept": "themes/t.md"})
        self.assertTrue(any("duplicate custody" in e for e in core.validate_manifest(data)))

    def test_interrupted_restart_contract_is_repeatable(self):
        data = self.manifest()
        data["lifecycle_status"] = "remediation"
        self.assertEqual(core.validate_manifest(data), core.validate_manifest(json.loads(json.dumps(data))))

    def test_unresolved_transfer_and_independent_approval_gate(self):
        plan = {"schema_version": "1.0", "plan_id": "p", "baseline_hash": "b", "scope": [],
                "transfers": [{"claim_id": "C", "canonical_home": "x", "retained_facets": [],
                               "removed_copies": [], "expected_citations": [], "pre_edit_hashes": {}, "decision": "unresolved"}],
                "review": {"status": "approved", "independent": False, "review_id": "r"}}
        errors = core.validate_transfer_plan(plan)
        self.assertTrue(any("unresolved" in e for e in errors))
        self.assertTrue(any("independent" in e for e in errors))

    def test_review_must_declare_evidence_basis(self):
        review = {"findings": [{"id": "F", "severity": "low", "evidence": "e", "affected": {},
                                "required_disposition": "fix", "resolution_status": "open"}],
                  "verdict": "Needs remediation"}
        self.assertTrue(any("basis" in e for e in core.validate_findings(review)))


class CapabilityTests(unittest.TestCase):
    def test_image_requires_vision(self):
        ok, reason = core.source_capability(Path("x.png"), vision=False)
        self.assertFalse(ok)
        self.assertIn("vision", reason)

    def test_pdf_uses_supported_extractor_or_fails_clearly(self):
        ok, method = core.source_capability(Path("x.pdf"), vision=False)
        self.assertTrue(ok or "requires" in method)


if __name__ == "__main__":
    unittest.main()
