#!/usr/bin/env python3
"""Regression guard for twwa-growth (spec 12a).

baseline   record, per sitemap URL and money page: status, final URL, canonical, indexability (meta and
           header), title, H1, schema types, a hash of the NAP fields, primary call to action, phone link,
           sitemap membership; plus every redirect in vercel.json and where it lands
run        compare the live site (or a built dist folder) with the latest baseline; add GSC inspection,
           Bing index, lab performance and the form probe from the latest snapshots when present, else
           report them as "nicht geprüft". A regression on a money page is P1 and exits 1
verify     post-deploy form of run for one action (its pages plus the money pages); logs live_verified
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, http, state as st, textde  # noqa: E402
import site_audit  # noqa: E402

CTA_RE = site_audit.CTA_RE
LB_TYPES = None


def _lb_types() -> set:
    global LB_TYPES
    if LB_TYPES is None:
        import schema_gen
        LB_TYPES = set(schema_gen.types_data().get("local_business_types") or [])
    return LB_TYPES


def nap_hash(page: htmlx.Page) -> Optional[str]:
    for n in page.jsonld_nodes():
        t = n.get("@type")
        types = set(t if isinstance(t, list) else [t])
        if types & _lb_types():
            a = n.get("address") or {}
            if not isinstance(a, dict):
                a = {}
            raw = "|".join([textde.norm_name(n.get("name")), textde.norm_address(a.get("streetAddress")), str(a.get("postalCode") or ""),
                            textde.norm_address(a.get("addressLocality")), textde.norm_phone(n.get("telephone"))])
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return None


def record_for(url: str, status: int, final_url: str, header_robots: str, html: str, in_sitemap: bool) -> Dict[str, Any]:
    page = htmlx.parse(html or "", final_url or url)
    robots = ", ".join(x for x in (page.robots, header_robots or "") if x)
    cta = bool(page.forms) or any(CTA_RE.search(l.get("text") or "") for l in page.links)
    return {"url": url, "status": status, "final_url": final_url, "canonical": page.canonical, "indexable": status == 200 and "noindex" not in robots,
            "robots": robots, "title": page.title, "h1": page.h1[0] if page.h1 else None, "schema_types": page.schema_types(),
            "nap_hash": nap_hash(page), "cta": cta, "phone_link": bool(page.tel_links), "in_sitemap": in_sitemap}


class Source:
    """Fetch pages live (optionally from a fixture) or read them from a dist folder."""

    def __init__(self, args: Any, cfg: Dict[str, Any], state: Optional[Path]):
        self.dist = Path(args.dist) if getattr(args, "dist", None) else None
        self.allow_private = bool(getattr(args, "allow_private", False))
        if getattr(args, "fixture", None):
            http.use_fixture(args.fixture)
        self.base = (getattr(args, "base_url", None) or (cfg.get("site") or {}).get("url") or ((st.load_business(state) or {}).get("url") if state else None) or "").rstrip("/")
        if not self.base:
            cli.die(cli.EXIT_USAGE, "No site URL: pass --base-url or set config.site.url.")
        repo = st.repo_root(state) if state else None
        self.slash = None
        self.vercel: Dict[str, Any] = {}
        if repo and (repo / "astro.config.mjs").is_file():
            m = re.search(r"trailingSlash\s*:\s*['\"](\w+)['\"]", (repo / "astro.config.mjs").read_text(encoding="utf-8"))
            self.slash = m.group(1) if m else None
        if repo and (repo / "vercel.json").is_file():
            self.vercel = st.load_json(repo / "vercel.json", {}) or {}

    def get(self, url: str) -> Tuple[int, str, str, str]:
        """(status, final_url, header_robots, html)"""
        if self.dist:
            path = urllib.parse.urlsplit(url).path or "/"
            rel = "index.html" if path == "/" else (path.strip("/") + ("/index.html" if self.slash == "always" else ".html"))
            f = self.dist / rel
            if not f.is_file() and path != "/":
                f = self.dist / (path.strip("/") + "/index.html")
            if not f.is_file():
                return 404, url, "", ""
            return 200, url, site_audit.dist_header_robots(_hctx(self.vercel), path), f.read_text(encoding="utf-8", errors="replace")
        try:
            r = http.fetch(url, allow_private=self.allow_private)
        except http.FetchError as exc:
            return 0, url, "", "<!-- %s -->" % exc
        return r.status, r.url, (r.headers.get("x-robots-tag") or "").lower(), r.text if "html" in r.content_type else ""

    def sitemap_urls(self) -> List[str]:
        text = None
        if self.dist:
            for n in ("sitemap-index.xml", "sitemap.xml"):
                if (self.dist / n).is_file():
                    text = (self.dist / n).read_text(encoding="utf-8")
                    break
        else:
            try:
                r = http.fetch(self.base + "/sitemap.xml", allow_private=self.allow_private)
                text = r.text if r.status == 200 else None
            except http.FetchError:
                text = None
        out: List[str] = []
        if not text:
            return out
        try:
            root = ET.fromstring(text.encode("utf-8"))
        except ET.ParseError:
            return out
        for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            if loc.text and loc.text.strip().endswith(".xml"):
                continue
            if loc.text:
                out.append(loc.text.strip())
        return out


class _hctx:
    def __init__(self, vercel: Dict[str, Any]):
        self.vercel_headers = vercel.get("headers") or []


def money_urls(base: str, cfg: Dict[str, Any], business: Optional[Dict[str, Any]]) -> List[str]:
    paths = list((cfg.get("site") or {}).get("money_pages") or ["/"])
    for s in (business or {}).get("services") or []:
        p = (s.get("page") or "").split("#")[0]
        if p and p not in paths:
            paths.append(p)
    return [base + (p if p.startswith("/") else "/" + p) for p in paths]


def take_baseline(src: Source, cfg: Dict[str, Any], state: Optional[Path], only: Optional[List[str]] = None) -> Dict[str, Any]:
    business = st.load_business(state) if state else None
    sm = src.sitemap_urls()
    money = money_urls(src.base, cfg, business)
    urls = only or list(dict.fromkeys(sm + money))
    pages = []
    for u in urls:
        status, final, hdr, html = src.get(u)
        rec = record_for(u, status, final, hdr, html, u in sm)
        rec["money"] = u in money
        pages.append(rec)
    redirects = []
    for r in src.vercel.get("redirects") or []:
        if re.search(r"[:(*]", r.get("source", "")):
            continue
        dest = r.get("destination", "")
        target = dest if dest.startswith("http") else src.base + dest.split("#")[0]
        status, _, _, _ = src.get(target)
        redirects.append({"source": r["source"], "destination": dest, "target_status": status})
    return {"source": "regression-baseline", "pulled_at": st.now_iso(), "range": {"start": None, "end": None},
            "origin": "dist" if src.dist else ("fixture" if http.fixture_active() else "live"), "base": src.base, "pages": pages, "redirects": redirects}


def F(*a: Any, **k: Any) -> Dict[str, Any]:
    return cli.finding(*a, **k)


def compare(base: Dict[str, Any], now: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cur = {p["url"]: p for p in now["pages"]}
    for b in base.get("pages") or []:
        n = cur.get(b["url"])
        if n is None:
            continue
        money = bool(b.get("money"))
        sev = "P1" if money else "P2"
        ev = {"url": b["url"]}
        if b.get("status") == 200 and n["status"] != 200:
            out.append(F("tech.regression.status", "tech", sev, "Seite liefert jetzt Status %s" % n["status"], "%s lieferte im Ausgangszustand 200, jetzt %s." % (b["url"], n["status"]),
                         evidence=dict(ev, value=n["status"]), action_type="tech_fix"))
            continue
        if b.get("indexable") and not n["indexable"]:
            out.append(F("tech.regression.noindex", "tech", sev, "Seite ist nicht mehr indexierbar", "%s ist jetzt auf noindex (%s)." % (b["url"], n.get("robots")),
                         evidence=dict(ev, snippet=n.get("robots")), action_type="tech_fix"))
        if b.get("canonical") and n.get("canonical") != b.get("canonical"):
            out.append(F("tech.regression.canonical", "tech", sev, "Canonical hat sich geändert", "Vorher %s, jetzt %s." % (b.get("canonical"), n.get("canonical") or "kein Canonical"),
                         evidence=dict(ev, snippet=n.get("canonical") or "kein canonical"), action_type="tech_fix"))
        if b.get("nap_hash") and n.get("nap_hash") != b.get("nap_hash"):
            out.append(F("tech.regression.nap", "tech", sev, "Name, Adresse oder Telefon im Markup verändert", "Die NAP-Prüfsumme im LocalBusiness-Markup ist anders (vorher %s, jetzt %s)." % (b.get("nap_hash"), n.get("nap_hash") or "kein Markup"),
                         evidence=dict(ev, value=n.get("nap_hash")), action_type="tech_fix"))
        lost = sorted(set(b.get("schema_types") or []) - set(n.get("schema_types") or []))
        if lost:
            out.append(F("tech.regression.schema", "tech", sev if set(lost) & _lb_types() else "P2", "Strukturierte Daten entfernt", "Nicht mehr vorhanden: %s." % ", ".join(lost),
                         evidence=dict(ev, snippet=", ".join(lost)), action_type="tech_fix"))
        if b.get("cta") and not n.get("cta"):
            out.append(F("cro.regression.cta", "cro", sev, "Anfrage-Möglichkeit verschwunden", "%s hat kein Formular und keinen Anfrage-Link mehr." % b["url"], evidence=dict(ev, snippet="kein CTA"), action_type="cro_change"))
        if b.get("phone_link") and not n.get("phone_link"):
            out.append(F("cro.regression.phone", "cro", sev, "Anruf-Link verschwunden", "%s hat keinen tel:-Link mehr." % b["url"], evidence=dict(ev, snippet="kein tel:"), action_type="cro_change"))
        if b.get("in_sitemap") and not n.get("in_sitemap"):
            out.append(F("tech.regression.sitemap", "tech", sev, "Seite aus der Sitemap gefallen", "%s steht nicht mehr in der Sitemap." % b["url"], evidence=dict(ev, snippet="fehlt in sitemap"), action_type="tech_fix"))
        for k, label in (("title", "Seitentitel"), ("h1", "H1")):
            if b.get(k) and n.get(k) != b.get(k):
                out.append(F("onpage.regression.%s" % k, "onpage", "P3" if money else "info", "%s geändert" % label,
                             "Vorher „%s“, jetzt „%s“. Prüfen, ob das zur freigegebenen Aktion gehört." % (b.get(k), n.get(k)), evidence=dict(ev, snippet=n.get(k) or ""), action_type="onpage_rewrite"))
    nowr = {r["source"]: r for r in now.get("redirects") or []}
    for r in base.get("redirects") or []:
        n = nowr.get(r["source"])
        if n is None:
            out.append(F("tech.regression.redirect_removed", "tech", "P2", "Weiterleitung entfernt", "%s → %s steht nicht mehr in vercel.json." % (r["source"], r["destination"]),
                         evidence={"snippet": r["source"]}, action_type="tech_fix"))
        elif r.get("target_status") == 200 and n.get("target_status") != 200:
            out.append(F("tech.regression.redirect_target", "tech", "P2", "Weiterleitungsziel kaputt", "%s zeigt auf %s, das jetzt Status %s liefert." % (r["source"], n["destination"], n.get("target_status")),
                         evidence={"snippet": r["source"], "value": n.get("target_status")}, action_type="tech_fix"))
    return out


def optional_checks(state: Optional[Path], cfg: Dict[str, Any], money: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    out: List[Dict[str, Any]] = []
    not_checked: List[str] = []
    norm = lambda u: (u or "").rstrip("/")
    gsc = st.load_latest_snapshot(state, "gsc")
    if gsc and gsc.get("inspection"):
        insp = {norm(i.get("url")): i for i in gsc["inspection"]}
        for u in money:
            i = insp.get(norm(u))
            if i is None:
                not_checked.append("GSC-Indexstatus für %s (nicht im Snapshot)" % u)
            elif str(i.get("verdict", "")).upper() != "PASS":
                out.append(F("tech.regression.gsc_not_indexed", "tech", "P1", "Wichtige Seite laut Search Console nicht indexiert",
                             "%s: %s (Snapshot %s)." % (u, i.get("coverage_state") or i.get("verdict"), gsc.get("_date")), evidence={"url": u, "value": i.get("verdict")}, action_type="tech_fix"))
            elif i.get("google_canonical") and i.get("user_canonical") and norm(i["google_canonical"]) != norm(i["user_canonical"]):
                out.append(F("tech.regression.gsc_canonical", "tech", "P2", "Google wählt ein anderes Canonical", "%s: Google nimmt %s statt %s." % (u, i["google_canonical"], i["user_canonical"]),
                             evidence={"url": u, "snippet": i["google_canonical"]}, action_type="tech_fix"))
    else:
        not_checked.append("GSC-Indexstatus (kein Snapshot mit inspection)")
    bing = st.load_latest_snapshot(state, "bing")
    if bing and bing.get("urlinfo"):
        info = {norm(i.get("url")): i for i in bing["urlinfo"]}
        for u in money:
            i = info.get(norm(u))
            if i is not None and i.get("indexed") is False:
                out.append(F("tech.regression.bing_not_indexed", "tech", "P2", "Wichtige Seite nicht im Bing-Index", "%s fehlt im Bing-Index; ChatGPT-Suche und Copilot greifen auf Bing zurück." % u,
                             evidence={"url": u, "value": False}, action_type="tech_fix"))
    else:
        not_checked.append("Bing-Indexstatus (kein Snapshot mit urlinfo)")
    psi = st.load_latest_snapshot(state, "psi")
    budget = cfg["thresholds"]["regression"]
    if psi and psi.get("pages"):
        for p in psi["pages"]:
            if norm(p.get("url")) not in {norm(u) for u in money}:
                continue
            probs = []
            if p.get("performance") is not None and float(p["performance"]) < float(budget["performance_min"]):
                probs.append("Performance %s (Ziel mindestens %s)" % (p["performance"], budget["performance_min"]))
            if p.get("cls") is not None and float(p["cls"]) > float(budget["cls_max"]):
                probs.append("CLS %s (Ziel höchstens %s)" % (p["cls"], budget["cls_max"]))
            if p.get("lcp_ms") is not None and float(p["lcp_ms"]) > float(budget["lcp_max_ms"]):
                probs.append("LCP %.1f s (Ziel höchstens %.1f s)" % (float(p["lcp_ms"]) / 1000, float(budget["lcp_max_ms"]) / 1000))
            if probs:
                out.append(F("tech.regression.performance", "tech", "P2", "Ladezeit-Budget überschritten", "%s (%s, Labormessung): %s." % (p.get("url"), p.get("strategy", "mobile"), "; ".join(probs)),
                             evidence={"url": p.get("url"), "value": probs}, action_type="tech_fix"))
    else:
        not_checked.append("Labor-Performance (kein psi.json)")
    probe = st.load_latest_snapshot(state, "form-probe")
    if probe is not None:
        if probe.get("ok") is False:
            out.append(F("tracking.regression.form", "tracking", "P1", "Formular-Test fehlgeschlagen", "Der synthetische Formular-Test vom %s ist fehlgeschlagen: %s. Anfragen gehen möglicherweise verloren." % (probe.get("_date"), probe.get("error") or probe.get("status")),
                         evidence={"url": probe.get("url"), "value": probe.get("status")}, action_type="tracking_fix", priority_group=1))
    else:
        not_checked.append("Formular-Strecke (kein form-probe.json; leads.py probe)")
    return out, not_checked


def _report(args: Any, findings: List[Dict[str, Any]], not_checked: List[str], extra: Dict[str, Any]) -> int:
    findings = cli.sort_findings(findings)
    lines = [cli.render_findings_de(findings, "Regressionsprüfung %s:" % extra.get("base"))]
    if not_checked:
        lines.append("Nicht geprüft: " + "; ".join(not_checked))
    out = dict(extra)
    out.update({"findings": findings, "not_checked": not_checked, "ok": not cli.at_or_above(findings, args.fail_on)})
    cli.emit(out, args, "\n".join(lines))
    return cli.EXIT_OK if out["ok"] else cli.EXIT_FAIL


def cmd_baseline(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    cfg = st.load_config(state)
    src = Source(args, cfg, state)
    snap = take_baseline(src, cfg, state)
    path = None
    if state:
        path = st.save_json(st.snapshot_dir(state) / "regression-baseline.json", snap)
    human = "Baseline %s: %d Seiten, %d Weiterleitungen%s" % (src.base, len(snap["pages"]), len(snap["redirects"]), (", gespeichert in %s" % path) if path else " (ohne State-Ordner nicht gespeichert)")
    cli.emit(dict(snap, written=str(path) if path else None), args, human)
    return cli.EXIT_OK


def _run(args: Any, only_pages: Optional[List[str]] = None) -> Tuple[int, List[Dict[str, Any]], Dict[str, Any]]:
    state = st.require_state(args)
    cfg = st.load_config(state)
    base = st.load_latest_snapshot(state, "regression-baseline")
    if base is None:
        cli.die(cli.EXIT_USAGE, "No baseline yet: run regression_guard.py baseline first.")
    src = Source(args, cfg, state)
    urls = [p["url"] for p in base.get("pages") or []]
    if only_pages:
        wanted = {src.base + (p if p.startswith("/") else "/" + p) for p in only_pages}
        urls = [u for u in urls if u in wanted or any(x.get("url") == u and x.get("money") for x in base["pages"])]
    now = take_baseline(src, cfg, state, only=urls)
    sm = set(src.sitemap_urls())
    for p in now["pages"]:
        p["in_sitemap"] = p["url"] in sm
        p["money"] = any(x.get("url") == p["url"] and x.get("money") for x in base["pages"])
    base_scoped = dict(base, pages=[p for p in base["pages"] if p["url"] in urls])
    findings = compare(base_scoped, now)
    money = [p["url"] for p in base["pages"] if p.get("money")]
    opt, nc = optional_checks(state, cfg, money)
    findings += opt
    st.save_json(st.snapshot_dir(state) / "regression.json", {"source": "regression", "pulled_at": st.now_iso(), "range": {"start": None, "end": None},
                                                             "origin": now["origin"], "baseline": base.get("_date"), "findings": findings, "not_checked": nc})
    return 0, findings, {"base": src.base, "baseline_date": base.get("_date"), "not_checked": nc, "state": state}


def cmd_run(args: Any) -> int:
    _, findings, extra = _run(args)
    nc = extra.pop("not_checked")
    extra.pop("state", None)
    return _report(args, findings, nc, extra)


def cmd_verify(args: Any) -> int:
    state = st.require_state(args)
    import twwa_actions
    acts = twwa_actions.load_actions(state)
    a = acts.get(args.action)
    if a is None:
        cli.die(cli.EXIT_USAGE, "Unknown action id: %s" % args.action)
    _, findings, extra = _run(args, a.get("pages_affected") or ["/"])
    p1 = [f for f in findings if f["severity"] == "P1"]
    twwa_actions.log_event(state, args.action, "live_verified", ok=not cli.at_or_above(findings, args.fail_on), p1=len(p1), findings=[f["id"] for f in findings][:30])
    nc = extra.pop("not_checked")
    extra.pop("state", None)
    extra["action_id"] = args.action
    return _report(args, findings, nc, extra)


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/regression_guard.py baseline\n  python3 scripts/regression_guard.py verify --action 2026-11-a01 --json")
    subs = cli.add_subcommands(p)

    def common(sp: Any) -> None:
        sp.add_argument("--base-url", dest="base_url", help="site URL (default config.site.url)")
        sp.add_argument("--dist", help="read pages from a built dist folder instead of the network")
        sp.add_argument("--fixture", help="answer HTTP from a saved fixture file")
        sp.add_argument("--allow-private", action="store_true")

    sp = cli.add_sub(subs, "baseline", "record the baseline to snapshots/<date>/regression-baseline.json")
    common(sp)
    for name, h in (("run", "compare with the latest baseline (weekly step 2); exit 1 on a P1 regression"),
                    ("verify", "post-deploy check for one action; exit 1 on a P1 regression")):
        sp = cli.add_sub(subs, name, h)
        common(sp)
        sp.add_argument("--fail-on", dest="fail_on", choices=("P1", "P2", "P3"), default="P1")
        if name == "verify":
            sp.add_argument("--action", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {"baseline": cmd_baseline, "run": cmd_run, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
