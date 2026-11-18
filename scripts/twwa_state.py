#!/usr/bin/env python3
"""State folder lifecycle for twwa-growth: init, status, doctor, scope, detect, conflicts, validate."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, state as st, textde  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_STATE = PLUGIN_ROOT / "templates" / "state"
TIERS = ("basic", "premium", "scale", "unknown")
VERTICALS = ("handwerk", "steuerberater", "finanzberatung", "ingenieure", "hausverwaltung", "spedition", "fahrschule", "restaurant", "other")
SCOPE_NAMES = ("scope.md", "SCOPE.md", "TIER-SCOPE.md", "TWWA-SCOPE.md")
APPROVED_LINE = re.compile(r"^\s*-\s*APPROVED:\s*(\S+)\s*(.*)$", re.IGNORECASE | re.MULTILINE)
TIER_WORD = re.compile(r"\b(basic|premium|scale)\b", re.IGNORECASE)
FORBIDDEN_DIRS = {"pages", "app", "routes"}

# Package name patterns the tier guard treats as Scale-level (commerce, data stores, server frameworks,
# auth, CMS, i18n) and as 3D/WebGL. Restated for the scope check; the guard itself stays authoritative.
SCALE_DEP = [r"^stripe$", r"^@stripe/", r"^@shopify/", r"^@medusajs/", r"^snipcart", r"^@lemonsqueezy/", r"^@paddle/",
             r"^prisma$", r"^@prisma/", r"^drizzle-orm$", r"^mongoose$", r"^mongodb$", r"^pg$", r"^mysql2$", r"^sequelize$",
             r"^typeorm$", r"^@supabase/", r"^firebase(-admin)?$", r"^@planetscale/", r"^@neondatabase/", r"^@vercel/(postgres|kv)$",
             r"^i?oredis$", r"^redis$", r"^express$", r"^fastify$", r"^koa$", r"^@nestjs/", r"^hono$", r"^next-auth$", r"^@auth/",
             r"^@clerk/", r"^lucia$", r"^better-auth$", r"^sanity$", r"^@sanity/", r"^contentful$", r"^@contentful/", r"^@storyblok/",
             r"^@strapi/", r"^payload$", r"^@payloadcms/", r"^@directus/", r"^tinacms$", r"^@builder\.io/", r"^@prismicio/",
             r"^@keystatic/", r"^decap-cms", r"^next-intl$", r"^i18next$", r"^react-i18next$", r"^react-intl$", r"^@formatjs/",
             r"^@lingui/", r"^astro-i18next$", r"^@inlang/"]
WEBGL_DEP = [r"^three$", r"^@react-three/", r"^ogl$", r"^pixi\.js$", r"^@pixi/", r"^babylonjs$", r"^@babylonjs/", r"^@splinetool/",
             r"^regl$", r"^playcanvas$", r"^aframe$", r"^@theatre/", r"^postprocessing$"]
LEGAL_ROUTES = re.compile(r"^(impressum|imprint|datenschutz|datenschutzerklaerung|privacy(-policy)?|legal|agb|404|500)$", re.IGNORECASE)


# ---------------------------------------------------------------- scope

def find_scope_file(repo: Path, configured: Optional[str] = None) -> Optional[Path]:
    if configured:
        p = (repo / configured) if not os.path.isabs(configured) else Path(configured)
        if p.is_file():
            return p
    for n in SCOPE_NAMES:
        if (repo / n).is_file():
            return repo / n
    for p in sorted(repo.glob("*.md")):
        tier, _ = tier_from_heading(p.read_text(encoding="utf-8", errors="replace"))
        if tier:
            return p
    return None


def tier_from_heading(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Tier named in the first Markdown heading, plus the heading itself."""
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            m = TIER_WORD.search(line)
            return (m.group(1).lower() if m else None), line.strip()
    return None, None


