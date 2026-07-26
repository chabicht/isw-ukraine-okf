import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import citations as cit

ROOT = Path(__file__).resolve().parents[3]

REGISTRY = {
    "isw:2025-01-18": {
        "title": "Russian Offensive Campaign Assessment, January 18, 2025",
        "url": "https://understandingwar.org/a/jan-18/",
    },
    "isw:2025-01-19": {
        "title": "Russian Offensive Campaign Assessment, January 19, 2025",
        "url": "https://understandingwar.org/a/jan-19/",
    },
    "isw:2025-01-20": {
        "title": "Russian Offensive Campaign Assessment, January 20, 2025",
        "url": "https://understandingwar.org/a/jan-20/",
    },
}


def norm(body, prune=False):
    return cit.normalize_text(body, REGISTRY, prune)


class NormalizeTests(unittest.TestCase):
    def test_keys_become_numbers_in_order_of_appearance(self):
        body = (
            "Second source first.[isw:2025-01-20]\n\n"
            "Then an older one.[isw:2025-01-18]\n\n"
            "# Citations\n"
        )
        out, _ = norm(body)
        self.assertIn("Second source first.[1]", out)
        self.assertIn("Then an older one.[2]", out)
        self.assertIn("[1] [Russian Offensive Campaign Assessment, January 20, 2025]", out)
        self.assertIn("[2] [Russian Offensive Campaign Assessment, January 18, 2025]", out)

    def test_existing_numbers_are_renumbered_contiguously(self):
        body = (
            "Alpha.[7]\n\nBravo.[3]\n\n"
            "# Citations\n\n"
            "[3] [Jan 19](https://understandingwar.org/a/jan-19/)\n"
            "[7] [Jan 20](https://understandingwar.org/a/jan-20/)\n"
        )
        out, _ = norm(body)
        self.assertIn("Alpha.[1]", out)
        self.assertIn("Bravo.[2]", out)
        self.assertIn("[1] [Jan 20](https://understandingwar.org/a/jan-20/)", out)
        self.assertIn("[2] [Jan 19](https://understandingwar.org/a/jan-19/)", out)

    def test_repeated_source_collapses_to_one_entry(self):
        body = "A.[isw:2025-01-18]\n\nB.[isw:2025-01-18]\n\n# Citations\n"
        out, _ = norm(body)
        self.assertEqual(out.count("[1] [Russian Offensive"), 1)
        self.assertIn("A.[1]", out)
        self.assertIn("B.[1]", out)

    def test_mixed_keys_and_numbers(self):
        body = (
            "Old.[1]\n\nNew.[isw:2025-01-20]\n\n"
            "# Citations\n\n[1] [Jan 18](https://understandingwar.org/a/jan-18/)\n"
        )
        out, _ = norm(body)
        self.assertIn("Old.[1]", out)
        self.assertIn("New.[2]", out)
        self.assertIn("[2] [Russian Offensive Campaign Assessment, January 20, 2025]", out)

    def test_unreferenced_entry_is_kept_by_default(self):
        body = (
            "Only one.[1]\n\n# Citations\n\n"
            "[1] [Jan 18](https://understandingwar.org/a/jan-18/)\n"
            "[2] [Jan 19](https://understandingwar.org/a/jan-19/)\n"
        )
        out, notes = norm(body)
        self.assertIn("jan-19", out)
        self.assertTrue(any("kept 1 unreferenced" in n for n in notes))

    def test_unreferenced_entry_is_dropped_with_prune(self):
        body = (
            "Only one.[1]\n\n# Citations\n\n"
            "[1] [Jan 18](https://understandingwar.org/a/jan-18/)\n"
            "[2] [Jan 19](https://understandingwar.org/a/jan-19/)\n"
        )
        out, notes = norm(body, prune=True)
        self.assertNotIn("jan-19", out)
        self.assertTrue(any("pruned 1" in n for n in notes))

    def test_dangling_numeric_marker_refuses_to_write(self):
        body = "Claim.[9]\n\n# Citations\n\n[1] [Jan 18](https://understandingwar.org/a/jan-18/)\n"
        with self.assertRaises(cit.Problem) as ctx:
            norm(body)
        self.assertIn("[9]", str(ctx.exception))

    def test_unknown_key_refuses_to_write(self):
        body = "Claim.[isw:2099-01-01]\n\n# Citations\n"
        with self.assertRaises(cit.Problem) as ctx:
            norm(body)
        self.assertIn("unknown source key", str(ctx.exception))

    def test_markers_but_no_citations_section_is_an_error(self):
        with self.assertRaises(cit.Problem):
            norm("Claim.[isw:2025-01-18]\n")

    def test_markdown_links_are_not_mistaken_for_markers(self):
        body = (
            "See [Russia](https://x/russia.html) and cite this.[isw:2025-01-18]\n\n# Citations\n"
        )
        out, _ = norm(body)
        self.assertIn("[Russia](https://x/russia.html)", out)

    def test_citations_heading_stays_terminal(self):
        body = "A.[isw:2025-01-18]\n\n# Citations\n\n[1] [x](https://understandingwar.org/a/jan-18/)\n"
        out, _ = norm(body)
        self.assertEqual(out.count("# Citations"), 1)
        self.assertGreater(out.index("# Citations"), out.index("A.["))

    def test_idempotent(self):
        body = (
            "A.[isw:2025-01-20]\n\nB.[isw:2025-01-18]\n\nC.[isw:2025-01-20]\n\n# Citations\n"
        )
        once, _ = norm(body)
        twice, _ = norm(once)
        self.assertEqual(once, twice)


