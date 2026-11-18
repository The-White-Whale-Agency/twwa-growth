#!/usr/bin/env python3
"""Off-site and citations: German source catalogue by vertical, a ranked plan (tier-1 gaps first, then sources the AI
engines cite where competitors appear, then memberships, partner finders and local press), a tracker in offsite.json,
and an outreach lint. The plugin never submits a listing, sends an e-mail or posts anywhere: the client or TWWA sends, after `send-check` passes.
Banned: link exchanges, paid links without rel=sponsored, PBNs, self-published "best of" lists naming the client."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, spend, state as st  # noqa: E402

BANNED = [(r"link(tausch|exchange)|gegenseitig(e|en)? (verlink|link)|backlink.?tausch", "Linktausch"),
          (r"(kaufen|bezahl\w*|gegen gebühr).{0,40}\b(link|backlink|artikel)|gastartikel gegen", "bezahlter Link ohne Kennzeichnung"),
          (r"\b(die|unsere) (besten|top ?\d+) .{0,40}(in|aus) [A-ZÄÖÜ]", "selbst veröffentlichte Bestenliste"),
          (r"\b(pbn|blognetzwerk|private blog)", "Blognetzwerk"),
          (r"\b(bewertung|rezension).{0,30}(gegen|für) .{0,20}(gutschein|rabatt|geschenk)", "Bewertung gegen Gegenleistung")]


def catalog(vertical: str) -> List[Dict[str, Any]]:
    data = st.load_json(spend.DATA_DIR / "citations-de.json", {}) or {}
    v = "handwerk" if vertical in ("handwerk",) else vertical
    return [s for s in data.get("sources", []) if "*" in s["verticals"] or v in s["verticals"]]


def _tracker(state: Path) -> Dict[str, Any]:
    return st.load_json(state / "offsite.json", {"schema_version": 1, "entries": []}) or {"schema_version": 1, "entries": []}


def plan(state: Path) -> List[Dict[str, Any]]:
    b = st.load_business(state) or {}
    tr = _tracker(state)
    have = {e.get("source_id") for e in tr.get("entries", []) if e.get("status") in ("live", "verified", "listed", "submitted")}
    items = []
    for s in catalog(b.get("vertical") or "other"):
        if s["id"] in have:
            continue
        base = {"1": 1.0, "2": 0.6}.get(str(s["tier"]), 0.8 if s["tier"] == "vertical" else 0.5)
        items.append({"source_id": s["id"], "name": s["name"], "url": s.get("url"), "tier": s["tier"], "cost": s["cost"],
                      "score": base, "why": s.get("why") or "Grundeintrag mit identischen Firmendaten (NAP)",
                      "action_type": "citation" if s["tier"] in (1, 2, "vertical") else "offsite_mention"})
    ai = st.load_latest_snapshot(state, "ai-panel") or {}
    for c in ai.get("cited_domains", [])[:15]:
        if c["domain_type"] in ("directory", "association", "publisher") and not any(c["domain"] in (e.get("url") or "") for e in tr.get("entries", [])):
            hit = next((i for i in items if i.get("url") and c["domain"] in i["url"]), None)
            if hit:
                hit["score"] += 0.5 + 0.1 * c["count"]
                hit["why"] += "; wird in KI-Antworten zitiert (%dx)" % c["count"]
            else:
                items.append({"source_id": "ai:" + c["domain"], "name": c["domain"], "url": "https://" + c["domain"], "tier": "ai_cited",
                              "cost": "prüfen", "score": 0.7 + 0.1 * c["count"], "why": "in KI-Antworten zitiert, Wettbewerber dort präsent",
                              "action_type": "citation" if c["domain_type"] == "directory" else "offsite_mention"})
    for m in b.get("memberships", []):
        items.append({"source_id": "member:" + st.slugify(m.get("name", "")), "name": m.get("name"), "url": m.get("url"), "tier": "membership",
                      "cost": "Mitgliedschaft", "score": 0.9, "why": "echte Mitgliedschaft: Eintrag und Link im Mitgliederverzeichnis anfragen",
                      "action_type": "offsite_mention"})
    return sorted(items, key=lambda i: -i["score"])


def cmd_catalog(args: Any) -> int:
    rows = catalog(args.vertical)
    cli.emit(rows, args, "\n".join("%-28s tier %-9s %s" % (r["name"], r["tier"], r["cost"]) for r in rows))
    return cli.EXIT_OK


def cmd_plan(args: Any) -> int:
    state = st.require_state(args)
    rows = plan(state)[: args.top]
    cli.emit(rows, args, "\n".join("%.2f  %-30s %s" % (r["score"], r["name"][:30], r["why"]) for r in rows))
    return cli.EXIT_OK


def cmd_track(args: Any) -> int:
    state = st.require_state(args)
    tr = _tracker(state)
    e = next((x for x in tr["entries"] if x.get("source_id") == args.source_id), None)
    if not e:
        e = {"source_id": args.source_id, "created": st.today()}
        tr["entries"].append(e)
    for k in ("url", "status", "kind", "note"):
        v = getattr(args, k)
        if v is not None:
            e[k] = v
    e["updated"] = st.today()
    st.save_json(state / "offsite.json", tr)
    cli.emit(e, args, "%s: %s" % (args.source_id, e.get("status")))
    return cli.EXIT_OK


def lint(text: str) -> List[Dict[str, Any]]:
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for rx, label in BANNED:
            if re.search(rx, line, re.I):
                out.append({"line": n, "level": "block", "rule": label, "snippet": line.strip()[:120]})
    try:
        from legal_lint import lint_text  # type: ignore
        out += [{"line": i.get("line"), "level": i.get("level"), "rule": i.get("rule"), "snippet": i.get("snippet")} for i in lint_text(text, "outreach")]
    except Exception:  # noqa: BLE001
        pass
    return out


# Legal channel rules for outreach in Germany (summary, not legal advice; references/outreach-law-de.md).
# E-mail, messenger and contact forms used for advertising need prior express consent, also between businesses
# (§ 7 Abs. 2 Nr. 2 UWG). Asking a third party to list or mention the client is advertising for the client.
RELATIONSHIPS = {
    "member": ("e-mail ok: request inside an existing membership (Innung, Kammer, Verband)", ["email", "phone", "letter", "portal"]),
    "partner": ("e-mail ok: existing business relationship (manufacturer, supplier, partner programme)", ["email", "phone", "letter", "portal"]),
    "invited": ("e-mail ok: the recipient publicly invites submissions (form or address for suggestions); use exactly that channel", ["form", "email", "letter"]),
    "press": ("press note with real local news to an editorial address: generally accepted; no sales wording, unsubscribe line", ["email", "letter", "phone"]),
    "listing": ("self-service entry on the directory's own sign-up form; no message needed", ["portal"]),
    "cold": ("no e-mail, messenger or contact form: no consent. Use a postal letter, or a phone call to the business only where interest can be presumed", ["letter", "phone"]),
}


def send_check(cfg: Dict[str, Any], relationship: str, channel: str, sender: str) -> Dict[str, Any]:
    o = cfg.get("outreach") or {}
    mode = o.get("send_mode", "draft_only")
    problems = []
    why, allowed = RELATIONSHIPS[relationship]
    if channel not in allowed:
        problems.append("Kanal %s ist für Beziehung '%s' nicht zulässig: %s" % (channel, relationship, why))
    if sender == "twwa":
        if mode != "twwa_sends":
            problems.append("outreach.send_mode ist '%s', nicht 'twwa_sends'" % mode)
        if not (o.get("mandate") or {}).get("granted"):
            problems.append("kein schriftlicher Auftrag des Kunden erfasst (outreach.mandate)")
    if sender == "client" and mode == "draft_only":
        pass  # the client always may send his own mail; draft_only only means the plugin itself sends nothing
    return {"relationship": relationship, "channel": channel, "sender": sender, "allowed": not problems, "rule_de": why,
            "problems": problems, "requirements_de": [
                "Absender klar: Name des Betriebs%s, vollständige Signatur mit Impressumsangaben" % (" und „im Auftrag durch The White Whale Agency“" if sender == "twwa" else ""),
                "ein Satz zum Widerspruch: „Falls Sie keine weiteren Nachrichten wünschen, genügt eine kurze Antwort.“",
                "keine Nachfass-Serie: höchstens eine Erinnerung, nur bei member/partner/invited",
                "Versand protokollieren: offsite.py track <id> --status submitted"]}


def cmd_send_check(args: Any) -> int:
    state = st.require_state(args)
    st.require_not_stopped(state)
    issues = lint(Path(args.file).read_text(encoding="utf-8")) if args.file else []
    res = send_check(st.load_config(state), args.relationship, args.channel, args.sender)
    if any(i["level"] == "block" for i in issues):
        res["allowed"] = False
        res["problems"].append("Text verletzt Regeln: %s" % ", ".join(sorted({i["rule"] for i in issues if i["level"] == "block"})))
    lines = ["%s: %s" % ("FREIGEGEBEN" if res["allowed"] else "GESPERRT", res["rule_de"])] + ["  - %s" % p for p in res["problems"]]
    if res["allowed"]:
        lines += ["Pflicht:"] + ["  - %s" % r for r in res["requirements_de"]]
    lines.append("Hinweis, keine Rechtsberatung. Der Versand erfolgt durch einen Menschen, nie durch das Plugin.")
    cli.emit(res, args, "\n".join(lines))
    return cli.EXIT_OK if res["allowed"] else cli.EXIT_BLOCKED


def cmd_lint(args: Any) -> int:
    issues = lint(Path(args.file).read_text(encoding="utf-8"))
    cli.emit(issues, args, "\n".join("Z.%s [%s] %s: %s" % (i["line"], i["level"], i["rule"], i["snippet"]) for i in issues) or "Ok.")
    return cli.EXIT_FAIL if any(i["level"] == "block" for i in issues) else cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  offsite.py plan --top 10")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "catalog", "German sources for a vertical")
    sp.add_argument("--vertical", default="handwerk")
    sp.set_defaults(fn=cmd_catalog)
    sp = cli.add_sub(subs, "plan", "ranked off-site opportunities")
    sp.add_argument("--top", type=int, default=15)
    sp.set_defaults(fn=cmd_plan)
    sp = cli.add_sub(subs, "track", "add or update an entry in offsite.json")
    sp.add_argument("source_id")
    sp.add_argument("--url", default=None)
    sp.add_argument("--status", choices=("planned", "drafted", "submitted", "listed", "live", "verified", "rejected"), default=None)
    sp.add_argument("--kind", choices=("citation", "membership", "press", "mention", "partner"), default=None)
    sp.add_argument("--note", default=None)
    sp.set_defaults(fn=cmd_track)
    sp = cli.add_sub(subs, "send-check", "may this draft go out, via this channel, from the client or from TWWA? (exit 4 = no)")
    sp.add_argument("--relationship", required=True, choices=sorted(RELATIONSHIPS))
    sp.add_argument("--channel", required=True, choices=("email", "form", "phone", "letter", "portal"))
    sp.add_argument("--sender", required=True, choices=("client", "twwa"))
    sp.add_argument("--file", default=None, help="the draft; it is linted too")
    sp.set_defaults(fn=cmd_send_check)
    sp = cli.add_sub(subs, "lint", "outreach draft lint (banned tactics)")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_lint)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
