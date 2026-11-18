"""Per-client state folder ``.twwa-growth/``: discovery, JSON IO, config defaults, snapshots.

Contract (spec 8.1): find_state, require_state, load_json, save_json (atomic), append_jsonl,
read_jsonl, load_config (defaults merged), stop_requested, snapshot_dir, latest_snapshot.
"""
from __future__ import annotations

import copy
import datetime as _dt
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from . import cli

STATE_DIRNAME = ".twwa-growth"
PathLike = Union[str, Path]

# Defaults for config.json (spec section 5). templates/state/config.json mirrors this exactly.
DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": 1,
    "tier": "unknown",
    "scope_file": None,
    "tier_guard": None,
    "state_dir": ".twwa-growth",
    "site": {
        "url": None,
        "default_branch": "main",
        "money_pages": ["/"],
        "preview_hosts": [],
        "dist_dir": "dist",
        "build_command": "npm run build",
    },
    "exclusivity": {"offered": False, "region": None},
    "guarantee": {"mode": "none"},
    "approval": {"owner_channel": "message", "twwa_channel": "branch_review"},
    "call_tracking": {"mode": "none"},
    "vercel": {"custom_events": False, "analytics_plus": False},
    "gbp": {"mode": "auto", "writes": "approved", "pacing_hours": 48},
    "providers": {"prefer": {}, "disabled": []},
    "spend": {"monthly_cap_usd": 0},
    "legal": {"signoff": False, "review_request_electronic": False, "referrer_capture": False},
    "owner_input": {"monthly_project_report": True},
    "outreach": {"send_mode": "draft_only", "_send_modes": "draft_only | client_sends | twwa_sends",
                 "mandate": {"granted": False, "date": None, "by": None, "evidence": None}, "sender_signature_de": None},
    "ai_bots": {"training": "no_change"},
    "paid_ads": {"mode": "mention_only"},
    "data": {"pii": "never"},
    "autopilot": {"level": "off"},
    "language": {"client": "de", "internal": "auto"},
    "caps": {
        "proposals_per_cycle": 5,
        "table_stakes_slots": 2,
        "target_queries": 15,
        "ai_prompts": 40,
        "ai_runs": 3,
        "grid_size": 7,
        "grid_keywords": 10,
        "crawl_pages": 25,
        "competitor_pages": 8,
        "page_cooldown_days": 14,
    },
    "thresholds": {
        "gates": {
            "demand_impressions_small_town": 10,
            "demand_impressions_other": 30,
            "small_town_population": 20000,
            "demand_window_days": 90,
            "demand_min_jobs": 2,
            "demand_jobs_months": 24,
            "max_drive_minutes": 120,
            "evidence_min_items": 3,
            "evidence_min_first_party": 1,
            "swap_min_town_bound_share": 0.25,
            "boilerplate_max_share": 0.6,
            "similarity_max_jaccard": 0.6,
            "shingle_size": 5,
            "townlist_max_towns": 8,
            "thin_min_words": 250,
            "ramp_week_min_pages": 2,
            "ramp_week_share": 0.10,
            "ramp_month_max_small_site": 8,
            "small_site_pages": 50,
            "pilot_min_pages": 3,
            "pilot_max_pages": 5,
            "pilot_indexed_share": 0.6,
            "pilot_indexed_days": 28,
            "pilot_impressions_share": 0.5,
            "pilot_impressions_days": 56,
            "prune_min_age_days": 90,
            "prune_max_impressions": 20,
            "prune_template_not_indexed_share": 0.4,
            "fact_freshness_days": 90,
            "subsidy_freshness_days": 31,
        },
        "teardown": {
            "valid_days": 35,
            "portal_dominated_min_non_business": 2,
            "organic_now_positions": [4, 15],
            "organic_now_max_gap": 0.35,
            "organic_with_work_max_gap": 0.65,
            "organic_with_work_rd_multiple": 3,
            "organic_with_work_rd_absolute": 20,
            "organic_long_term_rd_multiple": 10,
            "organic_long_term_rd_absolute": 50,
            "pack_max_km": 15,
            "pack_max_km_large_town": 5,
            "large_town_population": 100000,
            "pack_with_work_review_share": 0.5,
            "ai_min_rating": 4.3,
            "ai_min_reviews": 20,
            "winnability_factor": {"now": 1.0, "with_work": 0.6, "long_term": 0.25, "out_of_radius": 0, "blocked_by_basics": 0},
            "effort_weight": {"S": 1, "M": 2, "L": 4},
            "weights": {
                "organic": {"dedicated_page": 20, "geo_relevance": 15, "referring_domains": 15, "title_h1": 10,
                            "subquestions": 10, "evidence_depth": 10, "internal_links": 8, "domain_age": 5,
                            "page_experience": 4, "schema_entity": 3},
                "pack": {"primary_category": 20, "proximity": 20, "review_count": 12, "review_recency": 10,
                         "rating": 8, "profile_completeness": 8, "landing_title_h1": 8, "landing_links": 8, "nap_match": 6},
                "ai": {"cited_domains_presence": 30, "rating_volume": 20, "dedicated_page_facts": 20,
                       "third_party_mentions": 20, "bing_indexed": 10},
            },
        },
        "regression": {"performance_min": 90, "cls_max": 0.05, "lcp_max_ms": 2500},
        "measure": {"gsc_lag_days": 3, "min_row_impressions": 50, "min_verdict_impressions": 100},
        "alerts": {"position_drop": 3, "crawled_not_indexed_share": 0.2},
        "overrides": [],
    },
    "connectors": {
        "gsc": {"property": None},
        "bing": {"site_url": None},
        "gbp": {"location": None},
        "psi": {"strategy": "mobile"},
        "vercel": {"project_id": None, "team_id": None},
        "indexnow": {"key_file": None, "endpoint": "https://api.indexnow.org/indexnow"},
    },
}

