#!/usr/bin/env python3
"""Technical, on-page, CRO, legal-surface and tracking-surface audit for twwa-growth.

dist <dir>     audit the built Astro output against astro.config, vercel.json and business.json
live <url>     polite crawl (default 25 pages, robots.txt respected, GET only, forms are never submitted)
page <x>       one URL or one HTML file
linkgraph      internal link graph: inlinks, orphans, click depth, anchors
redirects      vercel.json redirect integrity: chains, loops, targets, anchors, old URLs that 404

Findings use the section 4.3 schema with German title_de and detail_de. Without a state folder
(prospect mode) business facts are inferred from the Impressum and marked as inferred."""
from __future__ import annotations

import datetime as _dt
import os
import random
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, http, state as st, textde  # noqa: E402
import legal_lint  # noqa: E402
import schema_gen  # noqa: E402
import twwa_state  # noqa: E402

SEARCH_BOTS = ["googlebot", "bingbot"]
ANSWER_BOTS = ["oai-searchbot", "chatgpt-user", "perplexitybot", "claude-searchbot", "claude-user", "perplexity-user", "applebot"]
TRAINING_BOTS = ["gptbot", "google-extended", "ccbot", "claudebot", "anthropic-ai", "applebot-extended", "bytespider", "meta-externalagent", "amazonbot", "cohere-ai"]
CTA_RE = re.compile(r"\b(anrufen|jetzt anfragen|anfrage|angebot|termin|kontakt|schreiben sie|whatsapp|rückruf|beratung|jetzt buchen|anmelden)\b", re.IGNORECASE)
SOURCE_FIELD_RE = re.compile(r"(wie haben sie uns gefunden|wie sind sie auf uns|aufmerksam geworden|woher kennen sie|\bquelle\b|gefunden über)", re.IGNORECASE)
PHONE_IN_TEXT = re.compile(r"(?<!\d)(?:\+49[\s/()0-9\-]{8,}|0\d{2,5}\s*[/\-]?\s*\d[\d \-]{4,}\d)")
LEGAL_PATH = re.compile(r"(impressum|datenschutz|privacy|agb|404|danke)", re.IGNORECASE)
INDEXNOW_KEY = re.compile(r"^[A-Za-z0-9\-]{8,128}$")
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def F(*a: Any, **k: Any) -> Dict[str, Any]:
    return cli.finding(*a, **k)


# ---------------------------------------------------------------- context

class Ctx:
    def __init__(self, args: Any, mode: str):
        self.mode = mode
        self.args = args
        self.state = st.resolve_state_arg(getattr(args, "state", None))
        self.cfg = st.load_config(self.state)
        self.business = st.load_business(self.state) if self.state else None
        if self.business and not self.business.get("name"):
            self.business = None
        self.facts_source = "business.json" if self.business else None
        self.repo: Optional[Path] = None
        self.det: Dict[str, Any] = {}
        self.site_url: Optional[str] = None
        self.slash: Optional[str] = None
        self.pages: Dict[str, Dict[str, Any]] = {}
        self.robots: Dict[str, Any] = {"status": None, "text": None}
        self.sitemap: Dict[str, Any] = {"found": False, "urls": [], "error": None}
        self.findings: List[Dict[str, Any]] = []
        self.redirects: List[Dict[str, Any]] = []
        self.vercel_headers: List[Dict[str, Any]] = []
        self.files: Set[str] = set()
        self.extra: Dict[str, Any] = {}

    def add(self, f: Dict[str, Any]) -> None:
        if self.facts_source and self.facts_source.startswith("impressum") and f["area"] in ("onpage", "tech", "cro") and "abgeleitet" not in f["detail_de"]:
            if any(k in f["id"] for k in ("nap", "title.no", "h1.no", "tel_mismatch")):
                f["detail_de"] += " (Stammdaten aus dem Impressum abgeleitet.)"
        key = (f["id"], f["evidence"].get("url"), f["evidence"].get("snippet"))
        if not any((x["id"], x["evidence"].get("url"), x["evidence"].get("snippet")) == key for x in self.findings):
            self.findings.append(f)

    @property
    def towns(self) -> List[str]:
        b = self.business or {}
        out = [t.get("town") for t in b.get("service_area") or [] if t.get("town")]
        c = (b.get("address") or {}).get("city")
        if c and c not in out:
            out.insert(0, c)
        return out

    def money_pages(self) -> List[str]:
        mp = list((self.cfg.get("site") or {}).get("money_pages") or ["/"])
        for s in (self.business or {}).get("services") or []:
            p = (s.get("page") or "").split("#")[0]
            if p and p not in mp:
                mp.append(p)
        out = [self.norm_path(p) for p in mp]
        ids = [s.get("id") for s in (self.business or {}).get("services") or [] if s.get("id")]
        for path in self.pages:
            if any(i in path.lower() for i in ids) and path not in out:
                out.append(path)
        return out

    def norm_path(self, p: str) -> str:
        p = (p or "/").split("#")[0].split("?")[0]
        if not p.startswith("/"):
            p = "/" + p
        p = re.sub(r"/index(\.html)?$", "/", p)
        p = re.sub(r"\.html$", "", p)
        if p != "/":
            p = p.rstrip("/") if self.slash != "always" else (p if p.endswith("/") else p + "/")
        return p or "/"

    def url_of(self, path: str) -> str:
        return (self.site_url or "https://site.invalid").rstrip("/") + path


# ---------------------------------------------------------------- vercel helpers

def vp_regex(source: str) -> re.Pattern:
    """Rough path-to-regexp conversion for vercel.json sources."""
    out = ""
    i = 0
    while i < len(source):
        ch = source[i]
        if ch == ":":
            m = re.match(r":(\w+)([*+?]?)", source[i:])
            if m:
                out += "(.*)" if m.group(2) in ("*", "+") else "([^/]+)"
                i += len(m.group(0))
                continue
        if ch == "(":
            j = source.find(")", i)
            out += source[i:j + 1]
            i = j + 1
            continue
        out += re.escape(ch) if ch not in "*" else ".*"
        i += 1
    return re.compile("^" + out + "/?$")


def load_vercel(ctx: Ctx) -> None:
    if not ctx.repo:
        return
    vj = st.load_json(ctx.repo / "vercel.json", None)
    if not isinstance(vj, dict):
        return
    ctx.extra["vercel"] = vj
    for r in vj.get("redirects") or []:
        if r.get("source"):
            ctx.redirects.append({"source": r["source"], "destination": r.get("destination", ""), "permanent": r.get("permanent", True),
                                  "regex": vp_regex(r["source"]), "literal": not re.search(r"[:(*]", r["source"])})
    ctx.vercel_headers = vj.get("headers") or []


def redirect_for(ctx: Ctx, path: str) -> Optional[Dict[str, Any]]:
    for r in ctx.redirects:
        if r["regex"].match(path):
            return r
    return None


def dist_header_robots(ctx: Ctx, path: str) -> str:
    vals = []
    for h in ctx.vercel_headers:
        if any(c.get("type") == "host" for c in h.get("has") or []):
            continue
        try:
            if not vp_regex(h.get("source", "")).match(path):
                continue
        except re.error:
            continue
        for kv in h.get("headers") or []:
            if kv.get("key", "").lower() == "x-robots-tag":
                vals.append(str(kv.get("value", "")).lower())
    return ", ".join(vals)


# ---------------------------------------------------------------- business facts in prospect mode

def infer_from_impressum(page: htmlx.Page, url: str) -> Dict[str, Any]:
    t = page.full_text
    b: Dict[str, Any] = {"inferred": True, "source_url": url, "address": {}, "service_area": [], "services": []}
    m = re.search(r"([A-ZÄÖÜ][\w&.\- äöüß]{2,80}?\s(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|UG(?:\s*\(haftungsbeschränkt\))?|AG|KG|OHG|e\.\s?K\.|GbR))", t)
    if m:
        b["name"] = m.group(1).strip()
    else:
        m = re.search(r"(?:Angaben gemäß[^\n]*\n)([^\n]{3,80})", t)
        b["name"] = m.group(1).strip() if m else None
    sm = re.search(r"([A-ZÄÖÜ][\wäöüß\-. ]*(?:straße|strasse|str\.|weg|gasse|platz|allee|ring|damm)\s*\d+\s*[a-z]?)", t, re.IGNORECASE)
    zm = re.search(r"\b(\d{5})\s+([A-ZÄÖÜ][\wäöüß\-]+(?:\s(?:am|an der|im|bei)\s[A-ZÄÖÜ][\wäöüß\-]+)?)", t)
    b["address"] = {"street": sm.group(1).strip() if sm else None, "zip": zm.group(1) if zm else None, "city": zm.group(2) if zm else None, "country": "DE"}
    pm = re.search(r"(?:telefon|tel\.?|fon)\s*:?\s*([+0(][\d\s/()\-]{6,}\d)", t, re.IGNORECASE)
    b["phone"] = pm.group(1).strip() if pm else (page.tel_links[0] if page.tel_links else None)
    em = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    b["email"] = em.group(0) if em else None
    b["address_public"] = True
    return b


# ---------------------------------------------------------------- loading: dist

