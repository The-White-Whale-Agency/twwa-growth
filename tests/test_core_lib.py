from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import twwa_testutil as tu  # noqa: F401  (sets sys.path)
from twwa_lib import cli, htmlx, http, spend, state as st, stats, textde


class TestCli(unittest.TestCase):
    def test_finding_valid(self):
        f = cli.finding("tech.canonical.missing", "tech", "P2", "Canonical fehlt", "Detail", evidence={"url": "https://x.example/"}, action_type="tech_fix")
        self.assertEqual(f["priority_group"], 3)
        self.assertEqual(set(f["evidence"]), {"url", "file", "line", "snippet", "value"})

    def test_finding_rejects(self):
        with self.assertRaises(ValueError):
            cli.finding("Bad Id", "tech", "P2", "t", "d", evidence={"url": "u"})
        with self.assertRaises(ValueError):
            cli.finding("a.b", "seo", "P2", "t", "d", evidence={"url": "u"})
        with self.assertRaises(ValueError):
            cli.finding("a.b", "tech", "P0", "t", "d", evidence={"url": "u"})
        with self.assertRaises(ValueError):
            cli.finding("a.b", "tech", "P2", "t", "d")  # verified without evidence
        f = cli.finding("a.b", "tech", "P2", "t", "d", status="hypothesis")
        self.assertEqual(f["status"], "hypothesis")

    def test_at_or_above(self):
        fs = [cli.finding("a.b", "tech", "P2", "t", "d", evidence={"url": "u"}), cli.finding("a.c", "tech", "P1", "t", "d", status="hypothesis")]
        self.assertEqual(len(cli.at_or_above(fs, "P2")), 1)
        self.assertEqual(len(cli.at_or_above(fs, "P1")), 0)

    def test_exit_codes(self):
        self.assertEqual((cli.EXIT_OK, cli.EXIT_FAIL, cli.EXIT_USAGE, cli.EXIT_NOCREDS, cli.EXIT_BLOCKED, cli.EXIT_REMOTE), (0, 1, 2, 3, 4, 5))


class TestTextDe(unittest.TestCase):
    def test_sentences(self):
        s = textde.sentences("Wir arbeiten seit 2001 in Musterstadt. Das gilt z. B. am 1. Januar! Danach ca. 3 Tage.")
        self.assertEqual(len(s), 3)

    def test_phone(self):
        self.assertEqual(textde.norm_phone("07000 / 12 34 56"), "+497000123456")
        self.assertEqual(textde.norm_phone("+49 (0) 7000 123456"), "+497000123456")
        self.assertEqual(textde.norm_phone("tel:+497000123456"), "+497000123456")
        self.assertEqual(textde.norm_phone("0049 7000 123456"), "+497000123456")

    def test_norm(self):
        self.assertEqual(textde.norm_address("Musterstraße 1"), textde.norm_address("Musterstr. 1"))
        self.assertEqual(textde.fold_umlauts("Südviertel Größe"), "Suedviertel Groesse")
        self.assertIn("Sankt Musterberg", textde.town_variants("St. Musterberg"))
        self.assertEqual(textde.norm_name("Musterbetrieb Stuck & Putz GmbH", True), "musterbetrieb stuck und putz")

    def test_shingles_jaccard(self):
        a = textde.shingles("eins zwei drei vier fünf sechs")
        self.assertEqual(len(a), 2)
        self.assertEqual(textde.jaccard(a, a), 1.0)
        self.assertEqual(textde.jaccard(set(), set()), 0.0)

    def test_numbers(self):
        self.assertEqual(textde.numbers("1.200 m², 2,5 Tage, 12 Fenster"), [1200.0, 2.5, 12.0])

    def test_town_runs(self):
        known = ["Musterstadt", "Nachbarstadt", "Beispielort"]
        runs = textde.town_runs("Wir sind tätig in Musterstadt, Nachbarstadt, Beispielort, Hinterhausen, Vorderbach, Oberdorf, Unterberg, Neuheim, Altingen und Bad Kurstadt.", known)
        self.assertEqual(len(runs[0]), 10)
        self.assertEqual(textde.town_runs("Fassadensanierung, Innenputz, Stuck und Trockenbau.", known), [])


class TestStats(unittest.TestCase):
    def test_wilson(self):
        lo, hi = stats.wilson(5, 10)
        self.assertTrue(0.2 < lo < 0.3 and 0.7 < hi < 0.8)
        self.assertEqual(stats.wilson(0, 0), (0.0, 1.0))

    def test_did(self):
        d = stats.diff_in_diff(100, 150, 100, 110)
        self.assertEqual(d["did"], 40)
        self.assertAlmostEqual(d["did_pct"], 40.0)
        self.assertIsNone(stats.pct_change(0, 5))
        self.assertEqual(stats.median([3, 1, 2, 4]), 2.5)


