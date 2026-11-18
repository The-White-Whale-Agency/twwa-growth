"""Provider-agnostic data layer (spec 9a).

No script names a vendor. Callers ask for a capability; this module picks the best provider whose
credentials are present, previews cost, guards spend, calls the adapter and returns a normalised result.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .. import spend as _spend
from .. import state as st

CAPABILITIES = ("serp_organic", "serp_maps", "keyword_volume", "autocomplete", "backlinks",
                "ai_answers", "business_reviews", "domain_age")
IMPORT_ONLY = ("manual", "agent_search")  # never auto-picked; used when the operator supplies a file


class NoProvider(Exception):
    def __init__(self, capability: str, how_to_enable: str):
        super().__init__("no provider for %s: %s" % (capability, how_to_enable))
        self.capability = capability
        self.how_to_enable = how_to_enable


class NotExecuted(Exception):
    """Raised by call() in dry-run mode; carries the plan (provider, cost)."""

    def __init__(self, plan: Dict[str, Any]):
        super().__init__("dry-run: %s" % json.dumps(plan))
        self.plan = plan


def registry() -> List[Dict[str, Any]]:
    data = st.load_json(_spend.DATA_DIR / "providers.json", {}) or {}
    return [e for e in data.get("providers", []) if isinstance(e, dict)]


def creds_present(entry: Dict[str, Any]) -> bool:
    return all(os.environ.get(v) for v in (entry.get("auth") or {}).get("env", []))


def status(state: Any = None) -> List[Dict[str, Any]]:
    cfg = st.load_config(state) if state else {}
    disabled = set(((cfg.get("providers") or {}).get("disabled")) or [])
    out = []
    for e in registry():
        out.append({"id": e["id"], "name": e.get("name"), "status": e.get("status"),
                    "creds_present": creds_present(e), "disabled": e["id"] in disabled,
                    "env": (e.get("auth") or {}).get("env", []),
                    "capabilities": {k: {"cost_usd": v.get("cost_usd"), "unit": v.get("unit"),
                                         "localised": v.get("localised"), "ui_parity": v.get("ui_parity")}
                                     for k, v in (e.get("capabilities") or {}).items()},
                    "verified_on": e.get("verified_on"), "live_verified_on": e.get("live_verified_on")})
    return out


def _how_to_enable(capability: str) -> str:
    opts = []
    for e in registry():
        if capability in (e.get("capabilities") or {}) and e["id"] not in IMPORT_ONLY:
            env = ", ".join((e.get("auth") or {}).get("env", [])) or "no credentials"
            opts.append("%s (%s; %s)" % (e["id"], e.get("status"), env))
    opts.append("or import a manual observation file (provider 'manual')")
    return "; ".join(opts)


def candidates(capability: str, state: Any = None, engine: Optional[str] = None) -> List[Dict[str, Any]]:
    cfg = st.load_config(state) if state else {}
    pcfg = cfg.get("providers") or {}
    disabled = set(pcfg.get("disabled") or [])
    prefer = (pcfg.get("prefer") or {}).get(capability)
    out = []
    for e in registry():
        cap = (e.get("capabilities") or {}).get(capability)
        if not cap or e.get("status") != "implemented" or e["id"] in disabled or e["id"] in IMPORT_ONLY:
            continue
        if engine and cap.get("engines") and engine not in cap["engines"]:
            continue
        if not creds_present(e):
            continue
        out.append(e)

    fresh_rank = {"live": 0, "daily": 1, "weekly": 2, "monthly": 3}

    def key(e: Dict[str, Any]) -> Any:
        c = e["capabilities"][capability]
        return (0 if e["id"] == prefer else 1,
                0 if c.get("localised") else 1,
                0 if c.get("ui_parity") else 1,
                fresh_rank.get(c.get("freshness"), 9),
                c.get("cost_usd") if c.get("cost_usd") is not None else 999)
    return sorted(out, key=key)


def pick(capability: str, state: Any = None, engine: Optional[str] = None) -> Dict[str, Any]:
    if capability not in CAPABILITIES:
        raise ValueError("unknown capability %s" % capability)
    c = candidates(capability, state, engine)
    if not c:
        raise NoProvider(capability, _how_to_enable(capability))
    return c[0]


def cost(capability: str, provider_id: str, units: float = 1) -> Optional[float]:
    return _spend.estimate(provider_id, capability, units)


def _adapter(name: str) -> Any:
    if name == "dataforseo":
        from . import dataforseo as m
    elif name == "ai_direct":
        from . import ai_direct as m
    elif name == "free":
        from . import free as m
    else:
        raise NoProvider("adapter", "adapter %s not implemented" % name)
    return m


def call(capability: str, params: Dict[str, Any], state: Any = None, execute: bool = False,
         fixture: Optional[str] = None, provider: Optional[str] = None, engine: Optional[str] = None) -> Dict[str, Any]:
    """Normalised result for ``capability``. Dry-run (raises NotExecuted with the plan) unless execute."""
    if provider:
        entry = next((e for e in registry() if e["id"] == provider), None)
        if not entry or capability not in (entry.get("capabilities") or {}):
            raise NoProvider(capability, "provider %s does not offer %s" % (provider, capability))
    else:
        entry = pick(capability, state, engine)
    usd = cost(capability, entry["id"]) or 0.0
    free = entry.get("billing") == "free" or usd == 0
    if fixture is None and not free:
        plan = {"capability": capability, "provider": entry["id"], "estimated_usd": usd, "params": params}
        if not execute:
            raise NotExecuted(plan)
        if state is not None:
            _spend.guard(state, usd)
    if state is not None and fixture is None and st.stop_requested(state) and not free:
        raise NotExecuted({"blocked": "STOP"})
    mod = _adapter(entry.get("adapter") or "")
    raw_fixture = st.load_json(fixture) if fixture else None
    result = mod.call(entry["id"], capability, params, fixture=raw_fixture, engine=engine)
    result.setdefault("provider", entry["id"])
    result.setdefault("origin", "fixture" if fixture else ("manual" if entry["id"] in IMPORT_ONLY else "api"))
    result.setdefault("observed_at", st.now_iso())
    result["cost_usd"] = 0.0 if (fixture or free) else usd
    if state is not None and fixture is None and not free:
        _spend.record(state, entry["id"], capability, 1, usd, json.dumps(params, ensure_ascii=False)[:200])
    return result
