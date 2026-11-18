#!/usr/bin/env python3
"""Review engine that is lawful in Germany by construction (dossier 03 §6, references/review-law-de.md):
no incentives, no gating (everyone is asked the same way), no staff reviews, electronic requests only with recorded
consent (BGH VI ZR 225/17), and a §5b UWG notice wherever reviews are shown. The plugin never sends requests:
the owner asks in person or hands out the card. `target` sets a velocity from the pack winners; `assets` writes the
German card, notice and request texts; `consent` keeps a ledger without names; `reply-lint` checks reply drafts."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st  # noqa: E402
from twwa_lib.stats import median  # noqa: E402

CARD = """# Bewertungskarte (Druckvorlage, Entwurf)

Vorderseite:
  {name}
  Wie zufrieden waren Sie mit unserer Arbeit?
  Ihre ehrliche Meinung hilft anderen bei der Wahl – und uns, besser zu werden.
  [QR-Code: direkter Bewertungslink des Google-Unternehmensprofils]

Rückseite:
  QR-Code mit der Handykamera scannen, Sterne wählen, ein paar Sätze schreiben.
  Danke für Ihre Zeit. {owner}

Regeln für die Übergabe (nicht drucken):
- Jede Kundin, jeder Kunde bekommt die Karte, egal wie der Auftrag lief (kein Vorsortieren).
- Keine Gegenleistung, kein Rabatt, keine Verlosung, keine Bitte um „5 Sterne“.
- Keine Bewertungen von Mitarbeitenden, Familie oder für Gefälligkeiten.
- QR-Code mit dem Link aus dem Profil („Rezensionen erhalten“) erzeugen und vor dem Druck mit dem Handy testen.
"""

NOTICE = """# Hinweis zu Bewertungen (§ 5b Abs. 3 UWG) – Entwurf, vor Einsatz rechtlich prüfen

Wo Bewertungen auf der Website gezeigt werden, steht direkt dabei:

„Die angezeigten Bewertungen stammen aus unserem Google-Unternehmensprofil. Wir prüfen nicht, ob die Bewertenden
unsere Leistung tatsächlich in Anspruch genommen haben. Wir zeigen alle Bewertungen ungefiltert in der von Google
gelieferten Reihenfolge.“

(Wenn eine Prüfung stattfindet, stattdessen beschreiben, wie geprüft wird.)
"""

ASK_IN_PERSON = """# Bitte um eine Bewertung – im Gespräch (Entwurf)

Bei der Abnahme oder Übergabe, an alle Kundinnen und Kunden gleich:

„Wenn Sie mit unserer Arbeit zufrieden waren oder etwas zu verbessern ist: Wir freuen uns über eine ehrliche
Bewertung bei Google. Auf der Karte ist ein QR-Code, das dauert zwei Minuten.“

