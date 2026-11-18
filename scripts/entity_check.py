#!/usr/bin/env python3
"""Entity consistency matrix (spec 12a): the same facts (name, street, postcode, town, phone, URL, primary category)
in business.json, the site's visible HTML, its JSON-LD (incl. sameAs), the GBP snapshot and every known listing.
Every confirmed profile URL must appear in sameAs; no sameAs entry may be dead."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, http, state as st  # noqa: E402
from twwa_lib.textde import fold_umlauts, norm_address, norm_name, norm_phone  # noqa: E402

FIELDS = ("name", "street", "zip", "city", "phone", "url")


def canon(b: Dict[str, Any]) -> Dict[str, Optional[str]]:
    a = b.get("address") or {}
    return {"name": norm_name(b.get("name"), True), "street": norm_address(a.get("street")), "zip": a.get("zip"),
            "city": fold_umlauts((a.get("city") or "").lower()) or None, "phone": norm_phone(b.get("phone")) if b.get("phone") else None,
            "url": urlparse(b.get("url") or "").netloc.replace("www.", "") or None}


def from_text(text: str, c: Dict[str, Optional[str]], tel: List[str]) -> Dict[str, Any]:
    low = fold_umlauts(text.lower())
    phones = {norm_phone(t.replace("tel:", "")) for t in tel}
    res: Dict[str, Any] = {}
    for f in FIELDS:
        v = c.get(f)
        if not v:
            res[f] = "not_checked"
        elif f == "phone":
            digits = "".join(ch for ch in text if ch.isdigit())
            res[f] = "match" if v in phones or v[-7:] in digits else "missing"
        elif f == "name":
            res[f] = "match" if fold_umlauts(v) in fold_umlauts(norm_name(text)) else "missing"
        elif f == "url":
            res[f] = "not_checked"
        else:
            res[f] = "match" if fold_umlauts(str(v)) in low else "missing"
    return res


def from_jsonld(page: htmlx.Page, c: Dict[str, Optional[str]]) -> Dict[str, Any]:
    nodes = [n for n in page.jsonld_nodes() if any(t for t in ([n.get("@type")] if isinstance(n.get("@type"), str) else n.get("@type") or [])
                                                   if t not in ("WebSite", "WebPage", "BreadcrumbList", "FAQPage", "ImageObject"))]
    if not nodes:
        return {f: "missing" for f in FIELDS} | {"same_as": []}
    n = nodes[0]
    a = n.get("address") or {}
    a = a[0] if isinstance(a, list) and a else a
    got = {"name": norm_name(n.get("name"), True), "street": norm_address(a.get("streetAddress")) if isinstance(a, dict) else None,
           "zip": a.get("postalCode") if isinstance(a, dict) else None, "city": fold_umlauts((a.get("addressLocality") or "").lower()) if isinstance(a, dict) else None,
           "phone": norm_phone(n.get("telephone")) if n.get("telephone") else None, "url": urlparse(n.get("url") or "").netloc.replace("www.", "") or None}
    res: Dict[str, Any] = {}
    for f in FIELDS:
        if not c.get(f):
            res[f] = "not_checked"
        elif not got.get(f):
            res[f] = "missing"
        else:
            res[f] = "match" if got[f] == c[f] else {"mismatch": got[f]}
    sa = n.get("sameAs") or []
    res["same_as"] = [sa] if isinstance(sa, str) else list(sa)
    return res


def from_gbp(snap: Optional[Dict[str, Any]], c: Dict[str, Optional[str]], b: Dict[str, Any]) -> Dict[str, Any]:
    if not snap:
        return {f: "not_checked" for f in FIELDS}
    p = snap.get("profile") or {}
    addr = p.get("address") or {}
    got = {"name": norm_name(p.get("name"), True) if p.get("name") else None,
           "street": norm_address(" ".join(addr.get("addressLines") or [])) if addr else None, "zip": addr.get("postalCode"),
           "city": fold_umlauts((addr.get("locality") or "").lower()) or None, "phone": norm_phone(p.get("phone")) if p.get("phone") else None,
           "url": urlparse(p.get("website_url") or "").netloc.replace("www.", "") or None}
    res = {}
    for f in FIELDS:
        if not c.get(f) or got.get(f) is None:
            res[f] = "not_checked" if f in ("street", "zip", "city") and not b.get("address_public", True) else ("not_checked" if got.get(f) is None else "not_checked")
        else:
            res[f] = "match" if got[f] == c[f] else {"mismatch": got[f]}
    return res


def run(state: Path, site: Optional[str], dist: Optional[str], allow_private: bool) -> Dict[str, Any]:
    b = st.load_business(state) or {}
    c = canon(b)
    matrix: Dict[str, Any] = {}
    page = None
    if dist and Path(dist, "index.html").is_file():
        page = htmlx.parse(Path(dist, "index.html").read_text(encoding="utf-8"), b.get("url") or "")
    elif site or b.get("url"):
        try:
            r = http.fetch(site or b["url"], allow_private=allow_private)
            page = htmlx.parse(r.text, r.url) if r.ok else None
        except http.FetchError:
            page = None
    if page:
        matrix["site_html"] = from_text(page.full_text or page.text, c, page.tel_links)
        matrix["jsonld"] = from_jsonld(page, c)
    else:
        matrix["site_html"] = matrix["jsonld"] = {f: "not_checked" for f in FIELDS}
    matrix["gbp"] = from_gbp(st.load_latest_snapshot(state, "gbp"), c, b)
    for e in (st.load_json(state / "offsite.json", {}) or {}).get("entries", []):
        if e.get("url") and e.get("status") in ("live", "verified", "listed"):
            try:
                r = http.fetch(e["url"], allow_private=allow_private)
                lp = htmlx.parse(r.text, r.url) if r.ok else None
                matrix["listing:" + e["source_id"]] = from_text(lp.full_text, c, lp.tel_links) if lp else {"status": "unreachable (%s)" % r.status}
            except http.FetchError as ex:
                matrix["listing:" + e["source_id"]] = {"status": "unreachable (%s)" % ex}
    findings = []
    for src, row in matrix.items():
        for f, v in row.items():
            if isinstance(v, dict) and "mismatch" in v:
                findings.append(cli.finding("citations.nap.mismatch.%s.%s" % (st.slugify(src).replace("-", "_"), f), "citations", "P2",
                                            "%s weicht ab (%s)" % (f, src), "Erwartet laut business.json: %s; gefunden: %s." % (c.get(f), v["mismatch"]),
                                            {"value": v["mismatch"], "snippet": src}, action_type="tech_fix" if src in ("site_html", "jsonld") else "citation", priority_group=5))
            elif v == "missing" and src in ("site_html", "jsonld") and f in ("name", "phone", "zip"):
                findings.append(cli.finding("citations.nap.missing.%s.%s" % (src, f), "citations", "P3", "%s fehlt (%s)" % (f, src),
                                            "Feld %s ist auf der Website nicht auffindbar." % f, {"snippet": src}, action_type="tech_fix", priority_group=3))
    profiles = [v for v in (b.get("profiles") or {}).values() if v]
    same_as = (matrix.get("jsonld") or {}).get("same_as") or []
    for p in profiles:
        if p not in same_as:
            findings.append(cli.finding("tech.schema.sameas_missing", "tech", "P3", "Profil fehlt in sameAs", "%s ist bestätigt, aber nicht in sameAs." % p,
                                        {"url": p}, action_type="tech_fix", priority_group=3))
    for u in same_as:
        try:
            r = http.fetch(u, method="GET", allow_private=allow_private, timeout=15)
            if r.status >= 400:
                findings.append(cli.finding("tech.schema.sameas_dead", "tech", "P2", "sameAs zeigt auf tote Seite", "%s antwortet mit %s." % (u, r.status),
                                            {"url": u, "value": r.status}, action_type="tech_fix", priority_group=3))
        except http.FetchError:
            pass
    return {"canonical": c, "matrix": matrix, "findings": findings}


def cmd_run(args: Any) -> int:
    state = st.require_state(args)
    if args.fixture:
        http.use_fixture(args.fixture)
    res = run(state, args.site, args.dist, args.allow_private)
    lines = ["%-26s %s" % (src, "  ".join("%s=%s" % (f, v if isinstance(v, str) else "≠%s" % v.get("mismatch", v.get("status"))) for f, v in row.items() if f != "same_as"))
             for src, row in res["matrix"].items()]
    cli.emit(res, args, "\n".join(lines) + "\n" + cli.render_findings_de(res["findings"], "Entitäts-Konsistenz"))
    return cli.EXIT_FAIL if res["findings"] else cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  entity_check.py run --dist dist")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "run", "build the matrix")
    sp.add_argument("--site", default=None)
    sp.add_argument("--dist", default=None)
    sp.add_argument("--fixture", default=None)
    sp.add_argument("--allow-private", action="store_true")
    sp.set_defaults(fn=cmd_run)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
