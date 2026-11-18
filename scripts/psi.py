#!/usr/bin/env python3
"""PageSpeed Insights (lab) and CrUX (field) for money pages. Works without a key at low volume;
PSI_API_KEY raises quota and is required for the CrUX API. CrUX usually has no data for SMB sites,
which is reported as such, never estimated. Budget (spec 12a): performance >= 90, CLS <= 0.05, LCP <= 2.5 s."""
from __future__ import annotations

import os
import sys
import urllib.parse
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, http, state as st  # noqa: E402

PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
CRUX = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def run(url: str, strategy: str = "mobile", raw: Any = None) -> Dict[str, Any]:
    if raw is None:
        q = {"url": url, "strategy": strategy, "category": "performance"}
        if os.environ.get("PSI_API_KEY"):
            q["key"] = os.environ["PSI_API_KEY"]
        raw = connect.get_json(PSI + "?" + urllib.parse.urlencode(q), timeout=120)
    lh = raw.get("lighthouseResult") or {}
    audits = lh.get("audits") or {}
    num = lambda k: (audits.get(k) or {}).get("numericValue")  # noqa: E731
    score = ((lh.get("categories") or {}).get("performance") or {}).get("score")
    field = (raw.get("loadingExperience") or {}).get("metrics")
    f = None
    if field:
        f = {k.lower(): (v or {}).get("percentile") for k, v in field.items()}
    return {"url": url, "strategy": strategy, "performance": round(score * 100) if score is not None else None,
            "lcp_ms": num("largest-contentful-paint"), "cls": num("cumulative-layout-shift"),
            "inp_ms": (f or {}).get("interaction_to_next_paint"), "tbt_ms": num("total-blocking-time"), "field": f}


def budget_findings(page: Dict[str, Any]) -> list:
    out = []
    if page.get("performance") is not None and page["performance"] < 90:
        out.append(cli.finding("tech.speed.performance_below_budget", "tech", "P3", "Ladezeit über Budget",
                               "Lighthouse-Performance %s (Budget 90) auf %s." % (page["performance"], page["url"]),
                               {"url": page["url"], "value": page["performance"]}, action_type="tech_fix", priority_group=3))
    if page.get("cls") is not None and page["cls"] > 0.05:
        out.append(cli.finding("tech.speed.cls_above_budget", "tech", "P3", "Layout springt beim Laden",
                               "CLS %.3f (Budget 0,05) auf %s." % (page["cls"], page["url"]),
                               {"url": page["url"], "value": page["cls"]}, action_type="tech_fix", priority_group=3))
    if page.get("lcp_ms") is not None and page["lcp_ms"] > 2500:
        out.append(cli.finding("tech.speed.lcp_above_budget", "tech", "P3", "Hauptinhalt erscheint zu spät",
                               "LCP %.1f s (Budget 2,5 s) auf %s." % (page["lcp_ms"] / 1000, page["url"]),
                               {"url": page["url"], "value": page["lcp_ms"]}, action_type="tech_fix", priority_group=3))
    return out


def cmd_run(args: Any) -> int:
    raw = st.load_json(args.fixture) if args.fixture else None
    pages = [run(u, args.strategy, raw) for u in args.urls]
    cli.emit({"pages": pages, "findings": [f for p in pages for f in budget_findings(p)]}, args)
    return cli.EXIT_OK


def cmd_crux(args: Any) -> int:
    key = os.environ.get("PSI_API_KEY")
    if not key:
        cli.die(cli.EXIT_NOCREDS, "PSI_API_KEY is needed for the CrUX API. Field data via PSI loadingExperience is in `psi.py run`.")
    try:
        r = http.post_json(CRUX + "?key=" + key, {"origin": args.origin})
    except http.FetchError as ex:
        cli.die(cli.EXIT_REMOTE, str(ex))
    if r.status == 404:
        cli.emit({"origin": args.origin, "field": None, "note": "CrUX hat keine Daten für diese Origin (typisch für kleine Websites)"}, args)
        return cli.EXIT_OK
    cli.emit(connect.json.loads(r.text), args)
    return cli.EXIT_OK


def cmd_snapshot(args: Any) -> int:
    state = st.require_state(args)
    pages = [run(u, args.strategy) for u in args.urls]
    path = connect.write_snapshot(state, "psi", {"pages": pages}, "api")
    cli.emit({"snapshot": path, "findings": [f for p in pages for f in budget_findings(p)]}, args, "PSI snapshot: %s" % path)
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  psi.py run https://www.musterbetrieb.example/")
    subs = cli.add_subcommands(p)
    for name, fn in (("run", cmd_run), ("snapshot", cmd_snapshot)):
        sp = cli.add_sub(subs, name, "lab run" if name == "run" else "write snapshots/<date>/psi.json")
        sp.add_argument("urls", nargs="+")
        sp.add_argument("--strategy", default="mobile", choices=("mobile", "desktop"))
        if name == "run":
            sp.add_argument("--fixture", default=None, help="saved PSI response")
        sp.set_defaults(fn=fn)
    sp = cli.add_sub(subs, "crux", "CrUX origin field data (needs PSI_API_KEY)")
    sp.add_argument("origin")
    sp.set_defaults(fn=cmd_crux)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
