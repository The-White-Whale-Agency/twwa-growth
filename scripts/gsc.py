#!/usr/bin/env python3
"""Google Search Console: search analytics, URL inspection, sitemap status, normalised snapshot.

Auth: twwa_lib.google_auth (GOOGLE_ACCESS_TOKEN, GOOGLE_APPLICATION_CREDENTIALS or gcloud), scope
webmasters.readonly; the Google user or service account must be added to the property. Free; 1,200 QPM per
site, URL inspection 2,000 per day per site. Without credentials: export from the Search Console UI and use
`snapshot --from-csv`. Windows end 3 days before today."""
from __future__ import annotations

import csv
import os
import sys
import urllib.parse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, google_auth, state as st  # noqa: E402

API = "https://www.googleapis.com/webmasters/v3"
INSPECT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _token() -> str:
    try:
        return google_auth.access_token(SCOPE)
    except google_auth.NoCredentials as ex:
        cli.die(cli.EXIT_NOCREDS, "%s\nFallback: export Performance > Pages+Queries as CSV and run gsc.py snapshot --from-csv <file>." % ex)
    return ""


def _prop(args: Any, state: Any) -> str:
    p = getattr(args, "property", None) or ((st.load_config(state).get("connectors") or {}).get("gsc") or {}).get("property")
    if not p:
        cli.die(cli.EXIT_USAGE, "Set --property (e.g. sc-domain:example.de) or connectors.gsc.property in config.json")
    return p


def query(token: str, prop: str, start: str, end: str, dims: List[str]) -> List[Dict[str, Any]]:
    rows, start_row = [], 0
    while True:
        body = {"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": 25000, "startRow": start_row, "dataState": "final"}
        res = connect.get_json("%s/sites/%s/searchAnalytics/query" % (API, urllib.parse.quote(prop, safe="")), token, "POST", body)
        batch = res.get("rows") or []
        rows += batch
        if len(batch) < 25000:
            return rows
        start_row += 25000


def inspect(token: str, prop: str, url: str) -> Dict[str, Any]:
    r = connect.get_json(INSPECT, token, "POST", {"inspectionUrl": url, "siteUrl": prop, "languageCode": "de"})
    idx = ((r.get("inspectionResult") or {}).get("indexStatusResult")) or {}
    return {"url": url, "verdict": idx.get("verdict"), "coverage_state": idx.get("coverageState"),
            "google_canonical": idx.get("googleCanonical"), "user_canonical": idx.get("userCanonical"),
            "last_crawl": idx.get("lastCrawlTime")}


def _norm_rows(raw: List[Dict[str, Any]], terms: list) -> List[Dict[str, Any]]:
    out = []
    for r in raw:
        page, q = (r.get("keys") or [None, None])[:2]
        out.append({"page": page, "query": q, "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
                    "ctr": round(r.get("ctr", 0), 4), "position": round(r.get("position", 0), 1),
                    "branded": connect.is_branded(q or "", terms)})
    return out