class CorruptedFixtureTests(unittest.TestCase):
    """0d43e88 dropped citation entries out from under the body. In
    conflicts/russia-ukraine-war.md the body was left referencing [20] with no
    matching entry; the tool must refuse rather than silently renumber around
    the hole and lose the source."""

    def _fixture(self, rel):
        try:
            return subprocess.run(
                ["git", "show", f"0d43e88:{rel}"],
                cwd=str(ROOT), capture_output=True, text=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest("git fixture 0d43e88 unavailable")

    def test_refuses_to_normalize_the_corrupted_commit(self):
        text = self._fixture("conflicts/russia-ukraine-war.md")
        body = text[text.index("\n---", 3) + 4:]
        registry = cit.load_registry()
        if not registry:
            self.skipTest("sources.json not built")
        with self.assertRaises(cit.Problem):
            cit.normalize_text(body, registry, prune=False)

    def test_reverted_version_normalizes_cleanly(self):
        path = ROOT / "regions" / "kherson-direction.md"
        registry = cit.load_registry()
        if not registry or not path.exists():
            self.skipTest("bundle or sources.json unavailable")
        text = path.read_text(encoding="utf-8")
        body = text[text.index("\n---", 3) + 4:]
        out, _ = cit.normalize_text(body, registry, prune=False)
        again, _ = cit.normalize_text(out, registry, prune=False)
        self.assertEqual(out, again)


class RegistryTests(unittest.TestCase):
    def test_roca_title_maps_to_dated_key(self):
        known = {"isw:2025-01-20": Path("sources/isw/2025-01-20.md")}
        key = cit.key_for_citation(
            "Russian Offensive Campaign Assessment, January 20, 2025",
            "https://understandingwar.org/a/jan-20/", known,
        )
        self.assertEqual(key, "isw:2025-01-20")

    def test_special_report_maps_by_url_slug(self):
        known = {
            "isw:2025-01-15-russias-quiet-conquest-belarus":
                Path("sources/isw/2025-01-15-russias-quiet-conquest-belarus.md")
        }
        key = cit.key_for_citation(
            "Russia's Quiet Conquest: Belarus",
            "https://understandingwar.org/research/russia-ukraine/russias-quiet-conquest-belarus/",
            known,
        )
        self.assertEqual(key, "isw:2025-01-15-russias-quiet-conquest-belarus")

    def test_third_party_source_gets_ref_key(self):
        key = cit.key_for_citation(
            "NATO - Relations with Georgia",
            "https://www.nato.int/cps/en/natohq/topics_38988.htm", {},
        )
        self.assertEqual(key, "ref:nato-relations-with-georgia")


if __name__ == "__main__":
    unittest.main()
