#!/usr/bin/env python3
"""IndexNow for twwa-growth: key file management, checks and URL submission.

IndexNow notifies Bing, Yandex, Seznam and Naver (not Google) about added, changed or removed URLs.
Bing's index also feeds ChatGPT search and Copilot. `submit` is a dry run unless --execute is given."""
from __future__ import annotations

import os
import re
import secrets
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, http, state as st  # noqa: E402

KEY_RE = re.compile(r"^[A-Za-z0-9\-]{8,128}$")
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"


def find_keys(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    out = []
    for f in sorted(folder.glob("*.txt")):
        if KEY_RE.match(f.stem):
            try:
                if f.read_text(encoding="utf-8").strip() == f.stem:
                    out.append(f)
            except OSError:
                continue
    return out


def _repo(args: Any, state: Optional[Path]) -> Path:
    if getattr(args, "repo", None):
        return Path(args.repo).resolve()
    if state:
        return st.repo_root(state)
    return Path(".").resolve()


def cmd_key(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    repo = _repo(args, state)
    public = repo / "public"
    existing = find_keys(public)
    if existing:
        key = existing[0].stem
        cli.emit({"key": key, "file": str(existing[0]), "created": False}, args, "Key file exists: %s" % existing[0])
        created = False
    else:
        key = args.key or secrets.token_hex(16)
        if not KEY_RE.match(key):
            cli.die(cli.EXIT_USAGE, "Key must be 8 to 128 characters of a-z, A-Z, 0-9 or '-'.")
        created = False
        if args.write:
            public.mkdir(parents=True, exist_ok=True)
            (public / ("%s.txt" % key)).write_text(key + "\n", encoding="utf-8")
            created = True
        cli.emit({"key": key, "file": str(public / ("%s.txt" % key)), "created": created}, args,
                 ("Created public/%s.txt (commit it on the action branch)." % key) if created else "New key (not written; add --write): %s" % key)
    if state and (created or existing):
        cfg = st.load_json(state / "config.json", {}) or {}
        cfg.setdefault("connectors", {}).setdefault("indexnow", {})["key_file"] = "public/%s.txt" % key
        st.save_json(state / "config.json", cfg)
    return cli.EXIT_OK


def cmd_check(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    cfg = st.load_config(state)
    repo = _repo(args, state)
    res: Dict[str, Any] = {"public": [str(p) for p in find_keys(repo / "public")], "dist": [str(p) for p in find_keys(repo / (cfg["site"].get("dist_dir") or "dist"))]}
    ok = bool(res["public"])
    if args.live:
        if args.fixture:
            http.use_fixture(args.fixture)
        key = Path(res["public"][0]).stem if res["public"] else Path(((cfg.get("connectors") or {}).get("indexnow") or {}).get("key_file") or "x.txt").stem
        url = args.live.rstrip("/") + "/%s.txt" % key
        try:
            r = http.fetch(url, allow_private=args.allow_private)
            res["live"] = {"url": url, "status": r.status, "ok": r.status == 200 and r.text.strip() == key}
        except http.FetchError as exc:
            res["live"] = {"url": url, "error": str(exc), "ok": False}
            cli.emit(res, args, "Live check failed: %s" % exc)
            return cli.EXIT_REMOTE
        ok = ok and res["live"]["ok"]
    human = "IndexNow key: %s; in dist: %s%s" % (res["public"][0] if res["public"] else "MISSING (indexnow.py key --write)", "yes" if res["dist"] else "no (build first)",
                                              ("; live: %s" % ("OK" if res["live"]["ok"] else "NOT SERVED")) if "live" in res else "")
    res["ok"] = ok
    cli.emit(res, args, human)
    return cli.EXIT_OK if ok else cli.EXIT_FAIL


def cmd_submit(args: Any) -> int:
    state = st.resolve_state_arg(getattr(args, "state", None))
    cfg = st.load_config(state)
    repo = _repo(args, state)
    site = (args.host and ("https://" + args.host)) or (cfg.get("site") or {}).get("url") or ((st.load_business(state) or {}).get("url") if state else None)
    if not site:
        cli.die(cli.EXIT_USAGE, "No site URL: pass --host or set config.site.url.")
    host = urllib.parse.urlsplit(site).netloc
    urls: List[str] = list(args.url or [])
    if args.from_file:
        urls += [x.strip() for x in Path(args.from_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    if args.action:
        if not state:
            cli.die(cli.EXIT_USAGE, "--action needs a state folder")
        import twwa_actions
        a = twwa_actions.load_actions(state).get(args.action)
        if not a:
            cli.die(cli.EXIT_USAGE, "Unknown action id: %s" % args.action)
        urls += [site.rstrip("/") + (p if p.startswith("/") else "/" + p) for p in a.get("pages_affected") or []]
    urls = list(dict.fromkeys(u.split("#")[0] for u in urls))
    foreign = [u for u in urls if urllib.parse.urlsplit(u).netloc != host]
    if foreign:
        cli.die(cli.EXIT_USAGE, "URLs must be on %s: %s" % (host, ", ".join(foreign[:5])))
    if not urls:
        cli.die(cli.EXIT_USAGE, "No URLs: use --url, --from-file or --action.")
    keys = find_keys(repo / "public")
    key = args.key or (keys[0].stem if keys else None)
    if not key:
        cli.die(cli.EXIT_NOCREDS, "No IndexNow key file in public/. Create one: python3 scripts/indexnow.py key --write (then deploy it).")
    payload = {"host": host, "key": key, "keyLocation": "https://%s/%s.txt" % (host, key), "urlList": urls}
    endpoint = ((cfg.get("connectors") or {}).get("indexnow") or {}).get("endpoint") or DEFAULT_ENDPOINT
    if not args.execute:
        cli.emit({"dry_run": True, "endpoint": endpoint, "payload": payload}, args,
                 "Dry run: would POST %d URL(s) to %s. Add --execute after live verification." % (len(urls), endpoint))
        return cli.EXIT_OK
    st.require_not_stopped(state)
    if args.fixture:
        http.use_fixture(args.fixture)
    try:
        r = http.post_json(endpoint, payload)
    except http.FetchError as exc:
        cli.die(cli.EXIT_REMOTE, "IndexNow request failed: %s" % exc)
    ok = r.status in (200, 202)
    if state and args.action:
        import twwa_actions
        twwa_actions.log_event(state, args.action, "indexnow_submitted", urls=urls, status=r.status, ok=ok)
    meaning = {200: "accepted", 202: "accepted, key validation pending", 400: "bad request", 403: "key not valid (key file not served?)",
               422: "URLs do not belong to the host or key mismatch", 429: "too many requests"}.get(r.status, "unexpected")
    cli.emit({"ok": ok, "status": r.status, "meaning": meaning, "urls": urls}, args, "IndexNow: %s %s (%d URL(s))" % (r.status, meaning, len(urls)))
    return cli.EXIT_OK if ok else cli.EXIT_REMOTE


def build_parser() -> Any:
    p = cli.base_parser(__doc__, "example:\n  python3 scripts/indexnow.py key --write\n  python3 scripts/indexnow.py submit --action 2026-11-a01            (dry run)\n"
                                 "  python3 scripts/indexnow.py submit --action 2026-11-a01 --execute")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "key", "show the key file in public/, or create one with --write")
    sp.add_argument("--repo")
    sp.add_argument("--key", help="use this key instead of a random one")
    sp.add_argument("--write", action="store_true")
    sp = cli.add_sub(subs, "check", "key file in public/ and dist/, optionally served live")
    sp.add_argument("--repo")
    sp.add_argument("--live", help="site base URL to fetch the key file from")
    sp.add_argument("--fixture")
    sp.add_argument("--allow-private", action="store_true")
    sp = cli.add_sub(subs, "submit", "submit changed URLs (dry run unless --execute)")
    sp.add_argument("--repo")
    sp.add_argument("--url", action="append", default=[])
    sp.add_argument("--from-file", dest="from_file")
    sp.add_argument("--action", help="submit the action's pages_affected")
    sp.add_argument("--host", help="host without scheme (default from config.site.url)")
    sp.add_argument("--key")
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--fixture")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {"key": cmd_key, "check": cmd_check, "submit": cmd_submit}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
