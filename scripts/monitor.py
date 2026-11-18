#!/usr/bin/env python3
"""Scheduled monitors (spec 12b): the legitimate parts of what agencies run on their own bots, as scripts for a
GitHub Actions workflow, a Claude Code routine or launchd. No own server. crawl = weekly self-crawl plus regression
guard; ranks = GSC positions plus provider observations; ai = prompt panel; bots = crawler hits from a Vercel log
drain export (Googlebot, Bingbot, OAI-SearchBot, ChatGPT-User, GPTBot, PerplexityBot, ClaudeBot, Claude-SearchBot),
time to first crawl of new pages; competitors = change detection on the teardown winners.
Banned and never implemented: click bots, CTR manipulation, traffic bots, fake engagement, scraping Google at scale.
Reports count humans only; bot hits are crawl activity."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, htmlx, http, state as st  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
BOTS = [("Googlebot", r"Googlebot"), ("Bingbot", r"bingbot"), ("OAI-SearchBot", r"OAI-SearchBot"), ("ChatGPT-User", r"ChatGPT-User"),
        ("GPTBot", r"GPTBot"), ("PerplexityBot", r"PerplexityBot"), ("Perplexity-User", r"Perplexity-User"), ("ClaudeBot", r"ClaudeBot"),
        ("Claude-SearchBot", r"Claude-SearchBot"), ("Applebot", r"Applebot"), ("YandexBot", r"YandexBot")]
VERIFY_DNS = {"Googlebot": (".googlebot.com", ".google.com"), "Bingbot": (".search.msn.com",), "Applebot": (".applebot.apple.com",)}


def _run(script: str, *args: str) -> Dict[str, Any]:
    p = subprocess.run([sys.executable, str(SCRIPTS / script)] + list(args) + ["--json"], capture_output=True, text=True)
    try:
        out = json.loads(p.stdout or "null")
    except json.JSONDecodeError:
        out = None
    return {"exit": p.returncode, "out": out, "err": (p.stderr or "")[-500:]}


def classify(ua: str) -> str:
    for name, rx in BOTS:
        if re.search(rx, ua or ""):
            return name
    return "bot_other" if re.search(r"bot|crawl|spider|slurp|fetch", ua or "", re.I) else "human"


def verify_ip(bot: str, ip: str) -> bool:
    import socket
    suf = VERIFY_DNS.get(bot)
    if not suf or not ip:
        return False
    try:
        host = socket.gethostbyaddr(ip)[0]
        return host.endswith(suf) and ip in socket.gethostbyname_ex(host)[2]
    except OSError:
        return False


def bots(state: Path, log_file: str, verify: bool = False) -> Dict[str, Any]:
    hits: Dict[str, Dict[str, int]] = {}
    errors: Dict[str, int] = {}
    first: Dict[str, Dict[str, str]] = {}
    humans = 0
    for line in Path(log_file).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        req = e.get("proxy") or e.get("request") or e
        ua = req.get("userAgent") or req.get("user_agent") or (req.get("headers") or {}).get("user-agent") or ""
        if isinstance(ua, list):
            ua = ua[0] if ua else ""
        path = req.get("path") or req.get("url") or e.get("path") or ""
        status = int(req.get("statusCode") or e.get("statusCode") or e.get("status") or 0)
        ts = e.get("timestamp") or e.get("ts") or ""
        who = classify(ua)
        if who == "human":
            humans += 1
            continue
        if verify and who in VERIFY_DNS and not verify_ip(who, req.get("clientIp") or e.get("ip") or ""):
            who += " (unverified)"
        hits.setdefault(who, {})
        hits[who][path] = hits[who].get(path, 0) + 1
        if status >= 400:
            errors["%s %s %s" % (who, status, path)] = errors.get("%s %s %s" % (who, status, path), 0) + 1
        f = first.setdefault(path, {})
        if who not in f or str(ts) < f[who]:
            f[who] = str(ts)
    import twwa_actions  # type: ignore
    ttfc = []
    for a in twwa_actions.fold(st.read_jsonl(state / "actions.jsonl")).values():
        if a.get("type") == "new_page" and a.get("shipped_at"):
            for p in a.get("pages_affected") or []:
                g = (first.get(p) or {}).get("Googlebot")
                ttfc.append({"page": p, "shipped": a["shipped_at"], "first_googlebot": g, "first_bingbot": (first.get(p) or {}).get("Bingbot")})
    return {"human_requests": humans, "bot_hits": {k: sum(v.values()) for k, v in hits.items()},
            "top_paths": {k: sorted(v.items(), key=lambda x: -x[1])[:10] for k, v in hits.items()},
            "errors_to_bots": sorted(errors.items(), key=lambda x: -x[1])[:20], "time_to_first_crawl": ttfc}


def competitors(state: Path, allow_private: bool = False) -> Dict[str, Any]:
    tds = sorted(state.glob("teardowns/*/*.json"))
    urls = set()
    for f in tds[-40:]:
        if f.name == "summary.json":
            continue
        for w in (((st.load_json(f) or {}).get("surfaces") or {}).get("organic") or {}).get("winners", []) or []:
            if w.get("domain_type") == "business" and w.get("url"):
                urls.add(w["url"])
    prev = st.load_latest_snapshot(state, "competitors-monitor") or {}
    prev_pages = {p["url"]: p for p in prev.get("pages", [])}
    pages, changes = [], []
    for u in sorted(urls):
        try:
            if not http.robots_allows(u, allow_private=allow_private):
                continue
            r = http.fetch(u, allow_private=allow_private)
        except http.FetchError:
            continue
        if not r.ok:
            continue
        pg = htmlx.parse(r.text, r.url)
        h1 = pg.h1() if callable(pg.h1) else pg.h1
        rec = {"url": u, "title": pg.title, "h1": h1[:1], "words": len((pg.text or "").split()),
               "hash": hashlib.sha256((pg.text or "").encode()).hexdigest()[:16]}
        pages.append(rec)
        old = prev_pages.get(u)
        if old:
            for k in ("title", "h1"):
                if old.get(k) != rec.get(k):
                    changes.append({"url": u, "field": k, "before": old.get(k), "after": rec.get(k)})
            if old.get("hash") != rec["hash"] and abs((old.get("words") or 0) - rec["words"]) > 150:
                changes.append({"url": u, "field": "content", "before": old.get("words"), "after": rec["words"]})
    return {"pages": pages, "changes": changes}


def cmd_crawl(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    site = args.url or b.get("url")
    res = {"live": _run("site_audit.py", "live", site, "--write-snapshot", "--with-graph", "--state", str(state)),
           "regression": _run("regression_guard.py", "run", "--state", str(state))}
    p1 = res["regression"]["exit"] == 1
    cli.emit({k: {"exit": v["exit"]} for k, v in res.items()}, args, "crawl: site_audit exit %s, regression_guard exit %s" % (res["live"]["exit"], res["regression"]["exit"]))
    return cli.EXIT_FAIL if p1 else cli.EXIT_OK


def cmd_ranks(args: Any) -> int:
    state = st.require_state(args)
    gsc = st.load_latest_snapshot(state, "gsc")
    targets = [q.lower() for c in (st.load_json(state / "keywords.json", {}) or {}).get("clusters", []) if c.get("target") for q in c.get("queries", [])]
    out = {"gsc": [], "provider": None}
    if gsc:
        for q in targets:
            rows = [r for r in gsc.get("rows", []) if (r.get("query") or "").lower() == q]
            imp = sum(r["impressions"] for r in rows)
            out["gsc"].append({"query": q, "impressions": imp, "position": round(sum(r["position"] * r["impressions"] for r in rows) / imp, 1) if imp else None})
    obs = _run("serp_teardown.py", "observe", "--state", str(state), *(["--execute"] if args.execute else []))
    out["provider"] = {"exit": obs["exit"], "result": obs["out"]}
    path = connect.write_snapshot(state, "ranks", out, "api" if args.execute else "mixed")
    cli.emit(out, args, "\n".join("%-40s Pos. %s (%s Impr.)" % (r["query"], r["position"], r["impressions"]) for r in out["gsc"]) + "\n-> %s" % path)
    return cli.EXIT_OK


def cmd_ai(args: Any) -> int:
    state = st.require_state(args)
    r = _run("ai_panel.py", "run", "--state", str(state), *(["--execute"] if args.execute else []))
    cli.emit(r["out"], args, "ai panel exit %s" % r["exit"])
    return cli.EXIT_OK if r["exit"] in (0, 3) else r["exit"]


def cmd_bots(args: Any) -> int:
    state = st.require_state(args)
    if not args.log:
        cli.emit({"status": "not_checked"}, args, "bots: nicht geprüft (kein Log-Export; Vercel log drain als NDJSON speichern und mit --log übergeben).")
        return cli.EXIT_OK
    res = bots(state, args.log, args.verify)
    path = connect.write_snapshot(state, "bots", res, "manual")
    cli.emit(res, args, "Bot-Zugriffe: %s; Menschen: %d; Fehler an Bots: %d\n-> %s" % (res["bot_hits"], res["human_requests"], len(res["errors_to_bots"]), path))
    return cli.EXIT_OK


def cmd_competitors(args: Any) -> int:
    state = st.require_state(args)
    if args.fixture:
        http.use_fixture(args.fixture)
    res = competitors(state, args.allow_private)
    path = connect.write_snapshot(state, "competitors-monitor", res, "api")
    cli.emit(res, args, "%d Gewinnerseiten beobachtet, %d Änderungen.\n%s\n-> %s" % (len(res["pages"]), len(res["changes"]),
                                                                                      "\n".join("  %s %s: %s -> %s" % (c["url"], c["field"], c["before"], c["after"]) for c in res["changes"]), path))
    return cli.EXIT_OK


def cmd_all(args: Any) -> int:
    state = st.require_state(args)
    st.require_not_stopped(state)
    codes = {}
    for name, fn in (("crawl", cmd_crawl), ("ranks", cmd_ranks), ("ai", cmd_ai), ("bots", cmd_bots), ("competitors", cmd_competitors)):
        for k, v in (("url", None), ("execute", getattr(args, "execute", False)), ("log", getattr(args, "log", None)), ("verify", False),
                     ("fixture", None), ("allow_private", False)):
            if not hasattr(args, k):
                setattr(args, k, v)
        try:
            codes[name] = fn(args)
        except SystemExit as ex:
            codes[name] = ex.code
    print(json.dumps({"monitors": codes}), file=sys.stderr)
    return cli.EXIT_FAIL if codes.get("crawl") == 1 else cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  monitor.py all --log drains/2026-11-17.ndjson")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "crawl", "self-crawl plus regression guard")
    sp.add_argument("--url", default=None)
    sp.set_defaults(fn=cmd_crawl)
    sp = cli.add_sub(subs, "ranks", "target query positions")
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_ranks)
    sp = cli.add_sub(subs, "ai", "prompt panel on schedule")
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_ai)
    sp = cli.add_sub(subs, "bots", "crawler activity from a log drain export (NDJSON)")
    sp.add_argument("--log", default=None)
    sp.add_argument("--verify", action="store_true", help="reverse-DNS verification for Googlebot, Bingbot, Applebot")
    sp.set_defaults(fn=cmd_bots)
    sp = cli.add_sub(subs, "competitors", "change detection on teardown winners")
    sp.add_argument("--fixture", default=None)
    sp.add_argument("--allow-private", action="store_true")
    sp.set_defaults(fn=cmd_competitors)
    sp = cli.add_sub(subs, "all", "every monitor (never merges, never writes to GBP, spends only with --execute under the cap)")
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--log", default=None)
    sp.set_defaults(fn=cmd_all)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
