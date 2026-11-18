#!/usr/bin/env python3
"""SERP teardown (spec 10a): the centre of the plugin. Run at use time on the real client, in its own trade and town.

Steps: queries -> observe (provider layer, or import a manual observation) -> collect (polite fetches of the
winners) -> score (gap per factor against the median business winner) -> winnability -> backlog (gap -> action ->
expected time). Nothing about any real business is stored in the plugin; everything goes to
.twwa-growth/teardowns/<date>/. Surfaces without an observation are "not_checked", never guessed.
All thresholds come from config.thresholds.teardown and are tunable once learning.py has data."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, http, providers as pv, state as st  # noqa: E402
from twwa_lib.stats import median  # noqa: E402
from twwa_lib.textde import contains_term, contains_town, fold_umlauts, norm_name, words  # noqa: E402

DIRECTORY = ("gelbeseiten.", "dasoertliche.", "11880.", "cylex", "yelp.", "golocal.", "werkenntdenbesten.", "provenexpert.",
             "jameda.", "anwalt.de", "branchenbuch", "meinestadt.", "kennstdueinen.", "trustlocal.", "firmenabc.", "wlw.",
             "stadtbranchenbuch", "hotfrog.", "marktplatz-mittelstand", "steuerberater-suchservice", "dastelefonbuch.", "google.")
LEAD_PORTAL = ("myhammer.", "check24.", "blauarbeit.", "aroundhome.", "houzz.", "homify.", "jobruf.", "werkspot.",
               "machdudas.", "daibau.", "markt.de", "kleinanzeigen.")
PUBLISHER = ("wikipedia.", "zeitung", "t-online.", "focus.de", "spiegel.de", "stern.de", "merkur.de", "swr.de", "br.de",
             "ndr.de", "wdr.de", "chip.de", "heise.de", "bauen.de", "haus.de", "energie-fachberater", "baunetz")
ASSOCIATION = ("hwk-", "handwerkskammer", "innung", "ihk", "verband", "kammer", "zdh.de", "bundesverband", "stbk-")
SUBQ = {"price": r"\b(preis|kosten|€|euro|pauschal|angebot)", "process": r"\b(ablauf|schritt|so arbeiten|vorgehen|beratung)",
        "duration": r"\b(\d+\s*(tage|wochen|stunden)|dauer|termin)", "area": r"\b(einzugsgebiet|umkreis|region|landkreis|in der nähe)",
        "proof": r"\b(referenz|projekt|bewertung|kunden(stimmen)?|vorher)", "faq": r"(häufige fragen|faq|\?)",
        "contact": r"\b(kontakt|anrufen|telefon|anfrage|rückruf)"}
UNIT_RE = re.compile(r"\d[\d.,]*\s?(m²|m2|qm|lfm|€|euro|jahre|jahren|kwh|cm|mm|%)", re.I)
EFFORT = {"new_page": "L", "onpage_rewrite": "S", "page_refresh": "M", "tech_fix": "S", "citation": "M",
          "offsite_mention": "L", "gbp_identity_edit": "S", "gbp_content_edit": "S", "review_engine": "M", "ai_refinement": "S"}
GAP_ACTION = {  # largest gap factor -> (action, first signal, evaluate after days, German reason)
    "dedicated_page": ("new_page", "2 bis 8 Wochen", 90, "eigene Seite für die Leistung fehlt"),
    "geo_relevance": ("page_refresh", "2 bis 4 Wochen", 28, "zu wenig belegter Ortsbezug"),
    "title_h1": ("onpage_rewrite", "nach dem nächsten Crawl", 28, "Title/H1 nennen Leistung und Ort nicht"),
    "subquestions": ("page_refresh", "2 bis 4 Wochen", 28, "Kundenfragen (Preis, Ablauf, Dauer) unbeantwortet"),
    "evidence_depth": ("page_refresh", "2 bis 4 Wochen", 28, "zu wenige Belege (Projekte, Zahlen, Fotos)"),
    "internal_links": ("tech_fix", "1 bis 3 Wochen", 28, "zu wenige interne Links auf die Seite"),
    "schema_entity": ("tech_fix", "1 bis 3 Wochen", 28, "strukturierte Daten unklar"),
    "page_experience": ("tech_fix", "1 bis 3 Wochen", 28, "Ladezeit schlechter als bei den Gewinnern"),
    "referring_domains": ("citation", "Wochen bis Monate", 120, "weniger verweisende Domains als die Gewinner"),
    "domain_age": ("offsite_mention", "Monate", 180, "junge Marke ohne Erwähnungen"),
    "primary_category": ("gbp_identity_edit", "2 bis 14 Tage", 14, "Hauptkategorie passt nicht zu den Gewinnern"),
    "profile_completeness": ("gbp_content_edit", "2 bis 14 Tage", 14, "Profil unvollständig"),
    "review_count": ("review_engine", "Wochen", 90, "deutlich weniger Bewertungen"),
    "review_recency": ("review_engine", "Wochen", 60, "keine aktuellen Bewertungen"),
    "rating": ("review_engine", "Monate", 90, "Durchschnittsbewertung niedriger"),
    "landing_title_h1": ("onpage_rewrite", "nach dem nächsten Crawl", 28, "Zielseite des Profils nicht auf Leistung/Ort optimiert"),
    "landing_links": ("tech_fix", "1 bis 3 Wochen", 28, "Zielseite schwach verlinkt"),
    "nap_match": ("tech_fix", "Wochen", 90, "Name/Adresse/Telefon nicht überall gleich"),
    "proximity": (None, None, None, "Entfernung zum Suchort"),
    "cited_domains_presence": ("citation", "Wochen", 120, "fehlt auf den Seiten, die KI-Antworten zitieren"),
    "rating_volume": ("review_engine", "Wochen", 90, "Bewertungsbasis zu klein für KI-Empfehlungen"),
    "dedicated_page_facts": ("ai_refinement", "2 bis 4 Wochen", 28, "Fakten nicht explizit auf der Seite"),
    "third_party_mentions": ("offsite_mention", "Wochen bis Monate", 120, "zu wenige Erwähnungen Dritter"),
    "bing_indexed": ("tech_fix", "Tage", 7, "nicht im Bing-Index (ChatGPT/Copilot)"),
}


# ---------------------------------------------------------------- helpers

def host(u: Optional[str]) -> str:
    h = urlparse(u or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def domain_type(domain: str, client_host: str) -> str:
    d = domain.lower()
    if client_host and (d == client_host or d.endswith("." + client_host)):
        return "client"
    for kind, pats in (("lead_portal", LEAD_PORTAL), ("directory", DIRECTORY), ("association", ASSOCIATION), ("publisher", PUBLISHER)):
        if any(p in d for p in pats):
            return kind
    return "business"


def tdir(state: Path, date: Optional[str] = None) -> Path:
    d = state / "teardowns" / (date or st.today())
    (d / "obs").mkdir(parents=True, exist_ok=True)
    return d


def latest_tdir(state: Path) -> Optional[Path]:
    base = state / "teardowns"
    ds = sorted(p for p in base.glob("????-??-??") if p.is_dir()) if base.is_dir() else []
    return ds[-1] if ds else None


def _h1(p: htmlx.Page) -> List[str]:
    v = p.h1
    return v() if callable(v) else v


def _town(b: Dict[str, Any], name: Optional[str]) -> Dict[str, Any]:
    return next((t for t in b.get("service_area", []) if fold_umlauts(t["town"].lower()) == fold_umlauts((name or "").lower())), {})


# ---------------------------------------------------------------- step 1: queries

PRIO_W = {1: 3, 2: 2, 3: 1}
MARGIN_W = {"high": 1.5, "medium": 1.0, "low": 0.6}


def build_queries(b: Dict[str, Any], cfg: Dict[str, Any], demand: Dict[str, float]) -> List[Dict[str, Any]]:
    trade = (b.get("trade") or "").replace("_", " ")
    terms = [trade] + [t for t in (b.get("voice") or {}).get("regional_terms", []) if t.lower() != trade.lower()]
    towns = sorted(b.get("service_area", []), key=lambda t: (t.get("drive_minutes") or 0))
    home = towns[0]["town"] if towns else (b.get("address") or {}).get("city")
    out: Dict[str, Dict[str, Any]] = {}

    def add(q: str, cls: str, svc: Dict[str, Any], town: Optional[str]) -> None:
        q = " ".join(q.lower().split())
        if q in out:
            return
        d = demand.get(q)
        val = PRIO_W.get(svc.get("priority", 3), 1) * MARGIN_W.get(svc.get("margin", "medium"), 1.0) * (d if d else 1)
        out[q] = {"query": q, "class": cls, "service": svc.get("id"), "town": town, "value": round(val, 2), "demand": d,
                  "demand_known": bool(d)}

    for svc in sorted(b.get("services", []), key=lambda s: s.get("priority", 9)):
        for t in towns[:6]:
            add("%s %s" % (svc["name"], t["town"]), "service_town", svc, t["town"])
            for term in terms[:2]:
                if term:
                    add("%s %s" % (term, t["town"]), "service_town", svc, t["town"])
        add("%s kosten" % svc["name"], "cost", svc, home)
        for need in svc.get("needs", [])[:2]:
            add("%s %s %s" % (trade or svc["name"], need, home), "need", svc, home)
    top = sorted(b.get("services", []), key=lambda s: s.get("priority", 9))[:1]
    if top and trade:
        add("%s in der nähe" % trade, "near_me", top[0], home)
        add("bester %s %s" % (trade, home), "best", top[0], home)
    rows = list(out.values())
    cap = (cfg.get("caps") or {}).get("target_queries", 15)
    must = [r for r in rows if r["class"] == "service_town" and r["town"] == home]
    must = [next(r for r in must if r["service"] == s["id"]) for s in b.get("services", []) if s.get("priority") == 1
            and any(r["service"] == s["id"] for r in must)]
    rest = sorted((r for r in rows if r not in must), key=lambda r: (-r["value"], r["town"] != home))
    return (must + rest)[:cap]


def demand_map(state: Path) -> Dict[str, float]:
    snap = st.load_latest_snapshot(state, "gsc") or {}
    d: Dict[str, float] = {}
    for r in snap.get("rows", []):
        if r.get("query"):
            d[r["query"].lower()] = d.get(r["query"].lower(), 0) + (r.get("impressions") or 0)
    kv = st.load_latest_snapshot(state, "keywords") or {}
    for it in kv.get("items", []):
        if it.get("volume"):
            d[it["keyword"].lower()] = max(d.get(it["keyword"].lower(), 0), it["volume"])
    return d


def cmd_queries(args: Any) -> int:
    state = st.require_state(args)
    b, cfg = st.load_business(state) or {}, st.load_config(state)
    qs = build_queries(b, cfg, demand_map(state))
    if args.write:
        kpath = state / "keywords.json"
        kw = st.load_json(kpath, {"schema_version": 1, "clusters": []})
        by_id = {c["id"]: c for c in kw.get("clusters", [])}
        for q in qs:
            cid = "td-" + st.slugify(q["query"])
            existing = next((c for c in kw["clusters"] if q["query"] in [x.lower() for x in c.get("queries", [])]), None)
            if existing:
                existing["target"] = True
                continue
            by_id[cid] = {"id": cid, "queries": [q["query"]], "intent": q["class"], "priority": 1 if q["value"] >= 3 else 2,
                          "target_page": None, "town": q["town"], "service": q["service"], "target": True, "source": "teardown"}
        kw["clusters"] = list({**{c["id"]: c for c in kw["clusters"]}, **by_id}.values())
        st.save_json(kpath, kw)
    unknown = sum(1 for q in qs if not q["demand_known"])
    cli.emit(qs, args, "\n".join("%-45s %-12s value %.1f%s" % (q["query"], q["class"], q["value"], "" if q["demand_known"] else " (Nachfrage unbekannt)")
                                 for q in qs) + ("\n%d queries without demand data (counted as 1)." % unknown if unknown else ""))
    return cli.EXIT_OK


def target_queries(state: Path) -> List[Dict[str, Any]]:
    b = st.load_business(state) or {}
    kw = st.load_json(state / "keywords.json", {}) or {}
    out = []
    for c in kw.get("clusters", []):
        if not c.get("target"):
            continue
        for q in c.get("queries", [])[:1] if c.get("source") != "teardown" else c.get("queries", []):
            out.append({"query": q.lower(), "class": c.get("intent", "service_town"), "town": c.get("town") or (b.get("address") or {}).get("city"),
                        "service": c.get("service"), "target_page": c.get("target_page"), "cluster": c["id"]})
    if not out:
        out = build_queries(b, st.load_config(state), demand_map(state))
    seen, uniq = set(), []
    for q in out:
        if q["query"] not in seen:
            seen.add(q["query"])
            uniq.append(q)
    return uniq[: (st.load_config(state).get("caps") or {}).get("target_queries", 15)]


# ---------------------------------------------------------------- step 2: observe / import

def _obs_path(d: Path, q: str) -> Path:
    return d / "obs" / ("%s.json" % st.slugify(q))


def cmd_observe(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    d = tdir(state)
    qs = target_queries(state)
    if args.query:
        qs = [q for q in qs if q["query"] in [x.lower() for x in args.query]] or [{"query": x.lower(), "class": "service_town",
                                                                                    "town": (b.get("address") or {}).get("city")} for x in args.query]
    plan, done, skipped = [], 0, []
    for q in qs:
        t = _town(b, q.get("town"))
        lat, lng = (t.get("lat"), t.get("lng")) if t.get("lat") else ((b.get("geo") or {}).get("lat"), (b.get("geo") or {}).get("lng"))
        loc = {"town": q.get("town"), "lat": lat, "lng": lng, "country": "DE", "language": "de"}
        obs = st.load_json(_obs_path(d, q["query"]), {"query": q["query"], "class": q["class"], "town": q.get("town"), "surfaces": {}})
        for surface, cap, params in (("organic", "serp_organic", {"query": q["query"], "location": loc, "depth": 10}),
                                     ("pack", "serp_maps", {"query": q["query"], "lat": lat, "lng": lng, "depth": 20})):
            if surface in obs["surfaces"] and not args.refresh:
                continue
            if surface == "pack" and lat is None:
                skipped.append("%s/pack: no coordinates for %s" % (q["query"], q.get("town")))
                continue
            try:
                res = pv.call(cap, params, state=state, execute=args.execute)
                obs["surfaces"][surface] = res
                done += 1
            except pv.NotExecuted as ex:
                plan.append(ex.plan)
            except pv.NoProvider as ex:
                skipped.append("%s/%s: %s" % (q["query"], surface, ex.how_to_enable))
            except http.FetchError as ex:
                cli.die(cli.EXIT_REMOTE, str(ex))
        st.save_json(_obs_path(d, q["query"]), obs)
    total = sum(p.get("estimated_usd") or 0 for p in plan)
    msg = ["Observed %d surfaces into %s." % (done, d)]
    if plan:
        msg.append("Dry run: %d paid calls, about %.3f USD. Re-run with --execute (spend cap applies)." % (len(plan), total))
    if skipped:
        msg.append("Not observed (stay 'not_checked'; import a manual observation instead):\n  " + "\n  ".join(skipped[:12]))
    cli.emit({"dir": str(d), "observed": done, "dry_run_calls": len(plan), "estimated_usd": round(total, 4), "skipped": skipped}, args, "\n".join(msg))
    return cli.EXIT_OK


def cmd_import(args: Any) -> int:
    """File: {"query": "...", "surface": "organic|pack|ai", "observed_at": "...", "how": "...", "results": [...], "local_pack": [...]}"""
    state = st.require_state(args)
    data = st.load_json(args.file)
    items = data if isinstance(data, list) else [data]
    d = tdir(state)
    for it in items:
        q = it["query"].lower()
        obs = st.load_json(_obs_path(d, q), {"query": q, "class": it.get("class", "service_town"), "town": it.get("town"), "surfaces": {}})
        surf = dict(it, origin="manual", provider=it.get("provider", "manual"), localised=it.get("localised", True))
        obs["surfaces"][it["surface"]] = surf
        if it["surface"] == "organic" and it.get("local_pack") and "pack" not in obs["surfaces"]:
            obs["surfaces"]["pack"] = {"origin": "manual", "provider": "manual", "results": it["local_pack"]}
        st.save_json(_obs_path(d, q), obs)
    cli.emit({"imported": len(items), "dir": str(d)}, args, "Imported %d manual observation(s) (labelled 'Stichprobe')." % len(items))
    return cli.EXIT_OK


# ---------------------------------------------------------------- step 4: collect

def page_data(url: str, html: str, b: Dict[str, Any], svc_name: Optional[str], town: Optional[str]) -> Dict[str, Any]:
    p = htmlx.parse(html, url)
    text = p.text or ""
    low = fold_umlauts(text.lower())
    title_h1 = " ".join([p.title or ""] + _h1(p))
    path = urlparse(url).path.lower()
    evidence = len(UNIT_RE.findall(text)) + sum(1 for i in p.images if (i.get("alt") or "").strip() and len((i.get("alt") or "")) > 15)
    if path in ("", "/"):
        ptype = "home"
    elif re.search(r"kosten|preis", path):
        ptype = "cost"
    elif re.search(r"referenz|projekt", path):
        ptype = "case_study"
    elif town and contains_town(path.replace("-", " "), town):
        ptype = "service_town"
    else:
        ptype = "service" if svc_name and fold_umlauts(svc_name.lower().split()[0]) in fold_umlauts(path) else "article"
    sub = {k: bool(re.search(v, low)) for k, v in SUBQ.items()}
    return {"url": url, "page_type": ptype, "title": p.title, "h1": _h1(p)[:2],
            "title_h1_service": bool(svc_name and contains_term(title_h1, svc_name.split()[0])),
            "title_h1_town": bool(town and contains_town(title_h1, town)),
            "words": len(words(text)), "subquestions": sum(sub.values()), "subquestions_detail": sub,
            "evidence_items": evidence, "town_mentions": len(re.findall(re.escape(fold_umlauts((town or "#").lower())), low)),
            "schema_types": sorted(set(p.schema_types() if callable(getattr(p, "schema_types", None)) else [])),
            "tel_link": bool(p.tel_links), "https": url.startswith("https://"),
            "dedicated": ptype in ("service", "service_town", "cost") or bool(svc_name and contains_term(title_h1, svc_name.split()[0])),
            "links": [urljoin(url, l.get("href") or l.get("url") or "") for l in p.links][:300]}


def _fetch(url: str, allow_private: bool = False) -> Optional[str]:
    try:
        if not http.robots_allows(url, allow_private=allow_private):
            return None
        r = http.fetch(url, timeout=20, max_bytes=2_000_000, allow_private=allow_private)
        return r.text if r.ok and "html" in r.content_type else None
    except http.FetchError:
        return None


def collect_domain(url: str, b: Dict[str, Any], svc: Optional[str], town: Optional[str], cap: int, allow_private: bool) -> Dict[str, Any]:
    html = _fetch(url, allow_private)
    if html is None:
        return {"url": url, "not_checked": ["page"]}
    data = page_data(url, html, b, svc, town)
    h = host(url)
    home = "%s://%s/" % (urlparse(url).scheme, urlparse(url).netloc)
    sample = [home] + [l for l in data["links"] if host(l) == h][: cap * 3]
    seen, inlinks, pages = set(), 0, 0
    target = url.split("#")[0].rstrip("/")
    for s in sample:
        s0 = s.split("#")[0]
        if s0 in seen or s0.rstrip("/") == target or pages >= cap:
            continue
        seen.add(s0)
        h2 = _fetch(s0, allow_private)
        pages += 1
        if h2 and any(urljoin(s0, l.get("href") or "").split("#")[0].rstrip("/") == target for l in htmlx.parse(h2, s0).links):
            inlinks += 1
    data["internal_inlinks"] = inlinks
    data["sampled_pages"] = pages
    data.pop("links", None)
    return data


def _optional(cap: str, params: Dict[str, Any], state: Path, execute: bool) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        return pv.call(cap, params, state=state, execute=execute), None
    except pv.NotExecuted:
        return None, "dry_run"
    except pv.NoProvider:
        return None, "no_provider"
    except http.FetchError as ex:
        return None, "error: %s" % ex


def cmd_collect(args: Any) -> int:
    state = st.require_state(args)
    b, cfg = st.load_business(state) or {}, st.load_config(state)
    d = latest_tdir(state) if not args.date else state / "teardowns" / args.date
    if not d:
        cli.die(cli.EXIT_USAGE, "no teardown observations; run `observe` or `import` first")
    cap = (cfg.get("caps") or {}).get("competitor_pages", 8)
    client_host = host(b.get("url"))
    cache: Dict[str, Any] = {}
    svc_names = {s["id"]: s["name"] for s in b.get("services", [])}
    for f in sorted((d / "obs").glob("*.json")):
        obs = st.load_json(f)
        org = (obs.get("surfaces") or {}).get("organic")
        svc = svc_names.get(obs.get("service") or "") or next(iter(svc_names.values()), None)
        if org:
            for r in org.get("results", []):
                r["domain"] = r.get("domain") or host(r.get("url"))
                r["domain_type"] = domain_type(r["domain"], client_host)
            top = org.get("results", [])[:3]
            org["serp_class"] = "portal_dominated" if sum(1 for r in top if r["domain_type"] not in ("business", "client")) >= \
                cfg["thresholds"]["teardown"]["portal_dominated_min_non_business"] else "business"
            cr = next((r for r in org.get("results", []) if r["domain_type"] == "client"), None)
            org["client_rank"] = cr["rank"] if cr else None
            for r in top:
                if r["domain_type"] != "business":
                    continue
                key = r["url"]
                if key not in cache:
                    cache[key] = collect_domain(r["url"], b, svc, obs.get("town"), cap, args.allow_private)
                    bl, why = _optional("backlinks", {"target": r["domain"]}, state, args.execute)
                    cache[key]["referring_domains"] = (bl or {}).get("referring_domains")
                    age, why2 = _optional("domain_age", {"domain": r["domain"]}, state, args.execute)
                    cache[key]["first_seen"] = (age or {}).get("first_seen")
                    cache[key]["not_checked"] = [k for k, w in (("referring_domains", why), ("domain_age", why2)) if w]
                r["data"] = cache[key]
        # client page for this query
        tp = obs.get("target_page") or next((c.get("target_page") for c in (st.load_json(state / "keywords.json", {}) or {}).get("clusters", [])
                                             if obs["query"] in [q.lower() for q in c.get("queries", [])]), None) or "/"
        curl = urljoin(b.get("url") or "", tp.split("#")[0] or "/")
        if curl not in cache:
            cache[curl] = collect_domain(curl, b, svc, obs.get("town"), cap, args.allow_private)
            bl, why = _optional("backlinks", {"target": client_host}, state, args.execute)
            cache[curl]["referring_domains"] = (bl or {}).get("referring_domains")
            age, why2 = _optional("domain_age", {"domain": client_host}, state, args.execute)
            cache[curl]["first_seen"] = (age or {}).get("first_seen")
            cache[curl]["not_checked"] = [k for k, w in (("referring_domains", why), ("domain_age", why2)) if w]
        obs["client_page"] = cache[curl]
        st.save_json(f, obs)
    cli.emit({"dir": str(d), "pages_collected": len(cache)}, args, "Collected %d pages (robots.txt respected, GET only)." % len(cache))
    return cli.EXIT_OK


# ---------------------------------------------------------------- step 5/6: score and winnability

def _years(first_seen: Optional[str]) -> Optional[float]:
    dt = st.parse_date(first_seen)
    return round((st.today_date() - dt).days / 365.25, 1) if dt else None


def num_gap(client: Optional[float], ref: Optional[float]) -> Optional[float]:
    if client is None or ref is None:
        return None
    if ref <= 0:
        return 0.0
    return round(max(0.0, min(1.0, (ref - client) / ref)), 3)


def factor(fid: str, weight: float, client: Any, ref: Any, gap: Optional[float]) -> Dict[str, Any]:
    return {"id": fid, "weight": weight, "client": client, "reference": ref, "gap": gap,
            "status": "checked" if gap is not None else "not_checked"}


def composite(factors: List[Dict[str, Any]]) -> Dict[str, Any]:
    chk = [f for f in factors if f["gap"] is not None]
    tw = sum(f["weight"] for f in factors) or 1
    cw = sum(f["weight"] for f in chk)
    return {"factors": factors, "composite": round(sum(f["gap"] * f["weight"] for f in chk) / cw, 3) if cw else None,
            "confidence": round(cw / tw, 2), "not_checked": [f["id"] for f in factors if f["gap"] is None]}


def _med(vals: List[Any]) -> Optional[float]:
    v = [x for x in vals if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return median(v) if v else None


def score_organic(org: Dict[str, Any], client: Dict[str, Any], w: Dict[str, float], psi: Dict[str, Any]) -> Dict[str, Any]:
    wins = [r.get("data") for r in org.get("results", [])[:3] if r.get("domain_type") == "business" and r.get("data") and "page" not in r["data"].get("not_checked", [])]
    if org.get("serp_class") == "portal_dominated" and not wins:
        wins = [r.get("data") for r in org.get("results", [])[:10] if r.get("domain_type") == "business" and r.get("data")][:1]
    if not wins or "page" in client.get("not_checked", []):
        return composite([factor(k, v, None, None, None) for k, v in w.items()])
    cm = lambda k: client.get(k)  # noqa: E731
    th = lambda x: int(bool(x.get("title_h1_service"))) + int(bool(x.get("title_h1_town")))  # noqa: E731
    geo = lambda x: int(bool(x.get("title_h1_town"))) + min(x.get("town_mentions") or 0, 5) / 5.0  # noqa: E731
    sch = lambda x: sum(1 for t in x.get("schema_types") or [] if t not in ("WebSite", "WebPage", "Organization")) and min(len(x.get("schema_types") or []), 3)  # noqa: E731
    ref_ded = sum(1 for x in wins if x.get("dedicated")) / len(wins)
    rd_c, rd_r = cm("referring_domains"), _med([x.get("referring_domains") for x in wins])
    age_c, age_r = _years(cm("first_seen")), _med([_years(x.get("first_seen")) for x in wins])
    perf = (psi.get(client.get("url")) or {}).get("performance")
    fs = [factor("dedicated_page", w["dedicated_page"], bool(cm("dedicated")), round(ref_ded, 2),
                 (1.0 if ref_ded >= 0.5 else 0.5) if not cm("dedicated") else 0.0),
          factor("geo_relevance", w["geo_relevance"], geo(client), _med([geo(x) for x in wins]), num_gap(geo(client), _med([geo(x) for x in wins]))),
          factor("referring_domains", w["referring_domains"], rd_c, rd_r, num_gap(rd_c, rd_r)),
          factor("title_h1", w["title_h1"], th(client), _med([th(x) for x in wins]), num_gap(th(client), _med([th(x) for x in wins]))),
          factor("subquestions", w["subquestions"], cm("subquestions"), _med([x.get("subquestions") for x in wins]),
                 num_gap(cm("subquestions"), _med([x.get("subquestions") for x in wins]))),
          factor("evidence_depth", w["evidence_depth"], cm("evidence_items"), _med([x.get("evidence_items") for x in wins]),
                 num_gap(cm("evidence_items"), _med([x.get("evidence_items") for x in wins]))),
          factor("internal_links", w["internal_links"], cm("internal_inlinks"), _med([x.get("internal_inlinks") for x in wins]),
                 num_gap(cm("internal_inlinks"), _med([x.get("internal_inlinks") for x in wins]))),
          factor("domain_age", w["domain_age"], age_c, age_r, num_gap(age_c, age_r)),
          factor("page_experience", w["page_experience"], perf, 90 if perf is not None else None, num_gap(perf, 90) if perf is not None else None),
          factor("schema_entity", w["schema_entity"], sch(client), _med([sch(x) for x in wins]), num_gap(sch(client), _med([sch(x) for x in wins])))]
    out = composite(fs)
    out["reference_rd_list"] = [x.get("referring_domains") for x in wins]
    return out


def _dist_km(a: Tuple[Any, Any], b: Tuple[Any, Any]) -> Optional[float]:
    import math
    if None in a or None in b:
        return None
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)), 1)


def score_pack(pack: Dict[str, Any], b: Dict[str, Any], gbp: Dict[str, Any], town: Dict[str, Any], w: Dict[str, float],
               client_page: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rows = pack.get("results", [])
    name = norm_name(b.get("name"), True)
    client_row = next((r for r in rows if norm_name(r.get("name"), True) == name or (r.get("website") and host(r["website"]) == host(b.get("url")))), None)
    wins = [r for r in rows[:3] if r is not client_row]
    prof, rev = (gbp or {}).get("profile") or {}, (gbp or {}).get("reviews") or {}
    center = (town.get("lat"), town.get("lng")) if town.get("lat") else ((b.get("geo") or {}).get("lat"), (b.get("geo") or {}).get("lng"))
    my_cat = prof.get("primary_category") or (b.get("gbp") or {}).get("primary_category")
    win_cats = [fold_umlauts((r.get("category") or "").lower()) for r in wins if r.get("category")]
    cat_gap = None if not (my_cat and win_cats) else (0.0 if fold_umlauts(my_cat.lower()) in win_cats else 1.0)
    rc = rev.get("count") if rev.get("count") is not None else (client_row or {}).get("reviews")
    rr = rev.get("rating") if rev.get("rating") is not None else (client_row or {}).get("rating")
    win_d = _med([_dist_km(center, (r.get("lat"), r.get("lng"))) for r in wins])
    my_d = _dist_km(center, ((b.get("geo") or {}).get("lat"), (b.get("geo") or {}).get("lng")))
    td = cfg["thresholds"]["teardown"]
    max_km = td["pack_max_km_large_town"] if (town.get("population") or 0) >= td["large_town_population"] else td["pack_max_km"]
    in_town = fold_umlauts(((b.get("address") or {}).get("city") or "").lower()) == fold_umlauts((town.get("town") or "").lower())
    prox_gap = 0.0 if in_town else (None if my_d is None else round(min(1.0, max(0.0, (my_d - (win_d or 0)) / max_km)), 3))
    filled = sum(1 for k in ("primary_category", "description", "hours", "services", "website_url", "phone") if prof.get(k)) if prof else None
    th = lambda x: int(bool(x.get("title_h1_service"))) + int(bool(x.get("title_h1_town")))  # noqa: E731
    fs = [factor("primary_category", w["primary_category"], my_cat, sorted(set(win_cats)), cat_gap),
          factor("proximity", w["proximity"], my_d, win_d, prox_gap),
          factor("review_count", w["review_count"], rc, _med([r.get("reviews") for r in wins]), num_gap(rc, _med([r.get("reviews") for r in wins]))),
          factor("review_recency", w["review_recency"], rev.get("last_90"), None, None),
          factor("rating", w["rating"], rr, _med([r.get("rating") for r in wins]), num_gap(rr, _med([r.get("rating") for r in wins]))),
          factor("profile_completeness", w["profile_completeness"], filled, 6 if filled is not None else None, num_gap(filled, 6) if filled is not None else None),
          factor("landing_title_h1", w["landing_title_h1"], th(client_page) if client_page.get("title") is not None else None, 2,
                 num_gap(th(client_page), 2) if client_page.get("title") is not None else None),
          factor("landing_links", w["landing_links"], client_page.get("internal_inlinks"), 3,
                 num_gap(client_page.get("internal_inlinks"), 3) if client_page.get("internal_inlinks") is not None else None),
          factor("nap_match", w["nap_match"], None, None, None)]
    out = composite(fs)
    out["client_rank"] = (client_row or {}).get("rank")
    meta = {"in_town": in_town, "distance_km": my_d, "max_km": max_km, "winners_have_address_in_town": None,
            "winner_review_median": _med([r.get("reviews") for r in wins]), "client_reviews": rc, "client_rating": rr}
    return out, meta


def score_ai(panel: Optional[Dict[str, Any]], b: Dict[str, Any], gbp: Dict[str, Any], organic: Dict[str, Any],
             offsite: Dict[str, Any], bing: Optional[Dict[str, Any]], w: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, Any]:
    rev = (gbp or {}).get("reviews") or {}
    td = cfg["thresholds"]["teardown"]
    rating, count = rev.get("rating"), rev.get("count")
    rv_gap = None if rating is None or count is None else round(max(0.0, (td["ai_min_rating"] - rating) / td["ai_min_rating"]) * 0.5
                                                                 + max(0.0, (td["ai_min_reviews"] - count) / td["ai_min_reviews"]) * 0.5, 3)
    ded = next((f for f in organic.get("factors", []) if f["id"] == "dedicated_page"), {})
    listed = {host(x.get("url") or x.get("domain") or "") for x in (offsite or {}).get("entries", []) if x.get("status") in ("live", "verified", "listed")}
    cited = [c["domain"] for c in (panel or {}).get("cited_domains", [])[:15] if c.get("domain")] if panel else []
    pres_gap = None if not panel else (round(1 - len([c for c in cited if c in listed]) / len(cited), 3) if cited else 0.0)
    bing_gap = None
    if bing:
        bing_gap = 0.0 if any(host(r.get("page") or "") == host(b.get("url")) for r in bing.get("pages", []) or bing.get("rows", [])) else 1.0
    mentions = len([x for x in (offsite or {}).get("entries", []) if x.get("kind") in ("press", "mention", "membership") and x.get("status") in ("live", "verified")])
    fs = [factor("cited_domains_presence", w["cited_domains_presence"], len(cited) - int((pres_gap or 0) * len(cited)) if panel else None, len(cited) if panel else None, pres_gap),
          factor("rating_volume", w["rating_volume"], {"rating": rating, "count": count}, {"rating": td["ai_min_rating"], "count": td["ai_min_reviews"]}, rv_gap),
          factor("dedicated_page_facts", w["dedicated_page_facts"], ded.get("client"), ded.get("reference"), ded.get("gap")),
          factor("third_party_mentions", w["third_party_mentions"], mentions if offsite else None, 3 if offsite else None, num_gap(mentions, 3) if offsite else None),
          factor("bing_indexed", w["bing_indexed"], None if bing_gap is None else bing_gap == 0, True, bing_gap)]
    out = composite(fs)
    if panel:
        out["client_mention_rate"] = panel.get("client_mention_rate")
        out["named_businesses"] = panel.get("named", [])[:5]
    return out


def winnability(surface: str, s: Dict[str, Any], cfg: Dict[str, Any], meta: Optional[Dict[str, Any]] = None,
                org: Optional[Dict[str, Any]] = None, b: Optional[Dict[str, Any]] = None, gbp: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    td = cfg["thresholds"]["teardown"]
    g = s.get("composite")
    if g is None:
        return {"class": "not_checked", "reasons": ["keine Beobachtung für diese Oberfläche"]}
    if surface == "organic":
        rank = (org or {}).get("client_rank")
        lo, hi = td["organic_now_positions"]
        rds = [x for x in s.get("reference_rd_list", []) if x is not None]
        crd = next((f["client"] for f in s["factors"] if f["id"] == "referring_domains"), None)
        if (org or {}).get("serp_class") == "portal_dominated":
            return {"class": "long_term", "reasons": ["Portale dominieren die Top 3: dort gelistet und stark sein, erster Platz für Betriebe ist das Ziel"]}
        if rank and lo <= rank <= hi and g < td["organic_now_max_gap"]:
            return {"class": "now", "reasons": ["bereits Position %s, Abstand %.2f" % (rank, g)]}
        if rds and crd is not None and all(x > td["organic_long_term_rd_multiple"] * max(crd, 1) and x > td["organic_long_term_rd_absolute"] for x in rds):
            return {"class": "long_term", "reasons": ["alle Gewinner haben über 10-mal mehr verweisende Domains"]}
        if g <= td["organic_with_work_max_gap"] or (rds and crd is not None and any(x <= td["organic_with_work_rd_multiple"] * max(crd, 1) or x <= td["organic_with_work_rd_absolute"] for x in rds)):
            return {"class": "with_work", "reasons": ["Abstand %.2f, Linkprofil der Gewinner erreichbar" % g]}
        return {"class": "long_term", "reasons": ["Abstand %.2f" % g]}
    if surface == "pack":
        meta = meta or {}
        if not meta.get("in_town") and meta.get("distance_km") is not None and meta["distance_km"] > meta.get("max_km", 15):
            return {"class": "out_of_radius", "reasons": ["%.1f km vom Suchort (Grenze %s km): organisch angreifen; Anzeigen nur als Hinweis" % (meta["distance_km"], meta["max_km"])]}
        med, mine = meta.get("winner_review_median"), meta.get("client_reviews")
        if med and mine is not None and mine < td["pack_with_work_review_share"] * med:
            vel = max(1.0, (((gbp or {}).get("reviews") or {}).get("last_90") or 0) / 3.0) or 1.0
            months = round((med - mine) / max(vel, 2.0), 1)
            return {"class": "with_work", "reasons": ["%s Bewertungen gegenüber Median %s: etwa %s Monate bei realistischer Rate" % (mine, med, months)], "months": months}
        return {"class": "now", "reasons": ["im Radius; Hauptlücke: %s" % (max(s["factors"], key=lambda f: (f["gap"] or 0) * f["weight"])["id"])]}
    rv = next((f for f in s["factors"] if f["id"] == "rating_volume"), {})
    ded = next((f for f in s["factors"] if f["id"] == "dedicated_page_facts"), {})
    if (rv.get("gap") or 0) > 0 or (ded.get("gap") or 0) >= 0.5:
        return {"class": "blocked_by_basics", "reasons": ["erst Bewertungsbasis (≥ %s, ≥ %s Bewertungen) und eigene Leistungsseite" % (td["ai_min_rating"], td["ai_min_reviews"])]}
    return {"class": "with_work", "reasons": ["Basis vorhanden; fehlt auf zitierten Quellen"]}


def cmd_score(args: Any) -> int:
    state = st.require_state(args)
    b, cfg = st.load_business(state) or {}, st.load_config(state)
    d = latest_tdir(state) if not args.date else state / "teardowns" / args.date
    if not d:
        cli.die(cli.EXIT_USAGE, "no teardown; run observe/import and collect first")
    W = cfg["thresholds"]["teardown"]["weights"]
    gbp = st.load_latest_snapshot(state, "gbp") or {}
    panel = st.load_latest_snapshot(state, "ai-panel")
    bing = st.load_latest_snapshot(state, "bing")
    offsite = st.load_json(state / "offsite.json", {}) or {}
    psi = {p["url"]: p for p in (st.load_latest_snapshot(state, "psi") or {}).get("pages", [])}
    out_files = []
    for f in sorted((d / "obs").glob("*.json")):
        obs = st.load_json(f)
        surf = obs.get("surfaces") or {}
        client_page = obs.get("client_page") or {"not_checked": ["page"]}
        town = _town(b, obs.get("town")) or {"town": obs.get("town")}
        res: Dict[str, Any] = {"query": obs["query"], "class": obs.get("class"), "town": obs.get("town"), "observed_at": st.now_iso(), "surfaces": {}}
        org = surf.get("organic")
        if org:
            s = score_organic(org, client_page, W["organic"], psi)
            res["surfaces"]["organic"] = {"origin": org.get("origin"), "localised": org.get("localised"), "serp_class": org.get("serp_class"),
                                          "client_rank": org.get("client_rank"),
                                          "winners": [{k: r.get(k) for k in ("rank", "url", "domain", "domain_type", "data")} for r in org.get("results", [])[:3]],
                                          "gap": s, "winnability": winnability("organic", s, cfg, org=org)}
        else:
            res["surfaces"]["organic"] = {"status": "not_checked"}
        pack = surf.get("pack")
        if pack:
            s, meta = score_pack(pack, b, gbp, town, W["pack"], client_page, cfg)
            res["surfaces"]["pack"] = {"origin": pack.get("origin"), "winners": pack.get("results", [])[:3], "client_rank": s.get("client_rank"),
                                       "gap": s, "meta": meta, "winnability": winnability("pack", s, cfg, meta=meta, gbp=gbp)}
        else:
            res["surfaces"]["pack"] = {"status": "not_checked"}
        if obs.get("class") in ("best", "need", "cost", "service_town") and (panel or org):
            s = score_ai(panel, b, gbp, (res["surfaces"].get("organic") or {}).get("gap") or {}, offsite, bing, W["ai"], cfg)
            res["surfaces"]["ai"] = {"origin": (panel or {}).get("origin"), "gap": s, "winnability": winnability("ai", s, cfg)}
        out = d / ("%s.json" % st.slugify(obs["query"]))
        st.save_json(out, res)
        out_files.append(str(out))
    cli.emit({"scored": len(out_files), "dir": str(d)}, args, "Scored %d queries in %s." % (len(out_files), d))
    return cli.EXIT_OK


# ---------------------------------------------------------------- step 7: backlog and summary

def backlog_items(td: Dict[str, Any], value: float, cfg: Dict[str, Any], tier: str) -> List[Dict[str, Any]]:
    wf = cfg["thresholds"]["teardown"]["winnability_factor"]
    ew = cfg["thresholds"]["teardown"]["effort_weight"]
    items = []
    for surface, s in (td.get("surfaces") or {}).items():
        g = (s or {}).get("gap")
        if not g or g.get("composite") is None:
            continue
        win = (s.get("winnability") or {}).get("class", "with_work")
        factors = sorted([f for f in g["factors"] if f["gap"]], key=lambda f: -(f["gap"] * f["weight"]))
        tot = sum(f["gap"] * f["weight"] for f in factors) or 1
        for f in factors[:3]:
            act, signal, window, why = GAP_ACTION.get(f["id"], (None, None, None, f["id"]))
            if not act:
                continue
            if act == "new_page" and tier not in ("scale",):
                act_eff, note = "onpage_rewrite", "Einseiter: Abschnitt auf der Landingpage stärken; eigene Seite als Angebot (Scope)"
            else:
                act_eff, note = act, None
            share = round(f["gap"] * f["weight"] / tot, 3)
            prio = round(value * wf.get(win, 0.6) * share / ew[EFFORT.get(act_eff, "M")], 3)
            if prio <= 0:
                continue
            items.append({"key": "%s:%s" % (act_eff, f["id"]), "action_type": act_eff, "gap_factor": f["id"], "surface": surface,
                          "queries": [td["query"]], "reason_de": why, "note_de": note, "first_signal_de": signal, "evaluate_after_days": window,
                          "winnability": win, "gap_share": share, "priority": prio, "scope_proposal": act == "new_page" and tier != "scale"})
    return items


def merge_backlog(state: Path, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    path = state / "backlog.json"
    bl = st.load_json(path, {"schema_version": 1, "items": []})
    keep = [i for i in bl.get("items", []) if i.get("source") != "teardown" or i.get("status") not in (None, "open")]
    merged: Dict[str, Dict[str, Any]] = {}
    for it in items:
        m = merged.get(it["key"])
        if m:
            m["queries"] = sorted(set(m["queries"] + it["queries"]))
            m["priority"] = round(m["priority"] + it["priority"], 3)
        else:
            merged[it["key"]] = dict(it, source="teardown", status="open", created=st.today())
    bl["items"] = keep + sorted(merged.values(), key=lambda x: -x["priority"])
    bl["teardown_date"] = st.today()
    st.save_json(path, bl)
    return bl


def cmd_backlog(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    d = latest_tdir(state)
    if not d:
        cli.die(cli.EXIT_USAGE, "no teardown")
    tier = cfg.get("tier") or "unknown"
    values = {q["query"]: q.get("value", 1) for q in build_queries(st.load_business(state) or {}, cfg, demand_map(state))}
    items = []
    for f in sorted(d.glob("*.json")):
        if f.name == "summary.json":
            continue
        td = st.load_json(f)
        items += backlog_items(td, values.get(td["query"], 1.0), cfg, tier)
    bl = merge_backlog(state, items)
    top = [i for i in bl["items"] if i.get("source") == "teardown"][:10]
    cli.emit(top, args, "\n".join("%.2f  %-18s %-22s %s (%d Suchanfragen)" % (i["priority"], i["action_type"], i["gap_factor"], i["reason_de"], len(i["queries"])) for i in top))
    return cli.EXIT_OK


def cmd_summary(args: Any) -> int:
    state = st.require_state(args)
    d = latest_tdir(state)
    if not d:
        cli.die(cli.EXIT_USAGE, "no teardown")
    rows, pack_winners = [], []
    for f in sorted(d.glob("*.json")):
        if f.name == "summary.json":
            continue
        td = st.load_json(f)
        row = {"query": td["query"]}
        for s in ("organic", "pack", "ai"):
            x = (td.get("surfaces") or {}).get(s) or {}
            g = x.get("gap") or {}
            row[s] = {"class": (x.get("winnability") or {}).get("class", "not_checked"), "gap": g.get("composite"),
                      "confidence": g.get("confidence"), "client_rank": x.get("client_rank")}
            if s == "pack":
                for w in x.get("winners") or []:
                    pack_winners.append({"name": w.get("name"), "category": w.get("category"), "review_count": w.get("reviews"), "rating": w.get("rating")})
        rows.append(row)
    summary = {"date": d.name, "valid_until_days": st.load_config(state)["thresholds"]["teardown"]["valid_days"], "queries": rows,
               "pack_winners": pack_winners[:20]}
    st.save_json(d / "summary.json", summary)
    lines = ["Teardown %s (gültig %s Tage)" % (d.name, summary["valid_until_days"]), "%-40s %-16s %-16s %-16s" % ("Suchanfrage", "Organisch", "Maps", "KI")]
    for r in rows:
        fmt = lambda s: ("%s %s" % (r[s]["class"], "" if r[s]["gap"] is None else "%.2f" % r[s]["gap"]))[:16]  # noqa: E731
        lines.append("%-40s %-16s %-16s %-16s" % (r["query"][:40], fmt("organic"), fmt("pack"), fmt("ai")))
    cli.emit(summary, args, "\n".join(lines))
    return cli.EXIT_OK


def cmd_run(args: Any) -> int:
    for fn in (cmd_observe, cmd_collect, cmd_score, cmd_backlog, cmd_summary):
        if fn is cmd_observe:
            args.query, args.refresh = getattr(args, "query", None), getattr(args, "refresh", False)
        if fn in (cmd_collect, cmd_score):
            args.date = None
        code = fn(args)
        if code not in (cli.EXIT_OK,):
            return code
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  serp_teardown.py queries --write\n  serp_teardown.py run            # dry run for paid observations\n  serp_teardown.py run --execute")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "queries", "build target queries from business.json (step 1)")
    sp.add_argument("--write", action="store_true", help="store them in keywords.json with target: true")
    sp.set_defaults(fn=cmd_queries)
    sp = cli.add_sub(subs, "observe", "observe organic and maps via the provider layer (step 2)")
    sp.add_argument("--query", nargs="*", default=None)
    sp.add_argument("--refresh", action="store_true")
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_observe)
    sp = cli.add_sub(subs, "import", "import a manual observation (references/method.md has the 5-minute procedure)")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_import)
    for name, fn, h in (("collect", cmd_collect, "fetch winners and the client page (step 4)"),
                        ("score", cmd_score, "gap per factor and winnability (steps 5-6)")):
        sp = cli.add_sub(subs, name, h)
        sp.add_argument("--date", default=None)
        sp.add_argument("--execute", action="store_true", help="allow paid backlinks/age lookups")
        sp.add_argument("--allow-private", action="store_true", help="tests only")
        sp.add_argument("--http-fixture", default=None, help="answer fetches from a fixture map (tests, demos)")
        sp.set_defaults(fn=fn)
    cli.add_sub(subs, "backlog", "gap -> action -> expected time into backlog.json (step 7)").set_defaults(fn=cmd_backlog)
    cli.add_sub(subs, "summary", "summary.json and a table").set_defaults(fn=cmd_summary)
    sp = cli.add_sub(subs, "run", "observe, collect, score, backlog, summary")
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--allow-private", action="store_true")
    sp.add_argument("--http-fixture", default=None)
    sp.set_defaults(fn=cmd_run)
    args = p.parse_args()
    if getattr(args, "http_fixture", None):
        http.use_fixture(args.http_fixture)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
