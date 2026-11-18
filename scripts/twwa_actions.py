#!/usr/bin/env python3
"""Action log for twwa-growth: proposals with caps, approvals bound to a content hash, ship and measure
events, due windows, the German approval packet, the STOP kill switch and one-command rollback."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, spend, state as st  # noqa: E402
import twwa_state  # noqa: E402

STATE_EVENTS = ("proposed", "approved", "shipped", "measured", "kept", "reverted", "rejected", "blocked", "superseded")
OPEN_STATES = ("proposed", "approved", "blocked")
CONTENT_TYPES = ("onpage_rewrite", "page_refresh", "cro_change", "ai_refinement", "page_consolidate")
REQUIRED_ROLES = {"R0": [], "R1": ["twwa"], "R2": ["twwa", "owner"], "R3": ["twwa", "owner"]}
CHANNELS = ("pr", "email", "whatsapp", "call", "in_person")
METRIC_DE = {
    "gsc.clicks": "Klicks aus der Google-Suche",
    "gsc.impressions": "Impressionen in der Google-Suche",
    "gsc.position": "durchschnittliche Position in der Google-Suche",
    "gsc.ctr": "Klickrate in der Google-Suche",
    "leads.count": "Anfragen über Website, Telefon und WhatsApp",
    "leads.qualified": "qualifizierte Anfragen",
    "gbp.calls": "Anrufe über das Google-Unternehmensprofil",
    "gbp.website_clicks": "Website-Klicks aus dem Google-Unternehmensprofil",
    "gbp.directions": "Routenanfragen aus dem Google-Unternehmensprofil",
    "reviews.last_30": "neue Google-Bewertungen pro Monat",
    "grid.solv": "Sichtbarkeit in der Kartensuche (Anteil der Rasterpunkte in den Top 3)",
    "ai.mention_rate": "Nennungen in KI-Antworten",
    "bing.indexed": "Seiten im Bing-Index",
}
RISK_DE = {
    "R0": "nur lesend, keine Änderung",
    "R1": "technische Änderung ohne sichtbare Aussagen",
    "R2": "sichtbare Inhalte oder Profilangaben; braucht Ihre Freigabe",
    "R3": "Identität oder Rechtstexte; wird ausschließlich von Menschen umgesetzt",
}
TIER_FOR = {"page": "SCALE", "api": "SCALE", "dependency": "SCALE", "webgl": "PREMIUM"}


# ---------------------------------------------------------------- event log

def actions_path(state: Path) -> Path:
    return state / "actions.jsonl"


def fold(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Current state of every action: merge of its payloads plus the last state event."""
    out: Dict[str, Dict[str, Any]] = {}
    for e in events:
        aid = e.get("action_id")
        if not aid or aid == "-":
            continue
        a = out.setdefault(aid, {"action_id": aid, "state": None, "events": [], "commits": [], "artifacts": []})
        a["events"].append(e)
        ev = e.get("event")
        payload = {k: v for k, v in e.items() if k not in ("ts", "event", "action_id")}
        if ev in ("proposed", "updated"):
            for k, v in payload.items():
                a[k] = v
            a.setdefault("proposed_at", e.get("ts"))
        if ev == "shipped":
            a["shipped_at"] = e.get("ts")
            for c in e.get("commits") or []:
                if c not in a["commits"]:
                    a["commits"].append(c)
            for k in ("branch", "preview_url", "deploy_id", "baseline_snapshot"):
                if e.get(k):
                    a[k] = e[k]
        if ev == "artifacts":
            for p in e.get("paths") or []:
                if p not in a["artifacts"]:
                    a["artifacts"].append(p)
        if ev == "measured":
            a["verdict"] = e.get("verdict")
            a["measured_at"] = e.get("ts")
        if ev in STATE_EVENTS:
            a["state"] = ev
            if ev in ("blocked", "rejected", "superseded", "kept", "reverted") and e.get("reason"):
                a["state_reason"] = e.get("reason")
    return out


def load_actions(state: Path) -> Dict[str, Dict[str, Any]]:
    return fold(st.read_jsonl(actions_path(state)))


def log_event(state: Path, action_id: str, event: str, **payload: Any) -> Dict[str, Any]:
    e = {"ts": st.now_iso(), "action_id": action_id, "event": event}
    e.update(payload)
    st.append_jsonl(actions_path(state), e)
    return e


def next_action_id(actions: Dict[str, Any], month: Optional[str] = None, state: Optional[Path] = None) -> str:
    """Next free id ``<yyyy-mm>-aNN``; ids used by drafts/ or approvals/ folders count as taken."""
    month = month or st.today()[:7]
    nums = []
    taken = list(actions)
    if state is not None:
        for sub in ("drafts", "approvals"):
            d = state / sub
            if d.is_dir():
                taken += [p.stem for p in d.iterdir()]
    for a in taken:
        m = re.match(r"^%s-a(\d+)$" % re.escape(month), a)
        if m:
            nums.append(int(m.group(1)))
    return "%s-a%02d" % (month, (max(nums) + 1) if nums else 1)


def get_action(state: Path, aid: str) -> Dict[str, Any]:
    acts = load_actions(state)
    if aid not in acts:
        cli.die(cli.EXIT_USAGE, "Unknown action id: %s" % aid)
    return acts[aid]


# ---------------------------------------------------------------- git helpers

def git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p


def git_out(repo: Path, *args: str) -> str:
    p = git(repo, *args)
    return p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else ""


def is_git(repo: Path) -> bool:
    return git(repo, "rev-parse", "--git-dir").returncode == 0


def branch_exists(repo: Path, name: str) -> bool:
    return git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/" + name).returncode == 0


def default_branch(repo: Path, cfg: Dict[str, Any]) -> str:
    configured = (cfg.get("site") or {}).get("default_branch")
    if configured and branch_exists(repo, configured):
        return configured
    return twwa_state.git_default_branch(repo) or "main"


