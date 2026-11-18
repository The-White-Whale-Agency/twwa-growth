#!/usr/bin/env python3
"""JSON-LD from business.json (LocalBusiness with the most specific subtype, Service, BreadcrumbList) and
validation of built pages against it: parse errors, required fields, NAP equal to business.json, schema
type, self-serving review markup, deprecated rich-result types, markup of content that is not visible.
Unknown values (null) are never emitted."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, state as st, textde  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "schema-types.json"
DAYS = {"Mo": "Monday", "Tu": "Tuesday", "We": "Wednesday", "Th": "Thursday", "Fr": "Friday", "Sa": "Saturday", "Su": "Sunday"}


def types_data() -> Dict[str, Any]:
    return st.load_json(DATA, {}) or {}


def schema_type_for(b: Dict[str, Any]) -> str:
    if b.get("schema_type"):
        return b["schema_type"]
    d = types_data()
    trade = textde.fold_umlauts((b.get("trade") or "")).lower()
    if trade in d.get("trades", {}):
        return d["trades"][trade]["type"]
    return d.get("verticals", {}).get(b.get("vertical") or "other", "LocalBusiness")


def prune(o: Any) -> Any:
    if isinstance(o, list):
        a = [prune(x) for x in o]
        a = [x for x in a if x is not None]
        return a or None
    if isinstance(o, dict):
        out = {k: prune(v) for k, v in o.items()}
        out = {k: v for k, v in out.items() if v is not None}
        return out if any(not k.startswith("@") for k in out) else None
    if o is None or o == "":
        return None
    return o


def base_url(b: Dict[str, Any]) -> str:
    return (b.get("url") or "").rstrip("/")


def localbusiness_node(b: Dict[str, Any], description: Optional[str] = None) -> Dict[str, Any]:
    base = base_url(b)
    a = b.get("address") or {}
    geo = b.get("geo") or {}
    profiles = [u for u in [(b.get("gbp") or {}).get("maps_url")] + list((b.get("profiles") or {}).values()) if isinstance(u, str) and u.startswith("http")]
    node = {
        "@type": schema_type_for(b),
        "@id": "%s/#betrieb" % base,
        "name": b.get("name"),
        "url": b.get("url"),
        "description": description,
        "telephone": b.get("phone"),
        "email": b.get("email"),
        "foundingDate": str(b["founded"]) if b.get("founded") else None,
        "address": None if b.get("address_public") is False else {
            "@type": "PostalAddress", "streetAddress": a.get("street"), "postalCode": a.get("zip"), "addressLocality": a.get("city"),
            "addressRegion": a.get("region"), "addressCountry": a.get("country")},
        "geo": {"@type": "GeoCoordinates", "latitude": geo.get("lat"), "longitude": geo.get("lng")} if geo.get("lat") is not None and geo.get("lng") is not None else None,
        "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": [DAYS.get(d, d) for d in h.get("days") or []],
                                       "opens": h.get("open"), "closes": h.get("close")} for h in b.get("hours") or []],
        "areaServed": [{"@type": "City", "name": t.get("town")} for t in b.get("service_area") or []],
        "knowsAbout": [s.get("name") for s in b.get("services") or []],
        "sameAs": profiles,
    }
    return prune(node)


def localbusiness_graph(b: Dict[str, Any], description: Optional[str] = None) -> Dict[str, Any]:
    base = base_url(b)
    website = {"@type": "WebSite", "@id": "%s/#website" % base, "url": b.get("url"), "name": b.get("name"), "inLanguage": "de-DE",
               "publisher": {"@id": "%s/#betrieb" % base}}
    return {"@context": "https://schema.org", "@graph": [website, localbusiness_node(b, description)]}


def service_node(b: Dict[str, Any], service_id: str, town: Optional[str] = None) -> Dict[str, Any]:
    s = next((x for x in b.get("services") or [] if x.get("id") == service_id), None)
    if not s:
        raise KeyError(service_id)
    p = s.get("price") or {}
    node: Dict[str, Any] = {
        "@context": "https://schema.org", "@type": "Service", "serviceType": s.get("name"),
        "name": "%s in %s" % (s.get("name"), town) if town else s.get("name"),
        "provider": {"@id": "%s/#betrieb" % base_url(b)},
        "areaServed": {"@type": "City", "name": town} if town else [{"@type": "City", "name": t.get("town")} for t in b.get("service_area") or []],
    }
    if p.get("confirmed_by") and (p.get("typical_min") is not None or p.get("min") is not None):
        spec = {"@type": "UnitPriceSpecification", "priceCurrency": "EUR", "minPrice": p.get("typical_min") if p.get("typical_min") is not None else p.get("min"),
                "maxPrice": p.get("typical_max"), "unitText": p.get("unit")}
        node["offers"] = {"@type": "Offer", "priceCurrency": "EUR", "priceSpecification": prune(spec)}
    return prune(node)


def breadcrumb_node(base: str, path: str, names: List[str]) -> Dict[str, Any]:
    parts = [p for p in path.strip("/").split("/") if p]
    urls = [base.rstrip("/") + "/"] + [base.rstrip("/") + "/" + "/".join(parts[: i + 1]) for i in range(len(parts))]
    if len(names) != len(urls):
        raise ValueError("need %d names (home plus one per path segment), got %d" % (len(urls), len(names)))
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(zip(names, urls))]}


# ---------------------------------------------------------------- validation

def _types(n: Dict[str, Any]) -> List[str]:
    t = n.get("@type")
    return [x for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)]


def validate_page(page: htmlx.Page, b: Optional[Dict[str, Any]], url: str, file: Optional[str] = None, is_home: bool = False) -> List[Dict[str, Any]]:
    """Findings (section 4.3) for the JSON-LD of one page."""
    out: List[Dict[str, Any]] = []
    d = types_data()
    lb_types = set(d.get("local_business_types") or [])
    ev = {"url": url, "file": file}
    for e in page.jsonld_errors:
        if e.startswith("JSON-LD"):
            out.append(cli.finding("tech.schema.parse_error", "tech", "P2", "Strukturierte Daten nicht lesbar",
                                   "Ein JSON-LD-Block lässt sich nicht parsen (%s). Suchmaschinen ignorieren ihn vollständig." % e,
                                   evidence=dict(ev, snippet=e[:160]), action_type="tech_fix"))
    nodes = page.jsonld_nodes()
    lbs = [n for n in nodes if set(_types(n)) & lb_types]
    if is_home and not lbs:
        out.append(cli.finding("tech.schema.localbusiness_missing", "tech", "P2", "Kein LocalBusiness-Markup auf der Startseite",
                               "Die Startseite enthält keine strukturierten Daten zum Betrieb (Name, Adresse, Telefon, Öffnungszeiten). Sie helfen Google und KI-Systemen, den Betrieb eindeutig zuzuordnen.",
                               evidence=dict(ev, snippet="Typen: %s" % (", ".join(page.schema_types()) or "keine")), fix_hint="Add LocalBusinessSchema from templates/site.",
                               action_type="tech_fix"))
    for n in nodes:
        for t in _types(n):
            info = (d.get("rich_result_status") or {}).get(t)
            if info:
                out.append(cli.finding("tech.schema.deprecated_type", "tech", info.get("severity", "info"), "Markup-Typ %s ohne Rich Result" % t,
                                       info.get("note_de", ""), evidence=dict(ev, snippet=t), action_type="tech_fix"))
    for n in lbs:
        if n.get("aggregateRating") or n.get("review"):
            out.append(cli.finding("tech.schema.self_serving_rating", "tech", "P2", "Eigene Bewertungen als Sterne-Markup",
                                   "Der Betrieb markiert seine eigenen Bewertungen als AggregateRating oder Review. Google zeigt dafür seit 2019 keine Sterne und kann das als Richtlinienverstoß werten; wenn Bewertungen sichtbar sind, gehört der §5b-Hinweis daneben.",
                                   evidence=dict(ev, snippet="aggregateRating" if n.get("aggregateRating") else "review"), action_type="tech_fix"))
    own_ids = {n.get("@id") for n in lbs if n.get("@id")}
    for n in nodes:
        if set(_types(n)) & {"AggregateRating", "Review"}:
            item = n.get("itemReviewed") or {}
            if not item or (isinstance(item, dict) and (item.get("@id") in own_ids or set(_types(item)) & lb_types)):
                out.append(cli.finding("tech.schema.self_serving_rating", "tech", "P2", "Eigene Bewertungen als Sterne-Markup",
                                       "Ein Review- oder AggregateRating-Block bewertet den eigenen Betrieb. Dafür gibt es keine Sterne in der Suche.",
                                       evidence=dict(ev, snippet=", ".join(_types(n))), action_type="tech_fix"))
                break
    if not b:
        return out
    want_type = schema_type_for(b)
    vis = page.full_text
    vis_digits = re.sub(r"\D", "", vis) + " " + " ".join(textde.norm_phone(t) for t in page.tel_links)
    allowed_phones = {textde.norm_phone(b.get("phone"))} | {textde.norm_phone(x if isinstance(x, str) else x.get("number")) for x in b.get("tracking_numbers") or []}
    for n in lbs:
        mism = []
        if n.get("name") and textde.norm_name(n["name"]) != textde.norm_name(b.get("name")):
            mism.append("Name „%s“ statt „%s“" % (n["name"], b.get("name")))
        addr = n.get("address") or {}
        ba = b.get("address") or {}
        if isinstance(addr, dict) and addr:
            if addr.get("streetAddress") and textde.norm_address(addr["streetAddress"]) != textde.norm_address(ba.get("street")):
                mism.append("Straße „%s“ statt „%s“" % (addr.get("streetAddress"), ba.get("street")))
            if addr.get("postalCode") and str(addr["postalCode"]) != str(ba.get("zip")):
                mism.append("PLZ %s statt %s" % (addr.get("postalCode"), ba.get("zip")))
            if addr.get("addressLocality") and textde.norm_address(addr["addressLocality"]) != textde.norm_address(ba.get("city")):
                mism.append("Ort „%s“ statt „%s“" % (addr.get("addressLocality"), ba.get("city")))
        elif b.get("address_public") is not False:
            mism.append("Adresse fehlt im Markup")
        tel = n.get("telephone")
        if tel and textde.norm_phone(tel) not in allowed_phones:
            mism.append("Telefon %s statt %s" % (tel, b.get("phone")))
        if not tel and b.get("phone"):
            mism.append("Telefon fehlt im Markup")
        if n.get("url") and b.get("url") and htmlx.bare_host(urllib.parse.urlsplit(n["url"]).netloc) != htmlx.bare_host(urllib.parse.urlsplit(b["url"]).netloc):
            mism.append("URL %s statt %s" % (n.get("url"), b.get("url")))
        if mism:
            out.append(cli.finding("tech.schema.nap_mismatch", "tech", "P2", "Strukturierte Daten weichen von den Stammdaten ab",
                                   "Im LocalBusiness-Markup: %s. Name, Adresse und Telefon müssen überall gleich sein (Website, Markup, Google-Profil, Verzeichnisse)." % "; ".join(mism),
                                   evidence=dict(ev, snippet="; ".join(mism)[:200], value=mism), fix_hint="Regenerate JSON-LD from business.json (schema_gen.py localbusiness).",
                                   action_type="tech_fix"))
        if want_type not in _types(n):
            out.append(cli.finding("tech.schema.type_mismatch", "tech", "P3", "Markup-Typ passt nicht zum Gewerk",
                                   "Typ %s im Markup, erwartet %s (business.json schema_type oder Gewerk)." % (", ".join(_types(n)), want_type),
                                   evidence=dict(ev, snippet=", ".join(_types(n))), action_type="tech_fix"))
        invisible = []
        if n.get("name") and not textde.contains_term(vis, textde.norm_name(n["name"], strip_legal_form=True).split(" ")[0]):
            invisible.append("Name")
        if tel and re.sub(r"\D", "", textde.norm_phone(tel))[2:] not in vis_digits.replace("+49", "0") and textde.norm_phone(tel) not in vis_digits:
            invisible.append("Telefon")
        if invisible:
            out.append(cli.finding("tech.schema.invisible", "tech", "P3", "Markup beschreibt Inhalte, die nicht sichtbar sind",
                                   "%s steht im Markup, aber nicht sichtbar auf der Seite. Strukturierte Daten sollen nur sichtbare Inhalte beschreiben." % " und ".join(invisible),
                                   evidence=dict(ev, snippet=", ".join(invisible)), action_type="tech_fix"))
    return out


def _pages_of(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    return sorted(target.rglob("*.html"))


def cmd_localbusiness(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    if not b.get("name"):
        cli.die(cli.EXIT_USAGE, "business.json has no name; fill it first (twwa-onboard).")
    g = localbusiness_graph(b, args.description)
    _write(args, g)
    return cli.EXIT_OK


def cmd_service(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    try:
        node = service_node(b, args.id, args.town)
    except KeyError:
        cli.die(cli.EXIT_USAGE, "Unknown service id %s (business.json services[].id)." % args.id)
    _write(args, node)
    return cli.EXIT_OK


def cmd_breadcrumb(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    b = (st.load_business(state) or {}) if state else {}
    base = args.base or b.get("url")
    if not base:
        cli.die(cli.EXIT_USAGE, "--base is required without business.json url")
    try:
        node = breadcrumb_node(base, args.path, [n.strip() for n in args.names.split(",")])
    except ValueError as exc:
        cli.die(cli.EXIT_USAGE, str(exc))
    _write(args, node)
    return cli.EXIT_OK


def _write(args: Any, obj: Dict[str, Any]) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    cli.emit(obj, args, None if cli.is_json(args) else text)


def cmd_validate(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    b = st.load_business(state) if state else None
    target = Path(args.target)
    if not target.exists():
        cli.die(cli.EXIT_USAGE, "Not found: %s" % target)
    root = target if target.is_dir() else target.parent
    findings: List[Dict[str, Any]] = []
    site = (b or {}).get("url") or "https://site.invalid"
    for f in _pages_of(target):
        rel = f.relative_to(root).as_posix()
        path = "/" + re.sub(r"(index)?\.html$", "", rel)
        page = htmlx.parse(f.read_text(encoding="utf-8", errors="replace"), site.rstrip("/") + path)
        findings += validate_page(page, b, site.rstrip("/") + path, str(f), is_home=(path == "/"))
    errors = [x for x in findings if x["severity"] in ("P1", "P2")]
    note = "" if b else "\nNAP-Abgleich nicht geprüft: keine business.json gefunden."
    cli.emit({"ok": not errors, "findings": findings, "nap_checked": bool(b)}, args, cli.render_findings_de(findings, "Strukturierte Daten:") + note)
    return cli.EXIT_FAIL if errors else cli.EXIT_OK


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/schema_gen.py localbusiness --out src/data/localbusiness.json\n"
                                 "  python3 scripts/schema_gen.py validate dist --json")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "localbusiness", "LocalBusiness plus WebSite graph from business.json")
    sp.add_argument("--description")
    sp.add_argument("--out")
    sp = cli.add_sub(subs, "service", "Service node for one service (optionally one town)")
    sp.add_argument("--id", required=True)
    sp.add_argument("--town")
    sp.add_argument("--out")
    sp = cli.add_sub(subs, "breadcrumb", "BreadcrumbList for a path")
    sp.add_argument("--path", required=True)
    sp.add_argument("--names", required=True, help="comma-separated names: home first, then one per segment")
    sp.add_argument("--base")
    sp.add_argument("--out")
    sp = cli.add_sub(subs, "validate", "validate the JSON-LD of built pages against business.json; exit 1 on P1 or P2 findings")
    sp.add_argument("target", help="dist folder or one HTML file")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {"localbusiness": cmd_localbusiness, "service": cmd_service, "breadcrumb": cmd_breadcrumb, "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
