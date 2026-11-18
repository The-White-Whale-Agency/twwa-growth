"""Tests for the data, teardown, planning, measurement and reporting layers (no network)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from twwa_testutil import FIX, run, run_json

TD = FIX / "teardown"


class Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(FIX, self.tmp / "m")
        self.repo = self.tmp / "m" / "repo"
        shutil.copytree(self.tmp / "m" / ".twwa-growth", self.repo / ".twwa-growth")
        self.state = str(self.repo / ".twwa-growth")
        self.agency = self.tmp / "agency"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def r(self, script, *a, extra_env=None):
        env = {"TWWA_AGENCY_DIR": str(self.agency)}
        env.update(extra_env or {})
        return run(script, *a, cwd=str(self.repo), extra_env=env)

    def rj(self, script, *a):
        return run_json(script, *a, cwd=str(self.repo), extra_env={"TWWA_AGENCY_DIR": str(self.agency)})


class ProviderTests(Workspace):
    def test_no_creds_exit_3_and_dry_run(self):
        code, out = self.rj("providers.py", "pick", "serp_maps")
        self.assertEqual(code, 3)
        code, _, _ = self.r("providers.py", "call", "serp_organic", "--params", '{"query":"x"}', extra_env={"DATAFORSEO_LOGIN": "a", "DATAFORSEO_PASSWORD": "b", "TWWA_AGENCY_DIR": str(self.agency)})
        self.assertEqual(code, 0)

    def test_dataforseo_fixture_normalises(self):
        raw = {"tasks": [{"status_code": 20000, "result": [{"items": [
            {"type": "local_pack", "title": "A", "rating": {"value": 4.7, "votes_count": 30}},
            {"type": "organic", "rank_group": 1, "url": "https://www.a.example/x", "title": "A", "description": "d"},
            {"type": "ai_overview", "references": [{"url": "https://www.gelbeseiten.de/y"}]}]}]}]}
        f = self.tmp / "raw.json"
        f.write_text(json.dumps(raw))
        code, out = run_json("providers.py", "call", "serp_organic", "--params", '{"query":"x"}', "--fixture", str(f),
                             cwd=str(self.repo), extra_env={"DATAFORSEO_LOGIN": "a", "DATAFORSEO_PASSWORD": "b"})
        self.assertEqual(code, 0)
        self.assertEqual(out["results"][0]["domain"], "a.example")
        self.assertEqual(out["local_pack"][0]["reviews"], 30)
        self.assertEqual(out["ai_overview"]["cited_domains"], ["gelbeseiten.de"])


class TeardownTests(Workspace):
    def run_teardown(self):
        self.assertEqual(self.r("serp_teardown.py", "import", str(TD / "obs-organic.json"))[0], 0)
        self.assertEqual(self.r("serp_teardown.py", "collect", "--http-fixture", str(self.tmp / "m" / "teardown" / "http.json"))[0], 0)
        self.assertEqual(self.r("serp_teardown.py", "score")[0], 0)
        self.assertEqual(self.r("serp_teardown.py", "backlog")[0], 0)
        return self.rj("serp_teardown.py", "summary")[1]

    def test_end_to_end_manual_observation(self):
        summary = self.run_teardown()
        q = summary["queries"][0]
        self.assertEqual(q["query"], "stuckateur musterstadt")
        self.assertEqual(q["organic"]["class"], "with_work")
        self.assertIsNotNone(q["pack"]["gap"])
        bl = json.loads((Path(self.state) / "backlog.json").read_text())
        kinds = {i["gap_factor"] for i in bl["items"]}
        self.assertIn("dedicated_page", kinds)
        ded = next(i for i in bl["items"] if i["gap_factor"] == "dedicated_page")
        self.assertTrue(ded["scope_proposal"])  # premium fixture: no new page, proposal instead
        self.assertEqual(ded["action_type"], "onpage_rewrite")

    def test_unobserved_surfaces_are_not_checked(self):
        summary = self.run_teardown()
        self.assertNotIn("guess", json.dumps(summary))
        td = json.loads(next((Path(self.state) / "teardowns").glob("*/stuckateur-musterstadt.json")).read_text())
        nc = td["surfaces"]["organic"]["gap"]["not_checked"]
        self.assertIn("referring_domains", nc)

    def test_plan_uses_teardown(self):
        self.run_teardown()
        code, plan = self.rj("plan.py", "rank")
        self.assertEqual(code, 0)
        self.assertTrue(plan["cycle"])
        self.assertTrue(all("propose_cmd" in c for c in plan["cycle"]))
        self.assertLessEqual(len(plan["cycle"]), 5)


class SafetyTests(Workspace):
    def test_gbp_refuses_identity_fields(self):
        code, _, err = self.r("gbp.py", "update", "--location", "locations/1", "--mask", "title,storefrontAddress", "--body-file", "x.json")
        self.assertEqual(code, 4)
        self.assertIn("never written", err)

    def test_gbp_write_needs_verified_approval(self):
        (self.repo / "r.txt").write_text("Vielen Dank für Ihre Bewertung.")
        code, _, err = self.r("gbp.py", "reply", "--action", "2026-11-a99", "--account", "accounts/1", "--location", "locations/1",
                              "--review-id", "x", "--text-file", "r.txt")
        self.assertEqual(code, 4)

    def test_leads_reject_pii(self):
        f = self.repo / "ev.jsonl"
        f.write_text('{"channel":"form","name":"Max","source":"google_maps"}\n')
        code, _, _ = self.r("leads.py", "import-events", str(f))
        self.assertEqual(code, 0)
        rows = (Path(self.state) / "leads.jsonl").read_text()
        self.assertNotIn("Max", rows)

    def test_probe_refuses_foreign_host(self):
        code, _, _ = self.r("leads.py", "probe", "https://evil.example/api/contact", "--execute")
        self.assertEqual(code, 4)

    def test_offsite_lint_blocks_link_exchange(self):
        f = self.repo / "pitch.md"
        f.write_text("Wir schlagen einen Linktausch vor.\n")
        self.assertEqual(self.r("offsite.py", "lint", str(f))[0], 1)

    def test_outreach_send_check(self):
        f = self.repo / "pitch.md"
        f.write_text("Guten Tag, wir sind Mitglied der Innung und bitten um einen Eintrag im Verzeichnis.\n")
        self.assertEqual(self.r("offsite.py", "send-check", "--relationship", "member", "--channel", "email", "--sender", "client", "--file", str(f))[0], 0)
        self.assertEqual(self.r("offsite.py", "send-check", "--relationship", "cold", "--channel", "email", "--sender", "client")[0], 4)
        self.assertEqual(self.r("offsite.py", "send-check", "--relationship", "cold", "--channel", "letter", "--sender", "client")[0], 0)
        # agency sending needs send_mode twwa_sends and a recorded mandate
        self.assertEqual(self.r("offsite.py", "send-check", "--relationship", "member", "--channel", "email", "--sender", "twwa")[0], 4)

    def test_review_reply_blocks_incentive(self):
        f = self.repo / "reply.txt"
        f.write_text("Danke! Beim nächsten Auftrag gibt es einen Gutschein über 10 %.\n")
        self.assertEqual(self.r("reviews.py", "reply-lint", str(f))[0], 1)


class MeasureReportTests(Workspace):
    def test_ai_panel_import_and_wilson(self):
        d = self.repo / "ans"
        d.mkdir()
        (d / "p01__chatgpt__1.txt").write_text("Empfehlenswert: Musterbetrieb Stuck und Putz. https://www.gelbeseiten.de/a")
        (d / "p01__chatgpt__2.txt").write_text("Beispiel Putz und Farbe.")
        code, out = self.rj("ai_panel.py", "import", str(d))
        self.assertEqual(code, 0)
        e = out["engines"]["chatgpt"]
        self.assertEqual((e["mentions"], e["runs"]), (1, 2))
        self.assertLess(e["ci95"][0], 0.5)
        self.assertGreater(e["ci95"][1], 0.5)

    def test_report_leads_first_and_no_estimates(self):
        self.r("leads.py", "add", "--channel", "form", "--service", "fassadensanierung", "--town", "Musterstadt", "--date", "2026-11-05")
        self.r("leads.py", "qualify")
        code, _, _ = self.r("report.py", "build", "--month", "2026-11")
        self.assertEqual(code, 0)
        text = (Path(self.state) / "reports" / "2026-11.md").read_text()
        self.assertLess(text.index("## Anfragen"), text.index("## Sichtbarkeit"))
        self.assertIn("1 qualifizierte Anfragen", text)
        self.assertIn("nicht erfasst", text)

    def test_measure_inconclusive_without_window(self):
        code, out = self.rj("measure.py", "evaluate")
        self.assertEqual(code, 0)

    def test_bot_classification(self):
        log = self.repo / "drain.ndjson"
        log.write_text('{"proxy":{"path":"/","userAgent":["Mozilla/5.0 (compatible; Googlebot/2.1)"],"statusCode":200}}\n'
                       '{"proxy":{"path":"/x","userAgent":["OAI-SearchBot/1.0"],"statusCode":404}}\n'
                       '{"proxy":{"path":"/","userAgent":["Mozilla/5.0 Safari"],"statusCode":200}}\n')
        code, out = self.rj("monitor.py", "bots", "--log", str(log))
        self.assertEqual(code, 0)
        self.assertEqual(out["human_requests"], 1)
        self.assertEqual(out["bot_hits"]["OAI-SearchBot"], 1)

    def test_geogrid_points_and_score(self):
        code, pts = self.rj("geogrid.py", "points", "--lat", "48", "--lng", "8", "--size", "3", "--spacing", "1")
        self.assertEqual(len(pts), 9)
        import geogrid  # type: ignore
        s = geogrid.score([{"rank": 1}, {"rank": None}, {"rank": 5}])
        self.assertEqual(s["solv"], round(1 / 3, 3))
        self.assertEqual(s["atrp"], round((1 + 21 + 5) / 3, 2))


if __name__ == "__main__":
    unittest.main()