# ---------------------------------------------------------------- artifacts and hash

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def collect_artifacts(state: Path, action: Dict[str, Any], cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(relative path, sha256) for every artifact: files under drafts/<id>/, the action's explicit
    artifacts, and files changed on the action branch (content taken from the branch)."""
    repo = st.repo_root(state)
    items: Dict[str, str] = {}
    aid = action["action_id"]
    ddir = state / "drafts" / aid
    if ddir.is_dir():
        for f in sorted(ddir.rglob("*")):
            if f.is_file():
                items[str(f.relative_to(repo)).replace(os.sep, "/")] = sha256_bytes(f.read_bytes())
    for rel in action.get("artifacts") or []:
        p = (repo / rel)
        items[rel.replace(os.sep, "/")] = sha256_bytes(p.read_bytes()) if p.is_file() else "MISSING"
    branch = action.get("branch") or ("twwa/%s" % aid)
    if is_git(repo) and branch_exists(repo, branch):
        base = default_branch(repo, cfg)
        names = git_out(repo, "diff", "--name-only", "%s...%s" % (base, branch)).splitlines()
        state_rel = os.path.relpath(str(state.resolve()), str(repo.resolve())).replace(os.sep, "/").rstrip("/") + "/"
        for n in names:
            n = n.strip()
            if not n or n.startswith(state_rel):
                continue  # the state folder is not site content; drafts are hashed above
            blob = git(repo, "show", "%s:%s" % (branch, n))
            items[n] = sha256_bytes(blob.stdout) if blob.returncode == 0 else "DELETED"
    return sorted(items.items())


def content_hash(artifacts: List[Tuple[str, str]]) -> str:
    lines = sorted("%s\t%s" % (p, h) for p, h in artifacts)
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def approvals_path(state: Path, aid: str) -> Path:
    return state / "approvals" / ("%s.json" % aid)


def load_approvals(state: Path, aid: str) -> Dict[str, Any]:
    return st.load_json(approvals_path(state, aid), {"action_id": aid, "records": []}) or {"action_id": aid, "records": []}


def required_roles(action: Dict[str, Any]) -> List[str]:
    return list(REQUIRED_ROLES.get(action.get("risk") or "R2", ["twwa", "owner"]))


def verify_action(state: Path, action: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    arts = collect_artifacts(state, action, cfg)
    now_hash = content_hash(arts) if arts else None
    recs = {r["role"]: r for r in load_approvals(state, action["action_id"]).get("records", [])}
    req = required_roles(action)
    problems: List[str] = []
    if not arts:
        problems.append("Keine Artefakte: eine leere Liste ist kein Freigabegegenstand.")
    missing = [r for r in req if r not in recs]
    if missing:
        problems.append("Fehlende Freigabe: %s" % ", ".join(missing))
    changed: List[str] = []
    for role in req:
        r = recs.get(role)
        if r and now_hash and r.get("content_hash") != now_hash:
            then = dict(r.get("artifacts") or [])
            nowd = dict(arts)
            changed = sorted({p for p in set(then) | set(nowd) if then.get(p) != nowd.get(p)})
            problems.append("Freigabe %s gilt nicht mehr: Inhalt nach der Freigabe geändert (%s)." % (role, ", ".join(changed) or "?"))
    if action.get("legal_text") and not cfg.get("legal", {}).get("signoff"):
        problems.append("Rechtstext ohne legal.signoff: nur nach rechtlicher Prüfung durch einen Menschen.")
    if action.get("state") in ("rejected", "superseded", "reverted"):
        problems.append("Aktion ist %s." % action["state"])
    return {"action_id": action["action_id"], "ok": not problems, "risk": action.get("risk"), "required_roles": req,
            "present_roles": sorted(recs), "content_hash": now_hash, "artifacts": [p for p, _ in arts],
            "changed": changed, "problems": problems, "human_only": action.get("risk") == "R3"}


# ---------------------------------------------------------------- caps

def _ts_hours_ago(ts: Optional[str]) -> Optional[float]:
    t = st.parse_ts(ts)
    if not t:
        return None
    now = st.parse_ts(st.now_iso())
    return (now - t).total_seconds() / 3600.0  # type: ignore[operator]


def check_caps(state: Path, cfg: Dict[str, Any], payload: Dict[str, Any], acts: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    aid = payload["action_id"]
    caps = cfg["caps"]
    open_props = [a for k, a in acts.items() if k != aid and a.get("state") == "proposed"]
    if len(open_props) >= int(caps["proposals_per_cycle"]):
        errs.append("Cap: already %d open proposals (caps.proposals_per_cycle = %s)." % (len(open_props), caps["proposals_per_cycle"]))
    if payload["type"] == "gbp_identity_edit":
        hours = float(cfg["gbp"]["pacing_hours"])
        for k, a in acts.items():
            if k == aid or a.get("type") != "gbp_identity_edit" or a.get("state") in ("rejected", "superseded"):
                continue
            last = max((e.get("ts") for e in a["events"]), default=None)
            ago = _ts_hours_ago(last)
            if ago is not None and ago < hours:
                errs.append("Cap: one identity-level GBP edit per %d h; %s was touched %.0f h ago." % (hours, k, ago))
    if payload["type"] in CONTENT_TYPES:
        cool = int(caps["page_cooldown_days"])
        for k, a in acts.items():
            if k == aid or a.get("type") not in CONTENT_TYPES:
                continue
            shared = set(a.get("pages_affected") or []) & set(payload.get("pages_affected") or [])
            if not shared:
                continue
            if a.get("state") in ("proposed", "approved"):
                errs.append("Cap: page %s already has open content action %s (one content edit per page per window)." % (", ".join(sorted(shared)), k))
            elif a.get("state") in ("shipped", "measured", "kept") and a.get("shipped_at"):
                ago = _ts_hours_ago(a["shipped_at"])
                if ago is not None and ago < cool * 24:
                    errs.append("Cap: page %s was edited by %s %.0f days ago (cooldown %d days)." % (", ".join(sorted(shared)), k, ago / 24, cool))
    if payload["type"] == "new_page":
        try:
            import page_gates
            ramp = page_gates.ramp_status(state, cfg, add=1)
            if not ramp["ok"]:
                errs.append("Cap (Gate G): %s" % ramp["reason_de"])
        except Exception as exc:  # pragma: no cover - surfaced as a cap error
            errs.append("Cap (Gate G) could not be evaluated: %s" % exc)
    cost = payload.get("cost_usd")
    if cost:
        ok, reason = spend.check(state, float(cost))
        if not ok:
            errs.append("Spend: " + reason)
    return errs


# ---------------------------------------------------------------- proposal document

def proposal_markdown(payload: Dict[str, Any], scope: Dict[str, Any], what_de: str, needs_de: str, belongs: str) -> str:
    lines = [
        "# Vorschlag: %s" % payload["title_de"],
        "",
        "Stand: %s. Aktion %s." % (st.today(), payload["action_id"]),
        "",
        "## Was",
        what_de or payload.get("expected") or payload["title_de"],
        "",
        "## Warum",
        payload.get("hypothesis") or "Begründung folgt aus der SERP-Analyse.",
    ]
    if payload.get("source_findings"):
        lines += ["", "Grundlage: " + ", ".join(payload["source_findings"]) + "."]
    if payload.get("queries_targeted"):
        lines += ["Suchanfragen: " + ", ".join("„%s“" % q for q in payload["queries_targeted"]) + "."]
    lines += [
        "",
        "## Was dafür nötig ist",
        needs_de or "Umfang und Zuarbeit stimmen wir gemeinsam ab.",
        "",
        "## Warum das nicht im aktuellen Website-Paket enthalten ist",
        scope.get("reason") or "",
        "Die Arbeit gehört zum Website-Paket %s. Unter dem aktuellen Paket wird sie nicht umgesetzt." % belongs,
        "",
        "## Nächster Schritt",
        "Wenn Sie das angehen möchten, besprechen wir den Umfang in einem eigenen Gespräch. Bis dahin bleibt die Website, wie sie ist.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- commands

def _payload_from_args(args: Any, cfg: Dict[str, Any], acts: Dict[str, Any]) -> Dict[str, Any]:
    base: Dict[str, Any] = {}
    if args.file:
        base = st.load_json(args.file, {}) or {}
    t = args.type or base.get("type")
    if t not in cli.ACTION_TYPES:
        cli.die(cli.EXIT_USAGE, "--type must be one of: %s" % ", ".join(cli.ACTION_TYPES))
    group, window, risk = cli.ACTION_TYPES[t]

    def pick(name: str, default: Any = None) -> Any:
        v = getattr(args, name, None)
        if v not in (None, [], ""):
            return v
        return base.get(name, default)

    p: Dict[str, Any] = {
        "action_id": pick("action_id") or None,
        "type": t,
        "title_de": pick("title_de"),
        "priority_group": int(pick("priority_group", group)),
        "risk": pick("risk", risk),
        "hypothesis": pick("hypothesis", ""),
        "primary_metric": pick("primary_metric", "gsc.clicks"),
        "secondary_metrics": pick("secondary_metrics", []),
        "window_days": int(pick("window_days", window)),
        "pages_affected": pick("pages_affected", []),
        "queries_targeted": pick("queries_targeted", []),
        "control_pages": pick("control_pages", []),
        "owner_effort_minutes": int(pick("owner_effort_minutes", 0)),
        "source_findings": pick("source_findings", []),
        "expected": pick("expected", ""),
        "baseline_snapshot": pick("baseline_snapshot"),
        "artifacts": pick("artifacts", []),
    }
    for extra in ("template", "cost_usd", "legal_text", "p1", "town", "service"):
        v = getattr(args, extra, None)
        if v not in (None, False, ""):
            p[extra] = v
        elif extra in base:
            p[extra] = base[extra]
    if not p["title_de"]:
        cli.die(cli.EXIT_USAGE, "--title-de is required")
    if p["risk"] not in REQUIRED_ROLES:
        cli.die(cli.EXIT_USAGE, "--risk must be R0, R1, R2 or R3")
    if p["baseline_snapshot"] is None:
        dates = st.snapshot_dates(args._state)
        p["baseline_snapshot"] = dates[-1] if dates else None
    return p


def _find_duplicate(acts: Dict[str, Any], p: Dict[str, Any]) -> Optional[str]:
    for k, a in acts.items():
        if a.get("state") not in OPEN_STATES:
            continue
        if a.get("type") == p["type"] and sorted(a.get("pages_affected") or []) == sorted(p["pages_affected"]) \
                and sorted(a.get("source_findings") or []) == sorted(p["source_findings"]) and a.get("title_de") == p["title_de"]:
            return k
    return None


def cmd_propose(args: Any) -> int:
    state = st.require_state(args)
    args._state = state
    st.require_not_stopped(state)
    cfg = st.load_config(state)
    acts = load_actions(state)
    p = _payload_from_args(args, cfg, acts)
    existing = p["action_id"] if p["action_id"] in acts else _find_duplicate(acts, p)
    if existing:
        cur = acts[existing]
        if cur.get("state") not in ("proposed", "blocked"):
            cli.die(cli.EXIT_BLOCKED, "Action %s is %s; it cannot be re-proposed. Supersede it and propose a new one." % (existing, cur.get("state")))
        p["action_id"] = existing
    if not p["action_id"]:
        p["action_id"] = next_action_id(acts, state=state)
    repo = st.repo_root(state)
    scope_info = twwa_state.read_scope(repo, cfg)
    sc = twwa_state.scope_check(scope_info, p["type"], bool(args.adds_page), args.adds_dependency or [], bool(args.adds_api_route))
    p["scope"] = {"in_scope": sc["in_scope"], "reason": sc["reason"], "tier": sc["tier"]}
    if not sc["in_scope"]:
        if not args.as_proposal:
            cli.emit({"ok": False, "blocked": "scope", "scope": sc}, args,
                     "Out of scope: %s\nUse --as-proposal to write it up for the owner (no implementation)." % sc["reason"])
            return cli.EXIT_BLOCKED
        belongs = "PREMIUM" if (sc["effective_tier"] == "basic" and not args.adds_page and not any(
            re.search(rx, d) for d in (args.adds_dependency or []) for rx in twwa_state.SCALE_DEP)) else "SCALE"
        slug = st.slugify(p["title_de"], 50)
        path = state / "proposals" / ("%s-%s.md" % (st.today(), slug))
        old = sorted((state / "proposals").glob("*-%s.md" % slug)) if (state / "proposals").is_dir() else []
        if old:
            path = old[-1]
        st_text = proposal_markdown(p, sc, args.what_de or "", args.needs_de or "", belongs)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(st_text, encoding="utf-8")
        if acts.get(p["action_id"], {}).get("state") != "blocked":
            log_event(state, p["action_id"], "proposed", **{k: v for k, v in p.items() if k != "action_id"})
            log_event(state, p["action_id"], "blocked", reason="scope", proposal=str(path.relative_to(state)))
        cli.emit({"ok": True, "action_id": p["action_id"], "state": "blocked", "reason": "scope", "proposal": str(path)}, args,
                 "Proposal written: %s (action %s blocked: scope)" % (path, p["action_id"]))
        return cli.EXIT_OK
    errs = check_caps(state, cfg, p, acts)
    if errs:
        cli.emit({"ok": False, "blocked": "caps", "errors": errs}, args, "Blocked:\n  " + "\n  ".join(errs))
        return cli.EXIT_BLOCKED
    ev = "updated" if existing else "proposed"
    if existing and all(acts[existing].get(k) == v for k, v in p.items() if k != "action_id"):
        cli.emit({"ok": True, "action_id": existing, "state": acts[existing]["state"], "unchanged": True}, args, "Unchanged: %s" % existing)
        return cli.EXIT_OK
    log_event(state, p["action_id"], ev, **{k: v for k, v in p.items() if k != "action_id"})
    if ev == "updated" and acts[existing].get("state") == "blocked":
        log_event(state, p["action_id"], "proposed", **{k: v for k, v in p.items() if k != "action_id"})
    cli.emit({"ok": True, "action_id": p["action_id"], "event": ev, "action": p}, args, "%s %s: %s" % (ev.capitalize(), p["action_id"], p["title_de"]))
    return cli.EXIT_OK


def cmd_list(args: Any) -> int:
    state = st.require_state(args)
    acts = load_actions(state)
    rows = [a for a in acts.values() if not args.filter or a.get("state") == args.filter]
    rows.sort(key=lambda a: a["action_id"])
    slim = [{k: a.get(k) for k in ("action_id", "state", "type", "risk", "priority_group", "title_de", "window_days", "shipped_at", "verdict")} for a in rows]
    human = "\n".join("%-12s %-10s %-18s %-3s %s" % (a["action_id"], a["state"], a["type"], a["risk"], a["title_de"]) for a in slim) or "No actions."
    cli.emit({"actions": slim}, args, human)
    return cli.EXIT_OK


def cmd_show(args: Any) -> int:
    state = st.require_state(args)
    a = get_action(state, args.action_id)
    a = dict(a)
    a["approvals"] = load_approvals(state, args.action_id).get("records", [])
    cli.emit(a, args)
    return cli.EXIT_OK


def cmd_approve(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    a = get_action(state, args.action_id)
    if a.get("state") in ("rejected", "superseded", "reverted", "blocked"):
        cli.die(cli.EXIT_BLOCKED, "Action %s is %s and cannot be approved." % (args.action_id, a.get("state")))
    if not args.by.strip() or not args.evidence.strip():
        cli.die(cli.EXIT_USAGE, "--by and --evidence are required: record who said yes and where (message id, PR URL, call note).")
    if args.role not in required_roles(a):
        cli.die(cli.EXIT_USAGE, "Role %s is not required for risk %s (required: %s)." % (args.role, a.get("risk"), ", ".join(required_roles(a)) or "none"))
    if args.artifact:
        new = [x for x in args.artifact if x not in a.get("artifacts", [])]
        if new:
            log_event(state, args.action_id, "artifacts", paths=new)
            a = get_action(state, args.action_id)
    arts = collect_artifacts(state, a, cfg)
    if not arts:
        cli.die(cli.EXIT_BLOCKED, "No artifacts for %s (drafts/%s/ is empty, no branch twwa/%s, no --artifact). Nothing to approve." % (args.action_id, args.action_id, args.action_id))
    h = content_hash(arts)
    repo = st.repo_root(state)
    head = git_out(repo, "rev-parse", "HEAD") if is_git(repo) else None
    rec = {"action_id": args.action_id, "role": args.role, "by": args.by.strip(), "at": st.now_iso(), "channel": args.channel,
           "evidence": args.evidence.strip(), "content_hash": h, "git_head": head or None, "preview_url": args.preview_url,
           "artifacts": [list(x) for x in arts]}
    data = load_approvals(state, args.action_id)
    data["records"] = [r for r in data.get("records", []) if r.get("role") != args.role] + [rec]
    st.save_json(approvals_path(state, args.action_id), data)
    log_event(state, args.action_id, "approval", role=args.role, by=rec["by"], channel=args.channel, content_hash=h)
    res = verify_action(state, get_action(state, args.action_id), cfg)
    if res["ok"] and a.get("state") != "approved":
        log_event(state, args.action_id, "approved", content_hash=h, roles=res["present_roles"])
    cli.emit({"ok": True, "record": rec, "verify": res}, args,
             "Approval recorded: %s by %s (%s), hash %s. %s" % (args.role, rec["by"], args.channel, h[:12],
                                                                "All required approvals present." if res["ok"] else "Still missing: " + "; ".join(res["problems"])))
    return cli.EXIT_OK


def cmd_verify(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    res = verify_action(state, get_action(state, args.action_id), cfg)
    human = ("VERIFY OK %s (hash %s)" % (args.action_id, (res["content_hash"] or "")[:12])) if res["ok"] else "VERIFY FAILED %s\n  %s" % (args.action_id, "\n  ".join(res["problems"]))
    if res["ok"] and res["human_only"]:
        human += "\nRisk R3: approvals are complete, but execution is by a human only."
    cli.emit(res, args, human)
    return cli.EXIT_OK if res["ok"] else cli.EXIT_BLOCKED


def autopilot_allows_merge(cfg: Dict[str, Any], risk: Optional[str]) -> bool:
    level = cfg["autopilot"]["level"]
    if risk == "R3":
        return False
    if level == "technical":
        return risk in ("R0", "R1")
    if level == "approved":
        return risk in ("R0", "R1", "R2")
    return False


def cmd_ship(args: Any) -> int:
    state = st.require_state(args)
    st.require_not_stopped(state)
    cfg = st.load_config(state)
    a = get_action(state, args.action_id)
    res = verify_action(state, a, cfg)
    if not res["ok"]:
        cli.emit(res, args, "Not shipped, approvals do not verify:\n  " + "\n  ".join(res["problems"]))
        return cli.EXIT_BLOCKED
    if a.get("risk") == "R3" and not args.by_human:
        cli.die(cli.EXIT_BLOCKED, "R3 actions are executed by a human only; log it with --by-human <name> after the person did it.")
    if args.merged_by == "agent" and not autopilot_allows_merge(cfg, a.get("risk")):
        cli.die(cli.EXIT_BLOCKED, "autopilot.level=%s does not allow the agent to merge a %s action." % (cfg["autopilot"]["level"], a.get("risk")))
    commits = args.commit or []
    if a.get("state") == "shipped" and set(commits) <= set(a.get("commits") or []):
        cli.emit({"ok": True, "action_id": args.action_id, "unchanged": True}, args, "Already shipped: %s" % args.action_id)
        return cli.EXIT_OK
    if not commits and a.get("type") not in ("gbp_post", "gbp_content_edit", "gbp_identity_edit", "review_reply", "citation", "offsite_mention", "review_engine"):
        cli.die(cli.EXIT_USAGE, "--commit <sha> is required for a site action (rollback reverts these commits).")
    dates = st.snapshot_dates(state)
    log_event(state, args.action_id, "shipped", commits=commits, branch=args.branch or a.get("branch") or "twwa/%s" % args.action_id,
              preview_url=args.preview_url, deploy_id=args.deploy_id, merged_by=args.by_human or args.merged_by,
              content_hash=res["content_hash"], baseline_snapshot=a.get("baseline_snapshot") or (dates[-1] if dates else None))
    cli.emit({"ok": True, "action_id": args.action_id, "commits": commits}, args,
             "Shipped %s. Next: python3 scripts/regression_guard.py verify --action %s, then indexnow.py submit." % (args.action_id, args.action_id))
    return cli.EXIT_OK


def cmd_measure(args: Any) -> int:
    state = st.require_state(args)
    a = get_action(state, args.action_id)
    if a.get("state") not in ("shipped", "measured"):
        cli.die(cli.EXIT_USAGE, "Action %s is %s; only shipped actions are measured." % (args.action_id, a.get("state")))
    data = json.loads(args.data) if args.data else {}
    log_event(state, args.action_id, "measured", verdict=args.verdict, confidence=args.confidence, data=data, text_de=args.text_de)
    cli.emit({"ok": True, "action_id": args.action_id, "verdict": args.verdict}, args, "Measured %s: %s" % (args.action_id, args.verdict))
    return cli.EXIT_OK


def cmd_close(args: Any) -> int:
    state = st.require_state(args)
    get_action(state, args.action_id)
    if not args.reason.strip():
        cli.die(cli.EXIT_USAGE, "--reason is required")
    log_event(state, args.action_id, args.outcome, reason=args.reason.strip(), by=args.by)
    cli.emit({"ok": True, "action_id": args.action_id, "state": args.outcome}, args, "%s -> %s" % (args.action_id, args.outcome))
    return cli.EXIT_OK


def due_actions(state: Path, cfg: Dict[str, Any], on: Optional[str] = None) -> List[Dict[str, Any]]:
    day = st.parse_date(on) if on else st.today_date()
    lag = int(cfg["thresholds"]["measure"]["gsc_lag_days"])
    out = []
    for a in load_actions(state).values():
        if a.get("state") != "shipped" or not a.get("shipped_at"):
            continue
        shipped = st.parse_date(a["shipped_at"])
        end = shipped + _dt.timedelta(days=int(a.get("window_days") or 28))  # type: ignore[operator]
        ready = end + _dt.timedelta(days=lag)
        out.append({"action_id": a["action_id"], "type": a.get("type"), "shipped": shipped.isoformat(), "window_end": end.isoformat(),
                    "evaluate_from": ready.isoformat(), "due": ready <= day, "days_left": (ready - day).days})  # type: ignore[operator]
    return sorted(out, key=lambda x: x["evaluate_from"])


def cmd_due(args: Any) -> int:
    state = st.require_state(args)
    rows = due_actions(state, st.load_config(state), args.date)
    if not args.all:
        rows = [r for r in rows if r["due"]]
    human = "\n".join("%s %s window ended %s -> %s" % (r["action_id"], r["type"], r["window_end"], "due" if r["due"] else "in %d days" % r["days_left"]) for r in rows) or "Nothing due."
    cli.emit({"due": rows}, args, human)
    return cli.EXIT_OK


def packet_text(state: Path, a: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    res = verify_action(state, a, cfg)
    pages = ", ".join("Startseite (/)" if p == "/" else p for p in a.get("pages_affected") or []) or "keine Website-Seite (Profil oder Entwurf)"
    controls = ("den Vergleichsseiten " + ", ".join(a["control_pages"])) if a.get("control_pages") else "den übrigen, unveränderten Suchanfragen der Website"
    metric = METRIC_DE.get(a.get("primary_metric") or "", a.get("primary_metric") or "Anfragen")
    prev = a.get("preview_url") or next((r.get("preview_url") for r in load_approvals(state, a["action_id"]).get("records", []) if r.get("preview_url")), None)
    lines = [
        "# Freigabe: %s" % a.get("title_de"),
        "",
        "Aktion %s, Stand %s." % (a["action_id"], st.today()),
        "",
        "## Was sich ändert",
        a.get("expected") or a.get("title_de") or "",
        "",
        "Betroffen: %s." % pages,
        "",
        "## Warum",
        a.get("hypothesis") or "Begründung siehe Analyse.",
        "",
        "## Woran wir den Erfolg messen",
        "Hauptkennzahl: %s. Wir werten %d Tage nach der Veröffentlichung aus und vergleichen mit %s." % (metric, int(a.get("window_days") or 28), controls),
        "",
        "## Art der Änderung",
        "%s: %s." % (a.get("risk"), RISK_DE.get(a.get("risk") or "", "")),
        "",
        "## Vorschau",
        prev or "Der Vorschau-Link wird nachgereicht, bevor Sie freigeben.",
        "",
        "## Freigegebener Inhalt",
    ]
    if res["artifacts"]:
        lines.append("Prüfsumme %s über %d Datei(en). Jede spätere Änderung macht die Freigabe ungültig; dann fragen wir neu." % ((res["content_hash"] or "")[:12], len(res["artifacts"])))
        lines += ["- %s" % p for p in res["artifacts"]]
    else:
        lines.append("Noch keine Inhalte hinterlegt. Ohne Inhalt gibt es nichts freizugeben.")
    lines += [
        "",
        "## Ihr Aufwand",
        "Etwa %d Minuten." % int(a.get("owner_effort_minutes") or 5),
        "",
        "## So geben Sie frei",
        "Antworten Sie auf diese Nachricht mit „Ja, freigegeben“ oder schreiben Sie, was geändert werden soll. Ohne Ihre Antwort wird nichts veröffentlicht.",
        "",
    ]
    if a.get("risk") == "R3":
        lines.insert(-1, "Diese Änderung setzt ein Mensch von Hand um, nie ein Programm.")
    return "\n".join(lines)


def cmd_packet(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    a = get_action(state, args.action_id)
    text = packet_text(state, a, cfg)
    out = Path(args.out) if args.out else state / "out" / "packets" / ("%s.md" % args.action_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    cli.emit({"ok": True, "action_id": args.action_id, "path": str(out), "text": text}, args, text + "\n(written to %s)" % out)
    return cli.EXIT_OK


def cmd_stop(args: Any) -> int:
    state = st.require_state(args)
    if not args.reason.strip():
        cli.die(cli.EXIT_USAGE, "--reason is required")
    (state / "STOP").write_text(json.dumps({"reason": args.reason.strip(), "by": args.by, "at": st.now_iso()}, ensure_ascii=False) + "\n", encoding="utf-8")
    log_event(state, "-", "stop", reason=args.reason.strip(), by=args.by)
    cli.emit({"ok": True, "stop": True}, args, "STOP set. Nothing ships and nothing spends until: twwa_actions.py resume --by <name> --reason <text>")
    return cli.EXIT_OK


def cmd_resume(args: Any) -> int:
    state = st.require_state(args)
    if not args.by.strip() or not args.reason.strip():
        cli.die(cli.EXIT_USAGE, "--by and --reason are required")
    p = state / "STOP"
    was = p.exists()
    if was:
        p.unlink()
    log_event(state, "-", "resume", reason=args.reason.strip(), by=args.by.strip(), was_stopped=was)
    cli.emit({"ok": True, "stop": False, "was_stopped": was}, args, "STOP removed." if was else "STOP was not set.")
    return cli.EXIT_OK


def action_commits(repo: Path, a: Dict[str, Any]) -> List[str]:
    commits = list(a.get("commits") or [])
    if not commits:
        aid = a["action_id"]
        out = git_out(repo, "log", "--all", "--format=%H", "--fixed-strings", "--grep=[twwa:%s]" % aid)
        out2 = git_out(repo, "log", "--all", "--format=%H", "--fixed-strings", "--grep=Twwa-Action: %s" % aid)
        commits = [c for c in (out + "\n" + out2).split() if c]
    full = []
    for c in commits:
        sha = git_out(repo, "rev-parse", "--verify", "--quiet", c + "^{commit}")
        if sha and sha not in full:
            full.append(sha)
    if not full:
        return []
    ordered = git_out(repo, "log", "--no-walk=sorted", "--format=%H", *full).split()
    return ordered or full


def cmd_rollback(args: Any) -> int:
    state = st.require_state(args)
    st.require_not_stopped(state)
    cfg = st.load_config(state)
    a = get_action(state, args.action_id)
    repo = Path(args.repo).resolve() if args.repo else st.repo_root(state)
    if not is_git(repo):
        cli.die(cli.EXIT_USAGE, "Not a git repository: %s" % repo)
    base = default_branch(repo, cfg)
    branch = "twwa/rollback-%s" % args.action_id
    merge_cmd = "git checkout %s && git merge --no-ff %s" % (base, branch)
    if branch_exists(repo, branch):
        cli.emit({"ok": True, "branch": branch, "existing": True, "merge_command": merge_cmd}, args,
                 "Rollback branch already exists: %s\nMerge with: %s\nPushing is a separate, explicit step." % (branch, merge_cmd))
        return cli.EXIT_OK
    commits = action_commits(repo, a)
    if not commits:
        cli.die(cli.EXIT_USAGE, "No commits recorded for %s (shipped event or [twwa:%s] in a commit message)." % (args.action_id, args.action_id))
    tmp = Path(tempfile.mkdtemp(prefix="twwa-rollback-"))
    wt = tmp / "wt"
    p = git(repo, "worktree", "add", "-b", branch, str(wt), base)
    if p.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        cli.die(cli.EXIT_FAIL, "Could not create %s: %s" % (branch, p.stderr.decode("utf-8", "replace").strip()))
    reverted: List[str] = []
    gate: Dict[str, Any] = {"ran": False}
    try:
        for c in commits:
            parents = git_out(repo, "rev-list", "--parents", "-n", "1", c).split()
            cmd = ["revert", "--no-edit"] + (["-m", "1"] if len(parents) > 2 else []) + [c]
            r = git(wt, *cmd)
            if r.returncode != 0:
                git(wt, "revert", "--abort")
                raise RuntimeError("git revert %s failed: %s" % (c[:10], (r.stderr or r.stdout).decode("utf-8", "replace").strip()[:400]))
            reverted.append(c)
        if args.build:
            b = subprocess.run(args.build, shell=True, cwd=str(wt), capture_output=True)
            gate = {"ran": True, "build_exit": b.returncode}
            dist = wt / (cfg["site"].get("dist_dir") or "dist")
            if b.returncode == 0 and dist.is_dir():
                audit = subprocess.run([sys.executable, str(Path(__file__).with_name("site_audit.py")), "dist", str(dist), "--fail-on", "P1",
                                        "--state", str(state), "--json"], capture_output=True)
                gate["site_audit_exit"] = audit.returncode
            gate["ok"] = b.returncode == 0 and gate.get("site_audit_exit", 0) == 0
        head = git_out(wt, "rev-parse", "HEAD")
    except RuntimeError as exc:
        git(repo, "worktree", "remove", "--force", str(wt))
        git(repo, "branch", "-D", branch)
        shutil.rmtree(tmp, ignore_errors=True)
        cli.die(cli.EXIT_FAIL, "Rollback not prepared: %s" % exc)
    git(repo, "worktree", "remove", "--force", str(wt))
    shutil.rmtree(tmp, ignore_errors=True)
    log_event(state, args.action_id, "rollback_prepared", branch=branch, reverted=reverted, head=head, gates=gate)
    merged = False
    if args.merge:
        if gate.get("ran") and not gate.get("ok"):
            cli.die(cli.EXIT_FAIL, "Gates failed on %s; not merging." % branch)
        if not autopilot_allows_merge(cfg, a.get("risk")):
            cli.die(cli.EXIT_BLOCKED, "autopilot.level=%s does not allow a local merge of a %s rollback. Merge by hand: %s" % (cfg["autopilot"]["level"], a.get("risk"), merge_cmd))
        cur = git_out(repo, "rev-parse", "--abbrev-ref", "HEAD")
        dirty = git_out(repo, "status", "--porcelain", "--untracked-files=no")
        if cur != base or dirty:
            cli.die(cli.EXIT_BLOCKED, "Local merge needs a clean checkout of %s (now on %s%s). Merge by hand: %s" % (base, cur, ", dirty" if dirty else "", merge_cmd))
        m = git(repo, "merge", "--no-ff", "--no-edit", branch)
        if m.returncode != 0:
            git(repo, "merge", "--abort")
            cli.die(cli.EXIT_FAIL, "Merge failed: %s" % m.stderr.decode("utf-8", "replace").strip())
        merged = True
        log_event(state, args.action_id, "rollback_merged", branch=branch, into=base)
    nxt = "Pushing is a separate, explicit step. After the deploy: regression_guard.py verify --action %s, then twwa_actions.py close %s --outcome reverted --reason <text>." % (args.action_id, args.action_id)
    human = "Rollback branch %s created from %s, reverted %d commit(s).\n%s%s" % (
        branch, base, len(reverted), "" if merged else "Merge with: %s\n" % merge_cmd, nxt)
    if not gate.get("ran"):
        human += "\nGates not run (no --build). Build the branch and run: site_audit.py dist dist --fail-on P1"
    cli.emit({"ok": True, "branch": branch, "base": base, "reverted": reverted, "head": head, "gates": gate, "merged": merged,
              "merge_command": merge_cmd}, args, human)
    return cli.EXIT_OK


def build_parser() -> Any:
    p = cli.base_parser(
        "Action log for twwa-growth (.twwa-growth/actions.jsonl): propose with caps and scope check, list, show, approve "
        "(hash over the exact artifacts), verify, ship, measure, close, due windows, the German approval packet, "
        "STOP and resume, and rollback on a git branch (never pushes).",
        "example:\n  python3 scripts/twwa_actions.py propose --type onpage_rewrite --title-de \"Title mit Ort\" --pages / --hypothesis \"...\"\n"
        "  python3 scripts/twwa_actions.py approve 2026-11-a01 --role owner --by \"Max Mustermann\" --channel whatsapp --evidence \"Nachricht 2026-11-18 09:12\"\n"
        "  python3 scripts/twwa_actions.py verify 2026-11-a01 --json",
    )
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "propose", "propose an action (exit 4 on STOP, caps, spend or scope; --as-proposal writes an offer instead)")
    sp.add_argument("--file", help="JSON payload (section 4.4); flags override it")
    sp.add_argument("--action-id", dest="action_id")
    sp.add_argument("--type")
    sp.add_argument("--title-de", dest="title_de")
    sp.add_argument("--priority-group", dest="priority_group", type=int)
    sp.add_argument("--risk", choices=sorted(REQUIRED_ROLES))
    sp.add_argument("--hypothesis")
    sp.add_argument("--metric", dest="primary_metric")
    sp.add_argument("--secondary", dest="secondary_metrics", action="append", default=[])
    sp.add_argument("--window", dest="window_days", type=int)
    sp.add_argument("--pages", dest="pages_affected", action="append", default=[])
    sp.add_argument("--queries", dest="queries_targeted", action="append", default=[])
    sp.add_argument("--controls", dest="control_pages", action="append", default=[])
    sp.add_argument("--effort-minutes", dest="owner_effort_minutes", type=int)
    sp.add_argument("--findings", dest="source_findings", action="append", default=[])
    sp.add_argument("--expected")
    sp.add_argument("--baseline", dest="baseline_snapshot")
    sp.add_argument("--artifact", dest="artifacts", action="append", default=[], help="repo-relative file that is part of the approved content")
    sp.add_argument("--template", help="page template id (Gate G pilot)")
    sp.add_argument("--town")
    sp.add_argument("--service")
    sp.add_argument("--cost-usd", dest="cost_usd", type=float)
    sp.add_argument("--legal-text", dest="legal_text", action="store_true", help="the action changes legal text (needs legal.signoff)")
    sp.add_argument("--p1", action="store_true", help="fixes a P1 finding")
    sp.add_argument("--adds-page", action="store_true")
    sp.add_argument("--adds-dependency", action="append", default=[])
    sp.add_argument("--adds-api-route", action="store_true")
    sp.add_argument("--as-proposal", action="store_true", help="out of scope: write proposals/<date>-<slug>.md and a blocked action")
    sp.add_argument("--what-de", help="proposal: what would be done (German)")
    sp.add_argument("--needs-de", help="proposal: what it needs (German)")
    sp = cli.add_sub(subs, "list", "list actions with their current state")
    sp.add_argument("--filter", choices=STATE_EVENTS)
    sp = cli.add_sub(subs, "show", "show one action with events and approvals")
    sp.add_argument("action_id")
    sp = cli.add_sub(subs, "approve", "record an approval bound to the content hash of the action's artifacts")
    sp.add_argument("action_id")
    sp.add_argument("--role", required=True, choices=("twwa", "owner"))
    sp.add_argument("--by", required=True)
    sp.add_argument("--channel", required=True, choices=CHANNELS)
    sp.add_argument("--evidence", required=True, help="where the yes was given (PR URL, message reference, call note)")
    sp.add_argument("--preview-url", dest="preview_url")
    sp.add_argument("--artifact", action="append", default=[], help="add a repo-relative artifact before hashing")
    sp = cli.add_sub(subs, "verify", "recompute the hash; exit 4 if a required approval is missing or an artifact changed")
    sp.add_argument("action_id")
    sp = cli.add_sub(subs, "ship", "log a shipped action after verify passes (exit 4 otherwise)")
    sp.add_argument("action_id")
    sp.add_argument("--commit", action="append", default=[])
    sp.add_argument("--branch")
    sp.add_argument("--preview-url", dest="preview_url")
    sp.add_argument("--deploy-id", dest="deploy_id")
    sp.add_argument("--merged-by", dest="merged_by", choices=("human", "agent"), default="human")
    sp.add_argument("--by-human", dest="by_human", help="R3: name of the person who executed it")
    sp = cli.add_sub(subs, "measure", "log a verdict for a shipped action")
    sp.add_argument("action_id")
    sp.add_argument("--verdict", required=True, choices=("win", "neutral", "loss", "inconclusive"))
    sp.add_argument("--confidence", choices=("low", "medium", "high"), default="low")
    sp.add_argument("--data", help="JSON with the numbers")
    sp.add_argument("--text-de", dest="text_de", default="")
    sp = cli.add_sub(subs, "close", "close an action: kept, reverted, rejected, superseded or blocked")
    sp.add_argument("action_id")
    sp.add_argument("--outcome", required=True, choices=("kept", "reverted", "rejected", "superseded", "blocked"))
    sp.add_argument("--reason", required=True)
    sp.add_argument("--by", default=None)
    sp = cli.add_sub(subs, "due", "shipped actions whose measurement window has ended (GSC lag included)")
    sp.add_argument("--date", help="evaluate as of yyyy-mm-dd")
    sp.add_argument("--all", action="store_true", help="also list actions not yet due")
    sp = cli.add_sub(subs, "packet", "write the German approval summary for the owner to out/packets/<id>.md")
    sp.add_argument("action_id")
    sp.add_argument("--out")
    sp = cli.add_sub(subs, "stop", "set STOP: nothing ships and nothing spends")
    sp.add_argument("--reason", required=True)
    sp.add_argument("--by", default=None)
    sp = cli.add_sub(subs, "resume", "remove STOP and log who and why")
    sp.add_argument("--by", required=True)
    sp.add_argument("--reason", required=True)
    sp = cli.add_sub(subs, "rollback", "create twwa/rollback-<id> from the default branch and revert the action's commits (never pushes)")
    sp.add_argument("action_id")
    sp.add_argument("--repo", help="git repo (default: parent of the state folder)")
    sp.add_argument("--build", help="build command to run on the rollback branch before the gates, e.g. 'npm run build'")
    sp.add_argument("--merge", action="store_true", help="merge locally when the autopilot level allows it")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    handler = {"propose": cmd_propose, "list": cmd_list, "show": cmd_show, "approve": cmd_approve, "verify": cmd_verify,
               "ship": cmd_ship, "measure": cmd_measure, "close": cmd_close, "due": cmd_due, "packet": cmd_packet,
               "stop": cmd_stop, "resume": cmd_resume, "rollback": cmd_rollback}[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
