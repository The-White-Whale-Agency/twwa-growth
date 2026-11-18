"""Free providers: Wayback CDX (domain_age), manual observation files and agent search samples."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .. import http
from .. import state as st


def _wayback(params: Dict[str, Any], raw: Any) -> Dict[str, Any]:
    if raw is None:
        r = http.fetch("https://web.archive.org/cdx/search/cdx?url=%s&output=json&limit=1&fl=timestamp" % params["domain"], timeout=30)
        raw = json.loads(r.text or "[]") if r.status == 200 else []
    ts = raw[1][0] if isinstance(raw, list) and len(raw) > 1 else None
    return {"first_seen": "%s-%s-%s" % (ts[:4], ts[4:6], ts[6:8]) if ts else None}


def _from_file(capability: str, params: Dict[str, Any], raw: Any) -> Dict[str, Any]:
    data = raw if raw is not None else st.load_json(params.get("file") or "", None)
    if data is None:
        raise http.FetchError("manual provider needs params.file with an observation (see serp_teardown.py import --help)")
    data = dict(data)
    data.setdefault("origin", "manual")
    if capability == "serp_organic":
        data.setdefault("results", [])
        data.setdefault("local_pack", [])
        data.setdefault("ai_overview", None)
    return data


def call(provider_id: str, capability: str, params: Dict[str, Any], fixture: Any = None, engine: Optional[str] = None) -> Dict[str, Any]:
    if provider_id == "wayback":
        return _wayback(params, fixture)
    out = _from_file(capability, params, fixture)
    if provider_id == "agent_search":
        out["localised"] = False
        out["label_de"] = "Stichprobe (nicht lokalisiert)"
    return out
