#!/usr/bin/env python3
"""AI prompt panel (spec 11): generate German buyer prompts, run them per engine through the provider layer (or
import answers collected by hand), score mention rate with Wilson 95% intervals, cited domains, and gaps for
off-site work. Never reports an "AI ranking position": answers vary run to run, so only rates with intervals
count, and movement is claimed only when intervals separate or 4 measurements trend the same way."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, http, providers as pv, state as st  # noqa: E402
from twwa_lib.stats import intervals_overlap, wilson  # noqa: E402
from twwa_lib.textde import fold_umlauts, norm_name  # noqa: E402

ENGINES = ("chatgpt", "gemini", "ai_mode", "perplexity")
MIX = (("recommendation", 0.40), ("need", 0.25), ("cost_process", 0.20), ("brand", 0.15))


def generate(b: Dict[str, Any], cap: int) -> List[Dict[str, Any]]:
    trade = (b.get("trade") or "Handwerker").replace("_", " ").capitalize()
    towns = [t["town"] for t in sorted(b.get("service_area", []), key=lambda t: t.get("drive_minutes") or 0)][:3] or [(b.get("address") or {}).get("city")]
    svcs = sorted(b.get("services", []), key=lambda s: s.get("priority", 9))
    name = norm_name(b.get("name"), True).title() if b.get("name") else None
    pools = {
        "recommendation": [t % (trade, town) for town in towns for t in (
            "Welchen %s in %s kannst du empfehlen?", "Wer ist ein guter %s in %s?", "Ich suche einen zuverlässigen %s in %s. Wen würdest du nehmen?")]
        + ["Welcher Betrieb in %s ist gut für %s?" % (town, s["name"]) for town in towns[:2] for s in svcs[:3]],
        "need": ["Wer hilft in %s bei %s?" % (towns[0], n) for s in svcs for n in s.get("needs", [])]
        + ["Ich brauche %s in %s. Worauf sollte ich achten und wen kann ich fragen?" % (s["name"], towns[0]) for s in svcs[:3]],
        "cost_process": ["Was kostet %s in %s ungefähr?" % (s["name"], towns[0]) for s in svcs[:3]]
        + ["Wie läuft %s ab und wie lange dauert das in %s?" % (s["name"], towns[0]) for s in svcs[:2]],
        "brand": (["Was weißt du über %s in %s?" % (name, towns[0]), "Ist %s in %s empfehlenswert?" % (name, towns[0]),
                   "Welche Erfahrungen gibt es mit %s?" % name] if name else []),
    }
    out, n = [], 0
    for cls, share in MIX:
        k = max(1, round(cap * share))
        for text in pools[cls][:k]:
            n += 1
            town = next((t for t in towns if t and t in text), towns[0])
            out.append({"id": "p%02d" % n, "text": text, "class": cls, "location": town})
    return out[:cap]


def _names(state: Path, b: Dict[str, Any]) -> Dict[str, List[str]]:
    def variants(n: str) -> List[str]:
        core = norm_name(n, True)
        return [v for v in {core, " ".join(core.split()[:2])} if len(v) > 3]
    comps = (st.load_json(state / "competitors.json", {}) or {}).get("competitors", [])
    out = {"__client__": variants(b.get("name") or "")}
    for c in comps:
        if c.get("name"):
            out[c["name"]] = variants(c["name"])
    return out


def _mentioned(text: str, variants: List[str]) -> bool:
    t = fold_umlauts(norm_name(text))
    return any(fold_umlauts(v) in t for v in variants)


def score(state: Path, runs: List[Dict[str, Any]], b: Dict[str, Any]) -> Dict[str, Any]:
    from serp_teardown import domain_type, host  # type: ignore
    names = _names(state, b)
    client_host = host(b.get("url"))
    per_engine: Dict[str, Dict[str, Any]] = {}
    cited: Dict[str, int] = {}
    named: Dict[str, int] = {}
    for r in runs:
        e = per_engine.setdefault(r["engine"], {"n": 0, "client": 0, "client_cited": 0})
        e["n"] += 1
        if _mentioned(r.get("answer_text") or "", names["__client__"]):
            e["client"] += 1
        doms = {c.get("domain") for c in r.get("citations") or [] if c.get("domain")}
        if any(d == client_host or d.endswith("." + client_host) for d in doms):
            e["client_cited"] += 1
        for d in doms:
            cited[d] = cited.get(d, 0) + 1
        for cname, var in names.items():
            if cname != "__client__" and _mentioned(r.get("answer_text") or "", var):
                named[cname] = named.get(cname, 0) + 1
    engines = {}
    tot_n = tot_c = 0
    for eng, e in per_engine.items():
        lo, hi = wilson(e["client"], e["n"])
        engines[eng] = {"runs": e["n"], "mentions": e["client"], "mention_rate": round(e["client"] / e["n"], 3) if e["n"] else None,
                        "ci95": [round(lo, 3), round(hi, 3)], "domain_cited_rate": round(e["client_cited"] / e["n"], 3) if e["n"] else None}
        tot_n += e["n"]
        tot_c += e["client"]
    return {"engines": engines, "client_mention_rate": round(tot_c / tot_n, 3) if tot_n else None,
            "client_ci95": [round(x, 3) for x in wilson(tot_c, tot_n)] if tot_n else None,
            "cited_domains": [{"domain": d, "count": c, "domain_type": domain_type(d, client_host)} for d, c in sorted(cited.items(), key=lambda x: -x[1])][:40],
            "named": [{"name": k, "mentions": v} for k, v in sorted(named.items(), key=lambda x: -x[1])]}


def cmd_generate(args: Any) -> int:
    state = st.require_state(args)
    b, cfg = st.load_business(state) or {}, st.load_config(state)
    prompts = generate(b, args.max or (cfg.get("caps") or {}).get("ai_prompts", 40))
    if args.write:
        st.save_json(state / "prompts.json", {"schema_version": 1, "generated": st.today(), "prompts": prompts})
    cli.emit(prompts, args, "\n".join("%s [%s] %s" % (p["id"], p["class"], p["text"]) for p in prompts))
    return cli.EXIT_OK


def cmd_run(args: Any) -> int:
    state = st.require_state(args)
    b, cfg = st.load_business(state) or {}, st.load_config(state)
    prompts = (st.load_json(state / "prompts.json", {}) or {}).get("prompts", [])
    if not prompts:
        cli.die(cli.EXIT_USAGE, "prompts.json is empty: run `ai_panel.py generate --write`")
    runs_n = args.runs or (cfg.get("caps") or {}).get("ai_runs", 3)
    engines = args.engines or list(ENGINES)
    avail = {}
    for e in engines:
        try:
            avail[e] = pv.pick("ai_answers", state, engine=e)
        except pv.NoProvider:
            pass
    if not avail:
        cli.die(cli.EXIT_NOCREDS, "No ai_answers provider (OPENAI_API_KEY, PERPLEXITY_API_KEY, GEMINI_API_KEY or a UI-parity provider). "
                "Fallback: collect answers by hand and `ai_panel.py import <folder>`.")
    calls = len(prompts) * runs_n * len(avail)
    usd = sum((pv.cost("ai_answers", p["id"]) or 0) for p in avail.values()) * len(prompts) * runs_n
    if not args.execute:
        cli.emit({"dry_run": True, "calls": calls, "engines": {k: v["id"] for k, v in avail.items()}, "estimated_usd": round(usd, 3)}, args,
                 "Dry run: %d calls (%s), about %.2f USD. Re-run with --execute." % (calls, ", ".join("%s via %s" % (k, v["id"]) for k, v in avail.items()), usd))
        return cli.EXIT_OK
    from twwa_lib import spend
    spend.guard(state, usd)
    runs = []
    for p in prompts:
        loc = {"town": p.get("location"), "country": "DE", "region": (b.get("address") or {}).get("region")}
        for eng, prov in avail.items():
            for i in range(runs_n):
                try:
                    r = pv.call("ai_answers", {"prompt": p["text"], "engine": eng, "location": loc}, state=state, execute=True, provider=prov["id"])
                except http.FetchError as ex:
                    cli.die(cli.EXIT_REMOTE, str(ex))
                runs.append({"prompt_id": p["id"], "engine": eng, "run": i + 1, "provider": prov["id"], "ui_parity": r.get("ui_parity"),
                             "answer_text": r.get("answer_text"), "citations": r.get("citations", [])})
    return _store(state, b, runs, "api", args)


def _store(state: Path, b: Dict[str, Any], runs: List[Dict[str, Any]], origin: str, args: Any) -> int:
    payload = dict(score(state, runs, b), runs=runs, label_de="Stichprobe" if origin == "manual" else None)
    path = connect.write_snapshot(state, "ai-panel", payload, origin)
    cli.emit({k: v for k, v in payload.items() if k != "runs"}, args, _human(payload) + "\nSnapshot: %s" % path)
    return cli.EXIT_OK


def _human(s: Dict[str, Any]) -> str:
    lines = ["KI-Sichtbarkeit (Erwähnungsrate mit 95%-Intervall; keine 'KI-Platzierung'):"]
    for e, v in s["engines"].items():
        lines.append("  %-11s %d/%d = %s  [%s–%s]" % (e, v["mentions"], v["runs"], v["mention_rate"], v["ci95"][0], v["ci95"][1]))
    lines.append("  Meistzitierte Quellen: %s" % ", ".join("%s (%s)" % (c["domain"], c["domain_type"]) for c in s["cited_domains"][:8]))
    return "\n".join(lines)


def cmd_import(args: Any) -> int:
    """Folder of <prompt_id>__<engine>__<n>.txt files (citations as URLs inside the text), or a JSON list of runs."""
    state = st.require_state(args)
    b = st.load_business(state) or {}
    src = Path(args.source)
    runs: List[Dict[str, Any]] = []
    if src.is_dir():
        for f in sorted(src.glob("*.txt")):
            parts = f.stem.split("__")
            text = f.read_text(encoding="utf-8")
            urls = re.findall(r"https?://[^\s)\]>\"']+", text)
            from serp_teardown import host  # type: ignore
            runs.append({"prompt_id": parts[0], "engine": parts[1] if len(parts) > 1 else "unknown", "run": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1,
                         "provider": "manual", "ui_parity": True, "answer_text": text, "citations": [{"url": u, "domain": host(u)} for u in urls]})
    else:
        runs = st.load_json(src) or []
    if not runs:
        cli.die(cli.EXIT_USAGE, "no answers found in %s" % src)
    return _store(state, b, runs, "manual", args)


def cmd_score(args: Any) -> int:
    state = st.require_state(args)
    snap = st.load_json(args.file) if args.file else st.load_latest_snapshot(state, "ai-panel")
    if not snap:
        cli.die(cli.EXIT_USAGE, "no ai-panel snapshot")
    s = score(state, snap.get("runs", []), st.load_business(state) or {})
    cli.emit(s, args, _human(s))
    return cli.EXIT_OK


def compare(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for eng in set(a.get("engines", {})) & set(b.get("engines", {})):
        ea, eb = a["engines"][eng], b["engines"][eng]
        moved = not intervals_overlap(tuple(ea["ci95"]), tuple(eb["ci95"]))
        out[eng] = {"before": ea["mention_rate"], "after": eb["mention_rate"],
                    "verdict_de": ("belastbare Veränderung" if moved else "keine belastbare Veränderung")}
    return out


def cmd_compare(args: Any) -> int:
    state = st.require_state(args)
    files = sorted(state.glob("snapshots/*/ai-panel.json"))
    if len(files) < 2:
        cli.die(cli.EXIT_USAGE, "need at least two ai-panel snapshots")
    hist = [st.load_json(f) for f in files[-4:]]
    res = compare(hist[-2], hist[-1])
    for eng in res:
        rates = [h["engines"].get(eng, {}).get("mention_rate") for h in hist]
        if len(rates) == 4 and None not in rates and (rates == sorted(rates) or rates == sorted(rates, reverse=True)) and len(set(rates)) > 1:
            res[eng]["verdict_de"] = "Trend über 4 Messungen"
    cli.emit(res, args, "\n".join("%s: %s -> %s, %s" % (k, v["before"], v["after"], v["verdict_de"]) for k, v in res.items()))
    return cli.EXIT_OK


def cmd_gaps(args: Any) -> int:
    state = st.require_state(args)
    snap = st.load_latest_snapshot(state, "ai-panel")
    if not snap:
        cli.die(cli.EXIT_USAGE, "no ai-panel snapshot")
    from serp_teardown import host  # type: ignore
    listed = {host(x.get("url") or x.get("domain") or "") for x in (st.load_json(state / "offsite.json", {}) or {}).get("entries", [])}
    gaps = [c for c in snap.get("cited_domains", []) if c["domain_type"] in ("directory", "association", "publisher", "lead_portal", "business")
            and c["domain"] not in listed and c["domain_type"] != "client"]
    cli.emit(gaps, args, "Zitierte Quellen ohne Eintrag des Kunden (an twwa-offsite):\n" + "\n".join("  %s (%s, %dx)" % (g["domain"], g["domain_type"], g["count"]) for g in gaps[:15]))
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  ai_panel.py generate --write\n  ai_panel.py run            # dry run\n  ai_panel.py import answers/")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "generate", "German prompt panel from business.json")
    sp.add_argument("--write", action="store_true")
    sp.add_argument("--max", type=int, default=None)
    sp.set_defaults(fn=cmd_generate)
    sp = cli.add_sub(subs, "run", "ask each available engine (dry run unless --execute)")
    sp.add_argument("--engines", nargs="*", default=None, choices=ENGINES)
    sp.add_argument("--runs", type=int, default=None)
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_run)
    sp = cli.add_sub(subs, "import", "score answers collected by hand or with a browser tool")
    sp.add_argument("source")
    sp.set_defaults(fn=cmd_import)
    sp = cli.add_sub(subs, "score", "re-score a snapshot")
    sp.add_argument("--file", default=None)
    sp.set_defaults(fn=cmd_score)
    cli.add_sub(subs, "compare", "movement between measurements").set_defaults(fn=cmd_compare)
    cli.add_sub(subs, "gaps", "cited domains without the client, for off-site work").set_defaults(fn=cmd_gaps)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
