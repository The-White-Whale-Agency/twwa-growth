"""CLI helpers shared by every script: parser, exit codes, output, findings.

Contract (spec section 8 and 8.1):
- exit codes EXIT_OK 0, EXIT_FAIL 1, EXIT_USAGE 2, EXIT_NOCREDS 3, EXIT_BLOCKED 4, EXIT_REMOTE 5
- ``--json`` prints machine output on stdout; human text goes to stderr when ``--json`` is set
- ``finding(...)`` builds and validates a section 4.3 finding record
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_NOCREDS = 3
EXIT_BLOCKED = 4
EXIT_REMOTE = 5

EXIT_CODES_HELP = """exit codes:
  0  ok or pass
  1  gate failed, or findings at or above --fail-on
  2  usage or config error
  3  credentials or connector not configured
  4  blocked by safety (STOP, cap, approval, spend, scope)
  5  network or remote error"""

AREAS = ("tracking", "gbp", "tech", "onpage", "cro", "legal", "citations", "reviews", "ai", "content", "offsite")
SEVERITIES = ("P1", "P2", "P3", "info")
STATUSES = ("verified", "hypothesis", "not_checked")
SEVERITY_RANK = {"P1": 1, "P2": 2, "P3": 3, "info": 4}

# action type -> (priority group, default window days, default risk)  (spec 4.4)
ACTION_TYPES: Dict[str, tuple] = {
    "tracking_fix": (1, 7, "R1"),
    "gbp_identity_edit": (2, 14, "R3"),
    "gbp_content_edit": (2, 14, "R2"),
    "gbp_post": (2, 28, "R2"),
    "tech_fix": (3, 28, "R1"),
    "robots_policy": (3, 7, "R1"),
    "onpage_rewrite": (3, 28, "R2"),
    "cro_change": (3, 28, "R2"),
    "review_engine": (4, 90, "R2"),
    "review_reply": (4, 30, "R2"),
    "citation": (5, 120, "R2"),
    "new_page": (6, 90, "R2"),
    "page_refresh": (6, 28, "R2"),
    "page_consolidate": (6, 28, "R2"),
    "offsite_mention": (7, 180, "R2"),
    "ai_refinement": (8, 28, "R2"),
}

_ID_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")


class _Formatter(argparse.RawDescriptionHelpFormatter):
    pass


def base_parser(description: str, epilog: Optional[str] = None) -> argparse.ArgumentParser:
    """Return a parser with the shared options ``--json`` and ``--state``.

    ``epilog`` should hold one example; the exit code table is appended.
    """
    text = EXIT_CODES_HELP if not epilog else epilog.rstrip() + "\n\n" + EXIT_CODES_HELP
    p = argparse.ArgumentParser(description=description, epilog=text, formatter_class=_Formatter)
    p.add_argument("--json", action="store_true", default=False, help="machine output on stdout")
    p.add_argument("--state", default=None, help="state folder (default: .twwa-growth found from the current directory, or TWWA_STATE_DIR)")
    return p


def add_subcommands(parser: argparse.ArgumentParser, dest: str = "cmd") -> Any:
    subs = parser.add_subparsers(dest=dest, metavar="<command>")
    subs.required = True
    return subs


def add_sub(subs: Any, name: str, help_text: str, epilog: Optional[str] = None) -> argparse.ArgumentParser:
    """Add a subcommand that also accepts ``--json`` and ``--state`` after the subcommand name."""
    sp = subs.add_parser(name, help=help_text, description=help_text, epilog=epilog, formatter_class=_Formatter)
    sp.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="machine output on stdout")
    sp.add_argument("--state", default=argparse.SUPPRESS, help="state folder")
    return sp


def is_json(args: Any) -> bool:
    return bool(getattr(args, "json", False))


def say(args: Any, msg: str) -> None:
    """Human text: stdout normally, stderr when --json is set."""
    stream = sys.stderr if is_json(args) else sys.stdout
    print(msg, file=stream)


def emit(obj: Any, args: Any, human: Optional[str] = None) -> None:
    """Print ``obj`` as JSON when --json is set, else ``human`` (or pretty JSON) on stdout."""
    if is_json(args):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
        if human:
            print(human, file=sys.stderr)
    else:
        if human is None:
            human = json.dumps(obj, ensure_ascii=False, indent=2)
        print(human)


def die(code: int, msg: str) -> None:
    """Print ``msg`` to stderr and exit with ``code``. With --json on the command line, also print
    {"ok": false, "exit": code, "error": msg} on stdout so callers always get JSON."""
    if "--json" in sys.argv[1:]:
        sys.stdout.write(json.dumps({"ok": False, "exit": code, "error": msg}, ensure_ascii=False) + "\n")
    print(msg, file=sys.stderr)
    sys.exit(code)


def finding(
    id: str,
    area: str,
    severity: str,
    title_de: str,
    detail_de: str,
    evidence: Optional[Dict[str, Any]] = None,
    status: str = "verified",
    fix_hint: str = "",
    action_type: Optional[str] = None,
    priority_group: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a section 4.3 finding and validate it. Raises ValueError on a schema violation."""
    ev = {"url": None, "file": None, "line": None, "snippet": None, "value": None}
    if evidence:
        unknown = set(evidence) - set(ev)
        if unknown:
            raise ValueError("finding %s: unknown evidence keys %s" % (id, sorted(unknown)))
        ev.update(evidence)
    if not _ID_RE.match(id or ""):
        raise ValueError("finding id must be dotted lowercase: %r" % id)
    if area not in AREAS:
        raise ValueError("finding %s: area %r not in %s" % (id, area, AREAS))
    if severity not in SEVERITIES:
        raise ValueError("finding %s: severity %r" % (id, severity))
    if status not in STATUSES:
        raise ValueError("finding %s: status %r" % (id, status))
    if action_type is not None and action_type not in ACTION_TYPES:
        raise ValueError("finding %s: action_type %r" % (id, action_type))
    if priority_group is None:
        priority_group = ACTION_TYPES[action_type][0] if action_type else 3
    if not isinstance(priority_group, int) or not 1 <= priority_group <= 8:
        raise ValueError("finding %s: priority_group must be 1..8" % id)
    if not title_de or not detail_de:
        raise ValueError("finding %s: title_de and detail_de are required" % id)
    has_evidence = any(ev[k] not in (None, "") for k in ("url", "file", "snippet", "value"))
    if status == "verified" and not has_evidence:
        raise ValueError("finding %s: status verified needs evidence; use status hypothesis" % id)
    return {
        "id": id,
        "area": area,
        "severity": severity,
        "title_de": title_de,
        "detail_de": detail_de,
        "evidence": ev,
        "status": status,
        "fix_hint": fix_hint,
        "action_type": action_type,
        "priority_group": priority_group,
    }