def parse_scope_text(text: str) -> Dict[str, Any]:
    """Read tier and the owner's exception lines from scope-file text. Never writes anything."""
    tier, heading = tier_from_heading(text)
    exceptions = []
    for m in APPROVED_LINE.finditer(text):
        exceptions.append({"name": m.group(1).strip().rstrip(",;:").lower(), "note": m.group(2).strip()})
    return {"tier": tier or "unknown", "heading": heading, "exceptions": exceptions}


def read_scope(repo: Path, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or {}
    sf = find_scope_file(repo, cfg.get("scope_file"))
    if not sf:
        tier = cfg.get("tier") if cfg.get("tier") in TIERS else "unknown"
        return {"scope_file": None, "tier": tier, "heading": None, "exceptions": [], "tier_source": "config" if tier != "unknown" else "none"}
    info = parse_scope_text(sf.read_text(encoding="utf-8", errors="replace"))
    info["scope_file"] = str(sf.relative_to(repo)) if str(sf).startswith(str(repo)) else str(sf)
    info["tier_source"] = "scope_file"
    if info["tier"] == "unknown" and cfg.get("tier") in TIERS:
        info["tier"], info["tier_source"] = cfg["tier"], "config"
    return info


def scope_check(scope: Dict[str, Any], action_type: Optional[str], adds_page: bool = False,
                adds_dependency: Optional[List[str]] = None, adds_api_route: bool = False) -> Dict[str, Any]:
    """Answer whether an action fits the tier (spec 5.1). Unknown tier is treated as premium."""
    tier = scope.get("tier") or "unknown"
    eff = "premium" if tier == "unknown" else tier
    approved = {e["name"] for e in scope.get("exceptions", [])}
    reasons: List[str] = []
    used: List[str] = []
    if action_type == "new_page":
        adds_page = True
    if adds_page:
        if eff in ("basic", "premium"):
            if "pages" in approved or "page" in approved:
                used.append("pages")
            else:
                reasons.append("Neue Seiten sind im Tarif %s nicht enthalten (nur Landingpage, Impressum, Datenschutz, 404)." % eff.upper())
    if adds_api_route:
        if eff == "basic":
            if "api" in approved:
                used.append("api")
            else:
                reasons.append("Neue Server-Routen sind im Tarif BASIC nicht enthalten.")
        elif eff == "premium":
            if "api" in approved:
                used.append("api")
            else:
                reasons.append("Im Tarif PREMIUM ist nur der bestehende Formular-Handler erlaubt, keine weitere Server-Route.")
    for dep in adds_dependency or []:
        d = dep.strip()
        if any(re.search(rx, d) for rx in SCALE_DEP) and eff != "scale":
            if d.lower() in approved:
                used.append(d.lower())
            else:
                reasons.append("Abhängigkeit %s gehört zu Scale (Shop, Datenbank, Login, CMS oder Mehrsprachigkeit)." % d)
        elif eff == "basic" and any(re.search(rx, d) for rx in WEBGL_DEP):
            if d.lower() in approved:
                used.append(d.lower())
            else:
                reasons.append("Abhängigkeit %s ist 3D/WebGL und erst ab PREMIUM enthalten." % d)
    in_scope = not reasons
    out = {"tier": tier, "effective_tier": eff, "in_scope": in_scope, "action_type": action_type,
           "reasons": reasons, "exceptions_used": used,
           "reason": "; ".join(reasons) if reasons else "Im Rahmen des Tarifs %s." % eff.upper()}
    if tier == "unknown":
        out["note"] = "Tarif unbekannt: wie PREMIUM behandelt. TWWA sollte den Tarif in der Scope-Datei oder config.tier festlegen."
    return out


# ---------------------------------------------------------------- detect

def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_repo(repo: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"repo": str(repo)}
    astro = next((repo / n for n in ("astro.config.mjs", "astro.config.ts", "astro.config.js", "astro.config.cjs") if (repo / n).is_file()), None)
    a: Dict[str, Any] = {"file": None}
    if astro:
        t = _read(astro)
        a["file"] = astro.name
        m = re.search(r"\bsite\s*:\s*['\"]([^'\"]+)['\"]", t)
        a["site"] = m.group(1).rstrip("/") if m else None
        m = re.search(r"\btrailingSlash\s*:\s*['\"](never|always|ignore)['\"]", t)
        a["trailingSlash"] = m.group(1) if m else None
        m = re.search(r"\bformat\s*:\s*['\"](file|directory|preserve)['\"]", t)
        a["build_format"] = m.group(1) if m else None
        m = re.search(r"\boutput\s*:\s*['\"](static|server|hybrid)['\"]", t)
        a["output"] = m.group(1) if m else None
        a["sitemap_integration"] = "@astrojs/sitemap" in t
        a["i18n"] = bool(re.search(r"\bi18n\b", t))
    out["astro"] = a
    v: Dict[str, Any] = {"file": None}
    vp = repo / "vercel.json"
    if vp.is_file():
        try:
            vj = st.load_json(vp, {}) or {}
        except Exception as exc:  # invalid JSON is itself a finding for the audit
            vj = {}
            v["error"] = str(exc)
        v.update({"file": "vercel.json", "cleanUrls": vj.get("cleanUrls"), "trailingSlash": vj.get("trailingSlash"),
                  "redirects": len(vj.get("redirects") or []), "bulkRedirectsPath": vj.get("bulkRedirectsPath")})
        hosts = []
        for h in vj.get("headers") or []:
            if any(x.get("key", "").lower() == "x-robots-tag" and "noindex" in str(x.get("value", "")).lower() for x in h.get("headers") or []):
                for cond in h.get("has") or []:
                    if cond.get("type") == "host":
                        hosts.append(cond.get("value"))
        v["noindex_hosts"] = hosts
    out["vercel"] = v
    handlers = [str(p.relative_to(repo)) for pat in ("api/*.js", "api/*.ts", "api/*.mjs", "src/pages/api/*.js", "src/pages/api/*.ts") for p in sorted(repo.glob(pat))]
    out["form_handlers"] = handlers
    sc = read_scope(repo, {})
    out["scope_file"], out["tier"], out["scope_exceptions"] = sc["scope_file"], sc["tier"], len(sc["exceptions"])
    guards = [repo / "check-tier.mjs", Path.home() / ".claude/skills/twwa-basic/check-tier.mjs", Path.home() / ".claude/skills/twwa-premium/check-tier.mjs"]
    out["tier_guard"] = next((str(g) for g in guards if g.is_file()), None)
    pkg = st.load_json(repo / "package.json", {}) or {}
    out["dependencies"] = sorted({**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}.keys())
    out["git"] = (repo / ".git").exists()
    out["default_branch"] = git_default_branch(repo) if out["git"] else None
    pages_dir = repo / "src" / "pages"
    routes = []
    if pages_dir.is_dir():
        for p in sorted(pages_dir.rglob("*")):
            if p.suffix in (".astro", ".md", ".mdx") and "api" not in p.relative_to(pages_dir).parts:
                r = "/" + str(p.relative_to(pages_dir).with_suffix("")).replace(os.sep, "/")
                routes.append(re.sub(r"/index$", "/", r) or "/")
    out["routes"] = routes
    out["content_routes"] = [r for r in routes if r != "/" and not LEGAL_ROUTES.match(r.strip("/").split("/")[-1])]
    return out


def git_default_branch(repo: Path) -> Optional[str]:
    def run(*a: str) -> str:
        p = subprocess.run(["git", "-C", str(repo)] + list(a), capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else ""
    ref = run("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if ref:
        return ref.rsplit("/", 1)[-1]
    for b in ("main", "master"):
        if run("rev-parse", "--verify", "--quiet", "refs/heads/" + b):
            return b
    return run("rev-parse", "--abbrev-ref", "HEAD") or None


# ---------------------------------------------------------------- doctor

def doctor_checks(state: Path) -> List[Dict[str, Any]]:
    """Spec 4.1: no .html outside out/, no pages/app/routes folders, no '- APPROVED:' lines. Plus hygiene."""
    problems: List[Dict[str, Any]] = []
    for root, dirs, files in os.walk(state):
        rel_root = Path(root).relative_to(state)
        parts = rel_root.parts
        if parts and parts[0] == "out":
            dirs[:] = []
            continue
        for d in list(dirs):
            if d.lower() in FORBIDDEN_DIRS:
                problems.append({"check": "forbidden_dir", "path": str(rel_root / d),
                                 "message": "Folder named %r inside the state folder; the tier guard would read it as routes." % d})
        for f in files:
            rel = rel_root / f
            if f.lower().endswith((".html", ".htm")):
                problems.append({"check": "html_outside_out", "path": str(rel),
                                 "message": "HTML file outside out/; the tier guard would count it as a page."})
            p = Path(root) / f
            try:
                if p.stat().st_size > 5_000_000:
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if APPROVED_LINE.match(line):
                    problems.append({"check": "approved_line", "path": str(rel), "line": n,
                                     "message": "Line starting with '- APPROVED:' found; only the agency owner writes those, in the scope file."})
            if re.search(r"(?i)(api[_-]?key|secret|refresh_token|private_key)\"?\s*[:=]\s*\"?[A-Za-z0-9_\-]{20,}", text):
                problems.append({"check": "secret_like", "path": str(rel), "message": "Looks like a credential; secrets never go into the state folder."})
    gi = state / ".gitignore"
    if not gi.is_file() or not re.search(r"(?m)^/?out/?\s*$", _read(gi)):
        problems.append({"check": "gitignore_out", "path": ".gitignore", "message": "out/ is not git-ignored inside the state folder."})
    return problems


# ---------------------------------------------------------------- validate

def validate_business(b: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(b, dict):
        return ["business.json is not an object"]
    if b.get("schema_version") != 1:
        errs.append("schema_version must be 1")
    for k in ("name", "address", "phone", "url", "services", "service_area", "hours"):
        if k not in b:
            errs.append("missing key: %s" % k)
    if b.get("vertical") is not None and b.get("vertical") not in VERTICALS:
        errs.append("vertical %r not in %s" % (b.get("vertical"), ", ".join(VERTICALS)))
    if b.get("phone") and not re.match(r"^\+\d{6,15}$", textde.norm_phone(b["phone"])):
        errs.append("phone is not a valid number: %r" % b["phone"])
    if b.get("url") and not re.match(r"^https://", str(b["url"])):
        errs.append("url must start with https://")
    addr = b.get("address") or {}
    if addr.get("zip") and not re.match(r"^\d{5}$", str(addr["zip"])):
        errs.append("address.zip must have 5 digits")
    ids = [s.get("id") for s in b.get("services") or []]
    if len(ids) != len(set(ids)):
        errs.append("services[].id must be unique")
    for s in b.get("services") or []:
        if not s.get("id") or not s.get("name"):
            errs.append("every service needs id and name")
        pr = s.get("price") or {}
        if any(pr.get(k) is not None for k in ("min", "typical_min", "typical_max")) and not pr.get("confirmed_by"):
            errs.append("service %s: price values without price.confirmed_by" % s.get("id"))
    towns = [t.get("town") for t in b.get("service_area") or []]
    if len(towns) != len(set(towns)):
        errs.append("service_area towns must be unique")
    for t in b.get("service_area") or []:
        dm = t.get("drive_minutes")
        if dm is not None and (not isinstance(dm, (int, float)) or dm < 0):
            errs.append("service_area %s: drive_minutes must be a number >= 0" % t.get("town"))
    for h in b.get("hours") or []:
        if not re.match(r"^\d{2}:\d{2}$", str(h.get("open", ""))) or not re.match(r"^\d{2}:\d{2}$", str(h.get("close", ""))):
            errs.append("hours entries need open and close as HH:MM")
    if b.get("geo") and b["geo"].get("lat") is not None:
        if not (-90 <= float(b["geo"]["lat"]) <= 90 and -180 <= float(b["geo"]["lng"]) <= 180):
            errs.append("geo out of range")
    return errs


def validate_config(c: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if c.get("tier") not in TIERS:
        errs.append("tier must be one of %s" % ", ".join(TIERS))
    if c.get("autopilot", {}).get("level") not in ("off", "technical", "approved"):
        errs.append("autopilot.level must be off, technical or approved")
    if c.get("gbp", {}).get("mode") not in ("auto", "api", "manual", "off"):
        errs.append("gbp.mode must be auto, api, manual or off")
    if c.get("gbp", {}).get("writes") not in ("approved", "off"):
        errs.append("gbp.writes must be approved or off")
    if c.get("data", {}).get("pii") != "never":
        errs.append("data.pii must stay 'never'")
    if c.get("outreach", {}).get("send_mode") != "draft_only":
        errs.append("outreach.send_mode must stay 'draft_only' (no automated sending exists)")
    if c.get("guarantee", {}).get("mode") not in ("none", "exit_clause"):
        errs.append("guarantee.mode must be none or exit_clause")
    if c.get("call_tracking", {}).get("mode") not in ("none", "static"):
        errs.append("call_tracking.mode must be none or static (DNI is not implemented)")
    if c.get("ai_bots", {}).get("training") not in ("no_change", "allow", "block"):
        errs.append("ai_bots.training must be no_change, allow or block")
    try:
        if float(c.get("spend", {}).get("monthly_cap_usd", 0)) < 0:
            errs.append("spend.monthly_cap_usd must be >= 0")
    except (TypeError, ValueError):
        errs.append("spend.monthly_cap_usd must be a number")
    flat = json_keys(c)
    for bad in ("price", "pricing", "package", "packaging", "tariff_price"):
        if any(k.split(".")[-1] == bad for k in flat):
            errs.append("config must not contain pricing or packaging keys (%s)" % bad)
    for o in c.get("thresholds", {}).get("overrides") or []:
        if not o.get("reason"):
            errs.append("thresholds.overrides entries need a recorded reason")
    return errs


def json_keys(o: Any, prefix: str = "") -> List[str]:
    out: List[str] = []
    if isinstance(o, dict):
        for k, v in o.items():
            key = "%s.%s" % (prefix, k) if prefix else k
            out.append(key)
            out.extend(json_keys(v, key))
    return out


def validate_lists(state: Path) -> List[str]:
    errs: List[str] = []
    for name, key in (("keywords.json", "clusters"), ("prompts.json", "prompts"), ("competitors.json", "competitors"),
                      ("backlog.json", "items"), ("offsite.json", "entries")):
        p = state / name
        if not p.exists():
            continue
        try:
            d = st.load_json(p, {})
        except Exception as exc:
            errs.append("%s: invalid JSON (%s)" % (name, exc))
            continue
        if not isinstance(d.get(key), list):
            errs.append("%s: key %r must be a list" % (name, key))
    try:
        st.read_jsonl(state / "actions.jsonl")
    except ValueError as exc:
        errs.append(str(exc))
    return errs


# ---------------------------------------------------------------- commands

def cmd_init(args: Any) -> int:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        cli.die(cli.EXIT_USAGE, "Repo folder not found: %s" % repo)
    target = Path(os.environ.get("TWWA_STATE_DIR") or (repo / st.STATE_DIRNAME))
    created: List[str] = []
    kept: List[str] = []
    target.mkdir(parents=True, exist_ok=True)
    for src in sorted(TEMPLATE_STATE.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE_STATE)
        dst = target / rel
        if dst.exists():
            kept.append(str(rel))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        created.append(str(rel))
    for d in st.STATE_SUBDIRS:
        (target / d).mkdir(parents=True, exist_ok=True)
    det = detect_repo(repo)
    if "config.json" in created:
        cfg = st.load_json(target / "config.json", {})
        cfg["tier"] = det["tier"]
        cfg["scope_file"] = det["scope_file"]
        cfg["tier_guard"] = det["tier_guard"]
        if det["astro"].get("site"):
            cfg.setdefault("site", {})["url"] = det["astro"]["site"]
        if det.get("default_branch"):
            cfg.setdefault("site", {})["default_branch"] = det["default_branch"]
        st.save_json(target / "config.json", cfg)
    out = {"state": str(target), "created": created, "kept": kept, "detected": det}
    human = "State folder: %s\ncreated: %d files, kept: %d existing\ntier: %s (scope file: %s)\nNext: fill business.json (twwa-onboard), then: python3 scripts/twwa_state.py validate" % (
        target, len(created), len(kept), det["tier"], det["scope_file"])
    cli.emit(out, args, human)
    return cli.EXIT_OK


def cmd_status(args: Any) -> int:
    state = st.require_state(args)
    cfg = st.load_config(state)
    events = st.read_jsonl(state / "actions.jsonl")
    by: Dict[str, Dict[str, Any]] = {}
    for e in events:
        aid = e.get("action_id")
        if not aid or aid == "-":
            continue
        by.setdefault(aid, {"state": None})
        if e.get("event") in ("proposed", "approved", "shipped", "measured", "kept", "reverted", "rejected", "blocked", "superseded"):
            by[aid]["state"] = e["event"]
    counts: Dict[str, int] = {}
    for a in by.values():
        counts[a["state"] or "?"] = counts.get(a["state"] or "?", 0) + 1
    snaps: Dict[str, str] = {}
    for d in st.snapshot_dates(state):
        for f in (state / "snapshots" / d).glob("*.json"):
            snaps[f.stem] = d
    tds = sorted(p.name for p in (state / "teardowns").glob("*") if p.is_dir()) if (state / "teardowns").is_dir() else []
    month = st.today()[:7]
    projects = sorted((state / "evidence" / "projects").glob("*.json"))
    month_report = any(p.name.startswith(month) for p in projects) or any(p.name.startswith(month) for p in (state / "evidence" / "inbox").glob("*"))
    from twwa_lib import spend as spend_mod
    out = {
        "state": str(state), "tier": cfg.get("tier"), "autopilot": cfg["autopilot"]["level"], "stop": st.stop_requested(state),
        "actions": counts, "snapshots": snaps, "last_teardown": tds[-1] if tds else None,
        "evidence_projects": len(projects), "monthly_report_this_month": month_report,
        "spend_this_month_usd": spend_mod.month_total(state), "spend_cap_usd": cfg["spend"]["monthly_cap_usd"],
    }
    lines = ["State: %s" % state, "Tier: %s, autopilot: %s, STOP: %s" % (out["tier"], out["autopilot"], "JA" if out["stop"] else "nein"),
             "Actions: %s" % (", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none"),
             "Last teardown: %s" % (out["last_teardown"] or "none"),
             "Snapshots: %s" % (", ".join("%s %s" % kv for kv in sorted(snaps.items())) or "none"),
             "Evidence projects: %d; monthly report for %s: %s" % (len(projects), month, "yes" if month_report else "missing"),
             "Spend this month: %.2f of %.2f USD" % (out["spend_this_month_usd"], float(out["spend_cap_usd"] or 0))]
    cli.emit(out, args, "\n".join(lines))
    return cli.EXIT_OK


def cmd_doctor(args: Any) -> int:
    state = st.require_state(args)
    problems = doctor_checks(state)
    ok = not problems
    human = "doctor: OK (state folder is compatible with the tier guard)" if ok else "doctor: %d problem(s)\n" % len(problems) + "\n".join(
        "  %s %s%s: %s" % (p["check"], p["path"], (":%s" % p["line"]) if p.get("line") else "", p["message"]) for p in problems)
    cli.emit({"ok": ok, "problems": problems}, args, human)
    return cli.EXIT_OK if ok else cli.EXIT_FAIL


def cmd_scope(args: Any) -> int:
    repo = Path(args.repo).resolve() if args.repo else None
    state = None
    if repo is None:
        state = st.resolve_state_arg(getattr(args, "state", None))
        repo = st.repo_root(state) if state else Path(".").resolve()
    cfg = st.load_config(state) if state else {}
    sc = read_scope(repo, cfg)
    if args.op == "show":
        human = "Scope file: %s\nTier: %s (%s)\nOwner exceptions: %s" % (
            sc["scope_file"] or "none", sc["tier"], sc["tier_source"], ", ".join(e["name"] for e in sc["exceptions"]) or "none")
        cli.emit(sc, args, human)
        return cli.EXIT_OK
    deps = [d for d in (args.adds_dependency or []) if d]
    res = scope_check(sc, args.type, args.adds_page, deps, args.adds_api_route)
    res["scope_file"] = sc["scope_file"]
    human = ("IN SCOPE: " if res["in_scope"] else "OUT OF SCOPE: ") + res["reason"] + (
        "" if res["in_scope"] else "\nWrite it up as a proposal: twwa_actions.py propose --as-proposal ...")
    cli.emit(res, args, human)
    return cli.EXIT_OK if res["in_scope"] else cli.EXIT_BLOCKED


def cmd_detect(args: Any) -> int:
    repo = Path(args.repo).resolve()
    det = detect_repo(repo)
    if args.write:
        state = st.resolve_state_arg(getattr(args, "state", None)) or (repo / st.STATE_DIRNAME if (repo / st.STATE_DIRNAME).is_dir() else None)
        if not state:
            cli.die(cli.EXIT_USAGE, "--write needs a state folder (run init first)")
        cfg = st.load_json(state / "config.json", {}) or {}
        cfg["tier"], cfg["scope_file"], cfg["tier_guard"] = det["tier"], det["scope_file"], det["tier_guard"]
        if det["astro"].get("site"):
            cfg.setdefault("site", {})["url"] = det["astro"]["site"]
        st.save_json(state / "config.json", cfg)
    a, v = det["astro"], det["vercel"]
    human = "\n".join([
        "Astro: %s site=%s trailingSlash=%s build.format=%s" % (a.get("file"), a.get("site"), a.get("trailingSlash"), a.get("build_format")),
        "Vercel: %s cleanUrls=%s trailingSlash=%s redirects=%s noindex hosts=%s" % (v.get("file"), v.get("cleanUrls"), v.get("trailingSlash"), v.get("redirects"), v.get("noindex_hosts")),
        "Form handlers: %s" % (", ".join(det["form_handlers"]) or "none"),
        "Scope file: %s, tier: %s" % (det["scope_file"], det["tier"]),
        "Tier guard: %s" % det["tier_guard"],
        "Routes: %s" % ", ".join(det["routes"]),
    ])
    cli.emit(det, args, human)
    return cli.EXIT_OK


def agency_dir() -> Path:
    return Path(os.environ.get("TWWA_AGENCY_DIR") or (Path.home() / ".twwa-growth")).expanduser()


def cmd_conflicts(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    cfg = st.load_config(state)
    reg_path = Path(args.registry) if args.registry else agency_dir() / "clients.json"
    reg = st.load_json(reg_path, {"clients": []}) or {"clients": []}
    trade = (b.get("trade") or "").lower() or None
    district = (b.get("address") or {}).get("district") or cfg.get("exclusivity", {}).get("region")
    alias = args.alias or st.slugify(b.get("name") or "client")
    hits = [c for c in reg.get("clients", []) if c.get("alias") != alias and trade and c.get("trade") == trade
            and district and c.get("district") == district]
    if args.register:
        if not trade or not district:
            cli.die(cli.EXIT_USAGE, "Registering needs business.json trade and address.district (Landkreis) or config.exclusivity.region.")
        others = [c for c in reg.get("clients", []) if c.get("alias") != alias]
        others.append({"alias": alias, "trade": trade, "district": district, "registered_on": st.today()})
        st.save_json(reg_path, {"clients": others})
    warn = []
    for h in hits:
        warn.append("Kunde %s hat dasselbe Gewerk (%s) im selben Landkreis (%s)." % (h["alias"], trade, district))
    out = {"alias": alias, "trade": trade, "district": district, "registry": str(reg_path), "conflicts": hits,
           "exclusivity_offered": cfg["exclusivity"]["offered"], "warnings": warn}
    if not trade or not district:
        out["note"] = "nicht geprüft: trade or Landkreis unknown"
    human = "\n".join(warn) if warn else ("Keine Überschneidung gefunden." if trade and district else "Nicht geprüft: Gewerk oder Landkreis unbekannt.")
    cli.emit(out, args, human)
    return cli.EXIT_OK


def cmd_validate(args: Any) -> int:
    state = st.require_state(args)
    errors: Dict[str, List[str]] = {}
    try:
        raw_cfg = st.load_json(state / "config.json", None)
    except Exception as exc:
        raw_cfg, errors["config.json"] = None, ["invalid JSON: %s" % exc]
    if raw_cfg is None and "config.json" not in errors:
        errors["config.json"] = ["missing"]
    elif raw_cfg is not None:
        errors["config.json"] = validate_config(st.deep_merge(st.DEFAULT_CONFIG, raw_cfg))
    try:
        b = st.load_json(state / "business.json", None)
        errors["business.json"] = ["missing"] if b is None else validate_business(b)
    except Exception as exc:
        errors["business.json"] = ["invalid JSON: %s" % exc]
    errors["lists"] = validate_lists(state)
    errors = {k: v for k, v in errors.items() if v}
    ok = not errors
    human = "validate: OK" if ok else "validate: errors\n" + "\n".join("  %s: %s" % (k, e) for k, v in errors.items() for e in v)
    cli.emit({"ok": ok, "errors": errors}, args, human)
    return cli.EXIT_OK if ok else cli.EXIT_FAIL


def build_parser() -> Any:
    p = cli.base_parser(
        "State folder lifecycle for twwa-growth: create .twwa-growth/, show status, check guard compatibility, "
        "read the tier and scope, detect the repo setup, warn about client conflicts, validate config and business data.\n"
        "Writes only inside the state folder (init, detect --write) and the agency registry (conflicts --register).",
        "example:\n  python3 scripts/twwa_state.py init --repo .\n  python3 scripts/twwa_state.py scope check --type new_page --json",
    )
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "init", "create the state folder from templates/state (never overwrites existing files)")
    sp.add_argument("--repo", default=".", help="client repo root (default .)")
    cli.add_sub(subs, "status", "summary: tier, autopilot, STOP, actions, snapshots, teardown, evidence, spend")
    cli.add_sub(subs, "doctor", "check tier-guard compatibility (spec 4.1); exit 1 on a violation")
    sp = cli.add_sub(subs, "scope", "show the tier and owner exceptions, or 'check' whether an action is in scope (exit 4 if not)")
    sp.add_argument("op", nargs="?", choices=("show", "check"), default="show")
    sp.add_argument("--repo", default=None, help="client repo root (default: parent of the state folder)")
    sp.add_argument("--type", default=None, help="action type, e.g. new_page")
    sp.add_argument("--adds-page", action="store_true")
    sp.add_argument("--adds-dependency", action="append", default=[], metavar="NAME")
    sp.add_argument("--adds-api-route", action="store_true")
    sp = cli.add_sub(subs, "detect", "detect Astro and Vercel config, form handler, scope file, tier guard, routes")
    sp.add_argument("--repo", default=".")
    sp.add_argument("--write", action="store_true", help="store tier, scope file, tier guard and site URL in config.json")
    sp = cli.add_sub(subs, "conflicts", "warn when another registered client has the same trade in the same Landkreis")
    sp.add_argument("--registry", default=None, help="registry file (default ~/.twwa-growth/clients.json or TWWA_AGENCY_DIR)")
    sp.add_argument("--alias", default=None, help="client alias (no personal data)")
    sp.add_argument("--register", action="store_true", help="add or update this client in the registry")
    cli.add_sub(subs, "validate", "validate config.json, business.json and list files; exit 1 on errors")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    handler = {"init": cmd_init, "status": cmd_status, "doctor": cmd_doctor, "scope": cmd_scope, "detect": cmd_detect,
               "conflicts": cmd_conflicts, "validate": cmd_validate}[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
