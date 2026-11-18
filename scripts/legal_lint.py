#!/usr/bin/env python3
"""German legal-surface lint (Hinweis, keine Rechtsberatung).

text:      review incentives and gating, star steering, reminders, electronic review requests without
           consent, fake reviews, unverifiable superlatives and guarantees, ranking promises, banned off-site
           tactics, the label "Kundenbewertungen", ranking claims in GBP posts.
site:      reviews shown without a §5b UWG notice nearby, Impressum and Datenschutz reachable, map iframes
           without click-to-load, remote Google Fonts, superlatives on pages, consent text at the form.
impressum: required Impressum fields by legal form and profession (§ 5 DDG and profession rules).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, http, state as st, textde  # noqa: E402

DISCLAIMER = "Hinweis, keine Rechtsberatung."

NOTICE_RE = re.compile(
    r"(prüfen nicht|nicht geprüft|nicht überprüft|keine überprüfung|überprüfen nicht|nicht verifiziert|verifiziert|echtheit|"
    r"stammen (von|aus|bei) (google|provenexpert|trustpilot|jameda|myhammer|check24|werkenntdenbesten)|"
    r"wie wir bewertungen prüfen|bewertungen werden (nicht )?geprüft|ob die verfasser kunden sind)", re.IGNORECASE)
REVIEW_SECTION_RE = re.compile(r"\b(bewertungen|kundenstimmen|rezensionen|kundenbewertungen|erfahrungen unserer kunden|das sagen unsere kunden|referenzstimmen)\b", re.IGNORECASE)
STARS_RE = re.compile(r"(★{3,}|\b[1-5][,.][0-9]\s*(von 5\s*)?sterne?n?\b|\b[1-5] von 5 sternen?\b)", re.IGNORECASE)
QUOTED_RE = re.compile(r"„[^“”]{0,200}[“”]|\"[^\"]{0,200}\"|‚[^‘’]{0,200}[‘’]|»[^«]{0,200}«")

# (rule id, level, pattern, German message). Level "block" fails the lint; "warn" is reported.
TEXT_RULES: List[Tuple[str, str, str, str]] = [
    ("review.incentive", "block",
     r"(?=.*\b(gutschein\w*|rabatt\w*|gewinnspiel\w*|verlos\w*|geschenk\w*|prämie\w*|belohn\w*|preisnachlass|bonus|skonto|dankeschön)\b)(?=.*\b(bewert\w*|rezension\w*|sterne?n?|review\w*)\b)",
     "Anreiz für Bewertungen (Gutschein, Rabatt, Gewinnspiel, Geschenk). Bewertungen dürfen nicht belohnt werden, auch nicht die Bitte darum."),
    ("review.gating", "block",
     r"(nur zufriedene|wenn sie zufrieden (waren|sind)[^.]*bewert|(unzufrieden|nicht zufrieden)[^.]*(zuerst|direkt|vorher)[^.]*(uns|bei uns)|bevor sie (eine )?(negative )?bewertung)",
     "Vorauswahl bei Bewertungen: nur zufriedene Kunden zu fragen oder Unzufriedene abzufangen ist irreführend und verstößt gegen die Google-Richtlinien."),
    ("review.star_steering", "block", r"(\b(5|fünf)[\s-]*sterne|★★★★★)",
     "Sterne-Lenkung („5 Sterne“): bitten Sie neutral um eine ehrliche Bewertung."),
    ("review.fake", "block",
     r"(bewertungen kaufen|gekaufte bewertung|bewertungen (schreiben|verfassen) lassen|fake-?bewertung|mitarbeiter[^.]{0,40}(bewerten|bewertung schreiben)|eigene bewertung schreiben)",
     "Gefälschte, gekaufte oder Mitarbeiter-Bewertungen sind immer unzulässig."),
    ("review.reminder", "block", r"(?=.*\berinner\w*)(?=.*\bbewert\w*)",
     "Erinnerungen an Bewertungen sind nicht vorgesehen: eine Bitte pro Auftrag, keine Nachfass-Nachricht."),
    ("claim.superlative", "block",
     r"(\bbester\b|(?<!am )\bbesten?\b(?!\s+(dank|grüß\w*|wünsch\w*))|\bbestes\b|\bnr\.?\s?1\b|\bnummer\s?(1|eins)\b|\bführende[nrms]?\b|\bmarktführer\w*\b|\bunschlagbar\w*\b|\bkonkurrenzlos\w*\b|\beinzigartig\w*\b|\bunübertroffen\w*\b)",
     "Nicht belegbarer Superlativ („bester“, „Nr. 1“, „führend“). Ersetzen Sie ihn durch eine prüfbare Tatsache."),
    ("claim.guarantee", "block",
     r"(\bgarantiert\b|\bgarantie\b|\bgarantieren\b|geld-?zurück|zufriedenheitsgarantie|100\s?%\s?(zufriedenheit|zufrieden))",
     "Garantie-Aussage. Ohne ausdrücklich geregelte Garantie wird sie nicht verwendet (Gewährleistung ist etwas anderes)."),
    ("claim.ranking_promise", "block",
     r"(platz\s?(1|eins) (bei|in) google|erste seite (bei|von) google|top-?ranking|ranking[- ]garantie|garantiert (auf|in) (platz|seite))",
     "Ranking-Versprechen. Platzierungen bei Google kann niemand zusagen."),
    ("offsite.banned", "block",
     r"(linktausch|backlinks? kaufen|gekaufte links?|linkkauf|\bpbn\b|linkfarm|linknetzwerk|artikelverzeichnis|automatisch(e|en)? links?|keyword-?anchor)",
     "Verbotene Off-site-Taktik (Linktausch, Linkkauf, Linknetzwerk, automatische Links)."),
    ("review.label_customer", "warn", r"\bkundenbewertungen\b",
     "„Kundenbewertungen“ setzt voraus, dass geprüft wurde, ob die Verfasser Kunden sind. Sonst „Bewertungen“ verwenden."),
]
ELECTRONIC_REQUEST = re.compile(r"(?=.*\b(e-?mail|whatsapp|sms|newsletter|nachricht)\b)(?=.*\b(bitte\w*|bitten|bewerten sie)\b)(?=.*\bbewert\w*)", re.IGNORECASE)
POST_RANKING = re.compile(r"\b(ranking\w*|seo|suchmaschinenoptimierung|sichtbarkeit (bei|in) google|keyword\w*|google-platzierung)\b", re.IGNORECASE)
MARKER_RE = re.compile(r"\[\[[pfb]:[^\]]+\]\]")


def _strip_frontmatter(lines: List[str]) -> int:
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def lint_text(text: str, kind: Optional[str] = None, cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Issues [{rule, level, line, snippet, message_de}] for German text. kind: page, gbp_post, review_request, report, proposal, outreach."""
    cfg = cfg or st.DEFAULT_CONFIG
    lines = text.splitlines()
    start = _strip_frontmatter(lines)
    issues: List[Dict[str, Any]] = []
    for n in range(start, len(lines)):
        raw = MARKER_RE.sub("", lines[n])
        if not raw.strip():
            continue
        unquoted = QUOTED_RE.sub(" ", raw)
        if NOTICE_RE.search(raw) and re.search(r"bewertung", raw, re.IGNORECASE):
            # a §5b notice line explains verification; it is not a claim
            continue
        for sent in textde.sentences(unquoted) or [unquoted]:
            for rid, level, pat, msg in TEXT_RULES:
                if rid == "claim.guarantee" and cfg.get("guarantee", {}).get("mode") == "exit_clause" and kind == "proposal":
                    continue
                if re.search(pat, sent, re.IGNORECASE):
                    issues.append({"rule": rid, "level": level, "line": n + 1, "snippet": sent.strip()[:160], "message_de": msg})
            if ELECTRONIC_REQUEST.search(sent) and not cfg.get("legal", {}).get("review_request_electronic"):
                issues.append({"rule": "review.electronic_request", "level": "block", "line": n + 1, "snippet": sent.strip()[:160],
                               "message_de": "Elektronische Bitte um eine Bewertung (E-Mail, WhatsApp, SMS) ist Werbung und braucht eine dokumentierte Einwilligung; "
                                             "legal.review_request_electronic ist aus. Persönlich oder mit gedruckter Karte fragen."})
            if kind == "gbp_post" and POST_RANKING.search(sent):
                issues.append({"rule": "gbp_post.ranking_hypothesis", "level": "block", "line": n + 1, "snippet": sent.strip()[:160],
                               "message_de": "Beiträge im Unternehmensprofil dienen der Conversion, nicht dem Ranking. Ranking-Begründungen werden abgelehnt."})
    seen = set()
    out = []
    for i in issues:
        k = (i["rule"], i["line"])
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


