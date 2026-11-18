#!/usr/bin/env python3
"""Evidence registry for twwa-growth: monthly project-report intake, projects and facts, which pages each
record can support, coverage per service and town, claim provenance of drafts (spec 10b), and re-checks
of sourced facts (fetch, hash, flag change and staleness)."""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, http, state as st, textde  # noqa: E402

MONTHS = {"januar": 1, "jänner": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7,
          "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12}
PHOTO_RE = re.compile(r"[\w\-. ]*?[\w\-]+\.(?:jpe?g|png|heic|heif|webp|avif|tiff?)\b", re.IGNORECASE)
UNIT_RE = r"(m²|m2|qm|quadratmeter|lfm|laufende meter|m³|m3|meter|m\b|stück|stk\.?|zimmer|räume|etagen|geschosse|fenster|türen|wohnungen|einheiten)"
SCOPE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)\s*" + UNIT_RE, re.IGNORECASE)
DURATION_RE = re.compile(r"(\d+(?:,\d+)?|ein(?:e[nm]?)?|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)\s*(arbeitstage?n?|werktage?n?|tage?n?|wochen?|monate?n?|stunden?)", re.IGNORECASE)
WORDNUM = {"ein": 1, "eine": 1, "einen": 1, "einem": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10}
FIRST_PARTY_FACT_KINDS = {"travel_time", "travel_fee", "responsible_person", "review"}
LABELS = [
    ("quote_consent", r"^(zitat darf|zitat freigegeben|einverst(ä|ae)ndnis|freigabe (des|zum) zitat)"),
    ("district", r"^(ortsteil|stadtteil|viertel|wohngebiet)"),
    ("street", r"^(stra(ß|ss)e|strasse)"),
    ("month", r"^(monat|fertigstellung|fertig seit|abgeschlossen)"),
    ("local_note", r"^(besonderheit|vor ort|lokal)"),
    ("town", r"^(ort|stadt|gemeinde)\b"),
    ("service", r"^(leistung|gewerk|arbeiten|auftrag)"),
    ("scope", r"^(umfang|fl(ä|ae)che|menge)"),
    ("duration", r"^(dauer|bauzeit|zeitraum)"),
    ("material", r"^(material|produkt|system)"),
    ("challenge", r"^(herausforderung|problem|schwierigkeit)"),
    ("solution", r"^(l(ö|oe)sung|vorgehen)"),
    ("responsible", r"^(verantwortlich|bauleit\w*|team|ansprechpartner)"),
    ("quote", r"^(kundenzitat|zitat|kundenstimme)"),
    ("price_band", r"^(preis\w*|kosten)"),
    ("photos", r"^(fotos?|bilder?|dateien)"),
]
LOCAL_ENTITY_RE = re.compile(r"\b(?:Bauamt|Baurechtsamt|Landratsamt|Denkmalamt|Stadtverwaltung|Gemeinde|Ortskern|Altstadt|Gesamtanlage|Gestaltungssatzung|Sanierungsgebiet|Förderprogramm|Stadtteil|Ortsteil)\s+[A-ZÄÖÜ][\wäöüß\-]+(?:\s+[A-ZÄÖÜ][\wäöüß\-]+)?")
SUBSIDY_RE = re.compile(r"\b(förder\w*|kfw|bafa|beg\b|l-bank|zuschuss|zuschüsse|isfp|steuerbonus|§\s?35c)\b", re.IGNORECASE)
MARKER_RE = re.compile(r"\[\[(p|f|b):([^\]]+)\]\]")
CERT_RE = r"\b(meister\w*|meisterbetrieb|zertifiziert\w*|fachbetrieb|innung\w*|handwerkskammer|kammer|tüv|din\b|iso\b|sachverständig\w*|staatlich geprüft|geprüft\w*|ausgezeichnet|mitglied)\b"
PROGRAMME_RE = r"\b(kfw|bafa|beg\b|l-bank|förder\w*|landratsamt|bauamt|baurechtsamt|denkmalschutz\w*|denkmalamt|satzung|gestaltungssatzung|stadtverwaltung|gemeinde\w*|bebauungsplan|landesamt)\b"
COMPARE_RE = r"\b(besser|schneller|günstiger|billiger|länger|größer|höher|niedriger|mehr als|weniger als|über \d|unter \d|bis zu|am (besten|schnellsten|günstigsten)|schnellste\w*|günstigste\w*|größte\w*|einzige\w*|erste[nrs]?)\b"
UNIT_FACT_RE = r"(€|\beur\b|\beuro\b|%|\bprozent\b|m²|\bqm\b|\bkm\b|\bmin\b|minuten|stunden|tage|wochen|monate|jahre|\bcm\b|\bmm\b)"


# ---------------------------------------------------------------- registry IO

def projects_dir(state: Path) -> Path:
    return state / "evidence" / "projects"


def load_projects(state: Path) -> List[Dict[str, Any]]:
    out = []
    d = projects_dir(state)
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            rec = st.load_json(p, {}) or {}
            rec.setdefault("id", p.stem)
            out.append(rec)
    return out


def facts_path(state: Path) -> Path:
    return state / "evidence" / "facts.json"


