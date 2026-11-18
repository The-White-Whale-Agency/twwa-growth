#!/usr/bin/env python3
"""Vercel: deployment status (REST API, VERCEL_TOKEN) and Web Analytics numbers.

Vercel does not publish a stable REST endpoint for Web Analytics queries. Pageviews, referrers and custom
events are therefore imported: from the Vercel MCP tools (aggregate_pageviews, count_events) saved as JSON,
or from a dashboard export, with `snapshot --from-file`. Hobby plans have no custom events; Pro has them;
UTM data needs Web Analytics Plus. Missing numbers stay missing ("nicht geprüft")."""
from __future__ import annotations

import os
import sys
import urllib.parse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, state as st  # noqa: E402

API = "https://api.vercel.com"


def _token() -> str:
    t = os.environ.get("VERCEL_TOKEN")
    if not t:
        cli.die(cli.EXIT_NOCREDS, "VERCEL_TOKEN not set (Vercel > Account Settings > Tokens). Fallback: Vercel MCP tools or the dashboard.")
    return t or ""


def _ids(state: Any) -> Dict[str, Any]:
    c = (st.load_config(state).get("connectors") or {}).get("vercel") or {} if state else {}
    return {"projectId": c.get("project_id"), "teamId": c.get("team_id")}


def deployments(state: Any, limit: int = 5) -> List[Dict[str, Any]]:
    q = {k: v for k, v in dict(_ids(state), limit=limit, target="production").items() if v}
    res = connect.get_json("%s/v6/deployments?%s" % (API, urllib.parse.urlencode(q)), _token())
    return [{"uid": d.get("uid"), "url": d.get("url"), "state": d.get("state") or d.get("readyState"),
             "created": d.get("created"), "commit": (d.get("meta") or {}).get("githubCommitSha")} for d in res.get("deployments", [])]


def _norm_import(data: Any) -> Dict[str, Any]:
    """Accepts {"pageviews":[{"path","views","visitors"}],"referrers":[...],"events":[...]} or MCP-style rows."""
    if isinstance(data, dict) and any(k in data for k in ("pageviews", "referrers", "events")):
        return {k: data.get(k, []) for k in ("pageviews", "referrers", "events")}
    rows = data if isinstance(data, list) else (data or {}).get("data", [])
    pv = [{"path": r.get("path") or r.get("key"), "views": r.get("views") or r.get("count") or r.get("total"),
           "visitors": r.get("visitors") or r.get("devices")} for r in rows]
    return {"pageviews": pv, "referrers": [], "events": []}


def cmd_deployments(args: Any) -> int:
    state = st.find_state(".")
    d = deployments(state, args.limit)
    failed = [x for x in d[:1] if x["state"] == "ERROR"]
    findings = [cli.finding("tracking.deploy.production_failed", "tech", "P1", "Letztes Produktions-Deployment fehlgeschlagen",
                            "Deployment %s hat den Status ERROR." % failed[0]["uid"], {"url": failed[0]["url"]})] if failed else []
    cli.emit({"deployments": d, "findings": findings}, args)
    return cli.EXIT_FAIL if failed else cli.EXIT_OK


def cmd_snapshot(args: Any) -> int:
    state = st.require_state(args)
    if not args.from_file:
        cli.die(cli.EXIT_NOCREDS, "Web Analytics numbers are imported: save the Vercel MCP aggregate_pageviews/count_events output "
                "(or a dashboard export) as JSON and pass --from-file. Nothing is estimated.")
    payload = _norm_import(st.load_json(args.from_file))
    path = connect.write_snapshot(state, "vercel", payload, "manual", (args.start, args.end) if args.start else None)
    cli.emit({"snapshot": path, "pageviews": len(payload["pageviews"])}, args, "Vercel snapshot: %s" % path)
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  vercel_analytics.py snapshot --from-file pageviews.json --start 2026-10-01 --end 2026-10-31")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "deployments", "latest production deployments (P1 finding when the latest failed)")
    sp.add_argument("--limit", type=int, default=5)
    sp.set_defaults(fn=cmd_deployments)
    for name in ("snapshot", "pageviews", "events"):
        sp = cli.add_sub(subs, name, "import Web Analytics numbers into snapshots/<date>/vercel.json")
        sp.add_argument("--from-file", default=None)
        sp.add_argument("--start", default=None)
        sp.add_argument("--end", default=None)
        sp.set_defaults(fn=cmd_snapshot)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
