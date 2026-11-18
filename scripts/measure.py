#!/usr/bin/env python3
"""Action verdicts and alerts (spec 12). Baseline = last full window before the ship date for the affected pages
and queries plus a control set (untouched pages with similar impressions). At window end: difference in
differences on clicks and impressions, position change on targeted queries, leads on affected pages. Small data
or a control that moved more than the treatment gives "inconclusive" ("noch zu früh" / "zu wenig Daten").
Every verdict is also written to the agency learning log."""
from __future__ import annotations

import datetime as _dt
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st  # noqa: E402
from twwa_lib.stats import diff_in_diff  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
PCT_SCALE = 1.0  # stats.pct_change unit, set below
PCT_WIN = 10.0


def _gsc_snaps(state: Path) -> List[Tuple[str, Dict[str, Any]]]:
    out = []
    for f in sorted(state.glob("snapshots/*/gsc.json")):
        d = st.load_json(f)
        if d:
            out.append((f.parent.name, d))
    return out


def _sum(rows: List[Dict[str, Any]], pages: List[str], queries: Optional[List[str]] = None) -> Dict[str, float]:
    norm = lambda u: (u or "").split("#")[0].rstrip("/").replace("://www.", "://")  # noqa: E731
    ps = {norm(p) for p in pages}
    c = i = pw = 0.0
    for r in rows:
        if ps and not any(norm(r.get("page")).endswith(p.split("://")[-1]) or norm(r.get("page")) == p for p in ps):
            continue
        if queries and (r.get("query") or "").lower() not in queries:
            continue
        c += r.get("clicks") or 0
        i += r.get("impressions") or 0
        pw += (r.get("position") or 0) * (r.get("impressions") or 0)
    return {"clicks": c, "impressions": i, "position": round(pw / i, 2) if i else None}


def controls(rows: List[Dict[str, Any]], affected: List[str], n: int = 5) -> List[str]:
    agg: Dict[str, float] = {}
    for r in rows:
        p = (r.get("page") or "").split("#")[0]
        if p and not any(p.rstrip("/").endswith(a.split("#")[0].rstrip("/") or "/") for a in affected if a not in ("/", "")):
            agg[p] = agg.get(p, 0) + (r.get("impressions") or 0)
    return [p for p, _ in sorted(agg.items(), key=lambda x: -x[1])[:n]]


