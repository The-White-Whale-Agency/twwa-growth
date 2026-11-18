"""Direct model APIs for ai_answers (ui_parity false: answers can differ from the consumer apps).

Location is always explicit; the OpenAI call refuses to run without a town because the API default is the US.
Model names come from env (OPENAI_MODEL, PERPLEXITY_MODEL, GEMINI_MODEL) so they can follow vendor changes.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .. import http


def _dom(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    h = urlparse(u).netloc.lower()
    return h[4:] if h.startswith("www.") else (h or None)


def _post(url: str, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    headers = dict(headers, **{"Content-Type": "application/json"})
    r = http.fetch(url, method="POST", data=json.dumps(body).encode(), headers=headers, timeout=120)
    if r.status != 200:
        raise http.FetchError("HTTP %s: %s" % (r.status, r.text[:300]))
    return json.loads(r.text)


def _openai(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    loc = params.get("location") or {}
    if raw is None:
        if not loc.get("town"):
            raise http.FetchError("openai ai_answers refuses to run without location.town (API default is the US)")
        body = {"model": os.environ.get("OPENAI_MODEL", "gpt-5"), "input": params["prompt"],
                "tools": [{"type": "web_search", "user_location": {"type": "approximate", "country": loc.get("country", "DE"),
                                                                   "city": loc["town"], "region": loc.get("region")}}]}
        raw = _post("https://api.openai.com/v1/responses", body, {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
    text, cites = [], []
    for item in raw.get("output", []):
        if item.get("type") != "message":
            continue
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                text.append(c.get("text", ""))
                for a in c.get("annotations", []) or []:
                    if a.get("type") == "url_citation":
                        cites.append({"url": a.get("url"), "domain": _dom(a.get("url"))})
    return {"engine": "chatgpt", "answer_text": "\n".join(text), "citations": cites, "ui_parity": False}


def _perplexity(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    loc = params.get("location") or {}
    if raw is None:
        body = {"model": os.environ.get("PERPLEXITY_MODEL", "sonar"),
                "messages": [{"role": "user", "content": params["prompt"]}],
                "web_search_options": {"user_location": {"country": loc.get("country", "DE"), "city": loc.get("town")}}}
        raw = _post("https://api.perplexity.ai/chat/completions", body,
                    {"Authorization": "Bearer " + os.environ["PERPLEXITY_API_KEY"]})
    text = ((raw.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    urls: List[str] = list(raw.get("citations") or []) + [r.get("url") for r in raw.get("search_results") or [] if r.get("url")]
    seen, cites = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            cites.append({"url": u, "domain": _dom(u)})
    return {"engine": "perplexity", "answer_text": text, "citations": cites, "ui_parity": False}


def _gemini(params: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    loc = params.get("location") or {}
    if raw is None:
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        prompt = params["prompt"] + ("\n(Standort der Suche: %s, Deutschland)" % loc["town"] if loc.get("town") else "")
        body = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
        raw = _post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model, body,
                    {"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    cand = (raw.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
    chunks = (cand.get("groundingMetadata") or {}).get("groundingChunks") or []
    # grounding URIs are redirect links; the chunk title carries the source domain
    cites = [{"url": (c.get("web") or {}).get("uri"), "domain": ((c.get("web") or {}).get("title") or "").lower() or None}
             for c in chunks]
    return {"engine": "gemini", "answer_text": text, "citations": cites, "ui_parity": False}


def call(provider_id: str, capability: str, params: Dict[str, Any], fixture: Any = None, engine: Optional[str] = None) -> Dict[str, Any]:
    if capability != "ai_answers":
        raise http.FetchError("ai_direct only provides ai_answers")
    fn = {"openai": _openai, "perplexity": _perplexity, "gemini": _gemini}[provider_id]
    return fn(params, fixture)
