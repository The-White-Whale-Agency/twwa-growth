#!/usr/bin/env python3
"""Local rank grid (Local Falcon style, self-built): grid points around the business, maps rank per point via the
provider layer, ARP (average rank where found), ATRP (average rank counting misses as 21), SoLV (share of points in
the top 3) for the client and competitors, and an SVG map. Cost = size² × keywords maps requests; dry run first."""
from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, http, providers as pv, state as st  # noqa: E402
from twwa_lib.textde import norm_name  # noqa: E402

MISS = 21


def points(lat: float, lng: float, size: int, spacing_km: float) -> List[Dict[str, float]]:
    half = (size - 1) / 2.0
    dlat = spacing_km / 111.32
    dlng = spacing_km / (111.32 * math.cos(math.radians(lat)))
    return [{"row": r, "col": c, "lat": round(lat + (half - r) * dlat, 6), "lng": round(lng + (c - half) * dlng, 6)}
            for r in range(size) for c in range(size)]


def _host(u: Optional[str]) -> str:
    return urlparse(u or "").netloc.lower().replace("www.", "")


def match_rank(results: List[Dict[str, Any]], name: str, website: Optional[str]) -> Optional[int]:
    n = norm_name(name, strip_legal_form=True)
    for r in results:
        if (website and r.get("website") and _host(r["website"]) == _host(website)) or (n and norm_name(r.get("name"), True) == n):
            return r.get("rank")
    return None


def score(pts: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranks = [p.get("rank") for p in pts]
    found = [r for r in ranks if r]
    return {"arp": round(sum(found) / len(found), 2) if found else None,
            "atrp": round(sum(r or MISS for r in ranks) / len(ranks), 2) if ranks else None,
            "solv": round(sum(1 for r in ranks if r and r <= 3) / len(ranks), 3) if ranks else None}


def render(grid: Dict[str, Any], kw: Dict[str, Any]) -> str:
    size = grid["size"]
    cell = 48
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="14">' % (size * cell, size * cell + 28),
           '<text x="4" y="18">%s – ARP %s, SoLV %s</text>' % (kw["keyword"], kw.get("arp"), kw.get("solv"))]
    for p in kw["points"]:
        r = p.get("rank")
        color = "#1a7f37" if r and r <= 3 else "#d4a72c" if r and r <= 10 else "#cf222e"
        x, y = p["col"] * cell + cell / 2, p["row"] * cell + cell / 2 + 28
        out.append('<circle cx="%d" cy="%d" r="18" fill="%s"/><text x="%d" y="%d" text-anchor="middle" fill="#fff">%s</text>'
                   % (x, y, color, x, y + 5, r or "20+"))
    out.append("</svg>")
    return "\n".join(out)


def cmd_points(args: Any) -> int:
    cli.emit(points(args.lat, args.lng, args.size, args.spacing), args)
    return cli.EXIT_OK


def cmd_run(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    cfg = st.load_config(state)
    geo = b.get("geo") or {}
    if geo.get("lat") is None:
        cli.die(cli.EXIT_USAGE, "business.json geo.lat/lng is required for a grid")
    size = args.size or (cfg.get("caps") or {}).get("grid_size", 7)
    kws = args.keywords or [q for c in (st.load_json(state / "keywords.json", {}) or {}).get("clusters", [])
                            if c.get("target") and c.get("intent") in ("service_town", "near_me") for q in c.get("queries", [])[:1]]
    kws = kws[: (cfg.get("caps") or {}).get("grid_keywords", 10)]
    pts = points(geo["lat"], geo["lng"], size, args.spacing)
    calls = len(pts) * len(kws)
    try:
        prov = pv.pick("serp_maps", state)
    except pv.NoProvider as ex:
        cli.die(cli.EXIT_NOCREDS, "Grid needs serp_maps data: %s. Pack and grid stay 'nicht geprüft'." % ex.how_to_enable)
    usd = (pv.cost("serp_maps", prov["id"], calls) or 0)
    if not args.execute:
        cli.emit({"dry_run": True, "provider": prov["id"], "calls": calls, "estimated_usd": round(usd, 4), "keywords": kws}, args,
                 "Dry run: %d maps requests via %s, about %.2f USD. Re-run with --execute." % (calls, prov["id"], usd))
        return cli.EXIT_OK
    from twwa_lib import spend
    spend.guard(state, usd)
    out = {"center": {"lat": geo["lat"], "lng": geo["lng"]}, "spacing_km": args.spacing, "size": size, "keywords": []}
    for kw in kws:
        kp, comp = [], {}
        for p in pts:
            try:
                res = pv.call("serp_maps", {"query": kw, "lat": p["lat"], "lng": p["lng"], "depth": 20}, state=state, execute=True)
            except http.FetchError as ex:
                cli.die(cli.EXIT_REMOTE, str(ex))
            rows = res.get("results", [])
            kp.append(dict(p, rank=match_rank(rows, b.get("name", ""), b.get("url"))))
            for r in rows[:3]:
                comp[r.get("name")] = comp.get(r.get("name"), 0) + 1
        s = score(kp)
        out["keywords"].append(dict(s, keyword=kw, points=kp,
                                    competitors=[{"name": k, "solv": round(v / len(pts), 3)} for k, v in sorted(comp.items(), key=lambda x: -x[1])[:5]]))
    path = connect.write_snapshot(state, "grid", out, "api")
    cli.emit({"snapshot": path, "keywords": [{k: v for k, v in kw.items() if k != "points"} for kw in out["keywords"]]}, args)
    return cli.EXIT_OK


def cmd_score(args: Any) -> int:
    state = st.require_state(args)
    g = st.load_json(args.file) if args.file else st.load_latest_snapshot(state, "grid")
    if not g:
        cli.die(cli.EXIT_USAGE, "no grid snapshot")
    cli.emit([dict(score(k["points"]), keyword=k["keyword"]) for k in g["keywords"]], args)
    return cli.EXIT_OK


def cmd_render(args: Any) -> int:
    state = st.require_state(args)
    g = st.load_json(args.file) if args.file else st.load_latest_snapshot(state, "grid")
    if not g:
        cli.die(cli.EXIT_USAGE, "no grid snapshot")
    outdir = state / "out"
    outdir.mkdir(exist_ok=True)
    files = []
    for k in g["keywords"]:
        f = outdir / ("grid-%s.svg" % st.slugify(k["keyword"]))
        f.write_text(render(g, k), encoding="utf-8")
        files.append(str(f))
    cli.emit({"files": files}, args, "\n".join(files))
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  geogrid.py run --spacing 1.5            # dry run with cost\n  geogrid.py run --spacing 1.5 --execute")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "points", "grid coordinates")
    sp.add_argument("--lat", type=float, required=True)
    sp.add_argument("--lng", type=float, required=True)
    sp.add_argument("--size", type=int, default=7)
    sp.add_argument("--spacing", type=float, default=1.5, help="km between points")
    sp.set_defaults(fn=cmd_points)
    sp = cli.add_sub(subs, "run", "observe the grid via the provider layer (dry run unless --execute)")
    sp.add_argument("--keywords", nargs="*", default=None)
    sp.add_argument("--size", type=int, default=None)
    sp.add_argument("--spacing", type=float, default=1.5)
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_run)
    for name, fn in (("score", cmd_score), ("render", cmd_render)):
        sp = cli.add_sub(subs, name, "ARP/ATRP/SoLV" if name == "score" else "SVG per keyword into .twwa-growth/out/")
        sp.add_argument("--file", default=None)
        sp.set_defaults(fn=fn)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