def path_for_file(rel: str, slash: Optional[str]) -> str:
    rel = rel.replace(os.sep, "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        p = "/" + rel[: -len("/index.html")]
        return p + "/" if slash == "always" else p
    return "/" + rel[:-5]


def load_dist(ctx: Ctx, root: Path) -> None:
    ctx.extra["root"] = str(root)
    repo = Path(ctx.args.repo).resolve() if getattr(ctx.args, "repo", None) else None
    if repo is None:
        for cand in (root.parent, root.parent.parent):
            if any((cand / n).is_file() for n in ("astro.config.mjs", "astro.config.ts", "vercel.json", "package.json")):
                repo = cand
                break
    if repo is None and ctx.state:
        cand = st.repo_root(ctx.state)
        if any((cand / n).is_file() for n in ("astro.config.mjs", "astro.config.ts", "vercel.json", "package.json")):
            repo = cand
    ctx.repo = repo
    if repo:
        ctx.det = twwa_state.detect_repo(repo)
        ctx.slash = (ctx.det.get("astro") or {}).get("trailingSlash")
        load_vercel(ctx)
    ctx.site_url = getattr(ctx.args, "site", None) or (ctx.det.get("astro") or {}).get("site") or (ctx.business or {}).get("url") or (ctx.cfg.get("site") or {}).get("url")
    for f in sorted(root.rglob("*")):
        if f.is_file():
            ctx.files.add("/" + f.relative_to(root).as_posix())
    for f in sorted(root.rglob("*.html")):
        rel = f.relative_to(root).as_posix()
        path = path_for_file(rel, ctx.slash)
        html = f.read_text(encoding="utf-8", errors="replace")
        page = htmlx.parse(html, ctx.url_of(path))
        status = 404 if rel in ("404.html", "404/index.html") else 200
        hdr = dist_header_robots(ctx, path)
        ctx.pages[path] = {"path": path, "url": ctx.url_of(path), "file": str(f), "status": status, "page": page,
                           "header_robots": hdr, "history": [], "content_type": "text/html"}
    rp = root / "robots.txt"
    if rp.is_file():
        ctx.robots = {"status": 200, "text": rp.read_text(encoding="utf-8", errors="replace"), "file": str(rp), "url": ctx.url_of("/robots.txt")}
    else:
        ctx.robots = {"status": 404, "text": None, "url": ctx.url_of("/robots.txt")}
    for name in ("sitemap-index.xml", "sitemap.xml"):
        sp = root / name
        if sp.is_file():
            parse_sitemap_text(ctx, sp.read_text(encoding="utf-8", errors="replace"), str(sp), loader=lambda loc: _dist_child(root, loc))
            break


def _dist_child(root: Path, loc: str) -> Optional[str]:
    p = root / urllib.parse.urlsplit(loc).path.lstrip("/")
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


def parse_sitemap_text(ctx: Ctx, text: str, where: str, loader: Any = None, depth: int = 0) -> None:
    ctx.sitemap["found"] = True
    ctx.sitemap.setdefault("where", where)
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as exc:
        ctx.sitemap["error"] = "XML-Fehler: %s" % exc
        return
    tag = root.tag.replace(SM_NS, "")
    if tag == "sitemapindex":
        for sm in root.findall(SM_NS + "sitemap"):
            loc = (sm.findtext(SM_NS + "loc") or "").strip()
            if loc and loader and depth < 2:
                child = loader(loc)
                if child:
                    parse_sitemap_text(ctx, child, loc, loader, depth + 1)
        return
    for u in root.findall(SM_NS + "url"):
        loc = (u.findtext(SM_NS + "loc") or "").strip()
        lm = (u.findtext(SM_NS + "lastmod") or "").strip() or None
        if loc:
            ctx.sitemap["urls"].append({"loc": loc, "lastmod": lm})


# ---------------------------------------------------------------- loading: live

def load_live(ctx: Ctx, start: str) -> None:
    allow_private = bool(getattr(ctx.args, "allow_private", False))
    if getattr(ctx.args, "fixture", None):
        http.use_fixture(ctx.args.fixture)
    parts = urllib.parse.urlsplit(start)
    base = "%s://%s" % (parts.scheme or "https", parts.netloc)
    ctx.site_url = base
    if ctx.state:
        ctx.repo = st.repo_root(ctx.state)
        ctx.det = twwa_state.detect_repo(ctx.repo)
        ctx.slash = (ctx.det.get("astro") or {}).get("trailingSlash")
        load_vercel(ctx)
    _, rinfo = http.robots_for(base + "/", allow_private=allow_private)
    ctx.robots = {"status": rinfo.get("status"), "text": rinfo.get("text") if (rinfo.get("status") or 500) < 400 else None,
                  "url": rinfo.get("url"), "error": rinfo.get("error"), "content_type": rinfo.get("content_type")}
    limit = int(getattr(ctx.args, "max_pages", None) or ctx.cfg["caps"]["crawl_pages"])
    delay = 0.0 if http.fixture_active() else float(getattr(ctx.args, "delay", 0.5) or 0)
    queue = deque([start])
    seen: Set[str] = set()
    while queue and len(ctx.pages) < limit:
        url = queue.popleft()
        path = ctx.norm_path(urllib.parse.urlsplit(url).path)
        if path in seen:
            continue
        seen.add(path)
        if not http.robots_allows(url, http.UA_TOKEN, allow_private=allow_private):
            ctx.extra.setdefault("robots_skipped", []).append(url)
            continue
        try:
            r = http.fetch(url, allow_private=allow_private)
        except http.FetchError as exc:
            ctx.extra.setdefault("fetch_errors", []).append({"url": url, "error": str(exc)})
            if not ctx.pages:
                cli.die(cli.EXIT_REMOTE, "Could not fetch %s: %s" % (url, exc))
            continue
        if delay:
            time.sleep(delay)
        page = htmlx.parse(r.text, r.url) if "html" in r.content_type else htmlx.parse("", r.url)
        fpath = ctx.norm_path(urllib.parse.urlsplit(r.url).path)
        ctx.pages[path] = {"path": path, "url": url, "final_url": r.url, "file": None, "status": r.status, "page": page,
                           "header_robots": (r.headers.get("x-robots-tag") or "").lower(), "history": r.history, "content_type": r.content_type,
                           "final_path": fpath}
        if r.status >= 400 or "html" not in r.content_type:
            continue
        for l in page.links:
            href = l.get("href") or ""
            sp = htmlx.same_site_path(href, base)
            if sp is None or l.get("raw", "").startswith(("tel:", "mailto:", "#")):
                continue
            if re.search(r"\.(pdf|jpe?g|png|webp|avif|svg|zip|docx?|xlsx?)$", sp, re.IGNORECASE) or sp.startswith("/api/"):
                continue
            q = base + sp
            if ctx.norm_path(sp) not in seen:
                queue.append(q)
    # sitemap
    sm_urls = [l.split(":", 1)[1].strip() for l in (ctx.robots.get("text") or "").splitlines() if l.lower().startswith("sitemap:")]
    for sm in (sm_urls or [base + "/sitemap.xml", base + "/sitemap-index.xml"])[:3]:
        try:
            r = http.fetch(sm, allow_private=allow_private)
        except http.FetchError:
            continue
        if r.status == 200:
            ctx.sitemap["content_type"] = r.content_type
            ctx.sitemap["url"] = sm

            def loader(loc: str) -> Optional[str]:
                try:
                    rr = http.fetch(loc, allow_private=allow_private)
                    return rr.text if rr.status == 200 else None
                except http.FetchError:
                    return None
            parse_sitemap_text(ctx, r.text, sm, loader)
            break
    # 404 probe
    probe = base + "/twwa-404-probe-%06d" % random.randint(0, 999999)
    try:
        pr = http.fetch(probe, allow_private=allow_private)
        ctx.extra["probe_404"] = {"url": probe, "status": pr.status}
    except http.FetchError as exc:
        ctx.extra["probe_404"] = {"url": probe, "error": str(exc)}
    # IndexNow key
    key_file = ((ctx.cfg.get("connectors") or {}).get("indexnow") or {}).get("key_file")
    if key_file:
        kurl = base + "/" + Path(key_file).name
        try:
            kr = http.fetch(kurl, allow_private=allow_private)
            ctx.extra["indexnow"] = {"url": kurl, "status": kr.status, "ok": kr.status == 200 and kr.text.strip() == Path(key_file).stem}
        except http.FetchError as exc:
            ctx.extra["indexnow"] = {"url": kurl, "error": str(exc)}
    # preview hosts
    for host in (ctx.cfg.get("site") or {}).get("preview_hosts") or []:
        purl = host if host.startswith("http") else "https://%s/" % host
        try:
            pr = http.fetch(purl, allow_private=allow_private)
            pg = htmlx.parse(pr.text, pr.url)
            ctx.extra.setdefault("previews", []).append({"url": purl, "status": pr.status, "noindex": "noindex" in (pr.headers.get("x-robots-tag") or "").lower() or "noindex" in pg.robots})
        except http.FetchError as exc:
            ctx.extra.setdefault("previews", []).append({"url": purl, "error": str(exc)})


# ---------------------------------------------------------------- checks

def is_noindex(info: Dict[str, Any]) -> bool:
    return "noindex" in (info["page"].robots or "") or "noindex" in (info.get("header_robots") or "") or "none" in (info.get("header_robots") or "").split(", ")


def ensure_business(ctx: Ctx) -> None:
    if ctx.business:
        return
    imp = next((i for p, i in ctx.pages.items() if "impressum" in p.lower() or "imprint" in p.lower()), None)
    if imp is None and ctx.mode == "live":
        home = ctx.pages.get("/") or next(iter(ctx.pages.values()), None)
        link = next((l for l in (home["page"].links if home else []) if "impressum" in (l.get("href") or "").lower() or "impressum" in (l.get("text") or "").lower()), None)
        if link:
            try:
                r = http.fetch(link["href"], allow_private=bool(getattr(ctx.args, "allow_private", False)))
                imp = {"page": htmlx.parse(r.text, r.url), "url": r.url}
            except http.FetchError:
                imp = None
    if imp is not None:
        ctx.business = infer_from_impressum(imp["page"], imp["url"])
        ctx.facts_source = "impressum (abgeleitet)"
        ctx.extra["impressum_text"] = imp["page"].full_text
    else:
        ctx.facts_source = None


def check_config(ctx: Ctx) -> None:
    a = ctx.det.get("astro") or {}
    v = ctx.det.get("vercel") or {}
    if not ctx.repo or not a.get("file"):
        ctx.add(F("tech.config.not_checked", "tech", "info", "Astro- und Vercel-Konfiguration nicht geprüft",
                  "Ohne Repository (astro.config, vercel.json) lassen sich Slash-Regel und Weiterleitungen nur von außen prüfen.",
                  status="not_checked", action_type="tech_fix"))
        return
    ev = {"file": str(ctx.repo / a["file"])}
    if not a.get("site"):
        ctx.add(F("tech.config.site_missing", "tech", "P2", "astro.config ohne site-Angabe",
                  "Ohne `site` erzeugt Astro keine absoluten Canonicals und keine korrekte Sitemap.", evidence=dict(ev, snippet="site fehlt"), action_type="tech_fix"))
    elif ctx.business and ctx.business.get("url") and htmlx.bare_host(urllib.parse.urlsplit(a["site"]).netloc) != htmlx.bare_host(urllib.parse.urlsplit(ctx.business["url"]).netloc):
        ctx.add(F("tech.config.site_host", "tech", "P2", "Domain in astro.config weicht ab",
                  "astro.config nennt %s, die Stammdaten %s." % (a["site"], ctx.business["url"]), evidence=dict(ev, snippet=a["site"]), action_type="tech_fix"))
    elif ctx.business and ctx.business.get("url") and urllib.parse.urlsplit(a["site"]).netloc.lower() != urllib.parse.urlsplit(ctx.business["url"]).netloc.lower():
        ctx.add(F("tech.config.site_www", "tech", "P2", "www und ohne www gemischt",
                  "astro.config nutzt %s, die Stammdaten %s. Eine Variante muss per 308 auf die andere zeigen, Canonicals nutzen nur eine." % (a["site"], ctx.business["url"]),
                  evidence=dict(ev, snippet=a["site"]), action_type="tech_fix"))
    ts, fmt = a.get("trailingSlash"), a.get("build_format")
    problems = []
    if ts == "never" and fmt == "directory":
        problems.append("trailingSlash 'never' mit build.format 'directory'")
    if ts == "always" and fmt == "file":
        problems.append("trailingSlash 'always' mit build.format 'file'")
    if v.get("file"):
        if v.get("trailingSlash") is True and ts == "never":
            problems.append("vercel.json trailingSlash true, Astro 'never'")
        if v.get("trailingSlash") is False and ts == "always":
            problems.append("vercel.json trailingSlash false, Astro 'always'")
        if v.get("trailingSlash") is None and ts in ("never", "always"):
            problems.append("vercel.json legt trailingSlash nicht fest")
    if ts in (None, "ignore"):
        problems.append("Astro trailingSlash nicht festgelegt")
    if problems:
        ctx.add(F("tech.slash.policy_mismatch", "tech", "P2", "Uneinheitliche Slash-Regel",
                  "Die Regel für den Schrägstrich am URL-Ende ist nicht überall gleich: %s. Folge: interne 308-Sprünge oder doppelte URLs." % "; ".join(problems),
                  evidence=dict(ev, snippet="; ".join(problems)), fix_hint="Set trailingSlash and build.format in astro.config and trailingSlash in vercel.json to one policy.",
                  action_type="tech_fix"))
    if fmt == "file" and v.get("file") and v.get("cleanUrls") is not True:
        ctx.add(F("tech.config.clean_urls", "tech", "P2", "cleanUrls fehlt in vercel.json",
                  "Astro erzeugt `seite.html`; ohne `cleanUrls: true` antwortet Vercel unter `/seite` nicht oder es entstehen .html-Adressen.",
                  evidence={"file": str(ctx.repo / "vercel.json"), "snippet": "cleanUrls"}, action_type="tech_fix"))
    # preview hosts
    hosts = (ctx.cfg.get("site") or {}).get("preview_hosts") or []
    covered = set(v.get("noindex_hosts") or [])
    for h in hosts:
        hh = urllib.parse.urlsplit(h).netloc if "://" in h else h
        if hh.endswith(".vercel.app"):
            continue
        if hh not in covered:
            ctx.add(F("tech.preview.indexable", "tech", "P2", "Vorschau-Domain kann indexiert werden",
                      "%s ist als Vorschau-Domain eingetragen, aber vercel.json setzt dort kein `X-Robots-Tag: noindex`. Vorschauen auf *.vercel.app sind automatisch noindex, eigene Domains nicht." % hh,
                      evidence={"file": str(ctx.repo / "vercel.json"), "snippet": hh}, fix_hint="Add a headers rule with has: host for the preview domain.", action_type="tech_fix"))


def check_robots_txt(ctx: Ctx) -> None:
    r = ctx.robots
    url = r.get("url")
    if r.get("status") is None or (isinstance(r.get("status"), int) and r["status"] >= 500) or r.get("error"):
        ctx.add(F("tech.robots_txt.unreachable", "tech", "P1", "robots.txt nicht erreichbar",
                  "Bei einem Serverfehler auf robots.txt behandelt Google die ganze Website als gesperrt (%s)." % (r.get("error") or r.get("status")),
                  evidence={"url": url, "value": r.get("status")}, action_type="robots_policy"))
        return
    if r["status"] >= 400 or r.get("text") is None:
        ctx.add(F("tech.robots_txt.missing", "tech", "P3", "Keine robots.txt",
                  "Ohne robots.txt ist alles erlaubt, es fehlt aber der Verweis auf die Sitemap.", evidence={"url": url, "value": r["status"]}, action_type="robots_policy"))
        return
    text = r["text"]
    ev = {"url": url, "file": r.get("file")}
    if http.robots_blocks_root(text, "*") and not any(http.robots_blocks_root(text, b) is False and b in text.lower() for b in SEARCH_BOTS):
        ctx.add(F("tech.robots_txt.blocks_all", "tech", "P1", "robots.txt sperrt die ganze Website",
                  "`Disallow: /` für alle Crawler. Die Website kann nicht in Google erscheinen.", evidence=dict(ev, snippet="User-agent: * / Disallow: /"), action_type="robots_policy"))
    for bot in SEARCH_BOTS:
        if http.robots_blocks_root(text, bot) and bot in text.lower():
            ctx.add(F("tech.robots_txt.search_bot_blocked", "tech", "P1", "Suchmaschinen-Crawler %s gesperrt" % bot,
                      "robots.txt sperrt %s für die ganze Website." % bot, evidence=dict(ev, snippet=bot), action_type="robots_policy"))
    blocked_answer = [b for b in ANSWER_BOTS if http.robots_blocks_root(text, b)]
    if blocked_answer:
        ctx.add(F("ai.bots.answer_blocked", "ai", "P2", "Such- und Antwort-Crawler von KI-Diensten gesperrt",
                  "robots.txt sperrt %s. Diese Crawler holen Inhalte für Antworten mit Quellenangabe (ChatGPT-Suche, Perplexity, Claude); gesperrt kann die Website dort nicht zitiert werden." % ", ".join(blocked_answer),
                  evidence=dict(ev, snippet=", ".join(blocked_answer)), fix_hint="Allow search and answer bots; training bots are a separate client decision.",
                  action_type="robots_policy", priority_group=3))
    tb = {b: http.robots_blocks_root(text, b) for b in TRAINING_BOTS if b in text.lower()}
    blocked_t = [b for b, v in tb.items() if v]
    ctx.add(F("ai.bots.training_policy", "ai", "info", "Regeln für KI-Trainings-Crawler",
              "Gesperrt: %s. Ausdrücklich erlaubt oder ohne eigene Regel: alle übrigen. Das ist eine Entscheidung des Betriebs; das Plugin ändert sie nicht (ai_bots.training = %s)." % (
                  ", ".join(blocked_t) or "keine", ctx.cfg["ai_bots"]["training"]),
              evidence=dict(ev, snippet=", ".join(blocked_t) or "keine Sperre"), action_type="robots_policy"))
    if not re.search(r"(?im)^\s*sitemap\s*:", text):
        ctx.add(F("tech.robots_txt.no_sitemap", "tech", "P3", "robots.txt nennt keine Sitemap",
                  "Eine Zeile `Sitemap: https://…/sitemap.xml` hilft Crawlern ohne Search-Console-Zugang (Bing, KI-Dienste).", evidence=dict(ev, snippet="Sitemap fehlt"), action_type="robots_policy"))


def check_sitemap(ctx: Ctx) -> None:
    sm = ctx.sitemap
    if not sm["found"]:
        ctx.add(F("tech.sitemap.missing", "tech", "P2", "Keine XML-Sitemap",
                  "Weder sitemap.xml noch sitemap-index.xml gefunden.", evidence={"url": ctx.url_of("/sitemap.xml"), "snippet": "nicht gefunden"}, action_type="tech_fix"))
        return
    where = sm.get("url") or sm.get("where")
    ev = {"url": where if str(where).startswith("http") else None, "file": None if str(where).startswith("http") else where}
    if sm.get("error"):
        ctx.add(F("tech.sitemap.invalid", "tech", "P2", "Sitemap ist kein gültiges XML", sm["error"], evidence=dict(ev, snippet=sm["error"][:160]), action_type="tech_fix"))
        return
    if ctx.mode == "live" and sm.get("content_type") and "xml" not in sm["content_type"]:
        ctx.add(F("tech.sitemap.content_type", "tech", "P2", "Sitemap mit falschem Content-Type",
                  "Die Sitemap wird als %s ausgeliefert statt als XML." % sm["content_type"], evidence=dict(ev, value=sm["content_type"]), action_type="tech_fix"))
    host = htmlx.bare_host(urllib.parse.urlsplit(ctx.site_url or "").netloc)
    exact_host = urllib.parse.urlsplit(ctx.site_url or "").netloc.lower()
    bad: Dict[str, List[str]] = {"wrong_host": [], "broken_url": [], "noindex_url": [], "non_canonical": [], "redirect_url": []}
    in_sitemap: Set[str] = set()
    for u in sm["urls"]:
        parts = urllib.parse.urlsplit(u["loc"])
        if htmlx.bare_host(parts.netloc) != host or (exact_host and parts.netloc.lower() != exact_host):
            bad["wrong_host"].append(u["loc"])
            continue
        path = ctx.norm_path(parts.path)
        in_sitemap.add(path)
        raw_path = parts.path or "/"
        if raw_path != "/" and ((ctx.slash == "never" and raw_path.endswith("/")) or (ctx.slash == "always" and not raw_path.endswith("/"))):
            bad["redirect_url"].append(u["loc"])
        info = ctx.pages.get(path)
        if info is None:
            if redirect_for(ctx, parts.path):
                bad["redirect_url"].append(u["loc"])
            elif ctx.mode == "dist" or len(ctx.pages) < int(ctx.cfg["caps"]["crawl_pages"]):
                bad["broken_url"].append(u["loc"])
            continue
        if info["status"] != 200 or info.get("history"):
            bad["redirect_url" if info.get("history") else "broken_url"].append(u["loc"])
            continue
        if is_noindex(info):
            bad["noindex_url"].append(u["loc"])
            continue
        can = info["page"].canonical
        if can and ctx.norm_path(urllib.parse.urlsplit(can).path) != path:
            bad["non_canonical"].append(u["loc"])
    labels = {"wrong_host": ("Sitemap enthält URLs einer anderen Domain", "Diese URLs passen nicht zur Hauptdomain %s" % (ctx.site_url or "")),
              "broken_url": ("Sitemap enthält URLs ohne Seite", "Diese URLs liefern keine Seite (404 oder fehlen im Build)"),
              "noindex_url": ("Sitemap enthält Seiten mit noindex", "Diese Seiten sind auf noindex gesetzt und gehören nicht in die Sitemap"),
              "non_canonical": ("Sitemap enthält nicht-kanonische URLs", "Das Canonical dieser Seiten zeigt auf eine andere URL"),
              "redirect_url": ("Sitemap enthält weitergeleitete URLs", "Diese URLs leiten weiter oder verletzen die Slash-Regel")}
    for k, urls in bad.items():
        if urls:
            title, detail = labels[k]
            ctx.add(F("tech.sitemap.%s" % k, "tech", "P2", title, "%s: %s. In die Sitemap gehören nur indexierbare, kanonische URLs mit Status 200." % (detail, ", ".join(urls[:8])),
                      evidence=dict(ev, snippet=urls[0], value=urls[:20]), action_type="tech_fix"))
    lms = [u["lastmod"] for u in sm["urls"] if u["lastmod"]]
    if sm["urls"] and not lms:
        ctx.add(F("tech.sitemap.lastmod_missing", "tech", "P3", "Sitemap ohne lastmod",
                  "Kein Eintrag nennt ein Änderungsdatum. Google nutzt lastmod, wenn es verlässlich stimmt.", evidence=dict(ev, snippet="lastmod fehlt"), action_type="tech_fix"))
    elif len(lms) >= 3 and len(set(x[:10] for x in lms)) == 1:
        ctx.add(F("tech.sitemap.lastmod_uniform", "tech", "P3", "Alle lastmod-Daten identisch",
                  "Alle %d Einträge tragen %s. Das ist meist die Build-Zeit; Google ignoriert lastmod dann. Datum aus der letzten echten Änderung ableiten." % (len(lms), lms[0][:10]),
                  evidence=dict(ev, snippet=lms[0]), action_type="tech_fix"))
    future = [x for x in lms if x[:10] > st.today()]
    if future:
        ctx.add(F("tech.sitemap.lastmod_future", "tech", "P3", "lastmod in der Zukunft", "Einträge mit Datum nach heute: %s." % ", ".join(future[:3]),
                  evidence=dict(ev, snippet=future[0]), action_type="tech_fix"))
    missing = [p for p, i in ctx.pages.items() if i["status"] == 200 and not is_noindex(i) and p not in in_sitemap and not re.search(r"404", p)]
    if missing:
        ctx.add(F("tech.sitemap.page_missing", "tech", "P3", "Indexierbare Seiten fehlen in der Sitemap",
                  "Nicht in der Sitemap: %s." % ", ".join(missing[:8]), evidence=dict(ev, snippet=missing[0], value=missing[:20]), action_type="tech_fix"))


def service_terms(ctx: Ctx) -> List[str]:
    b = ctx.business or {}
    terms = [s.get("name") for s in b.get("services") or [] if s.get("name")]
    if b.get("trade"):
        terms.append(b["trade"])
    terms += list((b.get("voice") or {}).get("regional_terms") or [])
    if getattr(ctx.args, "trade", None):
        terms.append(ctx.args.trade)
    return [t for t in terms if t]


def page_town(ctx: Ctx, path: str) -> Optional[str]:
    for t in ctx.towns:
        if st.slugify(t) in path.lower():
            return t
    return (ctx.business or {}).get("address", {}).get("city")


def check_page(ctx: Ctx, info: Dict[str, Any], money: bool, titles: Dict[str, List[str]], descs: Dict[str, List[str]]) -> None:
    page: htmlx.Page = info["page"]
    path, url, file = info["path"], info["url"], info.get("file")
    ev = {"url": url, "file": file}
    if info["status"] >= 400:
        if path != "/404":
            ctx.add(F("tech.status.error", "tech", "P1" if money else "P2", "Seite liefert Fehlerstatus %s" % info["status"],
                      "%s antwortet mit %s." % (url, info["status"]), evidence=dict(ev, value=info["status"]), action_type="tech_fix"))
        return
    if info.get("history") and len(info["history"]) > 1:
        ctx.add(F("tech.status.redirect_chain", "tech", "P3", "Weiterleitungskette",
                  "%s erreicht das Ziel erst nach %d Sprüngen." % (url, len(info["history"])), evidence=dict(ev, value=[u for _, u in info["history"]]), action_type="tech_fix"))
    noindex = is_noindex(info)
    if noindex:
        if money:
            ctx.add(F("tech.robots.noindex_money", "tech", "P1", "Wichtige Seite auf noindex",
                      "%s ist auf noindex gesetzt (%s). Sie kann nicht bei Google erscheinen." % (path, (page.robots or info.get("header_robots"))),
                      evidence=dict(ev, snippet=page.robots or info.get("header_robots")), fix_hint="Remove noindex from the money page.", action_type="tech_fix"))
        return
    if "nofollow" in (page.robots or "") and money:
        ctx.add(F("tech.robots.nofollow_money", "tech", "P2", "Wichtige Seite mit nofollow", "Meta robots enthält nofollow; interne Links werden nicht gewertet.",
                  evidence=dict(ev, snippet=page.robots), action_type="tech_fix"))
    if not page.lang:
        ctx.add(F("tech.html.lang_missing", "tech", "P3", "Sprache der Seite fehlt", "`<html lang=\"de\">` fehlt.", evidence=dict(ev, snippet="<html>"), action_type="tech_fix"))
    # canonical
    if not page.canonicals:
        ctx.add(F("tech.canonical.missing", "tech", "P2", "Canonical fehlt", "%s hat kein `<link rel=\"canonical\">`. Ohne Canonical wählt Google selbst, und UTM-Varianten aus dem Unternehmensprofil können als eigene URLs zählen." % path,
                  evidence=dict(ev, snippet="kein canonical"), fix_hint="Use SeoHead.astro from templates/site.", action_type="tech_fix"))
    else:
        if len(set(page.canonicals)) > 1:
            ctx.add(F("tech.canonical.multiple", "tech", "P2", "Mehrere Canonicals", "Die Seite nennt %d verschiedene Canonicals; Google ignoriert dann alle." % len(set(page.canonicals)),
                      evidence=dict(ev, value=page.canonicals), action_type="tech_fix"))
        raw = page.canonicals[0]
        cp = urllib.parse.urlsplit(raw)
        if not cp.scheme:
            ctx.add(F("tech.canonical.not_absolute", "tech", "P3", "Canonical nicht absolut", "Canonical `%s` ist relativ; absolute URLs sind eindeutig." % raw,
                      evidence=dict(ev, snippet=raw), action_type="tech_fix"))
        elif ctx.site_url and cp.netloc.lower() != urllib.parse.urlsplit(ctx.site_url).netloc.lower():
            ctx.add(F("tech.canonical.wrong_host", "tech", "P2", "Canonical zeigt auf andere Domain", "Canonical `%s` passt nicht zu %s." % (raw, ctx.site_url),
                      evidence=dict(ev, snippet=raw), action_type="tech_fix"))
        if cp.query:
            ctx.add(F("tech.canonical.query", "tech", "P2", "Canonical mit Parametern", "Canonical `%s` enthält Parameter." % raw, evidence=dict(ev, snippet=raw), action_type="tech_fix"))
        cpath = cp.path or "/"
        if cpath != "/" and ((ctx.slash == "never" and cpath.endswith("/")) or (ctx.slash == "always" and not cpath.endswith("/"))):
            ctx.add(F("tech.canonical.slash", "tech", "P2", "Canonical verletzt die Slash-Regel", "Canonical `%s` passt nicht zu trailingSlash '%s'; die Canonical-URL leitet selbst weiter." % (raw, ctx.slash),
                      evidence=dict(ev, snippet=raw), action_type="tech_fix"))
        elif ctx.norm_path(cpath) != path:
            target_known = ctx.norm_path(cpath) in ctx.pages
            ctx.add(F("tech.canonical.not_self", "tech", "P3" if target_known else "P2", "Canonical zeigt auf eine andere Seite",
                      "%s nennt `%s` als Canonical. Absicht prüfen; sonst wird die Seite nicht indexiert." % (path, raw),
                      evidence=dict(ev, snippet=raw), status="verified" if not target_known else "hypothesis", action_type="tech_fix"))
    # title, h1, description
    t = (page.title or "").strip()
    town = page_town(ctx, path)
    terms = service_terms(ctx)
    if not t:
        ctx.add(F("onpage.title.missing", "onpage", "P2", "Seitentitel fehlt", "%s hat keinen `<title>`." % path, evidence=dict(ev, snippet="kein title"), action_type="onpage_rewrite"))
    else:
        titles.setdefault(t, []).append(path)
        if len(t) > 60:
            ctx.add(F("onpage.title.too_long", "onpage", "P3", "Seitentitel zu lang", "%d Zeichen; ab etwa 60 Zeichen kürzt Google. „%s“" % (len(t), t),
                      evidence=dict(ev, snippet=t, value=len(t)), action_type="onpage_rewrite"))
        if money and not LEGAL_PATH.search(path):
            if town and not textde.contains_town(t, town):
                ctx.add(F("onpage.title.no_town", "onpage", "P2", "Ort fehlt im Seitentitel", "Der Titel „%s“ nennt %s nicht. Für lokale Suchen sind Leistung und Ort im Titel ein starkes Signal." % (t, town),
                          evidence=dict(ev, snippet=t), fix_hint="Pattern: {Leistung} in {Ort} | {Firma}", action_type="onpage_rewrite"))
            if terms and not any(textde.contains_term(t, x) for x in terms):
                ctx.add(F("onpage.title.no_service", "onpage", "P2", "Leistung fehlt im Seitentitel", "Der Titel „%s“ nennt weder Gewerk noch Leistung (%s)." % (t, ", ".join(terms[:4])),
                          evidence=dict(ev, snippet=t), action_type="onpage_rewrite"))
            elif not terms:
                ctx.add(F("onpage.title.service_not_checked", "onpage", "info", "Leistung im Titel nicht geprüft",
                          "Gewerk und Leistungen sind unbekannt (keine business.json); --trade setzt ein Gewerk.", status="not_checked", action_type="onpage_rewrite"))
    h1 = page.h1
    if not h1:
        ctx.add(F("onpage.h1.missing", "onpage", "P2", "Hauptüberschrift (H1) fehlt", "%s hat keine H1." % path, evidence=dict(ev, snippet="keine h1"), action_type="onpage_rewrite"))
    else:
        if len(h1) > 1:
            ctx.add(F("onpage.h1.multiple", "onpage", "P3", "Mehrere H1", "%d H1-Überschriften: %s" % (len(h1), " | ".join(h1[:3])), evidence=dict(ev, value=h1), action_type="onpage_rewrite"))
        if money and not LEGAL_PATH.search(path):
            if town and not textde.contains_town(h1[0], town):
                ctx.add(F("onpage.h1.no_town", "onpage", "P2", "Ort fehlt in der H1", "Die H1 „%s“ nennt %s nicht." % (h1[0], town), evidence=dict(ev, snippet=h1[0]), action_type="onpage_rewrite"))
            if terms and not any(textde.contains_term(h1[0], x) for x in terms):
                ctx.add(F("onpage.h1.no_service", "onpage", "P3", "Leistung fehlt in der H1", "Die H1 „%s“ nennt weder Gewerk noch Leistung." % h1[0], evidence=dict(ev, snippet=h1[0]), action_type="onpage_rewrite"))
    d = (page.metas.get("description") or "").strip()
    if not d:
        ctx.add(F("onpage.meta_description.missing", "onpage", "P3", "Meta-Beschreibung fehlt", "%s hat keine Meta-Beschreibung; Google bildet dann selbst einen Ausschnitt." % path,
                  evidence=dict(ev, snippet="keine description"), action_type="onpage_rewrite"))
    else:
        descs.setdefault(d, []).append(path)
        if len(d) > 160:
            ctx.add(F("onpage.meta_description.too_long", "onpage", "P3", "Meta-Beschreibung zu lang", "%d Zeichen; ab etwa 160 wird gekürzt." % len(d), evidence=dict(ev, snippet=d[:160], value=len(d)), action_type="onpage_rewrite"))
        elif len(d) < 70:
            ctx.add(F("onpage.meta_description.too_short", "onpage", "P3", "Meta-Beschreibung sehr kurz", "%d Zeichen: „%s“." % (len(d), d), evidence=dict(ev, snippet=d, value=len(d)), action_type="onpage_rewrite"))
    levels = [h["level"] for h in page.headings]
    if levels:
        if levels[0] != 1:
            ctx.add(F("onpage.headings.order", "onpage", "P3", "Überschriften-Reihenfolge", "Die erste Überschrift ist H%d statt H1." % levels[0], evidence=dict(ev, value=levels[:10]), action_type="onpage_rewrite"))
        else:
            for a, b in zip(levels, levels[1:]):
                if b > a + 1:
                    ctx.add(F("onpage.headings.order", "onpage", "P3", "Überschriften-Ebene übersprungen", "Auf H%d folgt H%d; eine Ebene fehlt." % (a, b), evidence=dict(ev, value=levels[:12]), action_type="onpage_rewrite"))
                    break
    # images
    imgs = [i for i in page.images if i.get("src")]
    no_alt = [i["src"] for i in imgs if i.get("alt") is None]
    if no_alt:
        ctx.add(F("tech.images.alt_missing", "tech", "P3", "Bilder ohne Alternativtext", "%d Bild(er) ohne alt-Attribut, z. B. %s." % (len(no_alt), no_alt[0]), evidence=dict(ev, snippet=no_alt[0], value=len(no_alt)), action_type="tech_fix"))
    no_dim = [i["src"] for i in imgs if not (i.get("width") and i.get("height"))]
    if no_dim:
        ctx.add(F("tech.images.dimensions_missing", "tech", "P3", "Bilder ohne Breite und Höhe", "%d Bild(er) ohne width und height; das verschiebt das Layout beim Laden (CLS)." % len(no_dim),
                  evidence=dict(ev, snippet=no_dim[0], value=len(no_dim)), action_type="tech_fix"))
    lcp = next((i for i in imgs if i.get("main")), imgs[0] if imgs else None)
    if lcp and lcp.get("pos", 0) <= htmlx.FIRST_SCREEN_CHARS and lcp.get("loading") == "lazy":
        ctx.add(F("tech.images.lcp_lazy", "tech", "P2", "Hauptbild lädt verzögert", "Das erste große Bild (%s) hat loading=\"lazy\". Das verzögert den Largest Contentful Paint; Hero-Bild mit loading=\"eager\" und fetchpriority=\"high\"." % lcp["src"],
                  evidence=dict(ev, snippet=lcp["src"]), action_type="tech_fix"))
    # town list
    runs = textde.town_runs(page.full_text, ctx.towns) + [r for r in (textde.list_town_run(l["items"], ctx.towns) for l in page.lists) if r]
    big = max(runs, key=len) if runs else []
    if len(big) > int(ctx.cfg["thresholds"]["gates"]["townlist_max_towns"]):
        ctx.add(F("content.townlist", "content", "P2", "Ortsliste mit %d Orten" % len(big),
                  "Eine reine Aufzählung von Orten (%s …) wertet Google als Keyword-Stuffing. Besser: Einsatzgebiet mit Anfahrtszeiten und Projekten, Orte gruppiert." % ", ".join(big[:5]),
                  evidence=dict(ev, snippet=", ".join(big[:10]), value=len(big)), fix_hint="Replace the list with a grouped service-area section.", action_type="onpage_rewrite"))
    # legal surface on the page
    for f in legal_lint.page_findings(page, url, file, is_home=(path == "/"), cfg=ctx.cfg):
        ctx.add(f)
    # schema
    for f in schema_gen.validate_page(page, ctx.business if ctx.facts_source == "business.json" else None, url, file, is_home=(path == "/")):
        ctx.add(f)
    if money:
        check_conversion(ctx, info)


def check_conversion(ctx: Ctx, info: Dict[str, Any]) -> None:
    page: htmlx.Page = info["page"]
    path, url, file = info["path"], info["url"], info.get("file")
    ev = {"url": url, "file": file}
    b = ctx.business or {}
    allowed = {textde.norm_phone(b.get("phone"))} if b.get("phone") else set()
    allowed |= {textde.norm_phone(x if isinstance(x, str) else (x or {}).get("number")) for x in b.get("tracking_numbers") or []}
    tels = [textde.norm_phone(t) for t in page.tel_links]
    shown = PHONE_IN_TEXT.findall(page.full_text)
    if not tels:
        ctx.add(F("cro.phone.no_tel_link", "cro", "P2", "Telefonnummer nicht anklickbar",
                  ("Die Seite zeigt %s, aber ohne `tel:`-Link. Auf dem Handy ist Anrufen dann umständlich." % shown[0].strip()) if shown else "Auf der Seite gibt es keinen `tel:`-Link zum direkten Anrufen.",
                  evidence=dict(ev, snippet=shown[0].strip() if shown else "kein tel:-Link"), action_type="cro_change"))
    elif allowed - {""}:
        wrong = sorted({t for t in tels if t not in allowed})
        if wrong:
            ctx.add(F("cro.phone.tel_mismatch", "cro", "P2", "Anruf-Link mit anderer Nummer", "tel:-Link auf %s, die Stammdaten nennen %s." % (", ".join(wrong), b.get("phone")),
                      evidence=dict(ev, snippet=wrong[0]), action_type="cro_change"))
    if not page.wa_links and path == "/":
        ctx.add(F("cro.whatsapp.missing", "cro", "info", "Kein WhatsApp-Link", "Ein einfacher wa.me-Link (ohne eingebettetes Widget) senkt die Hürde für Anfragen per Handy.",
                  evidence=dict(ev, snippet="kein wa.me-Link"), action_type="cro_change"))
    forms = [f for f in page.forms if any(fl.get("type") in ("text", "email", "tel", "textarea") for fl in f["fields"])]
    if not forms:
        ctx.add(F("cro.form.missing", "cro", "P2", "Kein Anfrageformular", "%s hat kein Formular für Anfragen." % path, evidence=dict(ev, snippet="kein form"), action_type="cro_change"))
    else:
        f = forms[0]
        blob = " ".join([f.get("text") or ""] + [l.get("text") or "" for l in f["labels"]] + ["%s %s %s %s" % (x.get("name"), x.get("placeholder"), x.get("aria_label"), " ".join(x.get("options") or [])) for x in f["fields"]])
        if not SOURCE_FIELD_RE.search(blob):
            ctx.add(F("tracking.form.source_field_missing", "tracking", "P2", "Feld „Wie haben Sie uns gefunden?“ fehlt",
                      "Das Formular fragt nicht nach der Quelle. Ohne dieses Feld lassen sich Anfragen nicht Google-Suche, Karte, Empfehlung oder KI-Assistent zuordnen.",
                      evidence=dict(ev, snippet=f.get("raw_action") or "form"), fix_hint="Add a select named quelle with fixed options.", action_type="tracking_fix", priority_group=1))
        act = f.get("raw_action") or ""
        if ctx.repo and (ctx.repo / "package.json").is_file() and act.startswith("/api/"):
            name = act.split("?")[0].strip("/").split("/", 1)[1]
            exists = any((ctx.repo / "api" / (name + ext)).is_file() for ext in (".js", ".ts", ".mjs")) or any((ctx.repo / "src/pages/api" / (name + ext)).is_file() for ext in (".js", ".ts"))
            if not exists:
                ctx.add(F("tracking.form.handler_missing", "tracking", "P1", "Formular sendet ins Leere",
                          "Das Formular schickt an %s, im Repository gibt es dafür keinen Handler. Anfragen gehen verloren." % act,
                          evidence=dict(ev, snippet=act), action_type="tracking_fix", priority_group=1))
    early = [l for l in page.links if l["pos"] <= htmlx.FIRST_SCREEN_CHARS and ((l.get("raw") or "").startswith("tel:") or CTA_RE.search(l.get("text") or ""))]
    early += [x for x in page.buttons if x["pos"] <= htmlx.FIRST_SCREEN_CHARS and CTA_RE.search(x.get("text") or "")]
    anywhere = [l for l in page.links if (l.get("raw") or "").startswith("tel:") or CTA_RE.search(l.get("text") or "")]
    if not early:
        ctx.add(F("cro.cta.first_screen", "cro", "P2", "Keine Handlungsaufforderung im ersten Bildschirm",
                  ("Im oberen Seitenbereich steht kein Anruf- oder Anfrage-Link; der erste kommt erst später („%s“). Auf dem Handy sollte er ohne Scrollen sichtbar sein." % anywhere[0]["text"]) if anywhere
                  else "Die Seite enthält keinen Anruf- oder Anfrage-Link.",
                  evidence=dict(ev, snippet=anywhere[0]["text"] if anywhere else "kein CTA"),
                  status="hypothesis" if anywhere else "verified", fix_hint="Place call and request buttons in the hero; consider a sticky bar on mobile.", action_type="cro_change"))
    if ctx.business and path == "/":
        nap_missing = []
        txt = page.full_text
        if b.get("name") and textde.norm_name(b["name"], True) not in textde.norm_name(txt):
            nap_missing.append("Name")
        if (b.get("address") or {}).get("zip") and b["address"]["zip"] not in txt:
            nap_missing.append("PLZ")
        if (b.get("address") or {}).get("street") and textde.norm_address(b["address"]["street"]) not in textde.norm_address(txt):
            nap_missing.append("Straße")
        digits = re.sub(r"\D", "", txt)
        ph = textde.norm_phone(b.get("phone"))
        if ph and ph[3:] not in digits and not any(textde.norm_phone(t) == ph for t in page.tel_links):
            nap_missing.append("Telefon")
        if nap_missing and b.get("address_public") is not False:
            ctx.add(F("onpage.nap.missing", "onpage", "P2", "Name, Adresse oder Telefon nicht auf der Seite",
                      "Auf der Startseite fehlen: %s. Der NAP-Block (meist im Footer) muss den Angaben im Google-Profil entsprechen." % ", ".join(nap_missing),
                      evidence=dict(ev, snippet=", ".join(nap_missing)), action_type="tech_fix"))


def check_links(ctx: Ctx) -> Dict[str, Any]:
    """Internal link checks plus the link graph."""
    graph: Dict[str, Dict[str, Any]] = {p: {"inlinks": set(), "anchors": [], "out": set()} for p in ctx.pages}
    site = ctx.site_url or "https://site.invalid"
    for path, info in ctx.pages.items():
        page: htmlx.Page = info["page"]
        hops, broken, anchors = [], [], []
        for l in page.links:
            raw = l.get("raw") or ""
            if not raw or raw.startswith(("tel:", "mailto:", "javascript:", "data:")) or "wa.me" in raw:
                continue
            sp = htmlx.same_site_path(l["href"], site) if not raw.startswith("#") else path
            if sp is None:
                continue
            frag = urllib.parse.urlsplit(l["href"]).fragment if not raw.startswith("#") else raw[1:]
            raw_path = urllib.parse.urlsplit(raw).path if not raw.startswith("#") else path
            if sp.startswith("/api/") or re.search(r"\.(pdf|jpe?g|png|webp|avif|svg|ico|xml|txt|woff2?)$", sp, re.IGNORECASE):
                continue
            target = ctx.norm_path(sp)
            if raw_path and raw_path != "/" and not raw.startswith("#"):
                if (ctx.slash == "never" and raw_path.endswith("/")) or (ctx.slash == "always" and not raw_path.endswith("/")) or raw_path.endswith(".html"):
                    hops.append(raw)
            rd = redirect_for(ctx, raw_path) if raw_path else None
            if rd and not raw.startswith("#"):
                hops.append(raw)
                continue
            if target in graph:
                if target != path:
                    graph[target]["inlinks"].add(path)
                    graph[target]["anchors"].append(l.get("text") or "")
                if target != path:
                    graph[path]["out"].add(target)
                if frag and frag not in ctx.pages[target]["page"].ids:
                    anchors.append(raw)
            elif ctx.mode == "dist" and sp not in ctx.files:
                broken.append(raw)
        ev = {"url": info["url"], "file": info.get("file")}
        if hops:
            ctx.add(F("tech.links.redirect_hop", "tech", "P3", "Interne Links über Weiterleitungen",
                      "%d interne Link(s) zeigen auf eine Adresse, die erst weiterleitet (Slash-Regel, .html oder Weiterleitung in vercel.json), z. B. %s." % (len(hops), hops[0]),
                      evidence=dict(ev, snippet=hops[0], value=sorted(set(hops))[:10]), action_type="tech_fix"))
        if broken:
            ctx.add(F("tech.links.broken", "tech", "P2", "Interne Links ins Leere", "%d Link(s) ohne Ziel im Build, z. B. %s." % (len(broken), broken[0]),
                      evidence=dict(ev, snippet=broken[0], value=sorted(set(broken))[:10]), action_type="tech_fix"))
        if anchors:
            ctx.add(F("tech.links.anchor_missing", "tech", "P3", "Sprungmarke fehlt", "Link(s) auf nicht vorhandene Anker, z. B. %s." % anchors[0],
                      evidence=dict(ev, snippet=anchors[0], value=sorted(set(anchors))[:10]), action_type="tech_fix"))
    # depth
    depth: Dict[str, int] = {}
    if "/" in graph:
        dq = deque([("/", 0)])
        while dq:
            p, d = dq.popleft()
            if p in depth:
                continue
            depth[p] = d
            for o in graph[p]["out"]:
                if o not in depth:
                    dq.append((o, d + 1))
    money = set(ctx.money_pages())
    for p, g in graph.items():
        info = ctx.pages[p]
        if p in ("/",) or info["status"] != 200 or "404" in p:
            continue
        if not g["inlinks"]:
            ctx.add(F("tech.links.orphan", "tech", "P3", "Seite ohne interne Links", "%s wird von keiner anderen Seite verlinkt." % p,
                      evidence={"url": info["url"], "file": info.get("file"), "snippet": p}, action_type="tech_fix"))
        if p in money and len(g["inlinks"]) < 3:
            ctx.add(F("tech.links.money_few_inlinks", "tech", "P3", "Wichtige Seite mit wenig internen Links", "%s hat %d interne Verlinkung(en); Ziel sind mindestens 3." % (p, len(g["inlinks"])),
                      evidence={"url": info["url"], "file": info.get("file"), "value": len(g["inlinks"])}, action_type="tech_fix"))
    return {p: {"inlinks": sorted(g["inlinks"]), "inlink_count": len(g["inlinks"]), "depth": depth.get(p), "anchors": sorted(set(a for a in g["anchors"] if a))[:10],
                "outlinks": sorted(g["out"])} for p, g in graph.items()}


def check_site_level(ctx: Ctx) -> None:
    pages = {p: i["page"] for p, i in ctx.pages.items()}
    if "/" in pages:
        for f in legal_lint.legal_links_findings(pages, "/"):
            f["evidence"]["url"] = ctx.url_of("/")
            ctx.add(f)
        home = ctx.pages["/"]["page"]
        for key in ("impressum", "datenschutz"):
            link = next((l for l in home.links if key in (l.get("href") or "").lower()), None)
            if link:
                tp = ctx.norm_path(htmlx.same_site_path(link["href"], ctx.site_url or "https://site.invalid") or "")
                ti = ctx.pages.get(tp)
                if (ctx.mode == "dist" and ti is None) or (ti is not None and ti["status"] >= 400):
                    ctx.add(F("legal.%s.unreachable" % key, "legal", "P1", "%s-Link führt ins Leere" % key.capitalize(),
                              "Der Link %s liefert keine Seite. %s" % (link["href"], legal_lint.DISCLAIMER), evidence={"url": ctx.url_of("/"), "snippet": link["href"]}, action_type="tech_fix"))
    # 404
    if ctx.mode == "dist":
        if "/404" not in ctx.pages:
            ctx.add(F("tech.404.missing", "tech", "P2", "Keine 404-Seite", "Im Build fehlt 404.html; Vercel liefert dann eine Standardseite ohne Navigation und Kontakt.",
                      evidence={"file": ctx.extra.get("root"), "snippet": "404.html fehlt"}, action_type="tech_fix"))
        ctx.add(F("tech.404.status_not_checked", "tech", "info", "404-Status live nicht geprüft", "Ob unbekannte Adressen wirklich Status 404 liefern, zeigt erst `site_audit.py live`.",
                  status="not_checked", action_type="tech_fix"))
    else:
        pr = ctx.extra.get("probe_404") or {}
        if pr.get("status") and pr["status"] != 404:
            ctx.add(F("tech.404.soft", "tech", "P2", "Unbekannte Adressen liefern keinen 404-Status",
                      "%s antwortet mit %s statt 404 (Soft-404)." % (pr["url"], pr["status"]), evidence={"url": pr["url"], "value": pr["status"]}, action_type="tech_fix"))
    # indexnow
    if ctx.mode == "dist":
        root = Path(ctx.extra["root"])
        keys = [f for f in root.glob("*.txt") if INDEXNOW_KEY.match(f.stem) and f.read_text(encoding="utf-8", errors="replace").strip() == f.stem]
        if not keys:
            ctx.add(F("tech.indexnow.key_missing", "tech", "P3", "IndexNow-Schlüsseldatei fehlt",
                      "Ohne Schlüsseldatei kann die Website Bing und andere Suchmaschinen nicht sofort über neue Seiten informieren. Bing speist auch ChatGPT-Suche und Copilot.",
                      evidence={"file": str(root), "snippet": "keine <key>.txt"}, fix_hint="python3 scripts/indexnow.py key --write", action_type="tech_fix"))
        ctx.extra["indexnow_key_files"] = [k.name for k in keys]
    else:
        inx = ctx.extra.get("indexnow")
        if inx is None:
            ctx.add(F("tech.indexnow.not_checked", "tech", "info", "IndexNow nicht geprüft", "Kein Schlüssel in config.connectors.indexnow.key_file.", status="not_checked", action_type="tech_fix"))
        elif not inx.get("ok"):
            ctx.add(F("tech.indexnow.key_missing", "tech", "P3", "IndexNow-Schlüsseldatei nicht erreichbar", "%s liefert den Schlüssel nicht (%s)." % (inx["url"], inx.get("status") or inx.get("error")),
                      evidence={"url": inx["url"], "value": inx.get("status")}, action_type="tech_fix"))
        for pv in ctx.extra.get("previews") or []:
            if pv.get("status") == 200 and not pv.get("noindex"):
                ctx.add(F("tech.preview.indexable", "tech", "P1", "Vorschau-Domain ist indexierbar", "%s liefert die Website ohne noindex aus; das erzeugt doppelte Inhalte bei Google." % pv["url"],
                          evidence={"url": pv["url"], "value": pv["status"]}, action_type="tech_fix"))
    # duplicate titles and descriptions are added by run_audit


def run_audit(ctx: Ctx) -> Dict[str, Any]:
    ensure_business(ctx)
    check_config(ctx)
    check_robots_txt(ctx)
    check_sitemap(ctx)
    money = set(ctx.money_pages())
    titles: Dict[str, List[str]] = {}
    descs: Dict[str, List[str]] = {}
    for path, info in sorted(ctx.pages.items()):
        check_page(ctx, info, path in money, titles, descs)
    for t, ps in titles.items():
        if len(ps) > 1:
            ctx.add(F("onpage.title.duplicate", "onpage", "P3", "Gleicher Seitentitel mehrfach", "„%s“ auf %s." % (t, ", ".join(ps)), evidence={"url": ctx.url_of(ps[0]), "snippet": t, "value": ps}, action_type="onpage_rewrite"))
    for d, ps in descs.items():
        if len(ps) > 1:
            ctx.add(F("onpage.meta_description.duplicate", "onpage", "P3", "Gleiche Meta-Beschreibung mehrfach", "Auf %s." % ", ".join(ps), evidence={"url": ctx.url_of(ps[0]), "snippet": d[:120], "value": ps}, action_type="onpage_rewrite"))
    graph = check_links(ctx)
    check_site_level(ctx)
    if not ctx.business:
        ctx.add(F("onpage.nap.not_checked", "onpage", "info", "Stammdaten nicht geprüft", "Weder business.json noch ein lesbares Impressum gefunden; NAP-Abgleich nicht geprüft.",
                  status="not_checked", action_type="tech_fix"))
    findings = cli.sort_findings(ctx.findings)
    summary: Dict[str, int] = {}
    for f in findings:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1
    pages = []
    for p, i in sorted(ctx.pages.items()):
        pg = i["page"]
        pages.append({"url": i["url"], "path": p, "status": i["status"], "title": pg.title, "h1": pg.h1[0] if pg.h1 else None,
                      "canonical": pg.canonical, "indexable": i["status"] == 200 and not is_noindex(i), "words": pg.body_words,
                      "schema_types": pg.schema_types()})
    out = {"mode": ctx.mode, "site": ctx.site_url, "facts_source": ctx.facts_source or "keine", "money_pages": sorted(money),
           "pages": pages, "findings": findings, "summary": summary, "linkgraph": graph}
    if ctx.facts_source and ctx.facts_source.startswith("impressum"):
        out["inferred_business"] = {k: v for k, v in (ctx.business or {}).items() if k in ("name", "address", "phone", "email", "source_url")}
    for k in ("robots_skipped", "fetch_errors", "probe_404"):
        if k in ctx.extra:
            out[k] = ctx.extra[k]
    return out


def finish(ctx: Ctx, out: Dict[str, Any], args: Any) -> int:
    if getattr(args, "write_snapshot", False):
        if not ctx.state:
            cli.die(cli.EXIT_USAGE, "--write-snapshot needs a state folder")
        snap = {"source": "site", "pulled_at": st.now_iso(), "range": {"start": None, "end": None}, "origin": ctx.mode,
                "findings": out["findings"], "pages": out["pages"]}
        p = st.snapshot_dir(ctx.state) / "site.json"
        st.save_json(p, snap)
        out["snapshot"] = str(p)
    human = cli.render_findings_de(out["findings"], "Audit %s (%s), Stammdaten: %s, %d Seiten" % (out["site"], out["mode"], out["facts_source"], len(out["pages"])))
    if not getattr(args, "verbose", False) and not cli.is_json(args):
        human = human
    show = dict(out)
    if not getattr(args, "with_graph", False):
        show.pop("linkgraph", None)
    cli.emit(show, args, human)
    bad = cli.at_or_above(out["findings"], getattr(args, "fail_on", None))
    return cli.EXIT_FAIL if bad else cli.EXIT_OK


# ---------------------------------------------------------------- commands

def cmd_dist(args: Any) -> int:
    root = Path(args.dir)
    if not root.is_dir():
        cli.die(cli.EXIT_USAGE, "dist folder not found: %s (build first, e.g. npm run build)" % root)
    ctx = Ctx(args, "dist")
    load_dist(ctx, root)
    if not ctx.pages:
        cli.die(cli.EXIT_USAGE, "No HTML files in %s" % root)
    return finish(ctx, run_audit(ctx), args)


def cmd_live(args: Any) -> int:
    if not re.match(r"^https?://", args.url):
        cli.die(cli.EXIT_USAGE, "URL must start with http:// or https://")
    ctx = Ctx(args, "live")
    load_live(ctx, args.url)
    return finish(ctx, run_audit(ctx), args)


def cmd_page(args: Any) -> int:
    ctx = Ctx(args, "page")
    target = args.target
    if re.match(r"^https?://", target):
        if args.fixture:
            http.use_fixture(args.fixture)
        try:
            r = http.fetch(target, allow_private=args.allow_private)
        except http.FetchError as exc:
            cli.die(cli.EXIT_REMOTE, str(exc))
        ctx.site_url = "%s://%s" % urllib.parse.urlsplit(r.url)[:2]
        path = ctx.norm_path(urllib.parse.urlsplit(r.url).path)
        info = {"path": path, "url": r.url, "file": None, "status": r.status, "page": htmlx.parse(r.text, r.url),
                "header_robots": (r.headers.get("x-robots-tag") or "").lower(), "history": r.history}
    else:
        p = Path(target)
        if not p.is_file():
            cli.die(cli.EXIT_USAGE, "File not found: %s" % target)
        ctx.site_url = args.site or (ctx.business or {}).get("url") or "https://site.invalid"
        path = ctx.norm_path("/" + (p.stem if p.stem != "index" else ""))
        info = {"path": path, "url": ctx.url_of(path), "file": str(p), "status": 200,
                "page": htmlx.parse(p.read_text(encoding="utf-8", errors="replace"), ctx.url_of(path)), "header_robots": "", "history": []}
    ctx.pages[path] = info
    ensure_business(ctx)
    money = path in set(ctx.money_pages()) or args.money
    check_page(ctx, info, money, {}, {})
    out = {"mode": "page", "site": ctx.site_url, "facts_source": ctx.facts_source or "keine", "pages": [{"url": info["url"], "path": path}],
           "findings": cli.sort_findings(ctx.findings), "summary": {}}
    for f in out["findings"]:
        out["summary"][f["severity"]] = out["summary"].get(f["severity"], 0) + 1
    return finish(ctx, out, args)


def cmd_linkgraph(args: Any) -> int:
    target = args.target
    if re.match(r"^https?://", target or ""):
        ctx = Ctx(args, "live")
        load_live(ctx, target)
    else:
        root = Path(target or "dist")
        if not root.is_dir():
            cli.die(cli.EXIT_USAGE, "dist folder not found: %s" % root)
        ctx = Ctx(args, "dist")
        load_dist(ctx, root)
    graph = check_links(ctx)
    findings = [f for f in ctx.findings if f["id"].startswith("tech.links.")]
    orphans = [p for p, g in graph.items() if not g["inlinks"] and p != "/" and "404" not in p]
    out = {"mode": "linkgraph", "site": ctx.site_url, "nodes": graph, "orphans": orphans, "findings": cli.sort_findings(findings)}
    lines = ["Link-Graph %s: %d Seiten" % (ctx.site_url, len(graph))]
    for p, g in sorted(graph.items()):
        lines.append("  %-30s Tiefe %s, %d eingehende Links" % (p, g["depth"], g["inlink_count"]))
    lines.append(cli.render_findings_de(out["findings"]))
    cli.emit(out, args, "\n".join(lines))
    return cli.EXIT_FAIL if cli.at_or_above(findings, args.fail_on) else cli.EXIT_OK


def cmd_redirects(args: Any) -> int:
    repo = Path(args.repo).resolve()
    ctx = Ctx(args, "dist")
    ctx.repo = repo
    ctx.det = twwa_state.detect_repo(repo)
    ctx.slash = (ctx.det.get("astro") or {}).get("trailingSlash")
    load_vercel(ctx)
    dist = Path(args.dist) if args.dist else repo / ((ctx.cfg.get("site") or {}).get("dist_dir") or "dist")
    if dist.is_dir():
        load_dist(ctx, dist)
    ctx.findings = []
    vfile = str(repo / "vercel.json")
    results = []
    sources = {r["source"]: r for r in ctx.redirects}
    for r in ctx.redirects:
        dest = r["destination"]
        dparts = urllib.parse.urlsplit(dest)
        res = {"source": r["source"], "destination": dest, "problems": []}
        if dparts.netloc and htmlx.bare_host(dparts.netloc) != htmlx.bare_host(urllib.parse.urlsplit(ctx.site_url or "").netloc):
            res["external"] = True
            results.append(res)
            continue
        dpath = dparts.path or "/"
        seen = [r["source"]]
        cur = dpath
        hops = 0
        while True:
            nxt = redirect_for(ctx, cur)
            if not nxt:
                break
            hops += 1
            if nxt["source"] in seen:
                res["problems"].append("loop")
                ctx.add(F("tech.redirects.loop", "tech", "P1", "Weiterleitungsschleife", "%s führt im Kreis (%s)." % (r["source"], " → ".join(seen + [nxt["source"]])),
                          evidence={"file": vfile, "snippet": r["source"]}, action_type="tech_fix"))
                break
            seen.append(nxt["source"])
            cur = urllib.parse.urlsplit(nxt["destination"]).path or "/"
        if hops and "loop" not in res["problems"]:
            res["problems"].append("chain")
            ctx.add(F("tech.redirects.chain", "tech", "P2", "Weiterleitungskette", "%s → %s leitet noch %d-mal weiter. Direkt auf das Endziel zeigen." % (r["source"], dest, hops),
                      evidence={"file": vfile, "snippet": r["source"], "value": seen}, action_type="tech_fix"))
        if r["literal"] and ctx.pages:
            tp = ctx.norm_path(dpath)
            if tp not in ctx.pages and dpath not in ctx.files and "loop" not in res["problems"] and not redirect_for(ctx, dpath):
                res["problems"].append("target_missing")
                ctx.add(F("tech.redirects.target_missing", "tech", "P2", "Weiterleitung ins Leere", "%s leitet auf %s, diese Seite gibt es im Build nicht." % (r["source"], dest),
                          evidence={"file": vfile, "snippet": dest}, action_type="tech_fix"))
            elif dparts.fragment and tp in ctx.pages and dparts.fragment not in ctx.pages[tp]["page"].ids:
                res["problems"].append("anchor_missing")
                ctx.add(F("tech.redirects.anchor_missing", "tech", "P3", "Weiterleitung auf fehlenden Anker", "%s zeigt auf %s, den Anker #%s gibt es dort nicht." % (r["source"], dest, dparts.fragment),
                          evidence={"file": vfile, "snippet": dest}, action_type="tech_fix"))
        if dpath != "/" and ctx.slash == "never" and dpath.endswith("/"):
            res["problems"].append("slash")
            ctx.add(F("tech.redirects.slash", "tech", "P3", "Weiterleitungsziel verletzt die Slash-Regel", "%s → %s erzeugt einen zweiten Sprung." % (r["source"], dest),
                      evidence={"file": vfile, "snippet": dest}, action_type="tech_fix"))
        if not r.get("permanent", True):
            res["problems"].append("temporary")
            ctx.add(F("tech.redirects.temporary", "tech", "P3", "Vorübergehende Weiterleitung", "%s ist nicht permanent (307). Für dauerhafte Umzüge `permanent: true` (308)." % r["source"],
                      evidence={"file": vfile, "snippet": r["source"]}, action_type="tech_fix"))
        results.append(res)
    old: List[str] = []
    if args.old_urls:
        txt = Path(args.old_urls).read_text(encoding="utf-8")
        old = [x.strip() for x in re.split(r"[\n,]", txt) if x.strip() and not x.strip().startswith("#")]
    if args.from_gsc and ctx.state:
        gsc = st.load_latest_snapshot(ctx.state, "gsc") or {}
        for row in gsc.get("pages") or gsc.get("rows") or []:
            if row.get("page"):
                old.append(row["page"])
    lost = []
    for u in sorted(set(old)):
        pth = urllib.parse.urlsplit(u).path or "/"
        if ctx.norm_path(pth) in ctx.pages or redirect_for(ctx, pth) or pth in ctx.files:
            continue
        lost.append(u)
    if lost:
        ctx.add(F("tech.redirects.old_url_404", "tech", "P2", "Alte Adressen ohne Weiterleitung",
                  "%d frühere Adresse(n) führen ins Leere, z. B. %s. Jede alte URL mit Impressionen oder Links braucht eine 308-Weiterleitung auf die passende neue Seite (nicht pauschal auf die Startseite)." % (len(lost), lost[0]),
                  evidence={"file": vfile, "snippet": lost[0], "value": lost[:20]}, action_type="tech_fix"))
    live = []
    if args.live:
        if args.fixture:
            http.use_fixture(args.fixture)
        base = args.live.rstrip("/")
        for r in ctx.redirects:
            if not r["literal"]:
                continue
            try:
                resp = http.fetch(base + r["source"], allow_private=args.allow_private)
                hops = len(resp.history)
                ok = resp.status == 200 and hops == 1 and resp.history[0][0] in (301, 308)
                live.append({"source": r["source"], "status": resp.status, "hops": hops, "final": resp.url, "ok": ok})
                if not ok:
                    ctx.add(F("tech.redirects.live_failed", "tech", "P2", "Weiterleitung live fehlerhaft", "%s: Status %s nach %d Sprung/Sprüngen (erwartet: ein 308 auf eine Seite mit 200)." % (r["source"], resp.status, hops),
                              evidence={"url": base + r["source"], "value": resp.status}, action_type="tech_fix"))
            except http.FetchError as exc:
                live.append({"source": r["source"], "error": str(exc)})
    findings = cli.sort_findings(ctx.findings)
    out = {"mode": "redirects", "redirects": results, "old_urls_checked": len(set(old)), "old_urls_lost": lost, "live": live, "findings": findings}
    cli.emit(out, args, cli.render_findings_de(findings, "Weiterleitungen: %d Regeln, %d alte Adressen geprüft" % (len(results), len(set(old)))))
    return cli.EXIT_FAIL if cli.at_or_above(findings, args.fail_on or "P2") else cli.EXIT_OK


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/site_audit.py dist dist --fail-on P1\n  python3 scripts/site_audit.py live https://www.musterbetrieb.example --max-pages 25 --json")
    subs = cli.add_subcommands(p)

    def common(sp: Any) -> None:
        sp.add_argument("--fail-on", dest="fail_on", choices=("P1", "P2", "P3"), help="exit 1 when a verified finding at or above this severity exists")
        sp.add_argument("--write-snapshot", dest="write_snapshot", action="store_true", help="write snapshots/<date>/site.json")
        sp.add_argument("--with-graph", dest="with_graph", action="store_true", help="include the link graph in --json output")
        sp.add_argument("--trade", help="trade word for title and H1 checks in prospect mode")

    sp = cli.add_sub(subs, "dist", "audit a built dist folder")
    sp.add_argument("dir")
    sp.add_argument("--repo", help="repo root with astro.config and vercel.json (default: parent of dist)")
    sp.add_argument("--site", help="site URL when astro.config has none")
    common(sp)
    sp = cli.add_sub(subs, "live", "polite live crawl (GET only, robots.txt respected)")
    sp.add_argument("url")
    sp.add_argument("--max-pages", dest="max_pages", type=int, default=None, help="default caps.crawl_pages (25)")
    sp.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    sp.add_argument("--fixture", help="answer requests from a saved fixture file")
    sp.add_argument("--allow-private", action="store_true")
    common(sp)
    sp = cli.add_sub(subs, "page", "audit one URL or HTML file")
    sp.add_argument("target")
    sp.add_argument("--site")
    sp.add_argument("--money", action="store_true", help="treat as a money page")
    sp.add_argument("--fixture")
    sp.add_argument("--allow-private", action="store_true")
    common(sp)
    sp = cli.add_sub(subs, "linkgraph", "internal link graph from a dist folder or a live crawl")
    sp.add_argument("target", nargs="?", default="dist")
    sp.add_argument("--repo")
    sp.add_argument("--site")
    sp.add_argument("--fail-on", dest="fail_on", choices=("P1", "P2", "P3"))
    sp.add_argument("--max-pages", dest="max_pages", type=int, default=None)
    sp.add_argument("--delay", type=float, default=0.5)
    sp.add_argument("--fixture")
    sp.add_argument("--allow-private", action="store_true")
    sp = cli.add_sub(subs, "redirects", "redirect integrity from vercel.json (exit 1 on P2 or worse by default)")
    sp.add_argument("--repo", default=".")
    sp.add_argument("--dist")
    sp.add_argument("--site")
    sp.add_argument("--old-urls", dest="old_urls", help="file with old URLs (one per line)")
    sp.add_argument("--from-gsc", dest="from_gsc", action="store_true", help="add pages from the latest GSC snapshot as old URLs")
    sp.add_argument("--live", help="base URL: fetch every literal redirect source and expect one 308 to a 200")
    sp.add_argument("--fixture")
    sp.add_argument("--allow-private", action="store_true")
    sp.add_argument("--fail-on", dest="fail_on", choices=("P1", "P2", "P3"))
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {"dist": cmd_dist, "live": cmd_live, "page": cmd_page, "linkgraph": cmd_linkgraph, "redirects": cmd_redirects}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
