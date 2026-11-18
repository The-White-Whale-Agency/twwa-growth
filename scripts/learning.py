#!/usr/bin/env python3
"""Agency-level learning log, outside every client repo (~/.twwa-growth/learning.jsonl or $TWWA_AGENCY_DIR).
Records, per measured action: client alias, vertical, trade, town-size bucket, action type, gap factor, window,
verdict, effect against control and confidence. `summary` shows win rate and median effect by action type and
vertical (from 5 observations); `suggest` proposes threshold and window changes. Nothing is applied automatically."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st  # noqa: E402
from twwa_lib.stats import median  # noqa: E402


def log_path() -> Path:
    base = Path(os.environ.get("TWWA_AGENCY_DIR") or os.path.expanduser("~/.twwa-growth"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "learning.jsonl"


def bucket(pop: Any) -> str:
    if not pop:
        return "unknown"
    return "under_20k" if pop < 20000 else "20k_100k" if pop < 100000 else "over_100k"


def cmd_record(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    import twwa_actions  # type: ignore
    a = twwa_actions.get_action(state, args.action)
    home = (b.get("service_area") or [{}])[0]
    alias = hashlib.sha256((b.get("url") or str(state)).encode()).hexdigest()[:10]
    try:
        eff = float(args.effect)
    except (TypeError, ValueError):
        eff = None
    rec = {"ts": st.now_iso(), "client": alias, "vertical": b.get("vertical"), "trade": b.get("trade"), "town_size": bucket(home.get("population")),
           "action_type": a.get("type"), "gap_factor": a.get("gap_factor"), "window_days": a.get("window_days"),
           "verdict": args.verdict, "effect": eff, "confidence": args.confidence, "action_id": args.action}
    st.append_jsonl(log_path(), rec)
    cli.emit(rec, args, "Learning record written to %s" % log_path())
    return cli.EXIT_OK


def groups(rows: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        g = out.setdefault(str(r.get(key)), {"n": 0, "wins": 0, "effects": []})
        g["n"] += 1
        g["wins"] += 1 if r.get("verdict") == "win" else 0
        if isinstance(r.get("effect"), (int, float)):
            g["effects"].append(r["effect"])
    return {k: {"n": v["n"], "win_rate": round(v["wins"] / v["n"], 2), "median_effect": median(v["effects"]) if v["effects"] else None}
            for k, v in out.items()}


def cmd_summary(args: Any) -> int:
    rows = [r for r in st.read_jsonl(log_path()) if r.get("verdict") != "inconclusive" or args.all]
    if len(rows) < 5:
        cli.emit({"observations": len(rows)}, args, "Erst %d auswertbare Beobachtungen (ab 5 aussagekräftig)." % len(rows))
        return cli.EXIT_OK
    res = {"observations": len(rows), "by_action_type": groups(rows, "action_type"), "by_vertical": groups(rows, "vertical")}
    cli.emit(res, args)
    return cli.EXIT_OK


def cmd_suggest(args: Any) -> int:
    rows = st.read_jsonl(log_path())
    sug = []
    for at, g in groups([r for r in rows if r.get("verdict") != "inconclusive"], "action_type").items():
        if g["n"] >= 5 and g["win_rate"] < 0.2:
            sug.append({"action_type": at, "suggestion": "rarely wins (%d%% of %d): lower its priority or check the gap mapping" % (100 * g["win_rate"], g["n"])})
    inc = groups(rows, "action_type")
    for at, g in inc.items():
        n_inc = sum(1 for r in rows if r.get("action_type") == at and r.get("verdict") == "inconclusive")
        if g["n"] >= 5 and n_inc / g["n"] > 0.6:
            sug.append({"action_type": at, "suggestion": "mostly inconclusive: lengthen its window or widen the control set"})
    cli.emit(sug, args, "\n".join("%s: %s" % (s["action_type"], s["suggestion"]) for s in sug) or "Noch keine Vorschläge (zu wenige Daten).")
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  learning.py summary")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "record", "record one measured action")
    sp.add_argument("--action", required=True)
    sp.add_argument("--verdict", required=True)
    sp.add_argument("--confidence", default="low")
    sp.add_argument("--effect", default=None)
    sp.set_defaults(fn=cmd_record)
    sp = cli.add_sub(subs, "summary", "win rate and effect by action type and vertical")
    sp.add_argument("--all", action="store_true")
    sp.set_defaults(fn=cmd_summary)
    cli.add_sub(subs, "suggest", "proposed threshold/window changes (never applied)").set_defaults(fn=cmd_suggest)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