def validate_finding(f: Dict[str, Any]) -> Dict[str, Any]:
    """Re-validate an existing finding dict (e.g. read from a snapshot)."""
    return finding(
        f.get("id", ""), f.get("area", ""), f.get("severity", ""), f.get("title_de", ""), f.get("detail_de", ""),
        evidence=f.get("evidence"), status=f.get("status", ""), fix_hint=f.get("fix_hint", ""),
        action_type=f.get("action_type"), priority_group=f.get("priority_group"),
    )


def at_or_above(findings: Iterable[Dict[str, Any]], level: Optional[str], statuses: Iterable[str] = ("verified",)) -> List[Dict[str, Any]]:
    """Findings with severity at or above ``level`` (P1 is highest) and a status in ``statuses``."""
    if not level:
        return []
    limit = SEVERITY_RANK[level]
    st = set(statuses)
    return [f for f in findings if f.get("status") in st and SEVERITY_RANK.get(f.get("severity"), 9) <= limit]


def sort_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = {"verified": 0, "hypothesis": 1, "not_checked": 2}
    return sorted(findings, key=lambda f: (SEVERITY_RANK.get(f["severity"], 9), order.get(f["status"], 9), f["priority_group"], f["id"]))


def render_findings_de(findings: List[Dict[str, Any]], header: str = "") -> str:
    lines = [header] if header else []
    for f in sort_findings(findings):
        tag = {"verified": "", "hypothesis": " (Hypothese)", "not_checked": " (nicht geprüft)"}.get(f["status"], "")
        where = f["evidence"].get("url") or f["evidence"].get("file") or ""
        if f["evidence"].get("line"):
            where += ":%s" % f["evidence"]["line"]
        lines.append("[%s] %s%s" % (f["severity"], f["title_de"], tag))
        lines.append("      %s" % f["detail_de"])
        if where:
            lines.append("      Fundstelle: %s" % where)
    if not findings:
        lines.append("Keine Befunde.")
    return "\n".join(lines)