# ---------------------------------------------------------------- page-level legal findings (shared with site_audit)

def _near(text: str, idx: int, window: int = 1500) -> str:
    return text[max(0, idx - window): idx + window]


def page_findings(page: htmlx.Page, url: str, file: Optional[str] = None, is_home: bool = False, cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cfg = cfg or st.DEFAULT_CONFIG
    out: List[Dict[str, Any]] = []
    full = page.full_text
    ev = {"url": url, "file": file}
    # reviews shown without §5b notice nearby
    types = page.schema_types()
    review_markup = any(t in ("Review", "AggregateRating") for t in types)
    m = REVIEW_SECTION_RE.search(" ".join(h["text"] for h in page.headings)) or None
    star = STARS_RE.search(full)
    shows = bool(m) or bool(star) or review_markup or any(b["tag"] == "blockquote" for b in page.text_blocks if b["main"]) and bool(REVIEW_SECTION_RE.search(full))
    if shows:
        anchor = REVIEW_SECTION_RE.search(full) or star
        idx = anchor.start() if anchor else 0
        if not NOTICE_RE.search(_near(full, idx)):
            out.append(cli.finding(
                "legal.reviews.no_notice", "legal", "P2", "Bewertungen ohne Hinweis zur Echtheitsprüfung",
                "Die Seite zeigt Bewertungen, aber in ihrer Nähe steht nicht, ob und wie geprüft wird, dass sie von echten Kunden stammen (§ 5b Abs. 3 UWG). "
                "Vorschlag: „Diese Bewertungen stammen von Google. Wir haben keinen Einfluss auf Auswahl und Inhalt und prüfen nicht, ob die Verfasser Kunden sind.“ " + DISCLAIMER,
                evidence=dict(ev, snippet=(anchor.group(0) if anchor else "Review-Markup")), fix_hint="Add the §5b notice directly below the reviews.",
                action_type="cro_change", priority_group=4))
        if re.search(r"\bkundenbewertungen\b", full, re.IGNORECASE) and not re.search(r"verifiziert|geprüft, ob", full, re.IGNORECASE):
            out.append(cli.finding(
                "legal.reviews.label_customer", "legal", "P3", "Bezeichnung „Kundenbewertungen“ ohne Prüfung",
                "„Kundenbewertungen“ behauptet, dass die Verfasser Kunden sind. Ohne Prüfung besser „Bewertungen“. " + DISCLAIMER,
                evidence=dict(ev, snippet="Kundenbewertungen"), action_type="cro_change", priority_group=4))
    # map iframe without click-to-load
    for fr in page.iframes:
        if re.search(r"google\.[a-z.]+/maps|maps\.google\.|openstreetmap\.org/export/embed", fr.get("src") or "", re.IGNORECASE):
            out.append(cli.finding(
                "legal.maps.no_click_to_load", "legal", "P2", "Karte wird ohne Zustimmung geladen",
                "Ein eingebettetes Karten-iframe überträgt beim Seitenaufruf die IP-Adresse an den Kartendienst. In Deutschland üblich: Karte erst nach Klick laden (Zwei-Klick-Lösung). " + DISCLAIMER,
                evidence=dict(ev, snippet=fr.get("src")), fix_hint="Replace the iframe with a click-to-load placeholder.", action_type="tech_fix"))
            break
    # remote Google Fonts
    gf = [u for u in page.stylesheets + page.preloads if re.search(r"fonts\.(googleapis|gstatic)\.com", u)]
    if gf:
        out.append(cli.finding(
            "legal.fonts.google_remote", "legal", "P2", "Google Fonts werden von Google-Servern geladen",
            "Schriften von fonts.googleapis.com übertragen die IP-Adresse an Google. Schriften lokal einbinden (auch schneller). " + DISCLAIMER,
            evidence=dict(ev, snippet=gf[0]), fix_hint="Self-host the font files under public/fonts/.", action_type="tech_fix"))
    # superlatives and guarantees in the main text
    hits = [i for i in lint_text(page.text, kind="page", cfg=cfg) if i["rule"] in ("claim.superlative", "claim.guarantee", "claim.ranking_promise", "review.incentive", "review.star_steering")]
    if hits:
        out.append(cli.finding(
            "legal.claims.unverifiable", "legal", "P3", "Nicht belegbare Werbeaussagen auf der Seite",
            "%d Stelle(n) mit Superlativ, Garantie oder Bewertungsanreiz, z. B. „%s“. Solche Aussagen sind wettbewerbsrechtlich riskant, wenn sie nicht belegt werden. %s" % (len(hits), hits[0]["snippet"][:80], DISCLAIMER),
            evidence=dict(ev, snippet=hits[0]["snippet"]), action_type="onpage_rewrite"))
    # form consent / privacy link
    for f in page.forms:
        if any((fl.get("type") in ("text", "email", "tel", "textarea")) for fl in f["fields"]):
            near_links = [l for l in page.links if "datenschutz" in (l.get("href") or "").lower() and abs(l["pos"] - f["pos"]) < 2500]
            if not near_links and not re.search(r"datenschutz", f.get("text") or "", re.IGNORECASE):
                out.append(cli.finding(
                    "legal.form.privacy_notice", "legal", "P2", "Kontaktformular ohne Datenschutzhinweis",
                    "Am Formular fehlt ein Hinweis mit Link zur Datenschutzerklärung. " + DISCLAIMER,
                    evidence=dict(ev, snippet=f.get("raw_action") or "form"), action_type="cro_change"))
            break
    return out


def legal_links_findings(pages: Dict[str, htmlx.Page], home_url: str) -> List[Dict[str, Any]]:
    """Impressum and Datenschutz must be reachable (linked from the home page)."""
    out = []
    home = pages.get(home_url)
    if home is None:
        return out
    hrefs = " ".join((l.get("href") or "") + " " + (l.get("text") or "") for l in home.links).lower()
    for key, label, fid in (("impressum", "Impressum", "legal.impressum.unreachable"), ("datenschutz", "Datenschutzerklärung", "legal.datenschutz.unreachable")):
        if key not in hrefs and not (key == "datenschutz" and "privacy" in hrefs):
            out.append(cli.finding(
                fid, "legal", "P1", "%s nicht erreichbar" % label,
                "Die Startseite verlinkt kein %s. Es muss von jeder Seite mit einem Klick erreichbar sein. %s" % (label, DISCLAIMER),
                evidence={"url": home_url, "snippet": "kein Link mit '%s'" % key}, fix_hint="Link it in the footer of every page.",
                action_type="tech_fix", priority_group=3))
    return out


# ---------------------------------------------------------------- Impressum

LEGAL_FORM_RE = re.compile(r"\b(GmbH\s*&\s*Co\.?\s*KG|gGmbH|GmbH|UG\s*\(haftungsbeschränkt\)|UG|AG|KG|OHG|e\.\s?K\.|e\.\s?Kfm\.|e\.\s?V\.|GbR|PartG(?:\s?mbB)?)(?![\w])")
REGISTER_FORMS = {"GmbH", "gGmbH", "UG", "AG", "KG", "OHG", "e.K.", "e.V.", "PartG", "GmbH & Co. KG"}
DIRECTOR_FORMS = {"GmbH", "gGmbH", "UG", "AG", "GmbH & Co. KG"}


def _norm_form(f: str) -> str:
    f = re.sub(r"\s+", " ", f).strip()
    if f.startswith("GmbH &"):
        return "GmbH & Co. KG"
    if f.startswith("UG"):
        return "UG"
    if f.startswith("PartG"):
        return "PartG"
    return f.replace(" ", "").replace("Kfm.", "K.")


def impressum_checks(text: str, vertical: Optional[str] = None) -> List[Dict[str, Any]]:
    """Checks [{id, level: fail|warn|info, ok, message_de}]."""
    t = text or ""
    checks: List[Dict[str, Any]] = []

    def add(cid: str, ok: bool, level: str, msg: str) -> None:
        checks.append({"id": cid, "ok": ok, "level": level, "message_de": msg})

    forms = [_norm_form(m.group(1)) for m in LEGAL_FORM_RE.finditer(t)]
    form = forms[0] if forms else None
    add("name_legal_form", bool(form) or bool(re.search(r"\b(Inhaber(in)?|Einzelunternehm\w+)\b", t)), "warn",
        "Rechtsform oder Inhaber mit vollständigem Namen angeben.")
    street = re.search(r"[A-ZÄÖÜ][\wäöüß\-.]*(straße|strasse|str\.|weg|gasse|platz|allee|ring|damm|ufer|steig|pfad|markt|hof)\s*\d+\s*[a-z]?\b", t, re.IGNORECASE)
    zipcity = re.search(r"\b\d{5}\s+[A-ZÄÖÜ][\wäöüß\-]+", t)
    add("address", bool(street and zipcity), "fail", "Ladungsfähige Anschrift (Straße, Hausnummer, PLZ, Ort) fehlt.")
    add("no_po_box", not re.search(r"\bpostfach\b", t, re.IGNORECASE), "fail", "Ein Postfach ist keine ladungsfähige Anschrift.")
    email = re.search(r"[\w.+-]+(@|\s?\(at\)\s?|\s?\[at\]\s?)[\w-]+(\.|\s?\(dot\)\s?)[\w.]+", t)
    add("email", bool(email), "fail", "E-Mail-Adresse für schnelle elektronische Kontaktaufnahme fehlt.")
    phone = re.search(r"(telefon|tel\.?|fon|mobil)\s*:?\s*[+0(][\d\s/()\-]{6,}", t, re.IGNORECASE)
    add("phone", bool(phone), "warn", "Telefonnummer fehlt; ohne sie braucht es einen zweiten schnellen Kontaktweg.")
    if form in REGISTER_FORMS:
        add("register", bool(re.search(r"\b(HRB|HRA|VR|PR|GnR)\s*\d+|registergericht|amtsgericht", t, re.IGNORECASE)), "fail",
            "Registereintrag (Registergericht und Nummer) fehlt für die Rechtsform %s." % form)
    if form in DIRECTOR_FORMS:
        add("representative", bool(re.search(r"(geschäftsführ\w*|vertreten durch|vertretungsberechtigt|vorstand)", t, re.IGNORECASE)), "fail",
            "Vertretungsberechtigte Person (z. B. Geschäftsführer) fehlt.")
    vat = re.search(r"\bDE\s?\d{3}\s?\d{3}\s?\d{3}\b", t)
    if re.search(r"(ust-?id|umsatzsteuer-?identifikationsnummer|ust\.?-?idnr)", t, re.IGNORECASE):
        add("vat_format", bool(vat), "warn", "USt-IdNr. ist genannt, aber nicht im Format DE + 9 Ziffern.")
    else:
        add("vat", True, "info", "Keine USt-IdNr. genannt; falls vorhanden, angeben.")
    add("legal_basis", not re.search(r"§\s?5\s?TMG|telemediengesetz", t, re.IGNORECASE), "warn",
        "Rechtsgrundlage veraltet: seit 14.05.2024 gilt § 5 DDG statt § 5 TMG.")
    add("tdddg", not re.search(r"\bTTDSG\b", t), "warn", "TTDSG heißt seit Mai 2024 TDDDG.")
    add("odr_platform", not re.search(r"ec\.europa\.eu/consumers/odr|OS-Plattform|Online-Streitbeilegungsplattform", t, re.IGNORECASE), "warn",
        "Die EU-Plattform zur Online-Streitbeilegung wurde am 20.07.2025 eingestellt; den Link prüfen und entfernen.")
    v = (vertical or "").lower()
    if v == "handwerk":
        add("hwk", bool(re.search(r"handwerkskammer", t, re.IGNORECASE)), "fail", "Zuständige Handwerkskammer fehlt.")
        add("handwerksrolle", bool(re.search(r"handwerksrolle|verzeichnis (der )?zulassungsfreien", t, re.IGNORECASE)), "warn", "Eintrag in die Handwerksrolle fehlt.")
        add("berufsbezeichnung", bool(re.search(r"berufsbezeichnung|meister\w*,?\s*(verliehen|erworben)", t, re.IGNORECASE)), "warn",
            "Berufsbezeichnung und Staat der Verleihung fehlen (bei reglementierten Berufen Pflicht).")
    elif v == "steuerberater":
        add("kammer", bool(re.search(r"steuerberaterkammer", t, re.IGNORECASE)), "fail", "Zuständige Steuerberaterkammer fehlt.")
        add("berufsbezeichnung", bool(re.search(r"steuerberater\w*[^.]{0,80}verliehen|berufsbezeichnung", t, re.IGNORECASE)), "fail",
            "Berufsbezeichnung „Steuerberater“ und Staat der Verleihung fehlen.")
        add("berufsrecht", bool(re.search(r"\b(StBerG|BOStB|DVStB|StBVV)\b|steuerberatungsgesetz|berufsordnung", t)), "fail",
            "Berufsrechtliche Regelungen (StBerG, BOStB, DVStB, StBVV) und wo sie zugänglich sind fehlen.")
        add("haftpflicht", bool(re.search(r"berufshaftpflicht", t, re.IGNORECASE)), "warn", "Angaben zur Berufshaftpflichtversicherung fehlen.")
    elif v == "ingenieure":
        add("kammer", bool(re.search(r"(ingenieur|architekten)kammer", t, re.IGNORECASE)), "fail", "Zuständige Kammer fehlt.")
        add("berufsbezeichnung", bool(re.search(r"berufsbezeichnung", t, re.IGNORECASE)), "fail", "Berufsbezeichnung und Staat der Verleihung fehlen.")
        add("berufsrecht", bool(re.search(r"berufsordnung|ingenieurgesetz|baukammergesetz|architektengesetz", t, re.IGNORECASE)), "warn", "Berufsrechtliche Regelungen fehlen.")
        add("haftpflicht", bool(re.search(r"berufshaftpflicht", t, re.IGNORECASE)), "warn", "Angaben zur Berufshaftpflichtversicherung fehlen (in einigen Ländern Pflicht).")
    elif v == "finanzberatung":
        add("register", bool(re.search(r"vermittlerregister|registrierungsnummer|D-[A-Z0-9]{4}-[A-Z0-9]{5}-\d{2}", t, re.IGNORECASE)), "fail",
            "Eintrag im Vermittlerregister mit Registrierungsnummer fehlt.")
        add("erlaubnis", bool(re.search(r"§\s?34\s?[dfhi]\b", t)), "fail", "Erlaubnistatbestand (§ 34d, § 34f, § 34h oder § 34i GewO) fehlt.")
        add("ihk", bool(re.search(r"\bIHK\b|industrie- und handelskammer", t, re.IGNORECASE)), "warn", "Zuständige IHK fehlt.")
        add("schlichtung", bool(re.search(r"schlichtungsstelle|ombudsmann", t, re.IGNORECASE)), "warn", "Schlichtungsstellen fehlen.")
    elif v == "hausverwaltung":
        add("erlaubnis", bool(re.search(r"§\s?34\s?c\b", t)), "fail", "Erlaubnis nach § 34c GewO fehlt.")
        add("aufsicht", bool(re.search(r"aufsichtsbehörde", t, re.IGNORECASE)), "warn", "Zuständige Aufsichtsbehörde fehlt.")
    elif v == "fahrschule":
        add("aufsicht", bool(re.search(r"aufsichtsbehörde|erlaubnisbehörde|fahrschulerlaubnis", t, re.IGNORECASE)), "warn", "Erlaubnis- oder Aufsichtsbehörde fehlt.")
    return checks


def _load_text_or_page(target: str, allow_private: bool = False) -> Tuple[str, Optional[htmlx.Page], str]:
    if re.match(r"^https?://", target):
        try:
            r = http.fetch(target, allow_private=allow_private)
        except http.FetchError as exc:
            cli.die(cli.EXIT_REMOTE, "Fetch failed: %s" % exc)
        page = htmlx.parse(r.text, r.url)
        return page.full_text, page, r.url
    p = Path(target)
    if not p.is_file():
        cli.die(cli.EXIT_USAGE, "File not found: %s" % target)
    raw = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() in (".html", ".htm"):
        page = htmlx.parse(raw, "")
        return page.full_text, page, str(p)
    return raw, None, str(p)


def cmd_text(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    cfg = st.load_config(state)
    all_issues = []
    for f in args.files:
        text, page, src = _load_text_or_page(f)
        if page is not None:
            text = page.text
        for i in lint_text(text, args.kind, cfg):
            i["file"] = src
            all_issues.append(i)
    blocks = [i for i in all_issues if i["level"] == "block"]
    human = "\n".join("%s:%d [%s] %s\n    %s" % (i["file"], i["line"], i["level"], i["message_de"], i["snippet"]) for i in all_issues) or "Keine Beanstandungen."
    human += "\n" + DISCLAIMER
    cli.emit({"ok": not blocks, "issues": all_issues, "disclaimer": DISCLAIMER}, args, human)
    return cli.EXIT_FAIL if blocks else cli.EXIT_OK


def _site_pages(target: str, allow_private: bool) -> Dict[str, Tuple[htmlx.Page, Optional[str]]]:
    pages: Dict[str, Tuple[htmlx.Page, Optional[str]]] = {}
    if re.match(r"^https?://", target):
        try:
            r = http.fetch(target, allow_private=allow_private)
        except http.FetchError as exc:
            cli.die(cli.EXIT_REMOTE, "Fetch failed: %s" % exc)
        pages[r.url] = (htmlx.parse(r.text, r.url), None)
        return pages
    root = Path(target)
    if not root.is_dir():
        cli.die(cli.EXIT_USAGE, "Not a folder: %s" % target)
    for f in sorted(root.rglob("*.html")):
        rel = f.relative_to(root).as_posix()
        path = "/" + re.sub(r"(index)?\.html$", "", rel)
        pages[path] = (htmlx.parse(f.read_text(encoding="utf-8", errors="replace"), "https://site.invalid" + path), str(f))
    return pages


def cmd_site(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    cfg = st.load_config(state)
    pages = _site_pages(args.target, args.allow_private)
    findings: List[Dict[str, Any]] = []
    for url, (page, file) in pages.items():
        if "404" in url:
            continue
        findings += page_findings(page, url, file, cfg=cfg)
    home = "/" if "/" in pages else (next(iter(pages)) if pages else None)
    if home:
        findings += legal_links_findings({k: v[0] for k, v in pages.items()}, home)
    blocking = [f for f in findings if f["severity"] in ("P1", "P2")]
    cli.emit({"ok": not blocking, "findings": findings, "disclaimer": DISCLAIMER}, args, cli.render_findings_de(findings, "Rechtliche Oberfläche:") + "\n" + DISCLAIMER)
    return cli.EXIT_FAIL if blocking else cli.EXIT_OK


def cmd_impressum(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    vertical = args.vertical or ((st.load_business(state) or {}).get("vertical") if state else None)
    text, _, src = _load_text_or_page(args.target, args.allow_private)
    checks = impressum_checks(text, vertical)
    failed = [c for c in checks if not c["ok"] and c["level"] == "fail"]
    warned = [c for c in checks if not c["ok"] and c["level"] == "warn"]
    lines = ["Impressum-Prüfung (%s, Branche: %s)" % (src, vertical or "unbekannt")]
    for c in checks:
        if not c["ok"] or c["level"] == "info":
            lines.append("  [%s] %s" % ("FEHLT" if c["level"] == "fail" else ("HINWEIS" if c["level"] == "warn" else "INFO"), c["message_de"]))
    if not failed and not warned:
        lines.append("  Alle geprüften Pflichtangaben gefunden.")
    lines.append(DISCLAIMER)
    cli.emit({"ok": not failed, "source": src, "vertical": vertical, "checks": checks, "disclaimer": DISCLAIMER}, args, "\n".join(lines))
    return cli.EXIT_FAIL if failed else cli.EXIT_OK


def build_parser() -> Any:
    p = cli.base_parser(__doc__.split("\n\n")[0] + "\nAlways: " + DISCLAIMER,
                        "example:\n  python3 scripts/legal_lint.py text .twwa-growth/drafts/2026-11-a01/*.md --kind page\n"
                        "  python3 scripts/legal_lint.py impressum dist/impressum.html --vertical handwerk --json")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "text", "lint German text files (Markdown, text or HTML); exit 1 on a blocking rule")
    sp.add_argument("files", nargs="+")
    sp.add_argument("--kind", choices=("page", "gbp_post", "review_request", "review_reply", "report", "proposal", "outreach"), default=None)
    sp = cli.add_sub(subs, "site", "lint a built site folder or one URL; exit 1 on P1 or P2 findings")
    sp.add_argument("target")
    sp.add_argument("--allow-private", action="store_true")
    sp = cli.add_sub(subs, "impressum", "check required Impressum fields; exit 1 when a required field is missing")
    sp.add_argument("target", help="file (.html, .md, .txt) or URL")
    sp.add_argument("--vertical", choices=("handwerk", "steuerberater", "finanzberatung", "ingenieure", "hausverwaltung", "spedition", "fahrschule", "restaurant", "other"))
    sp.add_argument("--allow-private", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {"text": cmd_text, "site": cmd_site, "impressum": cmd_impressum}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