STATE_SUBDIRS = (
    "evidence/inbox",
    "evidence/projects",
    "teardowns",
    "approvals",
    "drafts",
    "snapshots",
    "reports",
    "proposals",
    "out",
)


def today() -> str:
    """Today's date as yyyy-mm-dd; TWWA_TODAY overrides it (tests and replays)."""
    fixed = os.environ.get("TWWA_TODAY")
    if fixed and re.match(r"^\d{4}-\d{2}-\d{2}$", fixed):
        return fixed
    return _dt.date.today().isoformat()


def today_date() -> _dt.date:
    return _dt.date.fromisoformat(today())


def now_iso() -> str:
    """UTC timestamp; with TWWA_TODAY set, that date at 12:00 UTC (deterministic tests)."""
    fixed = os.environ.get("TWWA_TODAY")
    if fixed and re.match(r"^\d{4}-\d{2}-\d{2}$", fixed):
        return fixed + "T12:00:00Z"
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_date(s: Optional[str]) -> Optional[_dt.date]:
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def parse_ts(s: Optional[str]) -> Optional[_dt.datetime]:
    if not s:
        return None
    t = str(s).replace("Z", "+00:00")
    try:
        d = _dt.datetime.fromisoformat(t)
    except ValueError:
        dd = parse_date(s)
        if not dd:
            return None
        d = _dt.datetime(dd.year, dd.month, dd.day)
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d


def find_state(start: PathLike = ".") -> Optional[Path]:
    """Find the state folder: TWWA_STATE_DIR, else ``.twwa-growth`` in ``start`` or a parent.

    The upward search stops at the first directory that holds ``.git`` (the repo root).
    """
    env = os.environ.get("TWWA_STATE_DIR")
    if env:
        p = Path(env).expanduser()
        return p.resolve() if p.is_dir() else None
    cur = Path(start).expanduser().resolve()
    if cur.name == STATE_DIRNAME and cur.is_dir():
        return cur
    while True:
        cand = cur / STATE_DIRNAME
        if cand.is_dir():
            return cand
        if (cur / ".git").exists() or cur.parent == cur:
            return None
        cur = cur.parent


