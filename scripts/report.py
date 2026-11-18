#!/usr/bin/env python3
"""One-page German monthly owner report (spec 6, dossier 09 §5, 12): leads with qualified Anfragen, compares them
with what lead portals charge (shared inquiries), then visibility (Google, Maps, AI), what was done and what it did,
and exactly one request to the owner. No prices for TWWA's work, no guarantees, missing numbers say "nicht erfasst"."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st  # noqa: E402

PORTAL_EUR = (50, 120)  # per inquiry, shared with 3-5 firms (dossier 12)


def _month_snap(state: Path, source: str, month: str) -> Optional[Dict[str, Any]]:
    files = [f for f in sorted(state.glob("snapshots/*/%s.json" % source)) if f.parent.name[:7] <= month]
    return st.load_json(files[-1]) if files else None


def _prev(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return "%04d-%02d" % ((y, m - 1) if m > 1 else (y - 1, 12))


def _n(v: Any) -> str:
    return "nicht erfasst" if v is None else ("{:,}".format(int(v)).replace(",", "."))


def owner_request(state: Path) -> str:
    cfg = st.load_config(state)
    import twwa_actions  # type: ignore
    acts = twwa_actions.fold(st.read_jsonl(state / "actions.jsonl"))
    waiting = [a for a in acts.values() if a.get("state") == "proposed" and (a.get("risk") in ("R2", "R3"))]
    if waiting:
        a = waiting[0]
        return "Bitte geben Sie diese Änderung frei: „%s“. Die Vorschau schicken wir Ihnen mit dieser Nachricht." % a.get("title_de")
    if (cfg.get("owner_input") or {}).get("monthly_project_report"):
        return ("Bitte schicken Sie uns zum Monatsende 3 bis 5 Fotos eines aktuellen Projekts und drei Sätze dazu: Ort (Ortsteil), "
                "was gemacht wurde, wie lange es gedauert hat. Daraus entstehen belegte Inhalte für Website und Google-Profil.")
    return "Bitte geben Sie jeder Kundin und jedem Kunden bei der Übergabe die Bewertungskarte mit."


def build(state: Path, month: str) -> str:
    b = st.load_business(state) or {}
    from leads import summary as lead_summary  # type: ignore
    leads, prev_leads = lead_summary(state, month), lead_summary(state, _prev(month))
    gsc = _month_snap(state, "gsc", month) or {}
    gbp = _month_snap(state, "gbp", month) or {}
    ai = _month_snap(state, "ai-panel", month)
    perf = gbp.get("performance") or {}
    nb = [r for r in gsc.get("rows", []) if r.get("branded") is False]
    clicks_nb = sum(r["clicks"] for r in nb) if gsc else None
    import twwa_actions  # type: ignore
    acts = twwa_actions.fold(st.read_jsonl(state / "actions.jsonl"))
    shipped = [a for a in acts.values() if (a.get("shipped_at") or "")[:7] == month]
    measured = [a for a in acts.values() if (a.get("measured_at") or "")[:7] == month]
    q = leads["qualified"]
    lines = ["# Monatsbericht %s – %s" % (month, b.get("name") or ""), "",
             "## Anfragen",
             "- **%d qualifizierte Anfragen** (insgesamt %d; Vormonat %d qualifiziert)." % (q, leads["total"], prev_leads["qualified"]),
             "- Kanäle: %s." % (", ".join("%s %d" % (k, v) for k, v in leads["by_channel"].items()) or "nicht erfasst"),
             "- Herkunft laut Kundenangabe: %s." % (", ".join("%s %d" % (k, v) for k, v in leads["by_source"].items()) or "nicht erfasst")]
    if q:
        lines.append("- Zum Vergleich: Über Anfrageportale kostet eine Anfrage typischerweise %d–%d €, und sie geht an 3–5 Betriebe gleichzeitig. "
                     "Diese %d Anfragen kamen direkt und exklusiv zu Ihnen." % (PORTAL_EUR[0], PORTAL_EUR[1], q))
    lines += ["", "## Sichtbarkeit",
              "- Google-Suche: %s Klicks ohne Markensuchen (Zeitraum %s bis %s)." % (_n(clicks_nb), (gsc.get("range") or {}).get("start", "–"), (gsc.get("range") or {}).get("end", "–")),
              "- Google-Profil: Anrufe %s, Website-Klicks %s, Routen %s." % (_n(perf.get("calls")), _n(perf.get("website_clicks")), _n(perf.get("directions")))]
    if ai:
        lines.append("- KI-Assistenten: in %s der geprüften Antworten genannt (Spanne %s)%s." % (
            "%d %%" % round(100 * ai["client_mention_rate"]) if ai.get("client_mention_rate") is not None else "nicht erfasst",
            "–".join("%d %%" % round(100 * x) for x in ai.get("client_ci95") or []) or "–", ", Stichprobe" if ai.get("origin") == "manual" else ""))
    else:
        lines.append("- KI-Assistenten: nicht geprüft.")
    lines += ["", "## Was wir gemacht haben"]
    lines += ["- %s" % a.get("title_de") for a in shipped] or ["- Keine Änderungen live gegangen."]
    if measured:
        lines += ["", "## Was es gebracht hat"]
        for a in measured:
            ev = next((e for e in reversed(a["events"]) if e.get("event") == "measured"), {})
            lines.append("- %s: %s" % (a.get("title_de"), ev.get("text_de") or a.get("verdict")))
    nxt = [a for a in acts.values() if a.get("state") in ("proposed", "approved")][:3]
    lines += ["", "## Als Nächstes"] + (["- %s" % a.get("title_de") for a in nxt] or ["- Planung für den nächsten Zyklus folgt."])
    lines += ["", "## Eine Bitte an Sie", owner_request(state), ""]
    return "\n".join(lines)


def cmd_build(args: Any) -> int:
    state = st.require_state(args)
    month = args.month or st.today()[:7]
    text = build(state, month)
    from legal_lint import lint_text  # type: ignore
    blocks = [i for i in lint_text(text, "report") if i.get("level") == "block"]
    if blocks:
        cli.die(cli.EXIT_FAIL, "Report fails legal lint: %s" % blocks)
    out = state / "reports" / ("%s.md" % month)
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    cli.emit({"report": str(out)}, args, text + "\n-> %s" % out)
    return cli.EXIT_OK


def cmd_owner_request(args: Any) -> int:
    state = st.require_state(args)
    cli.emit({"request_de": owner_request(state)}, args, owner_request(state))
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  report.py build --month 2026-11")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "build", "write reports/<yyyy-mm>.md")
    sp.add_argument("--month", default=None)
    sp.set_defaults(fn=cmd_build)
    cli.add_sub(subs, "owner-request", "the single German request to the owner").set_defaults(fn=cmd_owner_request)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
