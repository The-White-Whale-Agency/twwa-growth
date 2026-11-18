#!/usr/bin/env python3
"""Page quality gates A to H for twwa-growth (spec section 10).

A demand, B service relationship, C local evidence, D distinctness (swap test, shingle similarity, town
lists), E usefulness (thin flag), F facts and law (provenance and legal lint), G ramp and pilot, H prune.
`run` executes A to G for one page and exits 1 when a gate fails, with the measured value, the threshold
and the German backlog reason. All numbers are internal heuristics stored in config.thresholds.gates;
Google publishes no numeric threshold."""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, state as st, textde  # noqa: E402
import evidence as ev  # noqa: E402
import legal_lint  # noqa: E402
import style_lint_de  # noqa: E402

LEGAL_STEMS = {"index", "impressum", "datenschutz", "404", "500", "agb", "privacy"}
CTA_RE = re.compile(r"\b(anrufen|jetzt anfragen|anfrage|angebot|termin|kontakt|schreiben sie|whatsapp|rückruf|beratung vereinbaren)\b", re.IGNORECASE)
PRICE_RE = re.compile(r"(\d[\d.,]*\s*(€|euro|eur)\b|ab\s+\d[\d.,]*\s*(€|euro)|preis\w*[^.]{0,40}\d|kosten[^.]{0,40}\d)", re.IGNORECASE)
SPEED_RE = re.compile(r"(\b(\d+|ein\w*|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)\s*(arbeits|werk)?(tag|tage|tagen|woche|wochen|stunde|stunden|monat|monaten)\b|innerhalb von|binnen)", re.IGNORECASE)
PROOF_RE = re.compile(r"\b(projekt\w*|referenz\w*|bewertung\w*|kunde\w*|vorher|nachher|baustelle\w*|ausgeführt|saniert|fertiggestellt)\b", re.IGNORECASE)
PHONE_TXT_RE = re.compile(r"(\+49|\b0\d{2,5})[\s/\-]*\d[\d\s/\-]{4,}")


# ---------------------------------------------------------------- page loading

class Doc:
    def __init__(self, path: Path, business: Dict[str, Any]):
        self.path = path
        self.raw = path.read_text(encoding="utf-8", errors="replace")
        self.kind = "md" if path.suffix.lower() in (".md", ".mdx", ".txt") else "html"
        self.meta = ev.page_meta_from_file(path, business)
        self.page: Optional[htmlx.Page] = None
        self.blocks: List[Dict[str, Any]] = []
        if self.kind == "html":
            self.page = htmlx.parse(self.raw, "https://site.invalid" + (self.meta.get("path") or "/"))
            self.blocks = [b for b in self.page.text_blocks if b["main"]]
            self.full_text = self.page.full_text
            self.has_form = bool(self.page.forms)
            self.tel = bool(self.page.tel_links)
            self.cta = any(CTA_RE.search(l.get("text") or "") for l in self.page.links) or any(CTA_RE.search(b.get("text") or "") for b in self.page.buttons) or self.tel
        else:
            self.blocks = self._md_blocks()
            self.full_text = "\n".join(b["text"] for b in self.blocks)
            fm = ev.frontmatter(self.raw)
            layout = bool(fm.get("layout_contact"))
            self.has_form = layout or "<form" in self.raw
            self.tel = layout or "tel:" in self.raw or bool(PHONE_TXT_RE.search(self.full_text))
            self.cta = layout or bool(CTA_RE.search(self.full_text))
        self.unique_blocks = [b for b in self.blocks if not b["shared"]]
        self.text = "\n".join(ev.MARKER_RE.sub("", b["text"]) for b in self.unique_blocks)
        self.body_words = sum(len(ev.MARKER_RE.sub("", b["text"]).split()) for b in self.blocks)
        self.shared_words = sum(len(b["text"].split()) for b in self.blocks if b["shared"])
        self.unique_words = self.body_words - self.shared_words

    def _md_blocks(self) -> List[Dict[str, Any]]:
        lines = self.raw.splitlines()
        start = 0
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    start = i + 1
                    break
        blocks: List[Dict[str, Any]] = []
        shared = 0
        buf: List[str] = []

        def flush() -> None:
            t = " ".join(x.strip() for x in buf).strip()
            buf.clear()
            if t:
                blocks.append({"tag": "p", "text": t, "shared": shared > 0, "main": True})

        for ln in lines[start:]:
            s = ln.strip()
            if re.match(r"^<div[^>]*data-twwa-shared", s):
                flush()
                shared += 1
                continue
            if s.startswith("</div>") and shared:
                flush()
                shared -= 1
                continue
            if not s:
                flush()
                continue
            if s.startswith("<!--"):
                continue
            s = re.sub(r"^#+\s*", "", s)
            s = re.sub(r"^\s*[-*]\s+|^\s*\d+\.\s+", "", s)
            s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
            s = re.sub(r"<[^>]+>", " ", s)
            if ln.lstrip().startswith(("#", "-", "*")) or re.match(r"^\s*\d+\.\s", ln):
                flush()
                buf.append(s)
                flush()
            else:
                buf.append(s)
        flush()
        return blocks

    def sentences(self, unique_only: bool = True) -> List[str]:
        out = []
        for b in (self.unique_blocks if unique_only else self.blocks):
            for s in textde.sentences(b["text"]):
                if len(textde.words(ev.MARKER_RE.sub("", s))) >= 3:
                    out.append(s)
        return out