def load_facts(state: Path) -> List[Dict[str, Any]]:
    return (st.load_json(facts_path(state), {"facts": []}) or {}).get("facts", [])


def save_facts(state: Path, facts: List[Dict[str, Any]]) -> None:
    st.save_json(facts_path(state), {"schema_version": 1, "facts": facts})


def same_town(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b) and textde.fold_umlauts(a).lower().strip() == textde.fold_umlauts(b).lower().strip()


# ---------------------------------------------------------------- intake

def _label_of(line: str) -> Tuple[Optional[str], str]:
    m = re.match(r"^\s*[-*]?\s*([^:]{2,90}):\s*(.*)$", line)
    if not m:
        return None, line
    label = textde.fold_umlauts(m.group(1)).lower()
    label_raw = m.group(1).lower()
    for field, pat in LABELS:
        if re.search(pat, label_raw) or re.search(textde.fold_umlauts(pat), label):
            return field, m.group(2).strip()
    return None, line


def parse_month(s: str, fallback: Optional[str] = None) -> Optional[str]:
    if not s:
        return fallback
    m = re.search(r"\b(20\d{2})-(\d{2})\b", s)
    if m:
        return "%s-%s" % (m.group(1), m.group(2))
    m = re.search(r"\b(\d{1,2})[./](20\d{2})\b", s)
    if m:
        return "%s-%02d" % (m.group(2), int(m.group(1)))
    low = s.lower()
    for name, num in MONTHS.items():
        if re.search(r"\b%s\b" % name, low):
            y = re.search(r"\b(20\d{2})\b", s)
            if y:
                return "%s-%02d" % (y.group(1), num)
            today = st.today_date()
            year = today.year if num <= today.month else today.year - 1
            return "%d-%02d" % (year, num)
    return fallback


def _num(s: str) -> Optional[float]:
    s = s.strip().lower()
    if s in WORDNUM:
        return float(WORDNUM[s])
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _norm_unit(u: str) -> str:
    u = u.lower().rstrip(".")
    return {"m2": "m²", "qm": "m²", "quadratmeter": "m²", "m3": "m³", "stk": "Stück", "stück": "Stück", "laufende meter": "lfm"}.get(u, u)


def parse_report(text: str, business: Optional[Dict[str, Any]] = None, extra_photos: Optional[List[str]] = None,
                 month_hint: Optional[str] = None) -> Dict[str, Any]:
    """Turn a monthly project report (labelled form or a few free sentences plus photo names) into fields."""
    b = business or {}
    fields: Dict[str, str] = {}
    free: List[str] = []
    for line in (text or "").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.lstrip().startswith(">"):
            continue
        f, val = _label_of(line)
        if f and val:
            fields[f] = (fields.get(f, "") + " " + val).strip()
        elif not f:
            free.append(line.strip())
    free_text = " ".join(free)
    all_text = " ".join([free_text] + list(fields.values()))
    towns = [t.get("town") for t in b.get("service_area") or [] if t.get("town")]
    services = b.get("services") or []
    rec: Dict[str, Any] = {}
    # town
    town = fields.get("town")
    if not town:
        town = next((t for t in towns if textde.contains_town(all_text, t)), None)
    else:
        town = next((t for t in towns if same_town(t, town) or textde.contains_town(town, t)), town.strip())
    rec["town"] = town
    rec["town_in_service_area"] = bool(town) and any(same_town(town, t) for t in towns)
    # district
    district = fields.get("district")
    if not district:
        for t in b.get("service_area") or []:
            if same_town(t.get("town"), town):
                district = next((d for d in t.get("districts") or [] if textde.contains_term(all_text, d)), None)
    rec["district"] = district.strip() if district else None
    # street (no house number; only with permission, which the form asks for)
    street = fields.get("street")
    if street and street.strip().lower() not in ("nein", "-", "keine", "nicht erlaubt"):
        rec["street"] = re.sub(r"\s*\d+\s*[a-zA-Z]?\b", "", street).strip(" ,")
        rec["street_public"] = True
    else:
        rec["street"], rec["street_public"] = None, False
    # service
    svc_txt = fields.get("service") or all_text
    svc = next((s for s in services if textde.contains_term(svc_txt, s.get("name", "")) or textde.contains_term(svc_txt, s.get("id", ""))), None)
    if svc is None:
        svc = next((s for s in services if textde.contains_term(all_text, s.get("name", ""))), None)
    rec["service_id"] = svc.get("id") if svc else None
    rec["service_name"] = svc.get("name") if svc else (fields.get("service") or None)
    # scope and duration
    scope_src = fields.get("scope") or all_text
    rec["scope"] = [{"value": _num(m.group(1)), "unit": _norm_unit(m.group(2)), "text": m.group(0)} for m in SCOPE_RE.finditer(scope_src)]
    dur_src = fields.get("duration") or all_text
    dm = DURATION_RE.search(dur_src)
    rec["duration"] = {"value": _num(dm.group(1)), "unit": dm.group(2), "text": dm.group(0)} if dm else None
    rec["month"] = parse_month(fields.get("month", ""), None) or parse_month(free_text, None) or month_hint
    rec["material"] = fields.get("material") or None
    rec["local_note"] = fields.get("local_note") or None
    rec["challenge"] = fields.get("challenge") or None
    rec["solution"] = fields.get("solution") or None
    rec["responsible"] = fields.get("responsible") or None
    quote = fields.get("quote")
    consent_raw = (fields.get("quote_consent") or "").strip().lower()
    consent = True if consent_raw.startswith(("ja", "yes", "einverstanden")) else (False if consent_raw.startswith(("nein", "no")) else None)
    rec["quote"] = {"text": quote.strip(" „“\""), "consent": consent} if quote else None
    rec["price_band"] = fields.get("price_band") or None
    photos = []
    for src in (fields.get("photos", ""), free_text):
        for m in PHOTO_RE.finditer(src):
            name = m.group(0).strip(" ,;")
            if name and name not in photos:
                photos.append(name)
    for p in extra_photos or []:
        if p not in photos:
            photos.append(p)
    rec["photos"] = [{"file": p, "caption": None, "exif_stripped": None} for p in photos]
    if not rec["challenge"] and not rec["solution"] and free:
        rec["notes"] = free_text[:1000]
    ents: List[str] = []
    for e in (rec["district"], rec["street"] if rec["street_public"] else None):
        if e and e not in ents:
            ents.append(e)
    districts = [d for t in b.get("service_area") or [] if same_town(t.get("town"), town) for d in t.get("districts") or []]
    for src in (rec["local_note"], rec["challenge"], rec["solution"]):
        for m in LOCAL_ENTITY_RE.finditer(src or ""):
            phrase = m.group(0).strip()
            if phrase not in ents:
                ents.append(phrase)
        for d in districts:
            if textde.contains_term(src or "", d) and d not in ents:
                ents.append(d)
    rec["local_entities"] = ents
    rec["fields"] = {k: v for k, v in fields.items() if k not in ("street",)}
    return rec


