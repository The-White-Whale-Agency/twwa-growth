#!/usr/bin/env python3
"""Cookieless lead attribution without personal data. leads.jsonl stores per lead: date, channel (form, call,
whatsapp, email, gbp_call, gbp_message), landing page, self-reported source ("Wie haben Sie uns gefunden?"),
service, town, qualified (yes/no/unknown) and outcome. Never names, phone numbers or message text.
`probe` is the synthetic form test through the honeypot path and refuses any host but the configured client domain."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, http, state as st  # noqa: E402

CHANNELS = ("form", "call", "whatsapp", "email", "gbp_call", "gbp_message", "gbp_booking", "other")
SOURCES = ("google_suche", "google_maps", "ki_assistent", "empfehlung", "portal", "social", "werbung", "sonstiges", "unbekannt")
PII_KEYS = {"name", "email", "phone", "telefon", "message", "nachricht", "address", "adresse"}


def _path(state: Path) -> Path:
    return state / "leads.jsonl"


def add(state: Path, rec: Dict[str, Any]) -> Dict[str, Any]:
    bad = [k for k in rec if k.lower() in PII_KEYS]
    if bad:
        cli.die(cli.EXIT_BLOCKED, "Refused: personal data fields %s are never stored (data.pii = never)." % bad)
    rec = {"date": rec.get("date") or st.today(), "channel": rec.get("channel", "other"), "page": rec.get("page"),
           "source": rec.get("source", "unbekannt"), "service": rec.get("service"), "town": rec.get("town"),
           "qualified": rec.get("qualified", "unknown"), "outcome": rec.get("outcome"), "id": rec.get("id") or "L%s-%04d" % (st.today().replace("-", ""), len(st.read_jsonl(_path(state))) + 1)}
    st.append_jsonl(_path(state), rec)
    return rec


def cmd_add(args: Any) -> int:
    state = st.require_state(args)
    rec = add(state, {"channel": args.channel, "page": args.page, "source": args.source, "service": args.service, "town": args.town,
                      "qualified": args.qualified, "date": args.date})
    cli.emit(rec, args, "Lead %s erfasst." % rec["id"])
    return cli.EXIT_OK


def cmd_import_events(args: Any) -> int:
    """Import tagged notification events ({"date","channel","page","source","service","town"} per line, no PII) or Vercel custom events."""
    state = st.require_state(args)
    n = 0
    for line in Path(args.file).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            e = {k: v for k, v in (e.get("props") or e).items() if k.lower() not in PII_KEYS}
            add(state, e)
            n += 1
    cli.emit({"imported": n}, args, "%d Ereignisse importiert (personenbezogene Felder verworfen)." % n)
    return cli.EXIT_OK


def qualify_rules(rec: Dict[str, Any], b: Dict[str, Any]) -> str:
    towns = {t["town"].lower() for t in b.get("service_area", [])}
    services = {s["id"] for s in b.get("services", [])}
    if rec.get("town") and rec["town"].lower() not in towns:
        return "no"
    if rec.get("service") and rec["service"] not in services:
        return "no"
    return "yes" if rec.get("service") and rec.get("town") else "unknown"


def cmd_qualify(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    rows = st.read_jsonl(_path(state))
    for r in rows:
        if r.get("qualified") in (None, "unknown"):
            r["qualified"] = qualify_rules(r, b)
    tmp = _path(state).with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(_path(state))
    cli.emit({"leads": len(rows)}, args, "Qualifiziert nach Regeln (Leistung im Angebot, Ort im Einzugsgebiet).")
    return cli.EXIT_OK


def summary(state: Path, month: str) -> Dict[str, Any]:
    rows = [r for r in st.read_jsonl(_path(state)) if (r.get("date") or "").startswith(month)]
    q = [r for r in rows if r.get("qualified") == "yes"]
    return {"month": month, "total": len(rows), "qualified": len(q), "unknown": sum(1 for r in rows if r.get("qualified") == "unknown"),
            "by_channel": dict(Counter(r.get("channel") for r in rows)), "by_source": dict(Counter(r.get("source") for r in rows)),
            "by_page": dict(Counter(r.get("page") for r in rows if r.get("page"))),
            "won": sum(1 for r in rows if r.get("outcome") == "won")}


def cmd_summary(args: Any) -> int:
    state = st.require_state(args)
    s = summary(state, args.month or st.today()[:7])
    st.save_json(st.snapshot_dir(state) / "leads.json", dict(s, source="leads", pulled_at=st.now_iso(), origin="manual"))
    cli.emit(s, args, "%s: %d Anfragen, davon %d qualifiziert (%d unklar). Kanäle: %s" % (s["month"], s["total"], s["qualified"], s["unknown"], s["by_channel"]))
    return cli.EXIT_OK


def cmd_outcome(args: Any) -> int:
    state = st.require_state(args)
    rows = st.read_jsonl(_path(state))
    hit = [r for r in rows if r.get("id") == args.id]
    if not hit:
        cli.die(cli.EXIT_USAGE, "lead %s not found" % args.id)
    hit[0]["outcome"] = args.outcome
    _path(state).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    cli.emit(hit[0], args, "%s -> %s" % (args.id, args.outcome))
    return cli.EXIT_OK


def cmd_probe(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    target = urlparse(args.endpoint)
    allowed = urlparse(b.get("url") or "").netloc.replace("www.", "")
    if not allowed or target.netloc.replace("www.", "") != allowed:
        cli.die(cli.EXIT_BLOCKED, "Refused: probe only runs against the client's own domain (%s)." % allowed)
    st.require_not_stopped(state)
    body = {"name": "twwa-probe", "email": "probe@%s" % allowed, "message": "Synthetischer Formulartest (twwa-growth)", "_twwa_probe": "1",
            "website": ""}  # honeypot field stays empty; handler must short-circuit on _twwa_probe
    if not args.execute:
        cli.emit({"dry_run": True, "endpoint": args.endpoint}, args, "Dry run: POST %s with the probe flag. Re-run with --execute." % args.endpoint)
        return cli.EXIT_OK
    try:
        r = http.post_json(args.endpoint, body, headers={"X-TWWA-Probe": "1"})
    except http.FetchError as ex:
        cli.die(cli.EXIT_REMOTE, str(ex))
    ok = r.status in (200, 202, 204)
    res = {"endpoint": args.endpoint, "status": r.status, "ok": ok}
    if not ok:
        res["finding"] = cli.finding("tracking.form.pipeline_failed", "tracking", "P1", "Kontaktformular liefert nicht",
                                     "Synthetischer Test: HTTP %s." % r.status, {"url": args.endpoint, "value": r.status}, action_type="tracking_fix", priority_group=1)
    cli.emit(res, args, "Formular-Test: HTTP %s (%s)" % (r.status, "ok" if ok else "FEHLER"))
    return cli.EXIT_OK if ok else cli.EXIT_FAIL


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  leads.py add --channel form --page /fassadensanierung --source google_maps --service fassadensanierung --town Musterstadt")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "add", "add one lead (no personal data)")
    sp.add_argument("--channel", choices=CHANNELS, required=True)
    sp.add_argument("--page", default=None)
    sp.add_argument("--source", choices=SOURCES, default="unbekannt")
    sp.add_argument("--service", default=None)
    sp.add_argument("--town", default=None)
    sp.add_argument("--qualified", choices=("yes", "no", "unknown"), default="unknown")
    sp.add_argument("--date", default=None)
    sp.set_defaults(fn=cmd_add)
    sp = cli.add_sub(subs, "import-events", "import tagged events (JSON lines)")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_import_events)
    cli.add_sub(subs, "qualify", "rule-based qualification").set_defaults(fn=cmd_qualify)
    sp = cli.add_sub(subs, "summary", "monthly aggregates -> snapshots/<date>/leads.json")
    sp.add_argument("--month", default=None)
    sp.set_defaults(fn=cmd_summary)
    sp = cli.add_sub(subs, "outcome", "record won/lost for a lead")
    sp.add_argument("id")
    sp.add_argument("outcome", choices=("won", "lost", "open"))
    sp.set_defaults(fn=cmd_outcome)
    sp = cli.add_sub(subs, "probe", "synthetic form test against the client's own endpoint")
    sp.add_argument("endpoint")
    sp.add_argument("--execute", action="store_true")
    sp.set_defaults(fn=cmd_probe)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
