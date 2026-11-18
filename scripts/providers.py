#!/usr/bin/env python3
"""Provider layer CLI (spec 9a): registry, credentials present, best provider per capability,
cost preview, a uniform call per capability, and the registry refresh procedure.

No script in this plugin names a data vendor; they all go through this layer."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, http, spend, state as st  # noqa: E402
from twwa_lib import providers as pv  # noqa: E402


def _state(args: Any) -> Any:
    return st.resolve_state_arg(getattr(args, "state", None)) or st.find_state(".")


def cmd_list(args: Any) -> int:
    rows = pv.status(_state(args))
    lines = ["%-13s %-14s creds=%-5s %s" % (r["id"], r["status"], r["creds_present"], ", ".join(sorted(r["capabilities"])))
             for r in rows]
    cli.emit(rows, args, "\n".join(lines))
    return cli.EXIT_OK


def cmd_pick(args: Any) -> int:
    try:
        e = pv.pick(args.capability, _state(args), args.engine)
    except pv.NoProvider as ex:
        cli.emit({"capability": args.capability, "provider": None, "how_to_enable": ex.how_to_enable}, args,
                 "No provider with credentials for %s.\nEnable one of: %s" % (args.capability, ex.how_to_enable))
        return cli.EXIT_NOCREDS
    c = e["capabilities"][args.capability]
    cli.emit({"capability": args.capability, "provider": e["id"], "cost_usd": c.get("cost_usd"), "localised": c.get("localised"),
              "ui_parity": c.get("ui_parity")}, args, "%s -> %s (%s USD per %s)" % (args.capability, e["id"], c.get("cost_usd"), c.get("unit")))
    return cli.EXIT_OK


def cmd_cost(args: Any) -> int:
    try:
        e = pv.pick(args.capability, _state(args))
    except pv.NoProvider as ex:
        cli.die(cli.EXIT_NOCREDS, "No provider for %s: %s" % (args.capability, ex.how_to_enable))
    usd = (pv.cost(args.capability, e["id"], args.units) or 0.0)
    s = _state(args)
    month = spend.month_total(s) if s else 0.0
    cap = (st.load_config(s).get("spend") or {}).get("monthly_cap_usd", 0) if s else None
    cli.emit({"provider": e["id"], "units": args.units, "estimated_usd": round(usd, 4), "month_spent_usd": month, "monthly_cap_usd": cap},
             args, "%s x %s via %s = about %.4f USD (month so far %.2f, cap %s)" % (args.units, args.capability, e["id"], usd, month, cap))
    return cli.EXIT_OK


def cmd_call(args: Any) -> int:
    params = json.loads(args.params) if args.params else {}
    s = _state(args)
    try:
        res = pv.call(args.capability, params, state=s, execute=args.execute, fixture=args.fixture,
                      provider=args.provider, engine=args.engine)
    except pv.NotExecuted as ex:
        cli.emit({"dry_run": True, **ex.plan}, args, "Dry run: would call %s. Re-run with --execute." % json.dumps(ex.plan, ensure_ascii=False))
        return cli.EXIT_OK
    except pv.NoProvider as ex:
        cli.die(cli.EXIT_NOCREDS, "No provider for %s. %s" % (args.capability, ex.how_to_enable))
    except http.FetchError as ex:
        cli.die(cli.EXIT_REMOTE, str(ex))
    cli.emit(res, args)
    return cli.EXIT_OK


def cmd_refresh(args: Any) -> int:
    path = spend.DATA_DIR / "providers.json"
    data = st.load_json(path, {})
    if args.apply:
        upd = st.load_json(args.apply)
        if not isinstance(upd, dict) or "providers" not in upd:
            cli.die(cli.EXIT_USAGE, "--apply expects {\"providers\": [entries...]} with verified_on and source_url on each")
        by_id = {e["id"]: e for e in data["providers"]}
        for e in upd["providers"]:
            if not e.get("verified_on") or not e.get("source_url"):
                cli.die(cli.EXIT_USAGE, "entry %s lacks verified_on or source_url" % e.get("id"))
            if e["id"] not in by_id:
                e["status"] = "registry_only"  # new entries never arrive as implemented
            by_id[e["id"]] = st.deep_merge(by_id.get(e["id"], {}), e)
        data["providers"] = list(by_id.values())
        st.save_json(path, data)
        cli.emit({"applied": [e["id"] for e in upd["providers"]]}, args, "Registry updated.")
        return cli.EXIT_OK
    today = st.today_date()
    stale = []
    for e in data.get("providers", []):
        d = st.parse_date(e.get("verified_on"))
        if d is None or (today - d).days > 90:
            stale.append({"id": e["id"], "verified_on": e.get("verified_on"), "check": [
                "pricing page: %s" % e.get("source_url"), "API docs: endpoints, auth, rate limits", "capability changes"]})
    brief = {c: "Is there a newer or better provider for German local %s data (localised, UI parity, price per call)? "
                "Add it as registry_only with a source URL." % c for c in pv.CAPABILITIES}
    out = {"stale": stale, "scouting_briefs": brief, "apply_with": "providers.py refresh --apply <file.json>"}
    human = ["Stale entries (older than 90 days): %s" % (", ".join(s["id"] for s in stale) or "none"),
             "Scout per capability with your web tools, then apply dated updates with --apply."]
    cli.emit(out, args, "\n".join(human))
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  providers.py pick serp_maps\n  providers.py call serp_organic --params '{\"query\":\"stuckateur musterstadt\"}'")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "list", "registry with credentials present")
    sp.set_defaults(fn=cmd_list)
    cli.add_sub(subs, "status", "same as list").set_defaults(fn=cmd_list)
    sp = cli.add_sub(subs, "pick", "best provider for a capability")
    sp.add_argument("capability", choices=pv.CAPABILITIES)
    sp.add_argument("--engine", default=None)
    sp.set_defaults(fn=cmd_pick)
    sp = cli.add_sub(subs, "cost", "cost preview")
    sp.add_argument("capability", choices=pv.CAPABILITIES)
    sp.add_argument("--units", type=float, default=1)
    sp.set_defaults(fn=cmd_cost)
    sp = cli.add_sub(subs, "call", "uniform call (dry run unless --execute)")
    sp.add_argument("capability", choices=pv.CAPABILITIES)
    sp.add_argument("--params", default=None, help="JSON params (spec 9a)")
    sp.add_argument("--provider", default=None, help="force a provider id (e.g. manual with params.file)")
    sp.add_argument("--engine", default=None)
    sp.add_argument("--fixture", default=None, help="saved raw provider response")
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_call)
    sp = cli.add_sub(subs, "refresh", "list stale entries and scouting briefs, or --apply dated updates")
    sp.add_argument("--apply", default=None)
    sp.set_defaults(fn=cmd_refresh)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
