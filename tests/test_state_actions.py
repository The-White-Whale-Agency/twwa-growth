from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import twwa_testutil as tu
import twwa_state

MARKER = "- " + "APPROVED"  # never written as a line in any file


class TestScope(unittest.TestCase):
    def test_real_format_fixture(self):
        info = twwa_state.read_scope(tu.FIX / "repo", {})
        self.assertEqual(info["tier"], "premium")
        self.assertEqual(info["scope_file"], "scope.md")
        self.assertEqual(info["exceptions"], [])

    def test_exception_lines_parsed_from_text(self):
        text = "# Рамки тарифа: BASIC (x)\n\n## Одобренные исключения\n%s: api — Inhaber, 2026-11-01, Formular\n  %s: gsap — Inhaber\n" % (MARKER, MARKER)
        info = twwa_state.parse_scope_text(text)
        self.assertEqual(info["tier"], "basic")
        self.assertEqual([e["name"] for e in info["exceptions"]], ["api", "gsap"])
        self.assertTrue(twwa_state.scope_check(info, None, adds_api_route=True)["in_scope"])
        self.assertFalse(twwa_state.scope_check(info, "new_page")["in_scope"])

    def test_scope_rules(self):
        prem = {"tier": "premium", "exceptions": []}
        self.assertFalse(twwa_state.scope_check(prem, "new_page")["in_scope"])
        self.assertTrue(twwa_state.scope_check(prem, "onpage_rewrite")["in_scope"])
        self.assertFalse(twwa_state.scope_check(prem, None, adds_dependency=["@sanity/client"])["in_scope"])
        self.assertTrue(twwa_state.scope_check(prem, None, adds_dependency=["three"])["in_scope"])
        self.assertFalse(twwa_state.scope_check({"tier": "basic", "exceptions": []}, None, adds_dependency=["three"])["in_scope"])
        self.assertTrue(twwa_state.scope_check({"tier": "scale", "exceptions": []}, "new_page")["in_scope"])
        unk = twwa_state.scope_check({"tier": "unknown", "exceptions": []}, "new_page")
        self.assertEqual(unk["effective_tier"], "premium")
        self.assertIn("note", unk)

    def test_scope_cli_exit_4(self):
        c = tu.TempClient()
        try:
            code, out = tu.run_json("twwa_state.py", "scope", "check", "--type", "new_page", "--state", str(c.state))
            self.assertEqual(code, 4)
            self.assertFalse(out["in_scope"])
            code, _ = tu.run_json("twwa_state.py", "scope", "check", "--type", "tech_fix", "--state", str(c.state))
            self.assertEqual(code, 0)
            self.assertNotIn(MARKER + ":", (c.repo / "scope.md").read_text(encoding="utf-8"))
        finally:
            c.cleanup()


