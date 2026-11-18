#!/usr/bin/env python3
"""Cycle planner (spec 1 and 6): P1 findings first; table-stakes groups (1 tracking, 2 GBP, 4 reviews, 5 citations)
take at most `caps.table_stakes_slots` of the cycle while teardown-driven work exists; the rest is teardown backlog
ordered by query value × winnability × gap closed ÷ effort; at most `caps.proposals_per_cycle` minus open proposals.
Growth work needs a teardown younger than 35 days. Prints the cycle and the `twwa_actions.py propose` line for each."""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st  # noqa: E402

TABLE_STAKES = {1, 2, 4, 5}
GROUP = {"tracking_fix": 1, "gbp_identity_edit": 2, "gbp_content_edit": 2, "gbp_post": 2, "tech_fix": 3, "robots_policy": 3,
         "onpage_rewrite": 3, "cro_change": 3, "review_engine": 4, "review_reply": 4, "citation": 5, "new_page": 6,
         "page_refresh": 6, "page_consolidate": 6, "offsite_mention": 7, "ai_refinement": 8}
METRIC = {"tracking_fix": "leads.count", "gbp_identity_edit": "gbp.impressions_maps", "gbp_content_edit": "gbp.calls",
          "tech_fix": "gsc.impressions", "onpage_rewrite": "gsc.clicks", "page_refresh": "gsc.clicks", "new_page": "gsc.impressions",
          "review_engine": "gbp.reviews_last_90", "citation": "grid.solv", "offsite_mention": "ai.mention_rate",
          "ai_refinement": "ai.mention_rate", "page_consolidate": "gsc.clicks", "cro_change": "leads.count"}


def _latest_findings(state: Path) -> List[Dict[str, Any]]:
    out = []
    for src in ("site", "check"):
        s = st.load_latest_snapshot(state, src)
        if s:
            out += s.get("findings", [])
    return out


def teardown_age(state: Path) -> int:
    base = state / "teardowns"
    ds = sorted(p.name for p in base.glob("????-??-??")) if base.is_dir() else []
    if not ds:
        return 10 ** 6
    return (st.today_date() - st.parse_date(ds[-1])).days


def open_proposals(state: Path) -> int:
    import twwa_actions  # type: ignore
    acts = twwa_actions.fold(st.read_jsonl(state / "actions.jsonl"))
    return sum(1 for a in acts.values() if a.get("state") in ("proposed", "approved"))