class TestState(unittest.TestCase):
    def test_template_config_equals_defaults(self):
        tpl = json.loads((tu.ROOT / "templates/state/config.json").read_text(encoding="utf-8"))
        self.assertEqual(tpl, st.DEFAULT_CONFIG)

    def test_find_and_config(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            (root / ".twwa-growth").mkdir()
            (root / "src/deep").mkdir(parents=True)
            self.assertEqual(st.find_state(root / "src/deep"), (root / ".twwa-growth").resolve())
            st.save_json(root / ".twwa-growth/config.json", {"caps": {"proposals_per_cycle": 3}})
            cfg = st.load_config(root / ".twwa-growth")
            self.assertEqual(cfg["caps"]["proposals_per_cycle"], 3)
            self.assertEqual(cfg["caps"]["crawl_pages"], 25)
            self.assertEqual(cfg["autopilot"]["level"], "off")
            st.append_jsonl(root / ".twwa-growth/x.jsonl", {"a": 1})
            self.assertEqual(st.read_jsonl(root / ".twwa-growth/x.jsonl"), [{"a": 1}])

    def test_snapshots(self):
        state = tu.FIX / ".twwa-growth"
        p = st.latest_snapshot(state, "gsc")
        self.assertEqual(p.parent.name, "2026-11-14")
        self.assertIsNone(st.latest_snapshot(state, "gsc", before="2026-11-01"))
        self.assertIsNone(st.latest_snapshot(state, "nope"))

    def test_no_pricing_keys(self):
        flat = json.dumps(st.DEFAULT_CONFIG).lower()
        for bad in ('"price', '"pricing', '"package'):
            self.assertNotIn(bad, flat)


class TestHttpHtml(unittest.TestCase):
    def test_private_refused(self):
        http.use_fixture(None)
        with self.assertRaises(http.BlockedAddress):
            http.fetch("http://127.0.0.1:9/")

    def test_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d) / "fx.json"
            fx.write_text(json.dumps({"responses": {
                "https://www.musterbetrieb.example/alt": {"status": 308, "headers": {"location": "/neu"}},
                "https://www.musterbetrieb.example/neu": {"status": 200, "text": "<title>Neu</title>"},
                "https://www.musterbetrieb.example/robots.txt": {"status": 200, "text": "User-agent: *\nDisallow: /intern/\n"}}}), encoding="utf-8")
            http.use_fixture(str(fx))
            try:
                r = http.fetch("https://www.musterbetrieb.example/alt")
                self.assertEqual((r.status, r.url, len(r.history)), (200, "https://www.musterbetrieb.example/neu", 1))
                self.assertEqual(http.fetch("https://www.musterbetrieb.example/fehlt").status, 404)
                self.assertFalse(http.robots_allows("https://www.musterbetrieb.example/intern/x"))
                self.assertTrue(http.robots_allows("https://www.musterbetrieb.example/"))
            finally:
                http.use_fixture(None)

    def test_robots_groups(self):
        txt = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n"
        self.assertTrue(http.robots_blocks_root(txt, "gptbot"))
        self.assertFalse(http.robots_blocks_root(txt, "oai-searchbot"))

    def test_parse_page(self):
        html = (tu.FIX / "repo/dist/index.html").read_text(encoding="utf-8")
        p = htmlx.parse(html, "https://www.musterbetrieb.example/")
        self.assertEqual(p.canonical, "https://www.musterbetrieb.example/")
        self.assertEqual(p.lang, "de")
        self.assertEqual(len(p.h1), 1)
        self.assertIn("HousePainter", p.schema_types())
        self.assertTrue(p.tel_links and p.wa_links and p.forms)
        self.assertNotIn("Website by", p.text)  # footer is not main content
        self.assertIn("Website by", p.full_text)


class TestSpend(unittest.TestCase):
    def test_guard(self):
        with tempfile.TemporaryDirectory() as d:
            s = Path(d)
            ok, _ = spend.check(s, 0.01)
            self.assertFalse(ok)  # cap 0 by default
            st.save_json(s / "config.json", {"spend": {"monthly_cap_usd": 1}})
            self.assertTrue(spend.check(s, 0.5)[0])
            spend.record(s, "x", "serp_maps", 1, 0.8)
            self.assertFalse(spend.check(s, 0.5)[0])
            (s / "STOP").write_text("x")
            self.assertFalse(spend.check(s, 0.0)[0])
            with self.assertRaises(SystemExit) as cm:
                spend.guard(s, 0.1)
            self.assertEqual(cm.exception.code, 4)


if __name__ == "__main__":
    unittest.main()