class TestStateCli(unittest.TestCase):
    def test_init_idempotent_and_doctor(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            shutil.copy(tu.FIX / "repo/astro.config.mjs", repo / "astro.config.mjs")
            shutil.copy(tu.FIX / "repo/scope.md", repo / "scope.md")
            code, out = tu.run_json("twwa_state.py", "init", "--repo", str(repo))
            self.assertEqual(code, 0)
            self.assertIn("config.json", out["created"])
            cfg = json.loads((repo / ".twwa-growth/config.json").read_text(encoding="utf-8"))
            self.assertEqual(cfg["tier"], "premium")
            self.assertEqual(cfg["site"]["url"], "https://www.musterbetrieb.example")
            code, out = tu.run_json("twwa_state.py", "init", "--repo", str(repo))
            self.assertEqual(out["created"], [])
            st = str(repo / ".twwa-growth")
            self.assertEqual(tu.run("twwa_state.py", "doctor", "--state", st)[0], 0)
            (repo / ".twwa-growth/drafts/pages").mkdir(parents=True)
            (repo / ".twwa-growth/reports/x.html").write_text("<p>x</p>", encoding="utf-8")
            (repo / ".twwa-growth/out/ok.html").write_text("<p>ok</p>", encoding="utf-8")
            code, out = tu.run_json("twwa_state.py", "doctor", "--state", st)
            self.assertEqual(code, 1)
            checks = sorted(p["check"] for p in out["problems"])
            self.assertEqual(checks, ["forbidden_dir", "html_outside_out"])

    def test_approved_line_regex(self):
        self.assertTrue(twwa_state.APPROVED_LINE.match(MARKER + ": api"))
        self.assertTrue(twwa_state.APPROVED_LINE.match("   " + MARKER + ": api"))
        self.assertFalse(twwa_state.APPROVED_LINE.match("<!-- format: " + MARKER + ": x -->"))

    def test_fixture_state_valid(self):
        self.assertEqual(tu.run("twwa_state.py", "validate", "--state", str(tu.FIX / ".twwa-growth"))[0], 0)
        self.assertEqual(tu.run("twwa_state.py", "doctor", "--state", str(tu.FIX / ".twwa-growth"))[0], 0)

    def test_validate_rejects_pricing(self):
        c = tu.TempClient()
        try:
            cfg = json.loads((c.state / "config.json").read_text(encoding="utf-8"))
            cfg["pricing"] = {"monthly": 1}
            (c.state / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
            code, out = tu.run_json("twwa_state.py", "validate", "--state", str(c.state))
            self.assertEqual(code, 1)
            self.assertTrue(any("pricing" in e for e in out["errors"]["config.json"]))
        finally:
            c.cleanup()

    def test_no_state_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()
            code, _, err = tu.run("twwa_state.py", "status", cwd=d)
            self.assertEqual(code, 2)
            self.assertIn("init", err)

    def test_detect(self):
        code, out = tu.run_json("twwa_state.py", "detect", "--repo", str(tu.FIX / "repo"))
        self.assertEqual(code, 0)
        self.assertEqual(out["astro"]["trailingSlash"], "never")
        self.assertEqual(out["vercel"]["noindex_hosts"], ["staging.musterbetrieb.example"])
        self.assertEqual(out["form_handlers"], ["api/contact.js"])
        self.assertEqual(out["content_routes"], [])


class TestActions(unittest.TestCase):
    def setUp(self):
        self.c = tu.TempClient(git=True)
        self.s = str(self.c.state)

    def tearDown(self):
        self.c.cleanup()

    def propose(self, *args):
        return tu.run_json("twwa_actions.py", "propose", "--state", self.s, *args)

    def test_caps_and_stop(self):
        made = []
        for i in range(4):
            code, out = self.propose("--type", "tech_fix", "--title-de", "Technik %d" % i, "--pages", "/t%d" % i)
            self.assertEqual(code, 0, out)
            made.append(out["action_id"])
        self.assertNotIn("2026-11-a02", made)  # drafts/2026-11-a02 already exists in the fixture
        code, out = self.propose("--type", "tech_fix", "--title-de", "Technik 9", "--pages", "/t9")
        self.assertEqual(code, 4)
        self.assertIn("caps", out["blocked"])
        tu.run("twwa_actions.py", "close", made[0], "--outcome", "rejected", "--reason", "Test", "--state", self.s)
        code, out = self.propose("--type", "tech_fix", "--title-de", "Technik 9", "--pages", "/t9")
        self.assertEqual(code, 0)
        code, out = self.propose("--type", "tech_fix", "--title-de", "Technik 9", "--pages", "/t9")
        self.assertTrue(out.get("unchanged"))
        tu.run("twwa_actions.py", "stop", "--reason", "Test", "--state", self.s)
        self.assertEqual(self.propose("--type", "tech_fix", "--title-de", "X", "--pages", "/x")[0], 4)
        self.assertEqual(tu.run("twwa_actions.py", "resume", "--by", "Operator", "--reason", "Test", "--state", self.s)[0], 0)

    def test_gbp_pacing_and_cooldown(self):
        self.assertEqual(self.propose("--type", "gbp_identity_edit", "--title-de", "Hauptkategorie", "--risk", "R2")[0], 0)
        code, out = self.propose("--type", "gbp_identity_edit", "--title-de", "Telefon", "--risk", "R2")
        self.assertEqual(code, 4)
        self.assertTrue(any("48" in e for e in out["errors"]))
        self.assertEqual(self.propose("--type", "onpage_rewrite", "--title-de", "Titel", "--pages", "/")[0], 0)
        self.assertEqual(self.propose("--type", "cro_change", "--title-de", "CTA", "--pages", "/")[0], 4)

    def test_scope_proposal(self):
        code, out = self.propose("--type", "new_page", "--title-de", "Seite Nachbarstadt", "--adds-page", "--as-proposal", "--hypothesis", "Eigene Seite")
        self.assertEqual(code, 0)
        text = Path(out["proposal"]).read_text(encoding="utf-8")
        self.assertIn("SCALE", text)
        self.assertNotRegex(text, r"(€|EUR|Euro|Preis)")
        code, out = tu.run_json("twwa_actions.py", "list", "--state", self.s)
        self.assertEqual([a["state"] for a in out["actions"] if a["type"] == "new_page"], ["blocked"])
        self.assertEqual(self.propose("--type", "new_page", "--title-de", "Seite Beispielort", "--adds-page")[0], 4)

    def test_approve_verify_hash_and_rollback(self):
        c = self.c
        c.git("checkout", "-q", "-b", "twwa/2026-11-a01")
        p = c.repo / "api/contact.js"
        p.write_text(p.read_text(encoding="utf-8").replace("[Quelle: ${quelle}]", "[Quelle: ${quelle}] [Seite: Start]"), encoding="utf-8")
        c.git("add", "api/contact.js")
        c.git("commit", "-q", "-m", "Quelle im Betreff [twwa:2026-11-a01]")
        c.git("checkout", "-q", "main")
        self.assertEqual(tu.run("twwa_actions.py", "verify", "2026-11-a01", "--state", self.s)[0], 4)
        code, out = tu.run_json("twwa_actions.py", "approve", "2026-11-a01", "--role", "twwa", "--by", "Operator", "--channel", "pr", "--evidence", "PR 1", "--state", self.s)
        self.assertEqual(code, 0)
        self.assertTrue(out["verify"]["ok"])
        code, out = tu.run_json("twwa_actions.py", "verify", "2026-11-a01", "--state", self.s)
        self.assertEqual(code, 0)
        self.assertIn("api/contact.js", out["artifacts"])
        # a change on the branch after approval invalidates it
        c.git("checkout", "-q", "twwa/2026-11-a01")
        p.write_text(p.read_text(encoding="utf-8") + "\n// geaendert\n", encoding="utf-8")
        c.git("add", "api/contact.js")
        c.git("commit", "-q", "-m", "nachtrag [twwa:2026-11-a01]")
        c.git("checkout", "-q", "main")
        code, out = tu.run_json("twwa_actions.py", "verify", "2026-11-a01", "--state", self.s)
        self.assertEqual(code, 4)
        self.assertIn("api/contact.js", out["changed"])
        self.assertEqual(tu.run("twwa_actions.py", "ship", "2026-11-a01", "--commit", "HEAD", "--state", self.s)[0], 4)
        tu.run("twwa_actions.py", "approve", "2026-11-a01", "--role", "twwa", "--by", "Operator", "--channel", "pr", "--evidence", "PR 1 v2", "--state", self.s)
        c.git("merge", "-q", "--no-ff", "--no-edit", "twwa/2026-11-a01")
        merge_parent = c.git("rev-parse", "HEAD^2")
        first = c.git("rev-parse", "HEAD^2^")
        code, out = tu.run_json("twwa_actions.py", "ship", "2026-11-a01", "--commit", first, "--commit", merge_parent, "--state", self.s)
        self.assertEqual(code, 0, out)
        before = (c.repo / "api/contact.js").read_text(encoding="utf-8")
        code, out = tu.run_json("twwa_actions.py", "rollback", "2026-11-a01", "--state", self.s)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["branch"], "twwa/rollback-2026-11-a01")
        self.assertEqual(len(out["reverted"]), 2)
        self.assertEqual(c.git("rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual((c.repo / "api/contact.js").read_text(encoding="utf-8"), before)
        reverted = c.git("show", "twwa/rollback-2026-11-a01:api/contact.js")
        self.assertNotIn("[Seite: Start]", reverted)
        self.assertEqual(c.git("remote"), "")  # nothing to push to, nothing pushed
        code, out = tu.run_json("twwa_actions.py", "rollback", "2026-11-a01", "--state", self.s)
        self.assertTrue(out["existing"])
        self.assertEqual(tu.run("twwa_actions.py", "rollback", "2026-11-a01", "--merge", "--state", self.s)[0], 0)  # existing branch: reports only

    def test_owner_approval_required_for_r2_and_packet(self):
        code, out = self.propose("--type", "onpage_rewrite", "--title-de", "Titel mit Ort", "--pages", "/", "--hypothesis", "Wenn der Titel den Ort nennt, steigt die Klickrate.")
        aid = out["action_id"]
        d = self.c.state / "drafts" / aid
        d.mkdir(parents=True, exist_ok=True)
        (d / "titel.md").write_text("Stuckateur in Musterstadt | Musterbetrieb\n", encoding="utf-8")
        tu.run("twwa_actions.py", "approve", aid, "--role", "twwa", "--by", "Operator", "--channel", "pr", "--evidence", "PR 2", "--state", self.s)
        code, out = tu.run_json("twwa_actions.py", "verify", aid, "--state", self.s)
        self.assertEqual(code, 4)
        self.assertTrue(any("owner" in p for p in out["problems"]))
        code, out = tu.run_json("twwa_actions.py", "packet", aid, "--state", self.s)
        self.assertEqual(code, 0)
        self.assertTrue(out["path"].endswith("out/packets/%s.md" % aid))
        self.assertIn("So geben Sie frei", out["text"])
        self.assertNotIn("APPROVED", out["text"])
        tu.run("twwa_actions.py", "approve", aid, "--role", "owner", "--by", "Max Mustermann", "--channel", "whatsapp", "--evidence", "Nachricht 2026-11-17 09:12", "--state", self.s)
        self.assertEqual(tu.run("twwa_actions.py", "verify", aid, "--state", self.s)[0], 0)
        (d / "titel.md").write_text("Stuckateur in Musterstadt | Musterbetrieb GmbH\n", encoding="utf-8")
        self.assertEqual(tu.run("twwa_actions.py", "verify", aid, "--state", self.s)[0], 4)
        self.assertEqual(tu.run("twwa_state.py", "doctor", "--state", self.s)[0], 0)

    def test_due(self):
        events = [{"ts": "2026-10-01T10:00:00Z", "action_id": "2026-10-a01", "event": "proposed", "type": "tech_fix", "title_de": "X", "risk": "R1", "window_days": 28},
                  {"ts": "2026-10-02T10:00:00Z", "action_id": "2026-10-a01", "event": "shipped", "commits": ["abc"]}]
        with (self.c.state / "actions.jsonl").open("a", encoding="utf-8") as fh:
            for e in events:
                fh.write(json.dumps(e) + "\n")
        code, out = tu.run_json("twwa_actions.py", "due", "--state", self.s)
        self.assertEqual([d["action_id"] for d in out["due"]], ["2026-10-a01"])
        code, out = tu.run_json("twwa_actions.py", "due", "--date", "2026-10-20", "--state", self.s)
        self.assertEqual(out["due"], [])


if __name__ == "__main__":
    unittest.main()
