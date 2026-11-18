"""Polite HTTP: timeout, size cap, identifying User-Agent, robots.txt, private-address refusal.

``fetch`` follows redirects itself so that every hop is recorded in ``Response.history`` and checked
against the private-address rule. ``use_fixture(path)`` makes every fetch answer from a saved file,
so tests and demos never touch the network.

Fixture format::

    {"responses": {"https://www.musterbetrieb.example/": {"status": 200,
        "headers": {"content-type": "text/html"}, "text": "<html>...</html>"},
        "https://www.musterbetrieb.example/alt": {"status": 308, "headers": {"location": "/neu"}},
        "https://www.musterbetrieb.example/seite": {"status": 200, "file": "dist/seite.html"}}}

``file`` is relative to the fixture file. A URL missing from the fixture answers 404.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import __version__

USER_AGENT = "twwa-growth/%s (+https://github.com/The-White-Whale-Agency/twwa-growth)" % __version__
UA_TOKEN = "twwa-growth"


class FetchError(Exception):
    """Network failure, refused address or size overflow."""


class BlockedAddress(FetchError):
    """The host resolves to a private, loopback or otherwise non-public address."""


class Headers(dict):
    """Case-insensitive header dict (keys stored lowercase; repeated headers joined with ', ')."""

    def __init__(self, items: Any = None):
        super().__init__()
        if items:
            pairs = items.items() if isinstance(items, dict) else items
            for k, v in pairs:
                self.add(k, v)

    def add(self, k: str, v: str) -> None:
        k = str(k).lower()
        if k in self:
            super().__setitem__(k, self[k] + ", " + str(v))
        else:
            super().__setitem__(k, str(v))

    def __getitem__(self, k: str) -> str:
        return super().__getitem__(str(k).lower())

    def get(self, k: str, default: Any = None) -> Any:  # type: ignore[override]
        return super().get(str(k).lower(), default)

    def __contains__(self, k: object) -> bool:
        return super().__contains__(str(k).lower())


class Response:
    def __init__(self, status: int, headers: Headers, text: str, url: str, history: List[Tuple[int, str]], body: bytes = b"", elapsed: float = 0.0):
        self.status = status
        self.headers = headers
        self.text = text
        self.url = url
        self.history = history
        self.body = body
        self.elapsed = elapsed

    @property
    def content_type(self) -> str:
        return (self.headers.get("content-type") or "").split(";")[0].strip().lower()

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        return json.loads(self.text or "null")

    def __repr__(self) -> str:
        return "<Response %s %s>" % (self.status, self.url)


_FIXTURE: Optional[Dict[str, Any]] = None
_FIXTURE_BASE: Optional[Path] = None
_ROBOTS_CACHE: Dict[str, Any] = {}


def use_fixture(path: Optional[str]) -> None:
    """Answer every fetch from the fixture file (None switches back to the network)."""
    global _FIXTURE, _FIXTURE_BASE
    _ROBOTS_CACHE.clear()
    if not path:
        _FIXTURE, _FIXTURE_BASE = None, None
        return
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    _FIXTURE = data.get("responses", data)
    _FIXTURE_BASE = p.parent


def fixture_active() -> bool:
    return _FIXTURE is not None


def _norm_key(url: str) -> str:
    return url


def _fixture_response(url: str) -> Tuple[int, Headers, bytes]:
    assert _FIXTURE is not None
    spec = _FIXTURE.get(url)
    if spec is None and url.endswith("/") and url.count("/") > 3:
        spec = _FIXTURE.get(url[:-1])
    if spec is None:
        u = urllib.parse.urlsplit(url)
        if u.path in ("", "/"):
            spec = _FIXTURE.get(urllib.parse.urlunsplit((u.scheme, u.netloc, "/", u.query, "")))
            if spec is None:
                spec = _FIXTURE.get(urllib.parse.urlunsplit((u.scheme, u.netloc, "", u.query, "")))
    if spec is None:
        return 404, Headers({"content-type": "text/html"}), b"<html><head><title>404</title></head><body>Not found</body></html>"
    status = int(spec.get("status", 200))
    headers = Headers(spec.get("headers") or {})
    if "file" in spec:
        body = (_FIXTURE_BASE / spec["file"]).read_bytes()  # type: ignore[operator]
    else:
        body = (spec.get("text") or "").encode("utf-8")
    if "content-type" not in headers and body:
        if spec.get("file", "").endswith(".xml"):
            headers.add("content-type", "application/xml")
        elif spec.get("file", "").endswith(".txt"):
            headers.add("content-type", "text/plain")
        else:
            headers.add("content-type", "text/html; charset=utf-8")
    return status, headers, body


def is_public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchError("DNS lookup failed for %s: %s" % (host, exc))
    for info in infos:
        addr = info[4][0]
        ip = ipaddress.ip_address(addr.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return True


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _decode(body: bytes, headers: Headers) -> str:
    ct = headers.get("content-type") or ""
    charset = "utf-8"
    if "charset=" in ct:
        charset = ct.split("charset=")[-1].split(";")[0].strip().strip('"') or "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _one(url: str, method: str, headers: Dict[str, str], data: Optional[bytes], timeout: float, max_bytes: int, allow_private: bool) -> Tuple[int, Headers, bytes]:
    if _FIXTURE is not None:
        return _fixture_response(url)
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError("unsupported URL scheme: %s" % url)
    if not allow_private and not is_public_host(parts.hostname or ""):
        raise BlockedAddress("refusing private or loopback address for %s (use --allow-private for a local preview)" % url)
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = _OPENER.open(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        resp = exc
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as exc:
        raise FetchError("request failed for %s: %s" % (url, exc))
    hdrs = Headers()
    for k, v in resp.headers.items():
        hdrs.add(k, v)
    try:
        body = resp.read(max_bytes + 1) if method != "HEAD" else b""
    except (socket.timeout, OSError) as exc:
        raise FetchError("read failed for %s: %s" % (url, exc))
    if len(body) > max_bytes:
        raise FetchError("response larger than %d bytes: %s" % (max_bytes, url))
    return int(getattr(resp, "status", None) or resp.getcode()), hdrs, body


def fetch(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, data: Optional[bytes] = None,
          timeout: float = 20, max_bytes: int = 3_000_000, allow_private: bool = False,
          follow_redirects: bool = True, max_redirects: int = 10) -> Response:
    """Fetch ``url``; returns a Response for every HTTP status, raises FetchError on network failure."""
    h = {"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Language": "de-DE,de;q=0.9"}
    if headers:
        h.update(headers)
    history: List[Tuple[int, str]] = []
    cur = url
    t0 = time.time()
    for _ in range(max_redirects + 1):
        status, hdrs, body = _one(cur, method, h, data, timeout, max_bytes, allow_private)
        loc = hdrs.get("location")
        if follow_redirects and status in (301, 302, 303, 307, 308) and loc:
            history.append((status, cur))
            nxt = urllib.parse.urljoin(cur, loc)
            if nxt in [u for _, u in history]:
                return Response(status, hdrs, _decode(body, hdrs), cur, history + [(status, nxt)], body, time.time() - t0)
            cur = nxt
            if status == 303:
                method, data = "GET", None
            continue
        return Response(status, hdrs, _decode(body, hdrs), cur, history, body, time.time() - t0)
    raise FetchError("too many redirects starting at %s" % url)


def post_json(url: str, obj: Any, headers: Optional[Dict[str, str]] = None, timeout: float = 20, allow_private: bool = False) -> Response:
    h = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
    if headers:
        h.update(headers)
    return fetch(url, method="POST", headers=h, data=json.dumps(obj).encode("utf-8"), timeout=timeout, allow_private=allow_private, follow_redirects=False)


def robots_for(url: str, allow_private: bool = False) -> Tuple[Optional[urllib.robotparser.RobotFileParser], Dict[str, Any]]:
    """Parsed robots.txt for the URL's host plus info {status, text, url}.

    4xx means no restrictions (parser None, allow all). 5xx or network failure means disallow all.
    """
    parts = urllib.parse.urlsplit(url)
    base = "%s://%s" % (parts.scheme, parts.netloc)
    if base in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[base]
    rurl = base + "/robots.txt"
    info: Dict[str, Any] = {"url": rurl, "status": None, "text": ""}
    try:
        r = fetch(rurl, allow_private=allow_private, max_bytes=500_000)
        info["status"], info["text"], info["content_type"] = r.status, r.text, r.content_type
        if r.status >= 500:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(["User-agent: *", "Disallow: /"])
            info["disallow_all_reason"] = "5xx"
        elif r.status >= 400:
            rp = None
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(r.text.splitlines())
    except FetchError as exc:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(["User-agent: *", "Disallow: /"])
        info["error"] = str(exc)
        info["disallow_all_reason"] = "network"
    _ROBOTS_CACHE[base] = (rp, info)
    return rp, info


def robots_allows(url: str, agent: str = UA_TOKEN, allow_private: bool = False) -> bool:
    rp, _ = robots_for(url, allow_private=allow_private)
    if rp is None:
        return True
    return rp.can_fetch(agent, url)


def parse_robots_groups(text: str) -> List[Dict[str, Any]]:
    """Parse robots.txt into groups [{agents: [...], allow: [...], disallow: [...]}] plus sitemaps as a group with agents []."""
    groups: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    last_was_agent = False
    sitemaps: List[str] = []
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if cur is None or not last_was_agent:
                cur = {"agents": [], "allow": [], "disallow": []}
                groups.append(cur)
            cur["agents"].append(v.lower())
            last_was_agent = True
            continue
        last_was_agent = False
        if k == "sitemap":
            sitemaps.append(v)
        elif cur is not None and k in ("allow", "disallow"):
            cur[k].append(v)
    return groups + [{"agents": [], "allow": [], "disallow": [], "sitemaps": sitemaps}]


def robots_blocks_root(text: str, agent: str) -> Optional[bool]:
    """True if ``agent`` (lowercase token) may not fetch '/', using the most specific matching group."""
    groups = [g for g in parse_robots_groups(text) if g["agents"]]
    specific = [g for g in groups if agent.lower() in g["agents"]]
    use = specific or [g for g in groups if "*" in g["agents"]]
    if not use:
        return False
    disallow = [d for g in use for d in g["disallow"]]
    allow = [a for g in use for a in g["allow"]]
    blocked = any(d == "/" or d == "/*" for d in disallow)
    if blocked and any(a in ("/", "/*") for a in allow):
        return False
    return blocked