Elektronisch (E-Mail, WhatsApp) nur, wenn die Einwilligung vorher erfasst wurde (`reviews.py consent add`) und
config.legal.review_request_electronic auf true steht. Keine Erinnerungen.
"""


def cmd_target(args: Any) -> int:
    state = st.require_state(args)
    gbp = st.load_latest_snapshot(state, "gbp") or {}
    rev = gbp.get("reviews") or {}
    winners = []
    tds = sorted(state.glob("teardowns/*/summary.json"))
    if tds:
        winners = [w.get("review_count") for w in (st.load_json(tds[-1]) or {}).get("pack_winners", []) if w.get("review_count")]
    winners += [c.get("review_count") for c in gbp.get("competitors", []) if c.get("review_count")]
    med = median(winners) if winners else None
    mine = rev.get("count")
    vel = (rev.get("last_90") or 0) / 3.0
    if med is None or mine is None:
        res = {"status": "not_checked", "reason_de": "Bewertungszahlen der Gewinner oder des Kunden fehlen", "monthly_target": 2}
    else:
        gap = max(0, med - mine)
        months = 12
        tgt = max(1, min(8, round(gap / months + 0.49)))
        res = {"client_count": mine, "winner_median": med, "gap": gap, "current_per_month": round(vel, 1), "monthly_target": tgt,
               "months_to_median": round(gap / max(tgt, 1), 1) if gap else 0,
               "reason_de": "Ziel %d neue Bewertungen pro Monat (aktuell %.1f): Median der Gewinner in etwa %s Monaten" % (tgt, vel, round(gap / max(tgt, 1), 1))}
    rj = st.load_json(state / "reviews.json", {"schema_version": 1})
    rj["velocity_target"] = res
    st.save_json(state / "reviews.json", rj)
    cli.emit(res, args, res["reason_de"])
    return cli.EXIT_OK


def cmd_assets(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    out = state / "drafts" / (args.action or "review-assets")
    out.mkdir(parents=True, exist_ok=True)
    files = {"bewertungskarte.md": CARD.format(name=b.get("name") or "Musterbetrieb", owner=b.get("owner") or ""),
             "hinweis-5b-uwg.md": NOTICE, "bitte-im-gespraech.md": ASK_IN_PERSON}
    for n, t in files.items():
        (out / n).write_text(t, encoding="utf-8")
    cli.emit({"dir": str(out), "files": sorted(files)}, args, "Entwürfe in %s (rechtlich prüfen, bevor sie eingesetzt werden)." % out)
    return cli.EXIT_OK


def cmd_consent(args: Any) -> int:
    state = st.require_state(args)
    rj = st.load_json(state / "reviews.json", {"schema_version": 1})
    led = rj.setdefault("consent_ledger", [])
    if args.op == "add":
        led.append({"ref": args.ref, "date": st.today(), "channel": args.channel, "wording_version": args.wording, "recorded_by": args.by})
        st.save_json(state / "reviews.json", rj)
    cli.emit(led, args, "%d Einwilligungen erfasst (nur Referenzen, keine Namen)." % len(led))
    return cli.EXIT_OK


def reply_issues(text: str, b: Dict[str, Any]) -> List[Dict[str, Any]]:
    from legal_lint import lint_text  # type: ignore
    issues = [{"rule": i.get("rule"), "level": i.get("level"), "message_de": i.get("message_de")} for i in lint_text(text, "review_reply")]
    if len(text) > 1500:
        issues.append({"rule": "length", "level": "warn", "message_de": "Antwort zu lang (über 1.500 Zeichen)."})
    if re.search(r"\b(\+?49|0)\d[\d /-]{6,}", text) and (b.get("phone") or "")[-4:] not in text:
        issues.append({"rule": "pii", "level": "block", "message_de": "Telefonnummer, die nicht die des Betriebs ist."})
    if re.search(r"\b(Herr|Frau)\s+[A-ZÄÖÜ][a-zäöüß]+", text):
        issues.append({"rule": "pii_name", "level": "warn", "message_de": "Kundennamen in öffentlichen Antworten vermeiden."})
    if re.search(r"(rabatt|gutschein|nächsten auftrag.*%|dankeschön.*geschenk)", text, re.I):
        issues.append({"rule": "incentive", "level": "block", "message_de": "Gegenleistung in einer Bewertungsantwort."})
    return issues


def cmd_reply_lint(args: Any) -> int:
    state = st.require_state(args)
    text = Path(args.file).read_text(encoding="utf-8")
    issues = reply_issues(text, st.load_business(state) or {})
    cli.emit(issues, args, "\n".join("[%s] %s" % (i["level"], i["message_de"]) for i in issues) or "Antwort ok.")
    return cli.EXIT_FAIL if any(i["level"] == "block" for i in issues) else cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  reviews.py target\n  reviews.py assets --action 2026-11-a04")
    subs = cli.add_subcommands(p)
    cli.add_sub(subs, "target", "monthly velocity target from pack winners").set_defaults(fn=cmd_target)
    sp = cli.add_sub(subs, "assets", "German card, §5b notice and request texts (drafts)")
    sp.add_argument("--action", default=None)
    sp.set_defaults(fn=cmd_assets)
    sp = cli.add_sub(subs, "consent", "consent ledger for electronic requests (references only)")
    sp.add_argument("op", choices=("list", "add"))
    sp.add_argument("--ref", default=None)
    sp.add_argument("--channel", default="in_person")
    sp.add_argument("--wording", default="v1")
    sp.add_argument("--by", default=None)
    sp.set_defaults(fn=cmd_consent)
    sp = cli.add_sub(subs, "reply-lint", "check a review reply draft")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_reply_lint)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
