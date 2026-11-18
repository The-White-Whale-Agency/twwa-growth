#!/usr/bin/env python3
"""Opportunity detection from the client's own data: striking-distance queries, CTR outliers, uncovered clusters,
prune candidates, cannibalisation, review velocity gap, seasonal triggers, changed sources and a missing monthly
project report. Writes snapshots/<date>/opportunities.json for plan.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, spend, state as st  # noqa: E402


def _curve() -> Dict[str, Any]:
    return st.load_json(spend.DATA_DIR / "ctr-curve.json", {}) or {}


def expected_ctr(pos: float, curve: Dict[str, Any]) -> float:
    pts = sorted((int(k), v) for k, v in curve.get("by_position", {}).items())
    for p, v in pts:
        if pos <= p:
            return v
    return pts[-1][1] if pts else 0.0


def cannibalisation(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    byq: Dict[str, Dict[str, Dict[str, float]]] = {}
    for r in rows:
        if not r.get("query") or not r.get("page") or r.get("branded"):
            continue
        a = byq.setdefault(r["query"], {}).setdefault(r["page"].split("#")[0], {"imp": 0, "pos": 0.0})
        a["imp"] += r["impressions"]
        a["pos"] += r["position"] * r["impressions"]
    out = []
    for q, pages in byq.items():
        tot = sum(p["imp"] for p in pages.values())
        big = [(u, p["imp"], p["pos"] / p["imp"]) for u, p in pages.items() if p["imp"] and p["imp"] >= 0.2 * tot]
        if len(big) >= 2 and abs(big[0][2] - big[1][2]) <= 10 and tot >= 50:
            big.sort(key=lambda x: x[2])
            out.append({"query": q, "pages": [{"page": u, "impressions": i, "position": round(p, 1)} for u, i, p in big],
                        "owner_page": big[0][0], "advice_de": "eine Seite als Eigentümer festlegen; die andere differenzieren, verlinken oder zusammenführen"})
    return out


def detect(state: Path) -> Dict[str, Any]:
    cfg, b = st.load_config(state), st.load_business(state) or {}
    gsc = st.load_latest_snapshot(state, "gsc")
    out: Dict[str, Any] = {"date": st.today(), "items": [], "not_checked": []}
    add = lambda **kw: out["items"].append(kw)  # noqa: E731
    if gsc:
        curve = _curve()
        agg: Dict[tuple, Dict[str, float]] = {}
        for r in gsc.get("rows", []):
            if r.get("query") and r.get("page"):
                a = agg.setdefault((r["query"], r["page"]), {"c": 0, "i": 0, "p": 0.0, "branded": r.get("branded")})
                a["c"] += r["clicks"]
                a["i"] += r["impressions"]
                a["p"] += r["position"] * r["impressions"]
        for (q, page), a in agg.items():
            if not a["i"]:
                continue
            pos = a["p"] / a["i"]
            if 8 <= pos <= 20 and a["i"] >= 50:
                add(kind="striking_distance", action_type="page_refresh", priority_group=6, query=q, page=page, impressions=a["i"],
                    position=round(pos, 1), reason_de="Position %.1f bei %d Impressionen: Seite mit Belegen und Antworten ausbauen" % (pos, a["i"]))
            exp = expected_ctr(pos, curve)
            if a["i"] >= curve.get("min_impressions", 100) and not a["branded"] and pos <= 10 and a["c"] / a["i"] < exp * curve.get("outlier_share", 0.5):
                add(kind="ctr_outlier", action_type="onpage_rewrite", priority_group=3, query=q, page=page, ctr=round(a["c"] / a["i"], 4),
                    expected=exp, reason_de="CTR %.1f %% statt erwartet ~%.1f %%: Title und Beschreibung schärfen (Ort, Leistung, Beleg)" % (100 * a["c"] / a["i"], 100 * exp))
        for c in cannibalisation(gsc.get("rows", [])):
            add(kind="cannibalisation", action_type="page_consolidate", priority_group=6, query=c["query"], pages=c["pages"], reason_de=c["advice_de"])
    else:
        out["not_checked"].append("gsc")
    for c in (st.load_json(state / "keywords.json", {}) or {}).get("clusters", []):
        if c.get("target") and not c.get("target_page"):
            add(kind="uncovered_cluster", action_type="new_page" if cfg.get("tier") == "scale" else "onpage_rewrite", priority_group=6,
                cluster=c["id"], queries=c.get("queries", [])[:3],
                reason_de="Keine Zielseite für %s" % ", ".join(c.get("queries", [])[:2]))
    try:
        from page_gates import prune_candidates  # type: ignore
        pr = prune_candidates(state, cfg)
        for cand in pr.get("candidates", []):
            add(kind="prune", action_type="page_consolidate", priority_group=6, page=cand.get("page") or cand.get("url"),
                reason_de="90+ Tage ohne Klicks und Anfragen: zusammenführen")
    except Exception as ex:  # noqa: BLE001
        out["not_checked"].append("prune (%s)" % ex)
    gbp = st.load_latest_snapshot(state, "gbp")
    if gbp:
        rev = gbp.get("reviews") or {}
        if rev.get("last_90") is not None and rev["last_90"] < 3:
            add(kind="review_velocity", action_type="review_engine", priority_group=4, value=rev["last_90"],
                reason_de="Nur %d neue Bewertungen in 90 Tagen (Ziel: mindestens 1 pro Monat)" % rev["last_90"])
    else:
        out["not_checked"].append("gbp")
    seas = (st.load_json(spend.DATA_DIR / "seasonality.json", {}) or {}).get("trades", {}).get(b.get("trade") or "", {})
    month = st.today_date().month
    if seas and seas.get("prepare_month") == month:
        add(kind="seasonal", action_type="page_refresh", priority_group=6, topics=seas.get("topics_de"),
            reason_de="Saison beginnt bald: %s jetzt aktualisieren" % ", ".join(seas.get("topics_de", [])))
    if (cfg.get("owner_input") or {}).get("monthly_project_report"):
        inbox = state / "evidence" / "inbox"
        recent = [f for f in inbox.glob("*") if f.is_file() and (st.today_date() - st.parse_date(f.name[:7] + "-01")).days <= 45] if inbox.is_dir() else []
        if not recent and not any(p.name[:7] == st.today()[:7] for p in (state / "evidence" / "projects").glob("*.json")):
            add(kind="missing_project_report", action_type=None, priority_group=6,
                reason_de="Kein Projektbericht diesen Monat: Fotos und 3 Sätze beim Inhaber anfragen")
    for f in (st.load_json(state / "evidence" / "facts.json", {}) or {}).get("facts", []) if isinstance(st.load_json(state / "evidence" / "facts.json", {}), dict) else []:
        if f.get("changed_on") and f.get("changed_on") >= st.today()[:7]:
            add(kind="source_changed", action_type="page_refresh", priority_group=6, fact=f.get("id"), reason_de="Quelle geändert: %s prüfen" % f.get("claim"))
    return out


def cmd_detect(args: Any) -> int:
    state = st.require_state(args)
    res = detect(state)
    path = st.snapshot_dir(state) / "opportunities.json"
    st.save_json(path, res)
    cli.emit(res, args, "\n".join("%-22s %s" % (i["kind"], i["reason_de"]) for i in res["items"]) +
             ("\nnicht geprüft: %s" % ", ".join(res["not_checked"]) if res["not_checked"] else "") + "\n-> %s" % path)
    return cli.EXIT_OK


def cmd_cannibalisation(args: Any) -> int:
    state = st.require_state(args)
    gsc = st.load_latest_snapshot(state, "gsc")
    if not gsc:
        cli.die(cli.EXIT_NOCREDS, "no GSC snapshot: run gsc.py snapshot (or --from-csv)")
    res = cannibalisation(gsc.get("rows", []))
    cli.emit(res, args, "\n".join("%s: %s" % (c["query"], ", ".join("%s (Pos. %s)" % (p["page"], p["position"]) for p in c["pages"])) for c in res) or "Keine Kannibalisierung gefunden.")
    return cli.EXIT_FAIL if res else cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  opportunities.py detect")
    subs = cli.add_subcommands(p)
    cli.add_sub(subs, "detect", "all detectors -> snapshots/<date>/opportunities.json").set_defaults(fn=cmd_detect)
    cli.add_sub(subs, "cannibalisation", "own pages competing for one query").set_defaults(fn=cmd_cannibalisation)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