def evaluate(state: Path, a: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    snaps = _gsc_snaps(state)
    shipped = st.parse_date(a.get("shipped_at"))
    before = [s for d, s in snaps if st.parse_date(d) and shipped and st.parse_date(d) <= shipped]
    after = [s for d, s in snaps if st.parse_date(d) and shipped and st.parse_date(d) >= shipped + _dt.timedelta(days=int(a.get("window_days") or 28))]
    if not before or not after:
        return {"verdict": "inconclusive", "confidence": "low", "text_de": "noch zu früh: kein GSC-Snapshot vor und nach dem Fenster",
                "data": {"before": bool(before), "after": bool(after)}}
    b_rows, a_rows = before[-1]["rows"], after[-1]["rows"]
    pages = a.get("pages_affected") or ["/"]
    qs = [q.lower() for q in a.get("queries_targeted") or []] or None
    ctrl = a.get("control_pages") or controls(b_rows, pages)
    tb, ta = _sum(b_rows, pages, qs), _sum(a_rows, pages, qs)
    cb, ca = _sum(b_rows, ctrl), _sum(a_rows, ctrl)
    single = len({(r.get("page") or "").split("#")[0] for r in b_rows}) <= 1
    if single:  # one-page site: control = non-targeted queries
        cb = {"clicks": sum(r["clicks"] for r in b_rows if (r.get("query") or "").lower() not in (qs or [])),
              "impressions": sum(r["impressions"] for r in b_rows if (r.get("query") or "").lower() not in (qs or []))}
        ca = {"clicks": sum(r["clicks"] for r in a_rows if (r.get("query") or "").lower() not in (qs or [])),
              "impressions": sum(r["impressions"] for r in a_rows if (r.get("query") or "").lower() not in (qs or []))}
    metric = "clicks" if (a.get("primary_metric") or "gsc.clicks").endswith("clicks") else "impressions"
    did = diff_in_diff(tb[metric], ta[metric], cb.get(metric, 0), ca.get(metric, 0))
    m = cfg["thresholds"].get("measure", {})
    min_imp = m.get("min_verdict_impressions", 100)
    data = {"treatment": {"before": tb, "after": ta}, "control": {"before": cb, "after": ca, "pages": ctrl}, "did": did, "metric": metric}
    ctrl_move = abs(did.get("ctrl_pct") or 0)
    treat_move = abs(did.get("treat_pct") or 0)
    if ta["impressions"] < min_imp or tb["impressions"] < min_imp / 2:
        return {"verdict": "inconclusive", "confidence": "low", "data": data,
                "text_de": "zu wenig Daten: %d Impressionen im Fenster (mindestens %d nötig)" % (ta["impressions"], min_imp)}
    if ctrl_move > treat_move:
        return {"verdict": "inconclusive", "confidence": "low", "data": data, "text_de": "Kontrollseiten haben sich stärker bewegt als die Zielseiten"}
    eff = did.get("did_pct")
    did["effect"] = eff
    conf = "low" if single else ("medium" if ta["impressions"] < 1000 else "high")
    if eff is None:
        return {"verdict": "inconclusive", "confidence": "low", "data": data, "text_de": "keine Basis für den Vergleich"}
    win_t = m.get("win_effect_pct", PCT_WIN)
    verdict = "win" if eff >= win_t else ("loss" if eff <= -win_t else "neutral")
    pos_txt = ""
    if tb.get("position") and ta.get("position"):
        pos_txt = ", Position %.1f -> %.1f" % (tb["position"], ta["position"])
    return {"verdict": verdict, "confidence": conf, "data": data,
            "text_de": "%s %s: %d -> %d (Kontrolle %+.0f %%)%s" % ({"win": "Gewinn", "loss": "Verlust", "neutral": "neutral"}[verdict],
                                                              "Klicks" if metric == "clicks" else "Impressionen", tb[metric], ta[metric],
                                                              (did.get("ctrl_pct") or 0) * PCT_SCALE, pos_txt)}


def cmd_evaluate(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    import twwa_actions  # type: ignore
    due = twwa_actions.due_actions(state, cfg) if not args.action else [twwa_actions.get_action(state, args.action)]
    out = []
    for a in due:
        res = evaluate(state, a, cfg)
        res["action_id"] = a["action_id"]
        out.append(res)
        if args.write:
            subprocess.run([sys.executable, str(SCRIPTS / "twwa_actions.py"), "measure", a["action_id"], "--verdict", res["verdict"],
                            "--confidence", res["confidence"], "--text-de", res["text_de"], "--state", str(state)], check=False, capture_output=True)
            subprocess.run([sys.executable, str(SCRIPTS / "learning.py"), "record", "--state", str(state), "--action", a["action_id"],
                            "--verdict", res["verdict"], "--confidence", res["confidence"],
                            "--effect", str((res.get("data") or {}).get("did", {}).get("effect"))], check=False, capture_output=True)
    cli.emit(out, args, "\n".join("%s: %s (%s) – %s" % (r["action_id"], r["verdict"], r["confidence"], r["text_de"]) for r in out) or "Keine fälligen Aktionen.")
    return cli.EXIT_OK


def alerts(state: Path, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    gsc_files = sorted(state.glob("snapshots/*/gsc.json"))
    money = [q.lower() for c in (st.load_json(state / "keywords.json", {}) or {}).get("clusters", []) if c.get("priority") == 1 for q in c.get("queries", [])]
    if len(gsc_files) >= 2:
        prev, cur = st.load_json(gsc_files[-2]), st.load_json(gsc_files[-1])
        for q in money:
            a, b = _sum(prev["rows"], [], [q]), _sum(cur["rows"], [], [q])
            if a["position"] and b["position"] and b["position"] - a["position"] >= 3:
                out.append(cli.finding("alert.money_query.dropped", "onpage", "P2", "Wichtige Suchanfrage verliert Positionen",
                                       "„%s“: %.1f -> %.1f" % (q, a["position"], b["position"]), {"value": [a["position"], b["position"]]}))
        insp = cur.get("inspection") or []
        if insp:
            bad = [i for i in insp if (i.get("coverage_state") or "").lower().startswith("crawled - currently not indexed")]
            if len(bad) / len(insp) > 0.2:
                out.append(cli.finding("alert.index.crawled_not_indexed", "tech", "P2", "Viele Seiten gecrawlt, aber nicht indexiert",
                                       "%d von %d geprüften URLs." % (len(bad), len(insp)), {"value": len(bad)}))
    gbp = st.load_latest_snapshot(state, "gbp") or {}
    if (gbp.get("profile") or {}).get("state") in ("SUSPENDED", "DISABLED"):
        out.append(cli.finding("alert.gbp.suspended", "gbp", "P1", "Unternehmensprofil gesperrt", "Profilstatus: %s" % gbp["profile"]["state"], {"value": gbp["profile"]["state"]}))
    site = st.load_latest_snapshot(state, "site") or {}
    for f in site.get("findings", []):
        if f.get("severity") == "P1":
            out.append(f)
    return out


def cmd_alerts(args: Any) -> int:
    state = st.require_state(args)
    res = alerts(state, st.load_config(state))
    cli.emit(res, args, cli.render_findings_de(res, "Warnungen"))
    return cli.EXIT_FAIL if any(f["severity"] == "P1" for f in res) else cli.EXIT_OK


def cmd_baseline(args: Any) -> int:
    state = st.require_state(args)
    import twwa_actions  # type: ignore
    a = twwa_actions.get_action(state, args.action)
    snaps = _gsc_snaps(state)
    if not snaps:
        cli.die(cli.EXIT_NOCREDS, "no GSC snapshot: run gsc.py snapshot first")
    rows = snaps[-1][1]["rows"]
    pages = a.get("pages_affected") or ["/"]
    res = {"action_id": a["action_id"], "snapshot": snaps[-1][0], "treatment": _sum(rows, pages, [q.lower() for q in a.get("queries_targeted") or []] or None),
           "control_pages": a.get("control_pages") or controls(rows, pages)}
    cli.emit(res, args)
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  measure.py evaluate --write\n  measure.py alerts")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "baseline", "baseline and control set for an action")
    sp.add_argument("--action", required=True)
    sp.set_defaults(fn=cmd_baseline)
    sp = cli.add_sub(subs, "evaluate", "verdicts for actions whose window ended")
    sp.add_argument("--action", default=None)
    sp.add_argument("--write", action="store_true", help="log measured events and learning records")
    sp.set_defaults(fn=cmd_evaluate)
    cli.add_sub(subs, "alerts", "P1/P2 alerts from the latest snapshots").set_defaults(fn=cmd_alerts)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
