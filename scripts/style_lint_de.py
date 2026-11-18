#!/usr/bin/env python3
"""German copy lint: stock phrases and filler typical of machine-written German, empty superlatives and
vague adjectives, with line numbers. Without --gate it only reports (exit 0). With --gate it fails (exit 1)
on any stock phrase or empty superlative, or when the issue density is above the threshold.

The rules are our own restatement of common German editing advice: concrete numbers over adjectives,
short sentences, no agency boilerplate."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, htmlx, textde  # noqa: E402

# (rule id, class, pattern, hint). class "stock" and "superlative" fail the gate; "filler" and "vague" count toward density.
RULES: List[Tuple[str, str, str, str]] = [
    ("stock.heutige_zeit", "stock", r"\b(in der heutigen (zeit|welt)|heutzutage|in zeiten von)\b", "Zeitfloskel streichen; direkt zur Sache."),
    ("stock.kompetenter_partner", "stock", r"\b(ihr(en)? (kompetente[nr]?|zuverlässige[nr]?|starke[nr]?|verlässliche[nr]?) partner|ihr partner (für|rund um|in sachen))\b", "Agentur-Floskel; sagen Sie, was der Betrieb konkret tut."),
    ("stock.ganzheitlich", "stock", r"\bganzheitlich\w*\b", "„ganzheitlich“ sagt nichts; die einzelnen Leistungen nennen."),
    ("stock.massgeschneidert", "stock", r"\b(maßgeschneidert\w*|massgeschneidert\w*|individuelle lösung\w*|passgenaue lösung\w*)\b", "Floskel; beschreiben, was angepasst wird."),
    ("stock.rundum", "stock", r"\b(rundum[- ]sorglos\w*|alles aus einer hand|von a bis z)\b", "Floskel; Leistungsumfang konkret nennen."),
    ("stock.qualitaet", "stock", r"\b(qualität steht (bei uns )?an erster stelle|höchste qualität|qualität und zuverlässigkeit|qualität, die überzeugt)\b", "Qualitätsfloskel; Belege nennen (Material, Prüfung, Gewährleistung)."),
    ("stock.leidenschaft", "stock", r"\b(mit (viel )?leidenschaft|mit herz und (hand|verstand)|herzblut)\b", "Gefühlsfloskel; lieber Erfahrung in Zahlen."),
    ("stock.zufriedenheit", "stock", r"\b(ihre zufriedenheit ist unser (ziel|anspruch)|zufriedene kunden sind unser)\b", "Floskel; ersetzen durch Ablauf oder Bewertungshinweis."),
    ("stock.ki_wendungen", "stock", r"\b(tauchen sie ein|eintauchen in|in die welt der|nahtlos\w*|das herzstück|ein entscheidender faktor|spielt eine entscheidende rolle|es ist wichtig zu beachten|zusammenfassend lässt sich sagen|nicht zuletzt|last but not least)\b", "Typische Maschinen-Wendung; streichen oder konkret formulieren."),
    ("stock.vielerlei", "stock", r"\b(in vielerlei hinsicht|auf ganzer linie|keine wünsche offen)\b", "Leerformel."),
    ("superlative.empty", "superlative", r"\b(erstklassig\w*|unvergleichlich\w*|einzigartig\w*|herausragend\w*|exzellent\w*|perfekt\w*|optimal\w*|unschlagbar\w*|beste[nrs]? (qualität|service|preise?))\b", "Leerer Superlativ; durch eine prüfbare Angabe ersetzen."),
    ("vague.hochwertig", "vague", r"\b(hochwertig\w*|professionell\w*|kompetent\w*|zuverlässig\w*|innovativ\w*|modernst\w*|fachgerecht\w*)\b", "Vages Adjektiv; lieber Material, Norm, Zahl oder Beispiel."),
    ("filler.connective", "filler", r"\b(darüber hinaus|des weiteren|außerdem|zudem|ferner|im rahmen (von|der|des)|grundsätzlich|letztendlich|im endeffekt)\b", "Füllwort; meist entbehrlich."),
    ("filler.nicht_nur", "filler", r"\bnicht nur\b[^.]{0,80}\bsondern auch\b", "„nicht nur … sondern auch“ sparsam verwenden."),
    ("filler.exclamation", "filler", r"!{1}", "Ausrufezeichen in Fließtext vermeiden."),
]
GATE_CLASSES = {"stock", "superlative"}
DENSITY_LIMIT = 2.0  # issues of class filler or vague per 100 words
LONG_SENTENCE_WORDS = 28
MARKER_RE = re.compile(r"\[\[[pfb]:[^\]]+\]\]")


def _body_lines(text: str) -> List[Tuple[int, str]]:
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    out = []
    in_code = False
    for i in range(start, len(lines)):
        ln = lines[i]
        if ln.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        out.append((i + 1, MARKER_RE.sub("", ln)))
    return out


def lint(text: str) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    words = 0
    for n, ln in _body_lines(text):
        clean = re.sub(r"<[^>]+>", " ", ln)
        clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", clean)
        if not clean.strip():
            continue
        is_heading = clean.lstrip().startswith("#")
        words += len(textde.words(clean))
        for rid, klass, pat, hint in RULES:
            if rid == "filler.exclamation" and is_heading:
                continue
            for m in re.finditer(pat, clean, re.IGNORECASE):
                issues.append({"rule": rid, "class": klass, "line": n, "match": m.group(0), "hint": hint})
        for s in textde.sentences(clean):
            wc = len(textde.words(s))
            if wc > LONG_SENTENCE_WORDS and not is_heading:
                issues.append({"rule": "length.sentence", "class": "filler", "line": n, "match": s[:60] + "…", "hint": "Satz mit %d Wörtern; teilen." % wc})
    density_count = len([i for i in issues if i["class"] in ("filler", "vague")])
    density = (density_count * 100.0 / words) if words else 0.0
    gate_hits = [i for i in issues if i["class"] in GATE_CLASSES]
    return {"words": words, "issues": issues, "density_per_100_words": round(density, 2), "density_limit": DENSITY_LIMIT,
            "gate_failed": bool(gate_hits) or density > DENSITY_LIMIT, "gate_hits": len(gate_hits)}


def read_text(path: str) -> str:
    p = Path(path)
    raw = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() in (".html", ".htm"):
        page = htmlx.parse(raw, "")
        return "\n".join(b["text"] for b in page.text_blocks if b["main"] and not b["shared"])
    return raw


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/style_lint_de.py .twwa-growth/drafts/2026-11-a01/seite.md --gate")
    p.add_argument("files", nargs="+", help="Markdown, text or HTML files")
    p.add_argument("--gate", action="store_true", help="fail (exit 1) on stock phrases, empty superlatives or high filler density")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    results = []
    failed = False
    for f in args.files:
        if not Path(f).is_file():
            cli.die(cli.EXIT_USAGE, "File not found: %s" % f)
        r = lint(read_text(f))
        r["file"] = f
        results.append(r)
        failed = failed or r["gate_failed"]
    lines = []
    for r in results:
        lines.append("%s: %d Wörter, %d Hinweise, Dichte %.2f/100 Wörter (Grenze %.1f)%s" % (
            r["file"], r["words"], len(r["issues"]), r["density_per_100_words"], DENSITY_LIMIT, ", GATE: FAIL" if r["gate_failed"] and args.gate else ""))
        for i in r["issues"]:
            lines.append("  %s:%d [%s] „%s“: %s" % (r["file"], i["line"], i["class"], i["match"], i["hint"]))
    cli.emit({"ok": not (args.gate and failed), "gate": args.gate, "results": results}, args, "\n".join(lines))
    return cli.EXIT_FAIL if (args.gate and failed) else cli.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