def result(gate: str, name: str, ok: bool, value: Any, threshold: Any, reason_de: str, **details: Any) -> Dict[str, Any]:
    r = {"gate": gate, "name": name, "ok": ok, "value": value, "threshold": threshold, "reason_de": reason_de}
    r.update(details)
    return r


def _area(b: Dict[str, Any], town: Optional[str]) -> Optional[Dict[str, Any]]:
    return next((t for t in b.get("service_area") or [] if ev.same_town(t.get("town"), town)), None)


# ---------------------------------------------------------------- gates

def gate_demand(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    town = doc.meta.get("town")
    area = _area(b, town) or {}
    pop = area.get("population")
    need = int(g["demand_impressions_small_town"]) if (pop is not None and pop < int(g["small_town_population"])) else int(g["demand_impressions_other"])
    kw = st.load_json(state / "keywords.json", {}) or {}
    clusters = [c for c in kw.get("clusters") or [] if (doc.meta.get("cluster") and c.get("id") == doc.meta.get("cluster"))
                or (c.get("target_page") and c.get("target_page") == doc.meta.get("path"))
                or (ev.same_town(c.get("town"), town) and (not doc.meta.get("service") or c.get("service") in (None, doc.meta.get("service"))))]
    queries = {textde.fold_umlauts(q).lower() for c in clusters for q in c.get("queries") or []}
    svc = next((s for s in b.get("services") or [] if s.get("id") == doc.meta.get("service")), None)
    terms = [x for x in ([svc.get("name")] if svc else []) + [b.get("trade") or ""] + list((b.get("voice") or {}).get("regional_terms") or []) if x]
    gsc = st.load_latest_snapshot(state, "gsc")
    impressions = None
    if gsc is not None:
        impressions = 0
        for r in gsc.get("rows") or []:
            q = textde.fold_umlauts(r.get("query") or "").lower()
            if q in queries or (town and textde.contains_town(q, town) and any(textde.contains_term(q, t) for t in terms)):
                impressions += int(r.get("impressions") or 0)
    volume = sum(int(c.get("volume") or 0) for c in clusters)
    kv = st.load_latest_snapshot(state, "keyword-volume")
    if kv:
        for it in kv.get("items") or []:
            if textde.fold_umlauts(it.get("keyword") or "").lower() in queries:
                volume += int(it.get("volume") or 0)
    jobs = int(area.get("jobs_last_24_months") or 0)
    cutoff = (st.today_date() - _dt.timedelta(days=int(g["demand_jobs_months"]) * 30)).isoformat()[:7]
    proj_jobs = len([p for p in ev.load_projects(state) if ev.same_town(p.get("town"), town) and (p.get("month") or "9999") >= cutoff])
    jobs = max(jobs, proj_jobs)
    in_area = bool(area)
    ok_gsc = impressions is not None and impressions >= need
    ok_vol = volume > 0
    ok_jobs = jobs >= int(g["demand_min_jobs"]) and in_area
    ok = ok_gsc or ok_vol or ok_jobs
    value = {"gsc_impressions_90d": impressions if impressions is not None else "nicht geprüft", "keyword_volume": volume, "jobs_24m": jobs, "in_service_area": in_area}
    thr = {"gsc_impressions_90d": need, "keyword_volume": "> 0", "jobs_24m": int(g["demand_min_jobs"])}
    reason = "Nachfrage belegt" if ok else "wartet auf Nachfrage in %s: %s Impressionen in 90 Tagen (Ziel %d), kein Suchvolumen, %d Aufträge in 24 Monaten (Ziel %d). Bis dahin %s im Einsatzgebiet der Leistungsseite nennen." % (
        town or "?", value["gsc_impressions_90d"], need, jobs, int(g["demand_min_jobs"]), town or "den Ort")
    return result("A", "demand", ok, value, thr, reason, gsc_snapshot=(gsc or {}).get("_date"))


def gate_service(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    town = doc.meta.get("town")
    area = _area(b, town)
    dm = (area or {}).get("drive_minutes")
    conf = (area or {}).get("owner_confirmed")
    ok = bool(area) and bool(conf) and dm is not None and float(dm) <= float(g["max_drive_minutes"])
    if ok:
        reason = "Einsatzgebiet bestätigt"
    elif not area:
        reason = "%s steht nicht im Einsatzgebiet (business.json service_area)." % (town or "Kein Ort erkannt;")
    elif not conf:
        reason = "wartet auf Bestätigung des Betriebs, dass in %s aktiv Aufträge angenommen werden" % town
    else:
        reason = "Anfahrt nach %s unbekannt oder über %s Minuten" % (town, g["max_drive_minutes"])
    return result("B", "service", ok, {"in_service_area": bool(area), "owner_confirmed": conf, "drive_minutes": dm},
                  {"owner_confirmed": "Datum", "drive_minutes": "<= %s" % g["max_drive_minutes"]}, reason)


def gate_evidence(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    town = doc.meta.get("town")
    items = ev.items_for_page(state, town, doc.meta.get("service"), doc.meta.get("path"), b)
    first = [i for i in items if i["first_party"]]
    need, need_first = int(g["evidence_min_items"]), int(g["evidence_min_first_party"])
    ok = len(items) >= need and len(first) >= need_first
    if ok:
        reason = "genug Belege"
    elif not [i for i in items if i["kind"] == "project"]:
        reason = "wartet auf erstes Projekt mit Fotos in %s" % (town or "dem Ort")
    elif len(first) < need_first:
        reason = "wartet auf einen Beleg aus erster Hand in %s (eigenes Projekt mit Fotos, Bewertung mit Einwilligung, Ansprechpartner oder Anfahrt)" % town
    else:
        reason = "wartet auf %d weitere Belege in %s" % (need - len(items), town)
    return result("C", "evidence", ok, {"items": len(items), "first_party": len(first)}, {"items": need, "first_party": need_first}, reason,
                  items=[{"kind": i["kind"], "id": i["id"], "first_party": i["first_party"]} for i in items])


def _nearest_sibling(b: Dict[str, Any], town: Optional[str]) -> Optional[str]:
    area = _area(b, town)
    others = [t for t in b.get("service_area") or [] if not ev.same_town(t.get("town"), town)]
    if not others:
        return None
    base = float((area or {}).get("drive_minutes") or 0)
    others.sort(key=lambda t: abs(float(t.get("drive_minutes") or 0) - base))
    return others[0].get("town")


def swap_analysis(state: Path, b: Dict[str, Any], doc: Doc, sibling: Optional[str] = None) -> Dict[str, Any]:
    town = doc.meta.get("town")
    sibling = sibling or _nearest_sibling(b, town) or "Nachbarort"
    ents = ev.town_entities(state, town, b) if town else []
    nums = ev.town_numbers(state, town, b) if town else []
    proj_ids = {p["id"] for p in ev.load_projects(state) if ev.same_town(p.get("town"), town)}
    fact_ids = {f.get("id") for f in ev.load_facts(state) if ev.same_town(f.get("town"), town)}
    variants = textde.town_variants(town) if town else []
    area = _area(b, town) or {}
    for d in area.get("districts") or []:
        variants += textde.town_variants(d)
    rows = []
    for s in doc.sentences():
        clean = ev.MARKER_RE.sub("", s)
        why = []
        for e in ents:
            if textde.contains_term(clean, e):
                why.append(e)
        for val, unit in nums:
            for n in textde.numbers(clean):
                if n == val and re.search(r"%s\s*%s" % (re.escape(str(int(val)) if val == int(val) else str(val).replace(".", ",")), unit), clean, re.IGNORECASE):
                    why.append("%g %s" % (val, unit.split("|")[0].strip("()\\b")))
        for kind, ref in ev.MARKER_RE.findall(s):
            if (kind == "p" and ref.strip() in proj_ids) or (kind == "f" and ref.strip() in fact_ids):
                why.append("%s:%s" % (kind, ref.strip()))
        swapped = clean
        for v in sorted(set(variants), key=len, reverse=True):
            swapped = re.sub(r"(?<![\wäöüß])" + re.escape(v) + r"(?![\wäöüß])", sibling, swapped)
        rows.append({"sentence": clean, "town_bound": bool(why), "because": sorted(set(why)), "swapped": swapped if why else None})
    bound = [r for r in rows if r["town_bound"]]
    share = (len(bound) / float(len(rows))) if rows else 0.0
    boiler = (doc.shared_words / float(doc.body_words)) if doc.body_words else 0.0
    return {"town": town, "sibling": sibling, "sentences": len(rows), "town_bound": len(bound), "share": round(share, 3),
            "boilerplate_share": round(boiler, 3), "rows": rows, "entities": ents}


def gate_swap(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc, sibling: Optional[str] = None) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    a = swap_analysis(state, b, doc, sibling)
    need, bmax = float(g["swap_min_town_bound_share"]), float(g["boilerplate_max_share"])
    ok = a["share"] >= need and a["boilerplate_share"] < bmax
    if ok:
        reason = "ortsgebunden genug"
    elif a["boilerplate_share"] >= bmax:
        reason = "zu viel geteilter Text: %d%% Textbausteine (Grenze %d%%)" % (round(a["boilerplate_share"] * 100), round(bmax * 100))
    else:
        reason = "Ortstausch-Test nicht bestanden: nur %d von %d Sätzen werden falsch, wenn %s durch %s ersetzt wird (%d%%, Ziel %d%%). Es fehlen Belege aus %s." % (
            a["town_bound"], a["sentences"], a["town"], a["sibling"], round(a["share"] * 100), round(need * 100), a["town"])
    return result("D", "swap", ok, {"town_bound_share": a["share"], "boilerplate_share": a["boilerplate_share"]},
                  {"town_bound_share": ">= %s" % need, "boilerplate_share": "< %s" % bmax}, reason,
                  sibling=a["sibling"], town_bound_sentences=[r["sentence"] for r in a["rows"] if r["town_bound"]][:10],
                  swapped_examples=[r["swapped"] for r in a["rows"] if r["town_bound"]][:3])


def sibling_files(doc: Doc, extra_dirs: List[str]) -> List[Path]:
    dirs = [doc.path.parent] + [Path(d) for d in extra_dirs]
    out: List[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.resolve() == doc.path.resolve() or not f.is_file():
                continue
            if f.suffix.lower() not in (".html", ".md", ".mdx"):
                continue
            if f.stem.lower() in LEGAL_STEMS:
                continue
            if f not in out:
                out.append(f)
    return out


def gate_similarity(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc, extra_dirs: List[str]) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    n = int(g["shingle_size"])
    mine = textde.shingles(doc.text, n)
    scores = []
    for f in sibling_files(doc, extra_dirs):
        try:
            other = Doc(f, b)
        except OSError:
            continue
        scores.append((round(textde.jaccard(mine, textde.shingles(other.text, n)), 3), str(f)))
    scores.sort(reverse=True)
    top = scores[0] if scores else (0.0, None)
    limit = float(g["similarity_max_jaccard"])
    ok = top[0] <= limit
    reason = "eigenständig genug" if ok else "zu ähnlich zu %s (Jaccard %.2f, Grenze %.2f): eigene Abschnitte mit Belegen aus %s schreiben" % (
        Path(top[1]).name if top[1] else "?", top[0], limit, doc.meta.get("town") or "dem Ort")
    return result("D", "similarity", ok, top[0], "<= %s" % limit, reason, most_similar=top[1], compared=len(scores), scores=scores[:5])


def town_list_runs(doc: Doc, b: Dict[str, Any]) -> List[List[str]]:
    known = [t.get("town") for t in b.get("service_area") or [] if t.get("town")] + [x for x in [(b.get("address") or {}).get("city")] if x]
    runs = textde.town_runs(doc.full_text, known)
    if doc.page is not None:
        for lst in doc.page.lists:
            r = textde.list_town_run(lst["items"], known)
            if r:
                runs.append(r)
    return runs


def gate_townlist(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc) -> Dict[str, Any]:
    limit = int(cfg["thresholds"]["gates"]["townlist_max_towns"])
    runs = town_list_runs(doc, b)
    biggest = max((len(r) for r in runs), default=0)
    ok = biggest <= limit
    reason = "keine Ortsliste" if ok else "Ortsliste mit %d Orten entfernen; stattdessen eine Seite zum Einsatzgebiet mit gruppierten, verlinkten Orten" % biggest
    return result("D", "townlist", ok, biggest, "<= %d" % limit, reason, runs=[r[:12] for r in runs if len(r) > limit])


def gate_usefulness(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    full = doc.full_text
    svc = next((s for s in b.get("services") or [] if s.get("id") == doc.meta.get("service")), None)
    terms = [x for x in ([svc.get("name")] if svc else []) + [b.get("trade") or ""] + list((b.get("voice") or {}).get("regional_terms") or []) if x]
    town = doc.meta.get("town")
    checks = {
        "what": any(textde.contains_term(full, t) for t in terms) or bool(svc and textde.contains_term(full, svc.get("id", ""))),
        "where": bool(town) and textde.contains_town(full, town),
        "price_range": bool(PRICE_RE.search(full)),
        "how_fast": bool(SPEED_RE.search(full)),
        "proof": bool(PROOF_RE.search(full)) and (doc.kind == "md" or any(i.get("alt") for i in (doc.page.images if doc.page else []))),
        "contact": doc.tel or doc.has_form or bool(PHONE_TXT_RE.search(full)),
        "cta": doc.cta,
        "action_on_page": doc.has_form or doc.tel,
    }
    labels = {"what": "Leistung", "where": "Ort", "price_range": "Preisrahmen", "how_fast": "Dauer oder Reaktionszeit", "proof": "Nachweis (Projekt mit Foto, Bewertung)",
              "contact": "Kontaktweg", "cta": "Handlungsaufforderung", "action_on_page": "Anruf oder Formular direkt auf der Seite"}
    missing = [labels[k] for k, v in checks.items() if not v]
    thin = doc.unique_words < int(g["thin_min_words"])
    ok = not missing
    reason = ("vollständig" + ("; Hinweis: nur %d eigene Wörter (dünn unter %d)" % (doc.unique_words, int(g["thin_min_words"])) if thin else "")) if ok else "es fehlen: %s" % ", ".join(missing)
    return result("E", "usefulness", ok, checks, "alle vorhanden", reason, thin=thin, unique_words=doc.unique_words, thin_min_words=int(g["thin_min_words"]))


def html_claims(state: Path, b: Dict[str, Any], doc: Doc) -> List[Dict[str, Any]]:
    """Rule-based claim mapping for built pages (markers are stripped at build time)."""
    town = doc.meta.get("town")
    towns = [t.get("town") for t in b.get("service_area") or [] if t.get("town")] + [x for x in [(b.get("address") or {}).get("city")] if x]
    projects = ev.load_projects(state)
    facts = ev.load_facts(state)
    values = ev._flatten(b) + [v for p in projects for v in ev._flatten(p)] + [v for f in facts for v in ev._flatten(f)]
    have = set(ev._nums_in(values))
    phones = {textde.norm_phone(v) for v in values if re.search(r"\d{4}", v)}
    reg_text = textde.fold_umlauts(" ".join(values)).lower()
    rows = []
    for s in doc.sentences(unique_only=False):
        reasons = ev.factual_reasons(s, town, towns)
        reasons = [r for r in reasons if not r.startswith("anderer Ort")]  # service-area towns are business facts
        if not reasons:
            continue
        probs = []
        plain = s
        for ph in ev.PHONE_SEQ.findall(plain):
            if textde.norm_phone(ph) not in phones:
                probs.append("Telefonnummer %s nicht in business.json" % ph.strip())
            plain = plain.replace(ph, " ")
        for n in textde.numbers(plain):
            if n not in have:
                probs.append("Zahl %g ohne Beleg im Register" % n)
        if "Qualifikation" in reasons and not (b.get("credentials") or b.get("memberships") or any(f.get("kind") == "credential" for f in facts)):
            probs.append("Qualifikation ohne Eintrag in credentials")
        if "Programm oder Behörde" in reasons:
            words = re.findall(ev.PROGRAMME_RE, s, re.IGNORECASE)
            for w in words:
                if textde.fold_umlauts(w if isinstance(w, str) else w[0]).lower() not in reg_text:
                    probs.append("Programm oder Behörde „%s“ ohne Fakt" % (w if isinstance(w, str) else w[0]))
        if "Vergleich oder Superlativ" in reasons:
            m = re.search(ev.COMPARE_RE, s, re.IGNORECASE)
            if m and textde.fold_umlauts(m.group(0)).lower() not in reg_text:
                probs.append("Vergleich „%s“ ohne Beleg" % m.group(0))
        rows.append({"sentence": s, "reasons": reasons, "ok": not probs, "problems": probs})
    return rows


def gate_facts(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc) -> Dict[str, Any]:
    if doc.kind == "md":
        prov = ev.provenance_check(state, doc.raw, doc.meta.get("town"), cfg)
        fails = [r for r in prov["rows"] if r["status"] == "fail"]
        claims = [{"sentence": r["sentence"], "problems": r["problems"], "line": r["line"]} for r in fails]
        n_fact = prov["factual_sentences"]
        text_for_lint = doc.raw
    else:
        rows = html_claims(state, b, doc)
        fails = [r for r in rows if not r["ok"]]
        claims = [{"sentence": r["sentence"], "problems": r["problems"]} for r in fails]
        n_fact = len(rows)
        text_for_lint = doc.full_text
    legal = [i for i in legal_lint.lint_text(text_for_lint, "page", cfg) if i["level"] == "block"]
    style = style_lint_de.lint(doc.raw if doc.kind == "md" else "\n".join(b["text"] for b in doc.blocks))
    ok = not fails and not legal and not style["gate_failed"]
    if ok:
        reason = "alle Aussagen belegt, Rechtsprüfung ohne Befund"
    else:
        parts = []
        if fails:
            parts.append("%d von %d Tatsachenaussagen ohne Beleg (Owner-Rückfrage oder Satz streichen)" % (len(fails), n_fact))
        if legal:
            parts.append("%d unzulässige Formulierung(en): %s" % (len(legal), legal[0]["message_de"]))
        if style["gate_failed"]:
            hits = [i for i in style["issues"] if i["class"] in style_lint_de.GATE_CLASSES]
            parts.append("Stil: %s" % (("%d Floskel(n) oder leere Superlative, z. B. „%s“" % (len(hits), hits[0]["match"])) if hits else
                                       "Fülldichte %.1f je 100 Wörter (Grenze %.1f)" % (style["density_per_100_words"], style["density_limit"])))
        reason = "; ".join(parts)
    return result("F", "facts", ok, {"unsourced": len(fails), "legal_blocks": len(legal), "style_gate_failed": style["gate_failed"]},
                  {"unsourced": 0, "legal_blocks": 0, "style_gate_failed": False}, reason,
                  unsourced=claims[:10], legal=[{"line": i["line"], "rule": i["rule"], "snippet": i["snippet"]} for i in legal][:10])


def _indexed_pages(state: Path) -> Tuple[int, str]:
    gsc = st.load_latest_snapshot(state, "gsc")
    if gsc and gsc.get("inspection"):
        n = len([i for i in gsc["inspection"] if str(i.get("verdict", "")).upper() == "PASS"])
        if n:
            return n, "gsc.inspection"
    site = st.load_latest_snapshot(state, "site")
    if site and site.get("pages"):
        return len([p for p in site["pages"] if p.get("indexable")]), "site.json"
    return 1, "default"


def ramp_status(state: Path, cfg: Dict[str, Any], add: int = 1, exclude: Optional[str] = None) -> Dict[str, Any]:
    """Gate G: new indexable pages this week and month against max(2, 10% of indexed pages) and 8 per month for small sites."""
    g = cfg["thresholds"]["gates"]
    import twwa_actions
    acts = twwa_actions.load_actions(state)
    today = st.today_date()
    week = month = 0
    for k, a in acts.items():
        if k == exclude or a.get("type") != "new_page" or not a.get("shipped_at"):
            continue
        d = st.parse_date(a["shipped_at"])
        pages = max(1, len(a.get("pages_affected") or []))
        if d and (today - d).days < 7:
            week += pages
        if d and (today - d).days < 30:
            month += pages
    indexed, src = _indexed_pages(state)
    lim_week = max(int(g["ramp_week_min_pages"]), int(indexed * float(g["ramp_week_share"])))
    small = indexed < int(g["small_site_pages"])
    lim_month = int(g["ramp_month_max_small_site"]) if small else None
    ok = week + add <= lim_week and (lim_month is None or month + add <= lim_month)
    reason = "im Tempo-Rahmen" if ok else "Tempo-Grenze: %d neue Seiten diese Woche (max. %d) und %d in 30 Tagen (max. %s); nächste Seite später" % (
        week + add, lim_week, month + add, lim_month if lim_month is not None else "-")
    return {"ok": ok, "week": week, "month": month, "add": add, "limit_week": lim_week, "limit_month": lim_month,
            "indexed_pages": indexed, "indexed_source": src, "reason_de": reason}


def pilot_status(state: Path, cfg: Dict[str, Any], template: str) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    import twwa_actions
    acts = [a for a in twwa_actions.load_actions(state).values() if a.get("template") == template and a.get("type") == "new_page" and a.get("shipped_at")]
    pages: List[Tuple[str, Optional[_dt.date]]] = []
    for a in acts:
        for p in a.get("pages_affected") or []:
            pages.append((p, st.parse_date(a["shipped_at"])))
    n = len(pages)
    if n < int(g["pilot_max_pages"]):
        return {"template": template, "pilot_pages": n, "phase": "pilot", "ok": True,
                "reason_de": "Pilotphase: %d von höchstens %d Seiten der Vorlage veröffentlicht" % (n, int(g["pilot_max_pages"]))}
    gsc = st.load_latest_snapshot(state, "gsc") or {}
    today = st.today_date()
    insp = {i.get("url", "").rstrip("/").split("://")[-1].split("/", 1)[-1]: i for i in gsc.get("inspection") or []}
    impr: Dict[str, int] = {}
    for row in gsc.get("pages") or gsc.get("rows") or []:
        key = (row.get("page") or "").rstrip("/").split("://")[-1].split("/", 1)[-1]
        impr[key] = impr.get(key, 0) + int(row.get("impressions") or 0)
    young = [p for p, d in pages if d and (today - d).days < int(g["pilot_indexed_days"])]
    if young:
        return {"template": template, "pilot_pages": n, "phase": "waiting", "ok": False,
                "reason_de": "Pilot läuft noch: %d Seiten jünger als %d Tage; weitere Seiten dieser Vorlage erst nach der Auswertung" % (len(young), int(g["pilot_indexed_days"]))}
    keys = [p.strip("/") for p, _ in pages]
    indexed = len([k for k in keys if str((insp.get(k) or {}).get("verdict", "")).upper() == "PASS"])
    with_impr = len([k for k in keys if impr.get(k, 0) > 0])
    old_enough = all(d and (today - d).days >= int(g["pilot_impressions_days"]) for _, d in pages)
    ok = indexed / float(n) >= float(g["pilot_indexed_share"]) and (not old_enough or with_impr / float(n) >= float(g["pilot_impressions_share"]))
    return {"template": template, "pilot_pages": n, "phase": "evaluated", "ok": ok, "indexed_share": round(indexed / float(n), 2),
            "impressions_share": round(with_impr / float(n), 2) if old_enough else "noch nicht auswertbar",
            "reason_de": "Pilot bestanden" if ok else "Pilot nicht bestanden: %d von %d Seiten indexiert, %d mit Impressionen; Vorlage verbessern statt ausweiten" % (indexed, n, with_impr)}


def gate_ramp(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc, action_id: Optional[str] = None) -> Dict[str, Any]:
    r = ramp_status(state, cfg, add=1, exclude=action_id)
    details: Dict[str, Any] = {}
    ok = r["ok"]
    reason = r["reason_de"]
    template = doc.meta.get("template")
    if action_id:
        import twwa_actions
        a = twwa_actions.load_actions(state).get(action_id) or {}
        template = template or a.get("template")
    if template:
        p = pilot_status(state, cfg, template)
        details["pilot"] = p
        if not p["ok"]:
            ok, reason = False, p["reason_de"]
    return result("G", "ramp", ok, {"week": r["week"] + 1, "month": r["month"] + 1}, {"week": r["limit_week"], "month": r["limit_month"]}, reason,
                  indexed_pages=r["indexed_pages"], indexed_source=r["indexed_source"], **details)


def prune_candidates(state: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    g = cfg["thresholds"]["gates"]
    import twwa_actions
    gsc = st.load_latest_snapshot(state, "gsc")
    if gsc is None:
        return {"checked": False, "reason_de": "nicht geprüft: kein GSC-Snapshot", "candidates": [], "templates": []}
    today = st.today_date()
    agg: Dict[str, Dict[str, int]] = {}
    for row in gsc.get("pages") or gsc.get("rows") or []:
        key = "/" + (row.get("page") or "").split("://")[-1].split("/", 1)[-1].strip("/")
        a = agg.setdefault(key, {"clicks": 0, "impressions": 0})
        a["clicks"] += int(row.get("clicks") or 0)
        a["impressions"] += int(row.get("impressions") or 0)
    leads_pages = {l.get("page") for l in st.read_jsonl(state / "leads.jsonl")}
    cands = []
    templates: Dict[str, Dict[str, int]] = {}
    insp = gsc.get("inspection") or []
    for a in twwa_actions.load_actions(state).values():
        if a.get("type") != "new_page" or not a.get("shipped_at") or a.get("state") in ("reverted", "superseded"):
            continue
        d = st.parse_date(a["shipped_at"])
        for p in a.get("pages_affected") or []:
            key = "/" + p.strip("/")
            if a.get("template"):
                t = templates.setdefault(a["template"], {"pages": 0, "crawled_not_indexed": 0})
                t["pages"] += 1
                if any(key.strip("/") in (i.get("url") or "") and "crawled" in str(i.get("coverage_state", "")).lower() and "not indexed" in str(i.get("coverage_state", "")).lower() for i in insp):
                    t["crawled_not_indexed"] += 1
            if not d or (today - d).days < int(g["prune_min_age_days"]) or a.get("seasonal"):
                continue
            m = agg.get(key, {"clicks": 0, "impressions": 0})
            if m["clicks"] == 0 and m["impressions"] < int(g["prune_max_impressions"]) and key not in leads_pages:
                cands.append({"page": key, "action_id": a["action_id"], "age_days": (today - d).days, **m,
                              "proposal_de": "%s seit %d Tagen ohne Klick und mit %d Impressionen: in die übergeordnete Leistungsseite überführen (308) oder auf noindex setzen" % (key, (today - d).days, m["impressions"])})
    stop = []
    for name, t in templates.items():
        share = t["crawled_not_indexed"] / float(t["pages"]) if t["pages"] else 0.0
        if share > float(g["prune_template_not_indexed_share"]):
            stop.append({"template": name, "share": round(share, 2), "reason_de": "Vorlage %s stoppen: %d%% der Seiten „gecrawlt, nicht indexiert“" % (name, round(share * 100))})
    return {"checked": True, "snapshot": gsc.get("_date"), "candidates": cands, "templates": stop}


# ---------------------------------------------------------------- CLI

def _ctx(args: Any) -> Tuple[Path, Dict[str, Any], Dict[str, Any], Doc]:
    state = st.require_state(args)
    cfg = st.load_config(state)
    b = st.load_business(state) or {}
    p = Path(args.page)
    if not p.is_file():
        cli.die(cli.EXIT_USAGE, "Page file not found: %s" % p)
    doc = Doc(p, b)
    for k in ("town", "service"):
        if getattr(args, k, None):
            doc.meta[k] = getattr(args, k)
    return state, cfg, b, doc


def _print_one(args: Any, r: Dict[str, Any]) -> int:
    human = "Gate %s %s: %s (Wert %s, Schwelle %s)\n  %s" % (r["gate"], r["name"], "OK" if r["ok"] else "FAIL", r["value"], r["threshold"], r["reason_de"])
    cli.emit(r, args, human)
    return cli.EXIT_OK if r["ok"] else cli.EXIT_FAIL


def run_all(state: Path, cfg: Dict[str, Any], b: Dict[str, Any], doc: Doc, action_id: Optional[str], extra_dirs: List[str]) -> List[Dict[str, Any]]:
    return [
        gate_demand(state, cfg, b, doc),
        gate_service(state, cfg, b, doc),
        gate_evidence(state, cfg, b, doc),
        gate_swap(state, cfg, b, doc),
        gate_similarity(state, cfg, b, doc, extra_dirs),
        gate_townlist(state, cfg, b, doc),
        gate_usefulness(state, cfg, b, doc),
        gate_facts(state, cfg, b, doc),
        gate_ramp(state, cfg, b, doc, action_id),
    ]


def cmd_run(args: Any) -> int:
    state, cfg, b, doc = _ctx(args)
    results = run_all(state, cfg, b, doc, args.action, args.siblings or [])
    first = next((r for r in results if not r["ok"]), None)
    out = {"page": str(doc.path), "meta": doc.meta, "ok": first is None, "first_failure": first, "results": results}
    lines = ["Gates A bis G für %s (Ort %s, Leistung %s)" % (doc.path, doc.meta.get("town"), doc.meta.get("service"))]
    for r in results:
        lines.append("  %s %-11s %s  %s" % (r["gate"], r["name"], "OK  " if r["ok"] else "FAIL", r["reason_de"]))
    if first:
        lines.append("Erster Fehlschlag: Gate %s (%s), Wert %s, Schwelle %s.\nBacklog-Grund: %s" % (first["gate"], first["name"], first["value"], first["threshold"], first["reason_de"]))
    if args.action and not args.no_record:
        import twwa_actions
        if args.action in twwa_actions.load_actions(state):
            twwa_actions.log_event(state, args.action, "gates", ok=first is None, page=str(doc.path),
                                   failed=[{"gate": r["gate"], "name": r["name"], "reason_de": r["reason_de"]} for r in results if not r["ok"]])
            if first:
                bl = st.load_json(state / "backlog.json", {"schema_version": 1, "items": []}) or {"schema_version": 1, "items": []}
                key = "gate-%s" % args.action
                item = {"id": key, "action_id": args.action, "status": "waiting", "gate": first["gate"], "reason_de": first["reason_de"],
                        "owner_request_de": first["reason_de"] if first["gate"] in ("A", "B", "C", "F") else None, "updated_on": st.today()}
                bl["items"] = [i for i in bl.get("items", []) if i.get("id") != key] + [item]
                st.save_json(state / "backlog.json", bl)
    cli.emit(out, args, "\n".join(lines))
    return cli.EXIT_OK if first is None else cli.EXIT_FAIL


def cmd_single(name: str):
    def handler(args: Any) -> int:
        state, cfg, b, doc = _ctx(args)
        if name == "demand":
            r = gate_demand(state, cfg, b, doc)
        elif name == "service":
            r = gate_service(state, cfg, b, doc)
        elif name == "evidence":
            r = gate_evidence(state, cfg, b, doc)
        elif name == "swap":
            r = gate_swap(state, cfg, b, doc, args.sibling)
        elif name == "similarity":
            r = gate_similarity(state, cfg, b, doc, args.siblings or [])
        elif name == "townlist":
            r = gate_townlist(state, cfg, b, doc)
        elif name == "thin":
            r = gate_usefulness(state, cfg, b, doc)
        elif name == "sources":
            r = gate_facts(state, cfg, b, doc)
        else:
            r = gate_ramp(state, cfg, b, doc, getattr(args, "action", None))
        return _print_one(args, r)
    return handler


def cmd_ramp(args: Any) -> int:
    state = st.require_state(args)
    r = ramp_status(state, st.load_config(state), add=args.add)
    cli.emit(r, args, "Gate G: %s" % r["reason_de"])
    return cli.EXIT_OK if r["ok"] else cli.EXIT_FAIL


def cmd_pilot(args: Any) -> int:
    state = st.require_state(args)
    r = pilot_status(state, st.load_config(state), args.template)
    cli.emit(r, args, "Pilot %s: %s" % (args.template, r["reason_de"]))
    return cli.EXIT_OK if r["ok"] else cli.EXIT_FAIL


def cmd_prune(args: Any) -> int:
    state = st.require_state(args)
    r = prune_candidates(state, st.load_config(state))
    lines = [r.get("reason_de") or "Gate H (Snapshot %s): %d Kandidaten" % (r.get("snapshot"), len(r["candidates"]))]
    lines += ["  %s" % c["proposal_de"] for c in r["candidates"]] + ["  %s" % t["reason_de"] for t in r["templates"]]
    cli.emit(r, args, "\n".join(lines))
    return cli.EXIT_FAIL if (r["candidates"] or r["templates"]) else cli.EXIT_OK


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/page_gates.py run --page .twwa-growth/drafts/2026-11-a05/seite.md --action 2026-11-a05\n"
                                 "  python3 scripts/page_gates.py swap --page dist/fassadensanierung-nachbarstadt.html --json")
    subs = cli.add_subcommands(p)

    def page_args(sp: Any) -> None:
        sp.add_argument("--page", required=True, help="Markdown draft or built HTML page")
        sp.add_argument("--town", help="override the detected town")
        sp.add_argument("--service", help="override the detected service id")

    sp = cli.add_sub(subs, "run", "gates A to G for one page; exit 1 when a gate fails")
    page_args(sp)
    sp.add_argument("--action", help="action id: log the result and turn a failure into a backlog reason")
    sp.add_argument("--siblings", action="append", default=[], help="extra folder with sibling pages for the similarity gate")
    sp.add_argument("--no-record", action="store_true", help="do not write the gate result to actions.jsonl and backlog.json")
    for name, helptext in (("demand", "Gate A demand"), ("service", "Gate B service relationship"), ("evidence", "Gate C local evidence"),
                           ("swap", "Gate D swap test (rule based)"), ("similarity", "Gate D shingle similarity against sibling pages"),
                           ("townlist", "Gate D town lists over 8 towns"), ("thin", "Gate E usefulness and thin flag"),
                           ("sources", "Gate F claims and legal lint")):
        sp = cli.add_sub(subs, name, helptext)
        page_args(sp)
        if name == "swap":
            sp.add_argument("--sibling", help="town to swap in (default: nearest service-area town)")
        if name == "similarity":
            sp.add_argument("--siblings", action="append", default=[])
    sp = cli.add_sub(subs, "ramp", "Gate G: can another new indexable page ship now?")
    sp.add_argument("--add", type=int, default=1)
    sp = cli.add_sub(subs, "pilot", "Gate G: pilot status of a page template")
    sp.add_argument("--template", required=True)
    cli.add_sub(subs, "prune", "Gate H: pages older than 90 days without clicks, impressions or leads; templates to stop")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd in ("demand", "service", "evidence", "swap", "similarity", "townlist", "thin", "sources"):
        return cmd_single(args.cmd)(args)
    return {"ramp": cmd_ramp, "pilot": cmd_pilot, "prune": cmd_prune}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