def missing_fields(rec: Dict[str, Any]) -> List[Dict[str, str]]:
    miss = []

    def need(key: str, de: str) -> None:
        miss.append({"field": key, "frage_de": de})

    if not rec.get("month"):
        need("month", "In welchem Monat wurde der Auftrag fertig?")
    if not rec.get("town"):
        need("town", "In welchem Ort war die Baustelle?")
    elif not rec.get("town_in_service_area"):
        need("town_in_service_area", "Gehört %s zu Ihrem Einsatzgebiet? Dann nehmen wir den Ort auf." % rec["town"])
    if not rec.get("service_id"):
        need("service", "Welche Leistung war es (z. B. Fassadensanierung)?")
    if not rec.get("scope"):
        need("scope", "Wie groß war der Auftrag, mit Zahl und Einheit (z. B. 240 m² Fassade)?")
    if not rec.get("duration"):
        need("duration", "Wie lange hat die Ausführung gedauert (z. B. 9 Arbeitstage)?")
    if not rec.get("photos"):
        need("photos", "Bitte schicken Sie 3 bis 10 eigene Fotos (vorher und nachher).")
    elif len(rec["photos"]) < 3:
        need("photos_more", "Haben Sie noch weitere Fotos? Ideal sind 3 bis 10.")
    if not rec.get("challenge") and not rec.get("solution"):
        need("challenge_solution", "Was war die Herausforderung, und wie haben Sie sie gelöst? Ein bis zwei Sätze genügen.")
    if rec.get("quote") and rec["quote"].get("consent") is None:
        need("quote_consent", "Darf das Kundenzitat mit Vorname und Ort veröffentlicht werden (ja oder nein)?")
    return miss


def record_id(rec: Dict[str, Any]) -> str:
    parts = [rec.get("month") or "0000-00", rec.get("service_id") or st.slugify(rec.get("service_name") or "projekt"), rec.get("town") or "ort"]
    if rec.get("district"):
        parts.append(rec["district"])
    return "-".join([parts[0]] + [st.slugify(x, 30) for x in parts[1:]])


def summary_de(rec: Dict[str, Any]) -> str:
    bits = []
    if rec.get("service_name"):
        bits.append(rec["service_name"])
    where = rec.get("town") or "Ort unbekannt"
    if rec.get("district"):
        where += "-" + rec["district"] if not rec["district"].startswith(where) else ""
    bits.append("in " + where)
    if rec.get("scope"):
        bits.append(", ".join(s["text"] for s in rec["scope"]))
    if rec.get("duration"):
        bits.append(rec["duration"]["text"])
    if rec.get("month"):
        bits.append("fertig %s" % rec["month"])
    return ", ".join(bits) + "."


def normalise(rec: Dict[str, Any], source_file: Optional[str]) -> Dict[str, Any]:
    out = {"schema_version": 1, "id": record_id(rec), "received_on": st.today(), "source_file": source_file}
    out.update(rec)
    out["summary_de"] = summary_de(rec)
    out["missing"] = missing_fields(rec)
    out["status"] = "complete" if not [m for m in out["missing"] if m["field"] in ("month", "town", "service", "scope", "photos")] else "incomplete"
    out.setdefault("confirmed_by", None)
    return out