def aggregate_pages(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        a = agg.setdefault(r["page"], {"page": r["page"], "clicks": 0, "impressions": 0, "_pos": 0.0})
        a["clicks"] += r["clicks"]
        a["impressions"] += r["impressions"]
        a["_pos"] += r["position"] * r["impressions"]
    for a in agg.values():
        a["position"] = round(a.pop("_pos") / a["impressions"], 1) if a["impressions"] else None
    return sorted(agg.values(), key=lambda a: -a["impressions"])


def _from_csv(path: str, terms: list) -> List[Dict[str, Any]]:
    keymap = {"page": ("page", "seite", "top pages", "url"), "query": ("query", "suchanfrage", "top queries"),
              "clicks": ("clicks", "klicks"), "impressions": ("impressions", "impressionen"), "position": ("position",)}
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for raw in csv.DictReader(fh):
            low = {k.strip().lower(): v for k, v in raw.items() if k}
            def g(field: str) -> Any:
                return next((low[k] for k in keymap[field] if k in low), None)
            num = lambda v: float(str(v).replace("%", "").replace(".", "").replace(",", ".")) if v not in (None, "") else 0.0  # noqa: E731
            q = g("query") or ""
            rows.append({"page": g("page"), "query": q or None, "clicks": int(num(g("clicks"))), "impressions": int(num(g("impressions"))),
                         "ctr": None, "position": float(str(g("position") or "0").replace(",", ".")), "branded": connect.is_branded(q, terms)})
    return rows


def cmd_sites(args: Any) -> int:
    res = connect.get_json(API + "/sites", _token())
    cli.emit(res.get("siteEntry", []), args)
    return cli.EXIT_OK


def cmd_query(args: Any) -> int:
    state = st.find_state(".") if not getattr(args, "state", None) else st.resolve_state_arg(args.state)
    start, end = connect.gsc_window(args.days)
    rows = query(_token(), _prop(args, state), start, end, args.dims.split(","))
    cli.emit(rows, args)
    return cli.EXIT_OK


def cmd_inspect(args: Any) -> int:
    state = st.find_state(".")
    cli.emit([inspect(_token(), _prop(args, state), u) for u in args.urls], args)
    return cli.EXIT_OK


def cmd_sitemaps(args: Any) -> int:
    state = st.find_state(".")
    p = _prop(args, state)
    cli.emit(connect.get_json("%s/sites/%s/sitemaps" % (API, urllib.parse.quote(p, safe="")), _token()).get("sitemap", []), args)
    return cli.EXIT_OK


def cmd_snapshot(args: Any) -> int:
    state = st.require_state(args)
    terms = connect.brand_terms(st.load_business(state))
    start, end = connect.gsc_window(args.days)
    if args.from_csv:
        rows, origin, insp = _from_csv(args.from_csv, terms), "csv", []
    else:
        tok, prop = _token(), _prop(args, state)
        rows = _norm_rows(query(tok, prop, start, end, ["page", "query"]), terms)
        insp = [inspect(tok, prop, u) for u in (args.inspect or [])]
        origin = "api"
    path = connect.write_snapshot(state, "gsc", {"rows": rows, "pages": aggregate_pages([r for r in rows if r["page"]]),
                                                 "inspection": insp, "brand_terms": terms}, origin, (start, end))
    cli.emit({"snapshot": path, "rows": len(rows)}, args, "GSC snapshot: %s (%d rows)" % (path, len(rows)))
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  gsc.py snapshot --inspect https://www.musterbetrieb.example/")
    subs = cli.add_subcommands(p)
    cli.add_sub(subs, "sites", "properties the credentials can read").set_defaults(fn=cmd_sites)
    sp = cli.add_sub(subs, "query", "raw search analytics rows")
    sp.add_argument("--property", default=None)
    sp.add_argument("--days", type=int, default=90)
    sp.add_argument("--dims", default="page,query")
    sp.set_defaults(fn=cmd_query)
    sp = cli.add_sub(subs, "inspect", "URL inspection (2,000 per day per site)")
    sp.add_argument("urls", nargs="+")
    sp.add_argument("--property", default=None)
    sp.set_defaults(fn=cmd_inspect)
    sp = cli.add_sub(subs, "sitemaps", "sitemap status")
    sp.add_argument("--property", default=None)
    sp.set_defaults(fn=cmd_sitemaps)
    sp = cli.add_sub(subs, "snapshot", "write snapshots/<date>/gsc.json")
    sp.add_argument("--property", default=None)
    sp.add_argument("--days", type=int, default=90)
    sp.add_argument("--inspect", nargs="*", default=None, help="URLs to inspect (money pages)")
    sp.add_argument("--from-csv", default=None, help="Search Console UI export (no credentials needed)")
    sp.set_defaults(fn=cmd_snapshot)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
