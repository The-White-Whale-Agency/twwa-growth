#!/usr/bin/env python3
"""German check report from findings. `client` assembles the latest snapshots of a client into
reports/check-<date>.md. `prospect` crawls any public URL read-only (no repo, no credentials, no form posts) and writes
a one-page "Sichtbarkeits-Check" plus a call opener to ./twwa-checks/<domain>/, never into a client repo."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
AREA_DE = {"tracking": "Anfragen-Erfassung", "gbp": "Google-Profil", "tech": "Technik", "onpage": "Seiteninhalt", "cro": "Anfrage-Wege",
           "legal": "Recht", "citations": "Einträge", "reviews": "Bewertungen", "ai": "KI-Sichtbarkeit", "content": "Inhalte", "offsite": "Erwähnungen"}
IMPACT_DE = {"P1": "kostet jetzt Anfragen", "P2": "klarer Verlust an Sichtbarkeit oder Anfragen", "P3": "Verbesserung"}


def render(findings: List[Dict[str, Any]], title: str, site: str, top: int = 7) -> str:
    fs = cli.sort_findings([f for f in findings if f.get("severity") in ("P1", "P2", "P3")])
    ver = [f for f in fs if f.get("status") == "verified"]
    nc = sorted({f.get("detail_de") for f in fs if f.get("status") == "not_checked"})
    lines = ["# %s" % title, "", "Website: %s · Stand: %s" % (site, st.today()), "",
             "**Ergebnis:** %d belegte Punkte, davon %d dringend." % (len(ver), sum(1 for f in ver if f["severity"] == "P1")), "",
             "## Die wichtigsten Punkte"]
    for i, f in enumerate(ver[:top], 1):
        ev = f.get("evidence") or {}
        where = ev.get("url") or ev.get("file") or ""
        lines.append("%d. **%s** (%s, %s)  \n   %s%s" % (i, f["title_de"], AREA_DE.get(f["area"], f["area"]), IMPACT_DE[f["severity"]],
                                                     f.get("detail_de", ""), "  \n   Beleg: %s" % where if where else ""))
    hyp = [f for f in fs if f.get("status") == "hypothesis"][:3]
    if hyp:
        lines += ["", "## Vermutungen (noch ohne Beleg)"] + ["- %s" % f["title_de"] for f in hyp]
    if nc:
        lines += ["", "## Nicht geprüft"] + ["- %s" % x for x in nc[:6]]
    lines += ["", "_Hinweis: technische und inhaltliche Prüfung, keine Rechtsberatung._", ""]
    return "\n".join(lines)


def opener(findings: List[Dict[str, Any]], name: str) -> str:
    v = [f for f in cli.sort_findings(findings) if f.get("status") == "verified"]
    top = v[0]["title_de"] if v else "einige Punkte bei Ihrer Sichtbarkeit in Google"
    return ("Guten Tag%s, hier ist [Name] von The White Whale Agency. Ich habe mir Ihre Website angesehen und dabei etwas Konkretes gefunden: "
            "%s. Das kostet Sie wahrscheinlich Anfragen aus Ihrer Region. Haben Sie zwei Minuten, dann zeige ich Ihnen, was ich meine?"
            % ((" " + name) if name else "", top.rstrip(".")))


def _audit(url: str, out: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for script, argv in (("site_audit.py", ["live", url, "--with-graph"]), ("legal_lint.py", ["site", url])):
        p = subprocess.run([sys.executable, "-I", str(SCRIPTS / script)] + argv + ["--json"], capture_output=True, text=True, cwd=str(out))
        try:
            data = json.loads(p.stdout or "null")
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            findings += data.get("findings") or []
        elif isinstance(data, list):
            findings += [f for f in data if isinstance(f, dict) and "severity" in f]
    return findings


def cmd_prospect(args: Any) -> int:
    dom = urlparse(args.url).netloc.replace("www.", "") or args.url
    out = Path(args.out or "./twwa-checks") / dom
    out.mkdir(parents=True, exist_ok=True)
    if st.find_state(str(out)):
        cli.die(cli.EXIT_BLOCKED, "Refused: prospect output must not be inside a client repo with a state folder.")
    findings = _audit(args.url, out)
    (out / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=1), encoding="utf-8")
    report = render(findings, "Sichtbarkeits-Check", args.url, top=5)
    (out / "sichtbarkeits-check.md").write_text(report, encoding="utf-8")
    (out / "gespraechseinstieg.md").write_text(opener(findings, args.owner or "") + "\n", encoding="utf-8")
    cli.emit({"dir": str(out), "findings": len(findings)}, args, report + "\n-> %s" % out)
    return cli.EXIT_OK


def cmd_client(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    findings: List[Dict[str, Any]] = []
    for src in ("site", "check", "psi"):
        s = st.load_latest_snapshot(state, src)
        if s:
            findings += s.get("findings", [])
    for script, argv in (("gbp.py", ["audit"]), ("gbp.py", ["lint"]), ("entity_check.py", ["run"]), ("measure.py", ["alerts"])):
        p = subprocess.run([sys.executable, str(SCRIPTS / script)] + argv + ["--state", str(state), "--json"], capture_output=True, text=True)
        try:
            data = json.loads(p.stdout or "null")
        except json.JSONDecodeError:
            continue
        findings += data.get("findings", []) if isinstance(data, dict) else [f for f in data or [] if isinstance(f, dict) and "severity" in f]
    seen, uniq = set(), []
    for f in findings:
        if f["id"] not in seen:
            seen.add(f["id"])
            uniq.append(f)
    st.save_json(st.snapshot_dir(state) / "check.json", {"source": "check", "pulled_at": st.now_iso(), "origin": "api", "findings": uniq})
    report = render(uniq, "Check %s" % (b.get("name") or ""), b.get("url") or "")
    out = state / "reports" / ("check-%s.md" % st.today())
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    cli.emit({"report": str(out), "findings": len(uniq)}, args, report + "\n-> %s" % out)
    return cli.EXIT_OK


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  check_report.py prospect https://www.beispiel.de --owner 'Herr Beispiel'")
    subs = cli.add_subcommands(p)
    cli.add_sub(subs, "client", "check report from the client's snapshots").set_defaults(fn=cmd_client)
    sp = cli.add_sub(subs, "prospect", "read-only check of any public URL")
    sp.add_argument("url")
    sp.add_argument("--owner", default=None, help="owner name for the call opener")
    sp.add_argument("--out", default=None)
    sp.set_defaults(fn=cmd_prospect)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