def write_project(state: Path, rec: Dict[str, Any]) -> Path:
    d = projects_dir(state)
    d.mkdir(parents=True, exist_ok=True)
    path = d / ("%s.json" % rec["id"])
    old = st.load_json(path, None)
    if old:
        rec["received_on"] = old.get("received_on", rec["received_on"])
        if old.get("confirmed_by") and not rec.get("confirmed_by"):
            rec["confirmed_by"] = old["confirmed_by"]
        for k in ("photos",):
            names = {p["file"] for p in rec.get(k) or []}
            for p in old.get(k) or []:
                if p.get("file") not in names:
                    rec[k].append(p)
                else:
                    for q in rec[k]:
                        if q["file"] == p.get("file"):
                            q.update({kk: vv for kk, vv in p.items() if vv is not None})
    st.save_json(path, rec)
    return path


# ---------------------------------------------------------------- page attachment (Gate C, for-page)

def items_for_page(state: Path, town: Optional[str], service_id: Optional[str] = None, page_path: Optional[str] = None,
                   business: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Evidence items that can support a page about ``service_id`` in ``town`` (spec 10, Gate C)."""
    items: List[Dict[str, Any]] = []
    for p in load_projects(state):
        pages = p.get("pages") or []
        if not (same_town(p.get("town"), town) or (page_path and page_path in pages)):
            continue
        has_photos = bool(p.get("photos"))
        items.append({"kind": "project", "id": p["id"], "first_party": has_photos or bool(p.get("responsible")),
                      "service_match": (not service_id) or p.get("service_id") == service_id,
                      "label_de": p.get("summary_de") or p["id"], "group": 1 if has_photos else 2})
    for f in load_facts(state):
        pages = f.get("pages") or []
        if not (same_town(f.get("town"), town) or (page_path and page_path in pages)):
            continue
        first = f.get("kind") in FIRST_PARTY_FACT_KINDS and bool(f.get("confirmed_by"))
        sourced = bool(f.get("source_url")) and bool(f.get("verified_on"))
        if not first and not sourced and not f.get("confirmed_by"):
            continue  # unverified local facts do not count
        items.append({"kind": "fact", "id": f.get("id"), "first_party": first, "service_match": True,
                      "label_de": f.get("claim"), "group": 1 if first else 2})
    return items


def town_entities(state: Path, town: str, business: Optional[Dict[str, Any]] = None) -> List[str]:
    """Strings that bind a sentence to ``town``: districts, streets, local authority, local entities of
    projects and facts in that town, and project ids."""
    b = business or st.load_business(state) or {}
    ents: List[str] = []

    def add(x: Any) -> None:
        if isinstance(x, str) and len(x.strip()) >= 3 and x.strip() not in ents and not same_town(x, town):
            ents.append(x.strip())

    for t in b.get("service_area") or []:
        if same_town(t.get("town"), town):
            for d in t.get("districts") or []:
                add(d)
            add(t.get("local_authority"))
            for x in t.get("local_entities") or []:
                add(x)
    if same_town((b.get("address") or {}).get("city"), town) and b.get("address_public") is not False:
        add(re.sub(r"\s*\d+.*$", "", (b.get("address") or {}).get("street") or ""))
    for p in load_projects(state):
        if same_town(p.get("town"), town):
            add(p.get("district"))
            if p.get("street_public"):
                add(p.get("street"))
            for x in p.get("local_entities") or []:
                add(x)
    for f in load_facts(state):
        if same_town(f.get("town"), town):
            for x in f.get("entities") or []:
                add(x)
    return ents


def town_numbers(state: Path, town: str, business: Optional[Dict[str, Any]] = None) -> List[Tuple[float, str]]:
    """(value, unit pattern) pairs specific to ``town``: drive minutes, distance, project scope and duration."""
    b = business or st.load_business(state) or {}
    out: List[Tuple[float, str]] = []
    for t in b.get("service_area") or []:
        if same_town(t.get("town"), town):
            if t.get("drive_minutes"):
                out.append((float(t["drive_minutes"]), r"(minuten|min\b)"))
            if t.get("distance_km"):
                out.append((float(t["distance_km"]), r"km\b"))
    for p in load_projects(state):
        if same_town(p.get("town"), town):
            for s in p.get("scope") or []:
                if s.get("value") is not None:
                    out.append((float(s["value"]), re.escape(s.get("unit") or "")))
            d = p.get("duration") or {}
            if d.get("value") is not None:
                out.append((float(d["value"]), r"(arbeits|werk)?tage?n?|wochen?"))
    return out


# ---------------------------------------------------------------- provenance (spec 10b)

def _flatten(o: Any) -> List[str]:
    out: List[str] = []
    if isinstance(o, dict):
        for v in o.values():
            out += _flatten(v)
    elif isinstance(o, list):
        for v in o:
            out += _flatten(v)
    elif o is not None:
        out.append(str(o))
    return out


def resolve_business_path(b: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    cur: Any = b
    for part in re.split(r"\.(?![^\[]*\])", path):
        m = re.match(r"^([\w\-]+)(?:\[(\d+)\])?$", part)
        if not m:
            return False, None
        key, idx = m.group(1), m.group(2)
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list):
            found = next((x for x in cur if isinstance(x, dict) and (x.get("id") == key or x.get("town") == key)), None)
            if found is None:
                return False, None
            cur = found
        else:
            return False, None
        if idx is not None:
            if not isinstance(cur, list) or int(idx) >= len(cur):
                return False, None
            cur = cur[int(idx)]
    return True, cur


def _nums_in(strings: List[str]) -> List[float]:
    out: List[float] = []
    for s in strings:
        out += textde.numbers(s)
        for m in re.finditer(r"\d+(?:\.\d+)?", s):
            try:
                out.append(float(m.group(0)))
            except ValueError:
                pass
    return out


PHONE_SEQ = re.compile(r"(?:\+\d{2}[\s\d/()\-]{6,}\d|\b0\d{2,5}[\s/\-]+[\d\s\-]{4,}\d)")


def factual_reasons(sentence: str, own_town: Optional[str], other_towns: List[str]) -> List[str]:
    s = MARKER_RE.sub("", sentence)
    reasons = []
    if re.search(r"\d", s):
        reasons.append("Zahl")
    if re.search(UNIT_FACT_RE, s, re.IGNORECASE):
        reasons.append("Einheit")
    if re.search(CERT_RE, s, re.IGNORECASE):
        reasons.append("Qualifikation")
    if re.search(PROGRAMME_RE, s, re.IGNORECASE):
        reasons.append("Programm oder Behörde")
    if re.search(COMPARE_RE, s, re.IGNORECASE):
        reasons.append("Vergleich oder Superlativ")
    for t in other_towns:
        if t and not same_town(t, own_town) and textde.contains_town(s, t):
            reasons.append("anderer Ort (%s)" % t)
            break
    return reasons


def _draft_sentences(text: str) -> List[Tuple[int, str]]:
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    out = []
    for i in range(start, len(lines)):
        raw = lines[i].strip()
        if not raw or raw.startswith("<!--") or raw.startswith("```"):
            continue
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = re.sub(r"^#+\s*", "", raw)
        raw = re.sub(r"^\s*[-*]\s+|^\s*\d+\.\s+", "", raw)
        raw = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw)
        if not raw.strip():
            continue
        # split keeping markers attached to the sentence they close
        for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9„\"])|(?<=\]\])\s+(?=[A-ZÄÖÜ0-9„\"])", raw):
            if s.strip():
                out.append((i + 1, s.strip()))
    return out


def frontmatter(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    out: Dict[str, Any] = {}
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                break
            m = re.match(r"^([\w\-]+)\s*:\s*(.*)$", lines[i])
            if m:
                v = m.group(2).strip().strip("'\"")
                if v.startswith("[") and v.endswith("]"):
                    out[m.group(1)] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
                elif v.lower() in ("true", "false"):
                    out[m.group(1)] = v.lower() == "true"
                else:
                    out[m.group(1)] = v
    return out


def provenance_check(state: Path, text: str, own_town: Optional[str] = None, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or st.load_config(state)
    g = cfg["thresholds"]["gates"]
    b = st.load_business(state) or {}
    fm = frontmatter(text)
    own_town = own_town or fm.get("town")
    towns = [t.get("town") for t in b.get("service_area") or []] + [(b.get("address") or {}).get("city")]
    projects = {p["id"]: p for p in load_projects(state)}
    facts = {f.get("id"): f for f in load_facts(state)}
    today = st.today_date()
    rows = []
    for line, sent in _draft_sentences(text):
        reasons = factual_reasons(sent, own_town, [t for t in towns if t])
        markers = MARKER_RE.findall(sent)
        row: Dict[str, Any] = {"line": line, "sentence": MARKER_RE.sub("", sent).strip(), "reasons": reasons,
                               "markers": ["%s:%s" % m for m in markers], "status": "ok", "problems": []}
        if not reasons and not markers:
            row["status"] = "not_factual"
            rows.append(row)
            continue
        if reasons and not markers:
            row["status"] = "fail"
            row["problems"].append("Tatsachenbehauptung ohne Quellenmarker")
            rows.append(row)
            continue
        values: List[str] = []
        for kind, ref in markers:
            ref = ref.strip()
            if kind == "p":
                rec = projects.get(ref)
                if not rec:
                    row["problems"].append("Projekt %s nicht im Register" % ref)
                    continue
                values += _flatten(rec)
            elif kind == "f":
                rec = facts.get(ref)
                if not rec:
                    row["problems"].append("Fakt %s nicht in facts.json" % ref)
                    continue
                if rec.get("value") is None and not rec.get("claim"):
                    row["problems"].append("Fakt %s ohne Wert" % ref)
                values += _flatten(rec)
                if rec.get("source_url"):
                    subsidy = bool(rec.get("subsidy")) or bool(SUBSIDY_RE.search(" ".join(_flatten(rec.get("claim")))))
                    limit = int(g["subsidy_freshness_days"] if subsidy else g["fact_freshness_days"])
                    vd = st.parse_date(rec.get("verified_on"))
                    if not vd or (today - vd).days > limit:
                        row["problems"].append("Fakt %s zuletzt geprüft %s, älter als %d Tage" % (ref, rec.get("verified_on") or "nie", limit))
                elif not rec.get("confirmed_by"):
                    row["problems"].append("Fakt %s hat weder Quelle noch Bestätigung" % ref)
            elif kind == "b":
                ok, val = resolve_business_path(b, ref)
                if not ok:
                    row["problems"].append("business.json-Pfad %s existiert nicht" % ref)
                    continue
                if val is None or val == [] or val == {}:
                    row["problems"].append("business.json %s ist unbekannt (null)" % ref)
                    continue
                values += _flatten(val)
        plain = row["sentence"]
        phones = PHONE_SEQ.findall(plain)
        rec_phones = {textde.norm_phone(v) for v in values if re.search(r"\d{4}", v)}
        for ph in phones:
            if textde.norm_phone(ph) not in rec_phones:
                row["problems"].append("Telefonnummer %s nicht im Datensatz" % ph.strip())
            plain = plain.replace(ph, " ")
        have = set(_nums_in(values))
        for n in textde.numbers(plain):
            if n not in have:
                row["problems"].append("Zahl %s steht nicht im referenzierten Datensatz" % (int(n) if n == int(n) else n))
        if row["problems"]:
            row["status"] = "fail"
        rows.append(row)
    fails = [r for r in rows if r["status"] == "fail"]
    factual = [r for r in rows if r["status"] != "not_factual"]
    return {"ok": not fails, "factual_sentences": len(factual), "failed": len(fails), "rows": rows}


# ---------------------------------------------------------------- commands

def cmd_intake(args: Any) -> int:
    state = st.require_state(args)
    src = Path(args.file)
    if not src.is_file():
        cli.die(cli.EXIT_USAGE, "Report file not found: %s" % src)
    b = st.load_business(state) or {}
    text = src.read_text(encoding="utf-8", errors="replace")
    rec = normalise(parse_report(text, b, args.photo, args.month), _rel(state, src))
    if args.dry_run:
        cli.emit({"record": rec, "written": None}, args, _intake_human(rec, None))
        return cli.EXIT_OK
    path = write_project(state, rec)
    cli.emit({"record": rec, "written": str(path)}, args, _intake_human(rec, path))
    return cli.EXIT_OK


def _rel(state: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(state.resolve()))
    except ValueError:
        return p.name


def _intake_human(rec: Dict[str, Any], path: Optional[Path]) -> str:
    lines = ["Projekt %s: %s" % (rec["id"], rec["summary_de"]), "Status: %s, Fotos: %d" % (rec["status"], len(rec.get("photos") or []))]
    if rec["missing"]:
        lines.append("Rückfragen an den Betrieb:")
        lines += ["  - %s" % m["frage_de"] for m in rec["missing"]]
    lines.append("Gespeichert: %s" % path if path else "(Probelauf, nichts gespeichert)")
    return "\n".join(lines)


def cmd_add_project(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    if args.file:
        raw = st.load_json(args.file, {}) or {}
    else:
        lines = ["Monat: %s" % (args.month or ""), "Ort: %s" % (args.town or ""), "Ortsteil: %s" % (args.district or ""),
                 "Leistung: %s" % (args.service or ""), "Umfang: %s" % (args.scope or ""), "Dauer: %s" % (args.duration or ""),
                 "Herausforderung: %s" % (args.challenge or ""), "Lösung: %s" % (args.solution or ""),
                 "Verantwortlich: %s" % (args.responsible or ""), "Fotos: %s" % ", ".join(args.photo or [])]
        raw = parse_report("\n".join(lines), b, args.photo, args.month)
    rec = normalise(raw, None)
    if args.confirmed_by:
        rec["confirmed_by"] = args.confirmed_by
    path = write_project(state, rec)
    cli.emit({"record": rec, "written": str(path)}, args, _intake_human(rec, path))
    return cli.EXIT_OK


def cmd_add_fact(args: Any) -> int:
    state = st.require_state(args)
    facts = load_facts(state)
    fid = args.id or ("f-" + st.slugify("%s %s" % (args.claim, args.town or ""), 50))
    if args.source_url and not args.verified_on:
        cli.die(cli.EXIT_USAGE, "A fact with --source-url needs --verified-on (the date a person checked the source).")
    if not args.source_url and not args.confirmed_by:
        cli.die(cli.EXIT_USAGE, "A fact needs --source-url plus --verified-on, or --confirmed-by (owner or operator).")
    rec = {"id": fid, "claim": args.claim, "value": args.value, "unit": args.unit, "kind": args.kind, "town": args.town,
           "pages": args.page or [], "entities": args.entity or [], "source_url": args.source_url, "source_date": args.source_date,
           "verified_on": args.verified_on, "confirmed_by": args.confirmed_by,
           "subsidy": bool(args.subsidy) or bool(SUBSIDY_RE.search(args.claim or ""))}
    replaced = False
    for i, f in enumerate(facts):
        if f.get("id") == fid:
            keep = {k: f[k] for k in ("source_hash", "source_checked_on") if k in f}
            rec.update(keep)
            facts[i] = rec
            replaced = True
    if not replaced:
        facts.append(rec)
    save_facts(state, facts)
    cli.emit({"fact": rec, "updated": replaced}, args, "%s %s: %s" % ("Updated" if replaced else "Added", fid, args.claim))
    return cli.EXIT_OK


def cmd_list(args: Any) -> int:
    state = st.require_state(args)
    projects = load_projects(state)
    facts = load_facts(state)
    lines = ["Projekte (%d):" % len(projects)] + ["  %s [%s] %s" % (p["id"], p.get("status"), p.get("summary_de", "")) for p in projects]
    lines += ["Fakten (%d):" % len(facts)] + ["  %s: %s%s" % (f.get("id"), f.get("claim"), " (Quelle)" if f.get("source_url") else "") for f in facts]
    cli.emit({"projects": projects, "facts": facts}, args, "\n".join(lines))
    return cli.EXIT_OK


def page_meta_from_file(path: Path, business: Dict[str, Any]) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta: Dict[str, Any] = {"file": str(path)}
    if path.suffix.lower() in (".md", ".mdx"):
        fm = frontmatter(raw)
        meta.update({k: fm.get(k) for k in ("town", "service", "path", "cluster", "template")})
        body = raw
    else:
        page = htmlx.parse(raw, "")
        body = " ".join([page.title or ""] + page.h1)
    towns = [t.get("town") for t in business.get("service_area") or []]
    if not meta.get("town"):
        meta["town"] = next((t for t in towns if textde.contains_town(body, t)), None) or next((t for t in towns if t and st.slugify(t) in path.stem), None)
    if not meta.get("service"):
        s = next((s for s in business.get("services") or [] if textde.contains_term(body, s.get("name", "")) or s.get("id", "~") in path.stem), None)
        meta["service"] = s.get("id") if s else None
    if not meta.get("path"):
        meta["path"] = "/" + re.sub(r"(^index$)", "", path.stem)
    return meta


def cmd_for_page(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    if Path(args.page).is_file():
        meta = page_meta_from_file(Path(args.page), b)
    else:
        meta = {"path": args.page, "town": None, "service": None}
    town = args.town or meta.get("town")
    service = args.service or meta.get("service")
    items = items_for_page(state, town, service, meta.get("path"), b)
    first = [i for i in items if i["first_party"]]
    human = "Seite %s (Ort %s, Leistung %s): %d Belege, davon %d aus erster Hand\n%s" % (
        meta.get("path"), town, service, len(items), len(first), "\n".join("  [%s%s] %s" % (i["kind"], ", eigene" if i["first_party"] else "", i["label_de"]) for i in items))
    cli.emit({"page": meta, "town": town, "service": service, "items": items}, args, human)
    return cli.EXIT_OK


def cmd_coverage(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    g = cfg["thresholds"]["gates"]
    b = st.load_business(state) or {}
    rows = []
    for svc in b.get("services") or []:
        for t in b.get("service_area") or []:
            items = items_for_page(state, t.get("town"), svc.get("id"), None, b)
            first = [i for i in items if i["first_party"]]
            projects = [i for i in items if i["kind"] == "project" and i["service_match"]]
            ok = len(items) >= int(g["evidence_min_items"]) and len(first) >= int(g["evidence_min_first_party"])
            if ok:
                reason = "genug Belege für eine eigene Seite"
            elif not projects:
                reason = "wartet auf erstes Projekt mit Fotos in %s" % t.get("town")
            else:
                reason = "wartet auf %d weitere Belege in %s" % (int(g["evidence_min_items"]) - len(items), t.get("town"))
            rows.append({"service": svc.get("id"), "town": t.get("town"), "items": len(items), "first_party": len(first),
                         "projects_for_service": len(projects), "gate_c": ok, "reason_de": reason})
    supports = []
    for p in load_projects(state):
        pages = ["/"]
        svc = next((s for s in b.get("services") or [] if s.get("id") == p.get("service_id")), None)
        if svc and svc.get("page"):
            pages.append(svc["page"])
        if p.get("service_id") and p.get("town"):
            pages.append("/%s-%s" % (p["service_id"], st.slugify(p["town"])))
        supports.append({"project": p["id"], "pages": pages, "also": ["GBP-Beitrag", "Referenz", "Anlass für eine Bewertungsbitte"]})
    human = "\n".join("%-20s %-14s Belege %d (eigene %d): %s" % (r["service"], r["town"], r["items"], r["first_party"], r["reason_de"]) for r in rows)
    cli.emit({"coverage": rows, "supports": supports}, args, human or "Keine Leistungen oder Orte in business.json.")
    return cli.EXIT_OK


def cmd_provenance(args: Any) -> int:
    state = st.require_state(args)
    p = Path(args.draft)
    if not p.is_file():
        cli.die(cli.EXIT_USAGE, "Draft not found: %s" % p)
    res = provenance_check(state, p.read_text(encoding="utf-8"), args.town)
    res["file"] = str(p)
    lines = ["Provenienz %s: %d Tatsachensätze, %d ohne gültigen Beleg" % (p, res["factual_sentences"], res["failed"])]
    for r in res["rows"]:
        if r["status"] == "fail":
            lines.append("  Zeile %d: %s\n    %s" % (r["line"], r["sentence"][:120], "; ".join(r["problems"])))
    cli.emit(res, args, "\n".join(lines))
    return cli.EXIT_OK if res["ok"] else cli.EXIT_FAIL


def cmd_recheck(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    g = cfg["thresholds"]["gates"]
    if args.fixture:
        http.use_fixture(args.fixture)
    facts = load_facts(state)
    today = st.today_date()
    rows = []
    errors = 0
    checked = 0
    for f in facts:
        subsidy = bool(f.get("subsidy"))
        limit = int(g["subsidy_freshness_days"] if subsidy else g["fact_freshness_days"])
        vd = st.parse_date(f.get("verified_on"))
        stale = bool(f.get("source_url")) and (not vd or (today - vd).days > limit)
        row = {"id": f.get("id"), "source_url": f.get("source_url"), "stale": stale, "limit_days": limit, "status": "no_source"}
        if f.get("source_url"):
            checked += 1
            try:
                r = http.fetch(f["source_url"], allow_private=args.allow_private)
                body = htmlx.parse(r.text, r.url).full_text if "html" in r.content_type else r.text
                h = hashlib.sha256(re.sub(r"\s+", " ", body).strip().encode("utf-8")).hexdigest()
                row["http_status"] = r.status
                if r.status >= 400:
                    row["status"] = "unreachable"
                elif not f.get("source_hash"):
                    row["status"] = "baseline"
                elif f["source_hash"] != h:
                    row["status"] = "changed"
                else:
                    row["status"] = "unchanged"
                if args.update and r.status < 400:
                    if row["status"] == "changed":
                        f["source_changed_on"] = st.today()
                    f["source_hash"], f["source_checked_on"] = h, st.today()
            except http.FetchError as exc:
                errors += 1
                row["status"], row["error"] = "error", str(exc)
        rows.append(row)
    if args.update:
        save_facts(state, facts)
    flagged = [r for r in rows if r["stale"] or r["status"] in ("changed", "unreachable")]
    human = "\n".join("%s: %s%s" % (r["id"], r["status"], ", veraltet (älter als %d Tage)" % r["limit_days"] if r["stale"] else "") for r in rows) or "Keine Fakten."
    if flagged:
        human += "\nBitte prüfen: %s. verified_on wird nur von einem Menschen gesetzt (evidence.py add-fact)." % ", ".join(r["id"] for r in flagged)
    cli.emit({"facts": rows, "flagged": [r["id"] for r in flagged]}, args, human)
    if checked and errors == checked:
        return cli.EXIT_REMOTE
    return cli.EXIT_FAIL if flagged else cli.EXIT_OK


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/evidence.py intake .twwa-growth/evidence/inbox/2026-10-bericht.txt\n"
                                 "  python3 scripts/evidence.py provenance .twwa-growth/drafts/2026-11-a01/seite.md --json")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "intake", "normalise a monthly project report (text plus photo names) into evidence/projects/*.json and list missing fields")
    sp.add_argument("file")
    sp.add_argument("--photo", action="append", default=[], help="photo file name (repeatable)")
    sp.add_argument("--month", help="yyyy-mm when the report does not say")
    sp.add_argument("--dry-run", action="store_true")
    sp = cli.add_sub(subs, "add-project", "add or update a project record from flags or a JSON file")
    sp.add_argument("--file")
    for f in ("month", "town", "district", "service", "scope", "duration", "challenge", "solution", "responsible", "confirmed_by"):
        sp.add_argument("--" + f.replace("_", "-"), dest=f)
    sp.add_argument("--photo", action="append", default=[])
    sp = cli.add_sub(subs, "add-fact", "add or update a fact in evidence/facts.json (source plus verified_on, or a confirmation)")
    sp.add_argument("--id")
    sp.add_argument("--claim", required=True)
    sp.add_argument("--value")
    sp.add_argument("--unit")
    sp.add_argument("--kind", default="fact", help="travel_time, travel_fee, responsible_person, review, local_regulation, subsidy, building_stock, partner, credential, price, fact")
    sp.add_argument("--town")
    sp.add_argument("--page", action="append", default=[])
    sp.add_argument("--entity", action="append", default=[], help="town-bound name in the claim (district, authority, programme)")
    sp.add_argument("--source-url", dest="source_url")
    sp.add_argument("--source-date", dest="source_date")
    sp.add_argument("--verified-on", dest="verified_on")
    sp.add_argument("--confirmed-by", dest="confirmed_by")
    sp.add_argument("--subsidy", action="store_true")
    cli.add_sub(subs, "list", "list projects and facts")
    sp = cli.add_sub(subs, "for-page", "evidence items that can support a page (Gate C view)")
    sp.add_argument("page", help="page file (.md draft or built .html) or a URL path")
    sp.add_argument("--town")
    sp.add_argument("--service")
    cli.add_sub(subs, "coverage", "evidence per service and town, and which pages each project can support")
    sp = cli.add_sub(subs, "provenance", "check that every factual sentence of a draft carries a resolving marker (exit 1 if not)")
    sp.add_argument("draft")
    sp.add_argument("--town", help="the page's own town (default: frontmatter town)")
    sp = cli.add_sub(subs, "recheck", "re-fetch sourced facts, hash, flag changes and stale verification (exit 1 when flagged)")
    sp.add_argument("--update", action="store_true", help="store the new hash and check date (never verified_on)")
    sp.add_argument("--fixture")
    sp.add_argument("--allow-private", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {"intake": cmd_intake, "add-project": cmd_add_project, "add-fact": cmd_add_fact, "list": cmd_list, "for-page": cmd_for_page,
            "coverage": cmd_coverage, "provenance": cmd_provenance, "recheck": cmd_recheck}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
