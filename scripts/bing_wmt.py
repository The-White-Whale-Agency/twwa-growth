#!/usr/bin/env python3
"""Bing Webmaster Tools JSON API: sites, query and page stats, URL info, inbound links, sitemap and URL submission.

Bing is a first-class step: ChatGPT search and Copilot draw on Bing's index. Auth: BING_WEBMASTER_API_KEY
(Bing Webmaster > Settings > API access). Free. Without a key: verify the site by importing it from Search
Console in the Bing UI and read the reports there. Writes (sitemap, submit) are dry-run unless --execute."""
from __future__ import annotations

import os
import sys
import urllib.parse
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, state as st  # noqa: E402

API = "https://ssl.bing.com/webmaster/api.svc/json/"


def _key() -> str:
    k = os.environ.get("BING_WEBMASTER_API_KEY")
    if not k:
        cli.die(cli.EXIT_NOCREDS, "BING_WEBMASTER_API_KEY not set. Bing Webmaster > Settings > API access. "
                "Fallback: import the site from Search Console in the Bing UI and read its reports by hand.")
    return k or ""


def _site(args: Any) -> str:
    state = st.find_state(".")
    s = getattr(args, "site", None) or ((st.load_config(state).get("connectors") or {}).get("bing") or {}).get("site_url") if state else getattr(args, "site", None)
    if not s:
        cli.die(cli.EXIT_USAGE, "Set --site https://www.example.de/ or connectors.bing.site_url")
    return s


def call(method: str, params: Dict[str, str], body: Any = None) -> Any:
    q = urllib.parse.urlencode(dict(params, apikey=_key()))
    res = connect.get_json(API + method + "?" + q, method="POST" if body is not None else "GET", body=body)
    return res.get("d", res) if isinstance(res, dict) else res


def _rows(stats: Any) -> list:
    out = []
    for r in stats or []:
        out.append({"page": r.get("Page"), "query": r.get("Query"), "clicks": r.get("Clicks", 0), "impressions": r.get("Impressions", 0),
                    "ctr": None, "position": r.get("AvgImpressionPosition") or r.get("AvgClickPosition")})
    return out


def cmd_sites(args: Any) -> int:
    cli.emit(call("GetUserSites", {}), args)
    return cli.EXIT_OK


def cmd_query(args: Any) -> int:
    cli.emit(_rows(call("GetQueryStats", {"siteUrl": _site(args)})), args)
    return cli.EXIT_OK


def cmd_pages(args: Any) -> int:
    cli.emit(_rows(call("GetPageStats", {"siteUrl": _site(args)})), args)
    return cli.EXIT_OK


def cmd_urlinfo(args: Any) -> int:
    site = _site(args)
    out = []
    for u in args.urls:
        d = call("GetUrlInfo", {"siteUrl": site, "url": u}) or {}
        out.append({"url": u, "indexed": bool(d.get("LastCrawledDate") or d.get("DiscoveryDate")),
                    "last_crawled": d.get("LastCrawledDate"), "http_status": d.get("HttpStatus"), "raw": d})
    cli.emit(out, args)
    return cli.EXIT_OK


def cmd_links(args: Any) -> int:
    cli.emit(call("GetLinkCounts", {"siteUrl": _site(args), "page": "0"}), args)
    return cli.EXIT_OK


def _write(args: Any, method: str, body: Dict[str, Any]) -> int:
    state = st.find_state(".")
    if state and st.stop_requested(state):
        cli.die(cli.EXIT_BLOCKED, "STOP file present: nothing is submitted.")
    if not args.execute:
        cli.emit({"dry_run": True, "method": method, "body": body}, args, "Dry run: %s %s. Re-run with --execute." % (method, body))
        return cli.EXIT_OK
    q = urllib.parse.urlencode({"apikey": _key()})
    connect.get_json(API + method + "?" + q, method="POST", body=body)
    cli.emit({"ok": True, "method": method}, args, "%s submitted." % method)
    return cli.EXIT_OK


def cmd_sitemap(args: Any) -> int:
    return _write(args, "SubmitSitemap", {"siteUrl": _site(args), "feedUrl": args.feed})


def cmd_submit(args: Any) -> int:
    return _write(args, "SubmitUrlBatch", {"siteUrl": _site(args), "urlList": args.urls})


def cmd_snapshot(args: Any) -> int:
    state = st.require_state(args)
    site = _site(args)
    rows = _rows(call("GetQueryStats", {"siteUrl": site}))
    pages = _rows(call("GetPageStats", {"siteUrl": site}))
    path = connect.write_snapshot(state, "bing", {"site_url": site, "rows": rows, "pages": pages}, "api")
    cli.emit({"snapshot": path, "rows": len(rows)}, args, "Bing snapshot: %s" % path)
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  bing_wmt.py sitemap --site https://www.musterbetrieb.example/ --feed https://www.musterbetrieb.example/sitemap-index.xml --execute")
    subs = cli.add_subcommands(p)
    for name, fn, h in (("sites", cmd_sites, "verified sites"), ("query", cmd_query, "query stats"),
                        ("pages", cmd_pages, "page stats"), ("links", cmd_links, "inbound link counts"),
                        ("snapshot", cmd_snapshot, "write snapshots/<date>/bing.json")):
        sp = cli.add_sub(subs, name, h)
        sp.add_argument("--site", default=None)
        sp.set_defaults(fn=fn)
    sp = cli.add_sub(subs, "urlinfo", "index status of URLs")
    sp.add_argument("urls", nargs="+")
    sp.add_argument("--site", default=None)
    sp.set_defaults(fn=cmd_urlinfo)
    sp = cli.add_sub(subs, "sitemap", "submit a sitemap (dry run unless --execute)")
    sp.add_argument("--site", default=None)
    sp.add_argument("--feed", required=True)
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_sitemap)
    sp = cli.add_sub(subs, "submit", "submit URLs (dry run unless --execute)")
    sp.add_argument("urls", nargs="+")
    sp.add_argument("--site", default=None)
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_submit)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