def rank(state: Path) -> Dict[str, Any]:
    cfg = st.load_config(state)
    caps = cfg.get("caps") or {}
    valid = cfg["thresholds"]["teardown"]["valid_days"]
    age = teardown_age(state)
    slots = max(0, caps.get("proposals_per_cycle", 5) - open_proposals(state))
    findings = [f for f in _latest_findings(state) if f.get("status") == "verified"]
    p1 = [{"source": "finding", "id": f["id"], "action_type": f.get("action_type") or "tech_fix", "title_de": f["title_de"],
           "reason_de": f.get("detail_de"), "priority_group": f.get("priority_group") or GROUP.get(f.get("action_type") or "", 3), "p1": True}
          for f in findings if f.get("severity") == "P1"]
    stakes = [{"source": "finding", "id": f["id"], "action_type": f.get("action_type") or "tech_fix", "title_de": f["title_de"],
               "reason_de": f.get("detail_de"), "priority_group": f.get("priority_group") or 3}
              for f in findings if f.get("severity") == "P2" and (f.get("priority_group") in TABLE_STAKES)]
    opp = (st.load_latest_snapshot(state, "opportunities") or {}).get("items", [])
    stakes += [{"source": "opportunity", "id": o["kind"], "action_type": o["action_type"], "title_de": o["reason_de"], "reason_de": o["reason_de"],
                "priority_group": o["priority_group"]} for o in opp if o.get("action_type") and o.get("priority_group") in TABLE_STAKES]
    growth: List[Dict[str, Any]] = []
    notes = []
    if age > valid:
        notes.append("Teardown fehlt oder ist älter als %d Tage: keine Wachstums-Aktionen geplant. Erst `serp_teardown.py run`." % valid)
    else:
        bl = (st.load_json(state / "backlog.json", {}) or {}).get("items", [])
        growth = [{"source": "teardown", "id": i["key"], "action_type": i["action_type"], "title_de": i["reason_de"], "reason_de": i["reason_de"],
                   "queries": i.get("queries", []), "priority": i["priority"], "priority_group": GROUP.get(i["action_type"], 6),
                   "scope_proposal": i.get("scope_proposal"), "window_days": i.get("evaluate_after_days"), "first_signal_de": i.get("first_signal_de")}
                  for i in bl if i.get("status", "open") == "open" and i.get("source") == "teardown"]
        growth += [{"source": "opportunity", "id": o["kind"], "action_type": o["action_type"], "title_de": o["reason_de"], "reason_de": o["reason_de"],
                    "queries": [o["query"]] if o.get("query") else [], "priority": 0.5, "priority_group": o["priority_group"]}
                   for o in opp if o.get("action_type") and o.get("priority_group") not in TABLE_STAKES]
        growth.sort(key=lambda g: -(g.get("priority") or 0))
    cycle: List[Dict[str, Any]] = []
    for item in p1:
        if len(cycle) < slots:
            cycle.append(item)
    ts_cap = caps.get("table_stakes_slots", 2) if growth else slots
    seen = {c["id"] for c in cycle}
    for item in sorted(stakes, key=lambda s: s["priority_group"]):
        if len(cycle) >= slots or sum(1 for c in cycle if c["priority_group"] in TABLE_STAKES and not c.get("p1")) >= ts_cap:
            break
        if item["id"] not in seen:
            cycle.append(item)
            seen.add(item["id"])
    for item in growth:
        if len(cycle) >= slots:
            break
        if item["id"] not in seen:
            cycle.append(item)
            seen.add(item["id"])
    for c in cycle:
        at = c["action_type"]
        cmd = ["python3", "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_actions.py", "propose", "--type", at, "--title-de", c["title_de"][:120],
               "--metric", METRIC.get(at, "gsc.clicks"), "--hypothesis", "<if X then Y because Z: fill from the teardown evidence>"]
        if c.get("queries"):
            cmd += ["--queries", ",".join(c["queries"][:5])]
        if c.get("window_days"):
            cmd += ["--window", str(c["window_days"])]
        if c["source"] == "finding":
            cmd += ["--findings", c["id"]]
        if c.get("p1"):
            cmd += ["--p1"]
        if c.get("scope_proposal"):
            cmd += ["--as-proposal", "--adds-page"]
        c["propose_cmd"] = " ".join(shlex.quote(x) if "$" not in x else '"%s"' % x for x in cmd)
    return {"date": st.today(), "teardown_age_days": age if age < 10 ** 6 else None, "slots": slots, "cycle": cycle, "notes": notes,
            "waiting": [g["id"] for g in growth if g["id"] not in seen][:10]}


def cmd_rank(args: Any) -> int:
    state = st.require_state(args)
    res = rank(state)
    lines = ["Zyklus %s: %d von %d Plätzen" % (res["date"], len(res["cycle"]), res["slots"])] + res["notes"]
    for i, c in enumerate(res["cycle"], 1):
        lines.append("%d. [%s, Gruppe %s] %s%s" % (i, c["action_type"], c["priority_group"], c["title_de"],
                                                  "  (Angebot: außerhalb des Tarifs)" if c.get("scope_proposal") else ""))
        lines.append("   %s" % c["propose_cmd"])
    if res["waiting"]:
        lines.append("Wartet: %s" % ", ".join(res["waiting"]))
    cli.emit(res, args, "\n".join(lines))
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  plan.py rank")
    subs = cli.add_subcommands(p)
    cli.add_sub(subs, "rank", "build this cycle").set_defaults(fn=cmd_rank)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
