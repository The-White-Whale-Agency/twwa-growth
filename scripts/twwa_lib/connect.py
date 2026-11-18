"""Small helpers shared by the connector scripts (gsc, bing_wmt, psi, vercel_analytics, gbp)."""
from __future__ import annotations

import datetime as _dt
import json
from typing import Any, Dict, Optional, Tuple

from . import cli, http, state as st
from .textde import fold_umlauts, norm_name


def get_json(url: str, token: Optional[str] = None, method: str = "GET", body: Any = None,
             headers: Optional[Dict[str, str]] = None, timeout: float = 60) -> Any:
    h = dict(headers or {})
    if token:
        h["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    try:
        r = http.fetch(url, method=method, headers=h, data=data, timeout=timeout, max_bytes=20_000_000)
    except http.FetchError as ex:
        cli.die(cli.EXIT_REMOTE, "network error: %s" % ex)
    if r.status >= 400:
        cli.die(cli.EXIT_REMOTE, "HTTP %s from %s: %s" % (r.status, url.split("?")[0], r.text[:400]))
    return json.loads(r.text) if r.text.strip() else {}


def gsc_window(days: int = 90, lag: int = 3) -> Tuple[str, str]:
    """GSC windows end `lag` days before today (spec 12)."""
    end = st.today_date() - _dt.timedelta(days=lag)
    start = end - _dt.timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def brand_terms(business: Optional[Dict[str, Any]]) -> list:
    if not business or not business.get("name"):
        return []
    core = norm_name(business["name"], strip_legal_form=True)
    stop = {"und", "der", "die", "das", "gmbh", "malerbetrieb", "stuckateur", "betrieb", "meisterbetrieb", "inh"}
    trade = fold_umlauts((business.get("trade") or "").lower())
    return [t for t in fold_umlauts(core).split() if len(t) > 3 and t not in stop and t != trade]


def is_branded(query: str, terms: list) -> Optional[bool]:
    if not terms:
        return None
    q = fold_umlauts(query.lower())
    return any(t in q for t in terms)


def write_snapshot(state: Any, source: str, payload: Dict[str, Any], origin: str, rng: Optional[Tuple[str, str]] = None) -> str:
    snap = {"source": source, "pulled_at": st.now_iso(), "origin": origin,
            "range": {"start": rng[0], "end": rng[1]} if rng else None}
    snap.update(payload)
    path = st.snapshot_dir(state) / ("%s.json" % source)
    st.save_json(path, snap)
    return str(path)