def resolve_state_arg(value: Optional[str]) -> Optional[Path]:
    if not value:
        return find_state(".")
    p = Path(value).expanduser()
    if p.is_dir() and p.name != STATE_DIRNAME and (p / STATE_DIRNAME).is_dir():
        p = p / STATE_DIRNAME
    return p.resolve() if p.is_dir() else None


def require_state(args: Any) -> Path:
    """Return the state folder for ``args.state`` or exit 2 with setup instructions."""
    st = resolve_state_arg(getattr(args, "state", None))
    if st is None:
        cli.die(cli.EXIT_USAGE, "No state folder found (.twwa-growth). Create one with: "
                "python3 scripts/twwa_state.py init --repo <client repo>, or pass --state <dir>, or set TWWA_STATE_DIR.")
    return st  # type: ignore[return-value]


def repo_root(state: PathLike) -> Path:
    """The client repo root: the folder that contains the state folder."""
    return Path(state).resolve().parent


def load_json(path: PathLike, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return copy.deepcopy(default)
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: PathLike, obj: Any) -> Path:
    """Write JSON atomically (temp file in the same folder, then rename)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return p


def append_jsonl(path: PathLike, obj: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=False) + "\n")


def read_jsonl(path: PathLike) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError("%s line %d: %s" % (p, n, exc))
    return out


def deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(state: Optional[PathLike]) -> Dict[str, Any]:
    """config.json merged over DEFAULT_CONFIG (missing keys take the conservative default)."""
    if state is None:
        return copy.deepcopy(DEFAULT_CONFIG)
    data = load_json(Path(state) / "config.json", {}) or {}
    return deep_merge(DEFAULT_CONFIG, data)


def load_business(state: Optional[PathLike]) -> Optional[Dict[str, Any]]:
    if state is None:
        return None
    return load_json(Path(state) / "business.json", None)


def stop_requested(state: Optional[PathLike]) -> bool:
    return state is not None and (Path(state) / "STOP").exists()


def require_not_stopped(state: Optional[PathLike]) -> None:
    if stop_requested(state):
        reason = ""
        try:
            reason = (Path(state) / "STOP").read_text(encoding="utf-8").strip()  # type: ignore[arg-type]
        except OSError:
            pass
        cli.die(cli.EXIT_BLOCKED, "STOP is set in %s: nothing ships and nothing spends. %s\n"
                "Resume with: python3 scripts/twwa_actions.py resume --by <name> --reason <text>" % (state, reason))


_DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def snapshot_dir(state: PathLike, date: Optional[str] = None) -> Path:
    """``snapshots/<date>/`` (today by default), created if missing."""
    d = Path(state) / "snapshots" / (date or today())
    d.mkdir(parents=True, exist_ok=True)
    return d


def snapshot_dates(state: PathLike) -> List[str]:
    root = Path(state) / "snapshots"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and _DATE_DIR.match(p.name))


def latest_snapshot(state: PathLike, source: str, before: Optional[str] = None) -> Optional[Path]:
    """Path of the newest ``snapshots/<date>/<source>.json``; with ``before``, only dates strictly earlier."""
    for d in reversed(snapshot_dates(state)):
        if before and d >= before:
            continue
        p = Path(state) / "snapshots" / d / ("%s.json" % source)
        if p.exists():
            return p
    return None


def load_latest_snapshot(state: Optional[PathLike], source: str, before: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if state is None:
        return None
    p = latest_snapshot(state, source, before)
    if p is None:
        return None
    data = load_json(p, None)
    if isinstance(data, dict):
        data.setdefault("_path", str(p))
        data.setdefault("_date", p.parent.name)
    return data


def slugify(s: str, max_len: int = 60) -> str:
    """German slug convention: ä->ae, ö->oe, ü->ue, ß->ss."""
    from .textde import fold_umlauts

    t = fold_umlauts(s or "").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:max_len].strip("-") or "x"
