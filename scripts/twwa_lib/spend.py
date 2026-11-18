"""Paid-API ledger: estimate, guard (exit 4 over the monthly cap or under STOP), record.

The cap is ``config.spend.monthly_cap_usd`` (default 0: every paid call is blocked until the owner sets
a cap). Costs come from ``data/providers.json`` (capability ``cost_usd`` per unit).
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import cli, state as st

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _registry() -> Dict[str, Any]:
    p = DATA_DIR / "providers.json"
    data = st.load_json(p, {}) or {}
    entries = data.get("providers", data if isinstance(data, list) else [])
    return {e.get("id"): e for e in entries if isinstance(e, dict)}


def estimate(provider: str, endpoint: str, units: float) -> Optional[float]:
    """Estimated USD for ``units`` calls of capability ``endpoint`` at ``provider``; None when unknown."""
    entry = _registry().get(provider)
    if not entry:
        return None
    cap = (entry.get("capabilities") or {}).get(endpoint)
    if not cap or cap.get("cost_usd") is None:
        return None
    return round(float(cap["cost_usd"]) * float(units), 6)


def month_total(state: Any, month: Optional[str] = None) -> float:
    month = month or st.today()[:7]
    total = 0.0
    for row in st.read_jsonl(Path(state) / "spend.jsonl"):
        if str(row.get("month") or str(row.get("ts", ""))[:7]) == month:
            total += float(row.get("usd") or 0)
    return round(total, 6)


def check(state: Any, usd: Optional[float]) -> Tuple[bool, str]:
    """Non-exiting form of guard: (allowed, reason)."""
    if st.stop_requested(state):
        return False, "STOP is set: nothing spends."
    if usd is None:
        return False, "Cost unknown for this call; refusing a paid call without an estimate."
    if usd <= 0:
        return True, "free call"
    cap = float(st.load_config(state).get("spend", {}).get("monthly_cap_usd") or 0)
    used = month_total(state)
    if cap <= 0:
        return False, "Spend cap is 0 (config.spend.monthly_cap_usd); paid calls are off until the owner sets a cap."
    if used + usd > cap:
        return False, "Monthly cap %.2f USD would be exceeded (used %.4f, this call %.4f)." % (cap, used, usd)
    return True, "within cap (used %.4f of %.2f USD)" % (used, cap)


def guard(state: Any, usd: Optional[float]) -> None:
    """Exit 4 when STOP exists or the call would exceed the monthly cap."""
    ok, reason = check(state, usd)
    if not ok:
        cli.die(cli.EXIT_BLOCKED, "Spend blocked: " + reason)


def record(state: Any, provider: str, endpoint: str, units: float, usd: float, note: str = "") -> Dict[str, Any]:
    row = {
        "ts": st.now_iso(),
        "month": st.today()[:7],
        "provider": provider,
        "endpoint": endpoint,
        "units": units,
        "usd": round(float(usd or 0), 6),
        "note": note,
    }
    st.append_jsonl(Path(state) / "spend.jsonl", row)
    return row
