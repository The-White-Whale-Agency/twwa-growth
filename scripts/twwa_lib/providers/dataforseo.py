"""DataForSEO adapter (built from the public v3 documentation; live_verified_on stays null until a real call succeeds)."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .. import http

BASE = "https://api.dataforseo.com/v3"
GERMANY = 2276


def _post(path: str, body: List[Dict[str, Any]]) -> Dict[str, Any]:
    tok = base64.b64encode(("%s:%s" % (os.environ["DATAFORSEO_LOGIN"], os.environ["DATAFORSEO_PASSWORD"])).encode()).decode()
    r = http.fetch(BASE + path, method="POST", data=json.dumps(body).encode(),
                   headers={"Authorization": "Basic " + tok, "Content-Type": "application/json"}, timeout=60)
    if r.status != 200:
        raise http.FetchError("DataForSEO HTTP %s: %s" % (r.status, r.text[:300]))
    return json.loads(r.text)


def _items(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        task = raw["tasks"][0]
        if task.get("status_code") not in (20000, None):
            raise http.FetchError("DataForSEO task error %s: %s" % (task.get("status_code"), task.get("status_message")))
        res = task.get("result") or []
        return (res[0].get("items") or []) if res else []
    except (KeyError, IndexError, TypeError):
        raise http.FetchError("DataForSEO: unexpected response shape")


def _loc(params: Dict[str, Any]) -> Dict[str, Any]:
    loc = params.get("location") or {}
    lat, lng = loc.get("lat", params.get("lat")), loc.get("lng", params.get("lng"))
    body: Dict[str, Any] = {"language_code": loc.get("language", "de")}
    if lat is not None and lng is not None:
        body["location_coordinate"] = "%s,%s,%s" % (lat, lng, params.get("zoom", "14z") if params.get("maps") else 2000)
    else:
        body["location_code"] = GERMANY
    return body


def _dom(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def _rating(it: Dict[str, Any]) -> Any:
    r = it.get("rating") or {}
    return (r.get("value"), r.get("votes_count"))


def serp_organic(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if raw is None:
        body = dict(_loc(params), keyword=params["query"], depth=params.get("depth", 10))
        raw = _post("/serp/google/organic/live/advanced", [body])
    results, pack, aio = [], [], None
    for it in _items(raw):
        t = it.get("type")
        if t == "organic":
            results.append({"rank": it.get("rank_group"), "url": it.get("url"), "domain": _dom(it.get("url")),
                            "title": it.get("title"), "snippet": it.get("description")})
        elif t == "local_pack":
            val, votes = _rating(it)
            pack.append({"rank": len(pack) + 1, "name": it.get("title"), "place_id": it.get("cid"), "rating": val,
                         "reviews": votes, "category": None, "address": it.get("description")})
        elif t == "ai_overview":
            refs = it.get("references") or []
            aio = {"present": True, "cited_domains": sorted({_dom(r.get("url")) or r.get("domain") for r in refs if r})}
    return {"localised": "location_coordinate" in _loc(params), "results": results, "local_pack": pack,
            "ai_overview": aio if aio else {"present": False, "cited_domains": []}}


def serp_maps(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if raw is None:
        body = dict(_loc(dict(params, maps=True)), keyword=params["query"], depth=params.get("depth", 20))
        raw = _post("/serp/google/maps/live/advanced", [body])
    out = []
    for it in _items(raw):
        if it.get("type") != "maps_search":
            continue
        val, votes = _rating(it)
        out.append({"rank": it.get("rank_group"), "name": it.get("title"), "place_id": it.get("place_id") or it.get("cid"),
                    "rating": val, "reviews": votes, "category": it.get("category"),
                    "additional_categories": it.get("additional_categories") or [], "address": it.get("address"),
                    "lat": it.get("latitude"), "lng": it.get("longitude"), "website": it.get("url"), "phone": it.get("phone")})
    return {"results": out}


def keyword_volume(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if raw is None:
        raw = _post("/keywords_data/google_ads/search_volume/live",
                    [{"keywords": params["keywords"], "location_code": GERMANY, "language_code": "de"}])
    try:
        res = raw["tasks"][0].get("result") or []
    except (KeyError, IndexError):
        res = []
    return {"items": [{"keyword": r.get("keyword"), "volume": r.get("search_volume"), "volume_range": None,
                       "cpc": r.get("cpc")} for r in res]}


def backlinks(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if raw is None:
        raw = _post("/backlinks/summary/live", [{"target": params["target"], "include_subdomains": True}])
    try:
        r = raw["tasks"][0]["result"][0]
    except (KeyError, IndexError, TypeError):
        r = {}
    return {"referring_domains": r.get("referring_domains"), "backlinks": r.get("backlinks"),
            "authority": r.get("rank"), "authority_scale": "dataforseo_rank_0_1000", "top_referring": []}


def business_reviews(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    q = params.get("name") or params.get("query")
    m = serp_maps({"query": "%s %s" % (q, params.get("address", "")), "lat": params.get("lat"), "lng": params.get("lng"),
                   "depth": 5}, raw)
    best = m["results"][0] if m["results"] else {}
    return {"count": best.get("reviews"), "rating": best.get("rating"), "recent": [],
            "note": "recent review dates need the task-based reviews endpoint; not checked"}


def call(provider_id: str, capability: str, params: Dict[str, Any], fixture: Any = None, engine: Optional[str] = None) -> Dict[str, Any]:
    fn = {"serp_organic": serp_organic, "serp_maps": serp_maps, "keyword_volume": keyword_volume,
          "backlinks": backlinks, "business_reviews": business_reviews}.get(capability)
    if not fn:
        raise http.FetchError("dataforseo adapter: %s not implemented" % capability)
    return fn(params, fixture)
