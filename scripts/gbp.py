#!/usr/bin/env python3
"""Google Business Profile connector (spec 9b) for TWWA's own profile and every client profile where the
authenticated Google user is owner or manager.

Reads: accounts, locations (Business Information), daily metrics and monthly search keywords (Performance),
reviews, local posts and media (v4.9), notification settings. Writes, behind the approval gate: review
replies, local posts, info edits. Every write needs --action <id>, runs `twwa_actions.py verify`, is dry-run
unless --execute, keeps 10 edits/min per profile and the 48 h identity pacing, and re-reads afterwards.
Name, address and map pin are refused in every mode. Without API access: `template` writes a snapshot file the
operator fills from the profile; `audit` and `lint` work on it the same way. Setup: references/gbp-api-setup.md."""
from __future__ import annotations

import datetime as _dt
import http.server
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twwa_lib import cli, connect, google_auth, http, state as st  # noqa: E402
from twwa_lib.stats import median  # noqa: E402
from twwa_lib.textde import fold_umlauts, norm_name  # noqa: E402

SCOPE = ["https://www.googleapis.com/auth/business.manage"]
TOKEN_FILE = os.path.expanduser("~/.config/twwa-growth/google-token.json")
ACC = "https://mybusinessaccountmanagement.googleapis.com/v1"
INFO = "https://mybusinessbusinessinformation.googleapis.com/v1"
PERF = "https://businessprofileperformance.googleapis.com/v1"
V4 = "https://mybusiness.googleapis.com/v4"
NOTIF = "https://mybusinessnotifications.googleapis.com/v1"
READ_MASK = ("name,title,storefrontAddress,phoneNumbers,categories,websiteUri,regularHours,specialHours,serviceArea,"
             "profile,metadata,serviceItems,openInfo")
METRICS = ["CALL_CLICKS", "WEBSITE_CLICKS", "BUSINESS_DIRECTION_REQUESTS", "BUSINESS_CONVERSATIONS",
           "BUSINESS_IMPRESSIONS_DESKTOP_MAPS", "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
           "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", "BUSINESS_IMPRESSIONS_MOBILE_SEARCH", "BUSINESS_BOOKINGS"]
FORBIDDEN_FIELDS = {"title", "storefrontAddress", "latlng"}
IDENTITY_FIELDS = {"categories.primaryCategory", "phoneNumbers.primaryPhone", "websiteUri"}
ALLOWED_FIELDS = {"regularHours", "specialHours", "serviceItems", "profile.description", "categories.additionalCategories",
                  "moreHours", "serviceArea"} | IDENTITY_FIELDS
SCRIPTS = Path(__file__).resolve().parent


# ---------------------------------------------------------------- auth and reads

def token() -> str:
    try:
        return google_auth.access_token(SCOPE, token_file=TOKEN_FILE)
    except google_auth.NoCredentials:
        cli.die(cli.EXIT_NOCREDS, "No Google Business Profile credentials. Run `gbp.py auth --client-secrets <file>` "
                "(see references/gbp-api-setup.md). Fallback: `gbp.py template` and fill the snapshot by hand.")
    return ""


def cmd_auth(args: Any) -> int:
    sec = st.load_json(args.client_secrets) or {}
    c = sec.get("installed") or sec.get("web") or {}
    if not c.get("client_id"):
        cli.die(cli.EXIT_USAGE, "client secrets JSON must contain installed.client_id (OAuth client type: Desktop app)")
    box: Dict[str, str] = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            box["code"] = (q.get("code") or [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("twwa-growth: Anmeldung abgeschlossen. Fenster schließen.".encode("utf-8"))

        def log_message(self, *a: Any) -> None:
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    redirect = "http://127.0.0.1:%d/" % srv.server_port
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": " ".join(SCOPE),
        "access_type": "offline", "prompt": "consent"})
    print("Open this URL and sign in with the Google user that owns or manages the profiles:\n" + url, file=sys.stderr)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    t = threading.Thread(target=srv.handle_request)
    t.start()
    t.join(timeout=300)
    if not box.get("code"):
        cli.die(cli.EXIT_USAGE, "No authorization code received within 5 minutes.")
    body = urllib.parse.urlencode({"code": box["code"], "client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    r = http.fetch("https://oauth2.googleapis.com/token", method="POST", data=body,
                   headers={"Content-Type": "application/x-www-form-urlencoded"})
    tok = json.loads(r.text or "{}")
    if not tok.get("refresh_token"):
        cli.die(cli.EXIT_REMOTE, "Token exchange failed: %s" % r.text[:300])
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as fh:
        json.dump({"type": "authorized_user", "client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                   "refresh_token": tok["refresh_token"]}, fh)
    os.chmod(TOKEN_FILE, 0o600)
    cli.emit({"token_file": TOKEN_FILE}, args, "Refresh token stored at %s (mode 600, outside every repo)." % TOKEN_FILE)
    return cli.EXIT_OK


def accounts(tok: str) -> List[Dict[str, Any]]:
    return connect.get_json(ACC + "/accounts", tok).get("accounts", [])


def locations(tok: str, account: str) -> List[Dict[str, Any]]:
    out, page = [], None
    while True:
        q = {"readMask": READ_MASK, "pageSize": 100}
        if page:
            q["pageToken"] = page
        res = connect.get_json("%s/%s/locations?%s" % (INFO, account, urllib.parse.urlencode(q)), tok)
        out += res.get("locations", [])
        page = res.get("nextPageToken")
        if not page:
            return out


def performance(tok: str, location: str, days: int = 90) -> Dict[str, Any]:
    end = st.today_date() - _dt.timedelta(days=2)
    start = end - _dt.timedelta(days=days - 1)
    q = [("dailyMetrics", m) for m in METRICS] + [
        ("dailyRange.startDate.year", start.year), ("dailyRange.startDate.month", start.month), ("dailyRange.startDate.day", start.day),
        ("dailyRange.endDate.year", end.year), ("dailyRange.endDate.month", end.month), ("dailyRange.endDate.day", end.day)]
    res = connect.get_json("%s/%s:fetchMultiDailyMetricsTimeSeries?%s" % (PERF, location, urllib.parse.urlencode(q)), tok)
    totals: Dict[str, int] = {}
    for block in res.get("multiDailyMetricTimeSeries", []):
        for s in block.get("dailyMetricTimeSeries", []):
            totals[s.get("dailyMetric")] = sum(int(v.get("value", 0) or 0) for v in (s.get("timeSeries") or {}).get("datedValues", []))
    return {"range": {"start": start.isoformat(), "end": end.isoformat()},
            "calls": totals.get("CALL_CLICKS"), "website_clicks": totals.get("WEBSITE_CLICKS"),
            "directions": totals.get("BUSINESS_DIRECTION_REQUESTS"), "messages": totals.get("BUSINESS_CONVERSATIONS"),
            "bookings": totals.get("BUSINESS_BOOKINGS"),
            "impressions_maps": (totals.get("BUSINESS_IMPRESSIONS_DESKTOP_MAPS") or 0) + (totals.get("BUSINESS_IMPRESSIONS_MOBILE_MAPS") or 0),
            "impressions_search": (totals.get("BUSINESS_IMPRESSIONS_DESKTOP_SEARCH") or 0) + (totals.get("BUSINESS_IMPRESSIONS_MOBILE_SEARCH") or 0)}


def keywords(tok: str, location: str, months: int = 3) -> List[Dict[str, Any]]:
    end = st.today_date().replace(day=1) - _dt.timedelta(days=1)
    start = (end.replace(day=1) - _dt.timedelta(days=31 * (months - 1))).replace(day=1)
    q = {"monthlyRange.startMonth.year": start.year, "monthlyRange.startMonth.month": start.month,
         "monthlyRange.endMonth.year": end.year, "monthlyRange.endMonth.month": end.month}
    res = connect.get_json("%s/%s/searchkeywords/impressions/monthly?%s" % (PERF, location, urllib.parse.urlencode(q)), tok)
    out = []
    for k in res.get("searchKeywordsCounts", []):
        iv = k.get("insightsValue") or {}
        out.append({"keyword": k.get("searchKeyword"), "impressions": int(iv["value"]) if "value" in iv else None,
                    "below_threshold": iv.get("threshold")})
    return out


def reviews(tok: str, account: str, location: str) -> List[Dict[str, Any]]:
    out, page = [], None
    lid = location.split("/")[-1]
    while True:
        q = {"pageSize": 50}
        if page:
            q["pageToken"] = page
        res = connect.get_json("%s/%s/locations/%s/reviews?%s" % (V4, account, lid, urllib.parse.urlencode(q)), tok)
        out += res.get("reviews", [])
        page = res.get("nextPageToken")
        if not page or len(out) > 2000:
            return out


STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


def review_summary(raw: List[Dict[str, Any]]) -> Dict[str, Any]:
    today = st.today_date()
    dates = [st.parse_date((r.get("createTime") or "")[:10]) for r in raw]
    stars = [STARS.get(r.get("starRating")) for r in raw if STARS.get(r.get("starRating"))]
    replied = [r for r in raw if r.get("reviewReply")]
    valid = [d for d in dates if d]
    return {"count": len(raw), "rating": round(sum(stars) / len(stars), 2) if stars else None,
            "last_30": sum(1 for d in valid if (today - d).days <= 30), "last_90": sum(1 for d in valid if (today - d).days <= 90),
            "reply_rate": round(len(replied) / len(raw), 2) if raw else None,
            "latest_date": max(valid).isoformat() if valid else None,
            "unanswered": [{"review_id": r.get("reviewId"), "date": (r.get("createTime") or "")[:10], "stars": STARS.get(r.get("starRating")),
                            "has_text": bool(r.get("comment"))} for r in raw if not r.get("reviewReply")][:20]}


def _profile(loc: Dict[str, Any]) -> Dict[str, Any]:
    cats = loc.get("categories") or {}
    addr = loc.get("storefrontAddress") or {}
    return {"name": loc.get("title"), "location": loc.get("name"),
            "primary_category": (cats.get("primaryCategory") or {}).get("displayName"),
            "secondary_categories": [c.get("displayName") for c in cats.get("additionalCategories") or []],
            "address_shown": bool(addr.get("addressLines")), "address": addr,
            "service_areas": [p.get("placeName") for p in ((loc.get("serviceArea") or {}).get("places") or {}).get("placeInfos", [])],
            "hours": loc.get("regularHours"), "services": [((s.get("freeFormServiceItem") or {}).get("label") or {}).get("displayName")
                                                           or (s.get("structuredServiceItem") or {}).get("serviceTypeId") for s in loc.get("serviceItems") or []],
            "description": (loc.get("profile") or {}).get("description"), "website_url": loc.get("websiteUri"),
            "phone": (loc.get("phoneNumbers") or {}).get("primaryPhone"),
            "maps_url": (loc.get("metadata") or {}).get("mapsUri"), "place_id": (loc.get("metadata") or {}).get("placeId")}


def _match_location(locs: List[Dict[str, Any]], business: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    want = ((business or {}).get("gbp") or {}).get("location")
    if want:
        return next((l for l in locs if l.get("name") == want), None)
    name = norm_name((business or {}).get("name"), strip_legal_form=True)
    return next((l for l in locs if norm_name(l.get("title"), strip_legal_form=True) == name), None)


def cmd_accounts(args: Any) -> int:
    cli.emit(accounts(token()), args)
    return cli.EXIT_OK


def cmd_locations(args: Any) -> int:
    tok = token()
    out = []
    for a in accounts(tok):
        for l in locations(tok, a["name"]):
            out.append({"account": a["name"], "location": l.get("name"), "title": l.get("title"),
                        "category": ((l.get("categories") or {}).get("primaryCategory") or {}).get("displayName")})
    cli.emit(out, args, "\n".join("%s  %s  %s" % (o["location"], o["title"], o["category"]) for o in out))
    return cli.EXIT_OK


def _account_for(tok: str, location: str) -> str:
    for a in accounts(tok):
        if any(l.get("name") == location for l in locations(tok, a["name"])):
            return a["name"]
    cli.die(cli.EXIT_USAGE, "location %s is not accessible with these credentials" % location)
    return ""


def cmd_read(args: Any) -> int:
    tok = token()
    loc = args.location
    if args.cmd == "get":
        res: Any = connect.get_json("%s/%s?readMask=%s" % (INFO, loc, READ_MASK), tok)
    elif args.cmd == "performance":
        res = {"performance": performance(tok, loc, args.days), "keywords": keywords(tok, loc)}
    elif args.cmd == "reviews":
        res = review_summary(reviews(tok, _account_for(tok, loc), loc))
    elif args.cmd == "posts":
        acc = _account_for(tok, loc)
        res = connect.get_json("%s/%s/locations/%s/localPosts" % (V4, acc, loc.split("/")[-1]), tok).get("localPosts", [])
    elif args.cmd == "media":
        acc = _account_for(tok, loc)
        res = connect.get_json("%s/%s/locations/%s/media" % (V4, acc, loc.split("/")[-1]), tok)
    else:
        acc = _account_for(tok, loc)
        res = connect.get_json("%s/%s/notificationSetting" % (NOTIF, acc), tok)
    cli.emit(res, args)
    return cli.EXIT_OK


def snapshot_for(tok: str, account: str, loc: Dict[str, Any]) -> Dict[str, Any]:
    name = loc.get("name")
    lid = name.split("/")[-1]
    posts = connect.get_json("%s/%s/locations/%s/localPosts" % (V4, account, lid), tok).get("localPosts", [])
    media = connect.get_json("%s/%s/locations/%s/media" % (V4, account, lid), tok)
    items = media.get("mediaItems", [])
    prof = _profile(loc)
    prof["photos_count"] = media.get("totalMediaItemCount", len(items))
    prof["latest_photo_date"] = max(((m.get("createTime") or "")[:10] for m in items), default=None)
    return {"profile": prof, "reviews": review_summary(reviews(tok, account, name)), "performance": performance(tok, name),
            "keywords": keywords(tok, name), "posts": [{"date": (p.get("createTime") or "")[:10], "topic": p.get("topicType"),
                                                        "state": p.get("state")} for p in posts[:20]],
            "media": {"count": prof["photos_count"], "latest": prof["latest_photo_date"]}}


def cmd_snapshot(args: Any) -> int:
    state = st.require_state(args)
    business = st.load_business(state)
    if args.from_file:
        data = st.load_json(args.from_file)
        path = connect.write_snapshot(state, "gbp", data, "manual")
        cli.emit({"snapshot": path}, args, "GBP snapshot (manual): %s" % path)
        return cli.EXIT_OK
    tok = token()
    snaps = []
    for a in accounts(tok):
        for l in locations(tok, a["name"]):
            if args.all or l is _match_location([l], business):
                snaps.append(snapshot_for(tok, a["name"], l))
    if not snaps:
        cli.die(cli.EXIT_USAGE, "No accessible location matches business.json (set business.gbp.location to 'locations/<id>').")
    payload = dict(snaps[0])
    if args.all:
        payload["locations"] = snaps
    prev = st.load_latest_snapshot(state, "gbp")
    if prev and prev.get("competitors"):
        payload["competitors"] = prev["competitors"]
    path = connect.write_snapshot(state, "gbp", payload, "api")
    cli.emit({"snapshot": path, "locations": len(snaps)}, args, "GBP snapshot: %s" % path)
    return cli.EXIT_OK


def cmd_template(args: Any) -> int:
    state = st.require_state(args)
    b = st.load_business(state) or {}
    tpl = {"source": "gbp", "origin": "manual", "filled_by": None, "filled_on": None,
           "instructions_de": "Werte direkt aus dem Unternehmensprofil übernehmen (Google Maps, angemeldet als Inhaber/Manager). Unbekanntes leer lassen (null), nichts schätzen.",
           "profile": {"name": b.get("name"), "primary_category": None, "secondary_categories": [], "address_shown": None,
                       "service_areas": [], "hours": None, "services": [], "attributes": [], "description": None,
                       "website_url": None, "phone": None, "photos_count": None, "latest_photo_date": None},
           "reviews": {"count": None, "rating": None, "last_30": None, "last_90": None, "reply_rate": None, "latest_date": None},
           "performance": {"calls": None, "website_clicks": None, "directions": None, "messages": None,
                           "impressions_maps": None, "impressions_search": None},
           "competitors": [{"name": None, "primary_category": None, "review_count": None, "rating": None, "last_90": None}]}
    out = Path(args.out) if args.out else st.snapshot_dir(state) / "gbp.manual-template.json"
    st.save_json(out, tpl)
    cli.emit({"template": str(out)}, args, "Template written: %s. Fill it, then `gbp.py snapshot --from-file %s`." % (out, out))
    return cli.EXIT_OK


# ---------------------------------------------------------------- audit and lint

def _f(fid: str, sev: str, title: str, detail: str, value: Any = None, status: str = "verified", group: int = 2,
       action: str = "gbp_content_edit") -> Dict[str, Any]:
    return cli.finding(fid, "gbp", sev, title, detail, {"url": None, "snippet": "GBP-Snapshot", "value": value}, status=status,
                       action_type=action, priority_group=group)


def audit(snap: Optional[Dict[str, Any]], business: Dict[str, Any], winners: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if not snap:
        return [_f("gbp.snapshot.missing", "P2", "Unternehmensprofil nicht geprüft",
                   "Kein GBP-Snapshot vorhanden. API einrichten oder `gbp.py template` ausfüllen.", status="not_checked")]
    p, r = snap.get("profile") or {}, snap.get("reviews") or {}
    api = snap.get("origin") == "api"
    gone = lambda v: v in ("", [], {}) or (v is None and api)  # noqa: E731  manual snapshots: null = unknown, not missing
    out: List[Dict[str, Any]] = []
    today = st.today_date()
    want_cat = (business.get("gbp") or {}).get("primary_category")
    if p.get("primary_category") is None:
        out.append(_f("gbp.category.unknown", "P2", "Hauptkategorie unbekannt", "Hauptkategorie im Snapshot fehlt.", status="not_checked"))
    elif want_cat and fold_umlauts(p["primary_category"].lower()) != fold_umlauts(want_cat.lower()):
        out.append(_f("gbp.category.mismatch", "P1", "Hauptkategorie passt nicht zur Kernleistung",
                      "Profil: „%s“, Soll laut business.json: „%s“. Die Hauptkategorie ist der stärkste Faktor im Local Pack." % (p["primary_category"], want_cat),
                      p["primary_category"], action="gbp_identity_edit"))
    win_cats = [w.get("category") for w in winners or [] if w.get("category")]
    if win_cats and p.get("primary_category") and all(fold_umlauts(c.lower()) != fold_umlauts(p["primary_category"].lower()) for c in win_cats):
        out.append(_f("gbp.category.differs_from_winners", "P2", "Kategorie weicht von den Pack-Gewinnern ab",
                      "Gewinner nutzen: %s; Profil: %s. Nur ändern, wenn die Kategorie die Kernleistung wirklich beschreibt." % (", ".join(sorted(set(win_cats))), p["primary_category"]),
                      win_cats, status="hypothesis", action="gbp_identity_edit"))
    services = {fold_umlauts((s.get("name") or "").lower()) for s in business.get("services", [])}
    have = {fold_umlauts((s or "").lower()) for s in p.get("services") or []}
    missing = sorted(services - have) if (p.get("services") is not None and (api or p.get("services"))) else []
    if missing:
        out.append(_f("gbp.services.missing", "P3", "Leistungen im Profil fehlen", "Nicht im Profil: %s." % ", ".join(missing), missing))
    if gone(p.get("description")):
        out.append(_f("gbp.description.missing", "P3", "Beschreibung fehlt", "Keine Profilbeschreibung (hilft Conversion, nicht Ranking)."))
    if gone(p.get("hours")):
        out.append(_f("gbp.hours.missing", "P2", "Öffnungszeiten fehlen", "Ohne Öffnungszeiten wirkt das Profil unvollständig und verliert Anrufe."))
    lp = st.parse_date(p.get("latest_photo_date"))
    if lp and (today - lp).days > 90:
        out.append(_f("gbp.photos.stale", "P3", "Keine neuen Fotos seit %d Tagen" % (today - lp).days,
                      "Neue Projektfotos aus dem monatlichen Projektbericht hochladen.", p.get("latest_photo_date")))
    from urllib.parse import urlparse
    host = lambda u: urlparse(u or "").netloc.lower().replace("www.", "")  # noqa: E731
    if p.get("website_url") and business.get("url") and host(p["website_url"]) != host(business["url"]):
        out.append(_f("gbp.website.mismatch", "P1", "Website-Link zeigt nicht auf die Kunden-Website",
                      "Profil: %s; erwartet: %s." % (p["website_url"], business["url"]), p["website_url"], action="gbp_identity_edit"))
    if r.get("reply_rate") is not None and r["reply_rate"] < 0.8:
        out.append(cli.finding("reviews.reply_rate.low", "reviews", "P3", "Antwortquote auf Bewertungen niedrig",
                               "Antwortquote %d%% (Ziel ≥ 80%%)." % round(r["reply_rate"] * 100), {"value": r["reply_rate"]},
                               action_type="review_reply", priority_group=4))
    ld = st.parse_date(r.get("latest_date"))
    if ld and (today - ld).days > 45:
        out.append(cli.finding("reviews.recency.stale", "reviews", "P2", "Letzte Bewertung vor %d Tagen" % (today - ld).days,
                               "Aktualität zählt: Ziel ist mindestens eine neue Bewertung pro Monat.", {"value": r.get("latest_date")},
                               action_type="review_engine", priority_group=4))
    comp = [c.get("review_count") for c in (winners or snap.get("competitors") or []) if c.get("review_count") or c.get("reviews")]
    comp = [c for c in comp if c]
    if comp and r.get("count") is not None and r["count"] < 0.5 * median(comp):
        out.append(cli.finding("reviews.count.below_winners", "reviews", "P2", "Deutlich weniger Bewertungen als die Gewinner",
                               "%d gegenüber Median %d der Gewinner." % (r["count"], median(comp)), {"value": r["count"]},
                               action_type="review_engine", priority_group=4))
    return out


def lint(snap: Dict[str, Any], business: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suspension-risk lint (dossier 03 §2): stuffed names, hidden or virtual addresses, mismatches."""
    p = (snap or {}).get("profile") or {}
    out: List[Dict[str, Any]] = []
    legal = norm_name(business.get("name"), strip_legal_form=True)
    shown = norm_name(p.get("name"), strip_legal_form=True)
    if shown and legal and shown != legal:
        extra = set(shown.split()) - set(legal.split())
        towns = {fold_umlauts(t["town"].lower()) for t in business.get("service_area", [])}
        trade = fold_umlauts((business.get("trade") or "").lower())
        stuffed = [w for w in extra if fold_umlauts(w) in towns or fold_umlauts(w) == trade or len(w) > 3]
        if stuffed:
            out.append(_f("gbp.name.keyword_stuffing", "P1", "Profilname enthält Zusätze außerhalb des echten Firmennamens",
                          "Zusätzliche Wörter: %s. Sperr-Risiko; Name nur von Hand an den echten Namen anpassen (R3)." % ", ".join(sorted(stuffed)),
                          sorted(stuffed), action="gbp_identity_edit"))
    if p.get("address_shown") and business.get("customers_received_at_address") is False:
        out.append(_f("gbp.address.shown_without_customers", "P1", "Adresse sichtbar, obwohl dort keine Kunden empfangen werden",
                      "Service-Area-Betriebe blenden die Adresse aus. Änderung nur von Hand (R3).", action="gbp_identity_edit"))
    if business.get("address_public") is False and p.get("address_shown"):
        out.append(_f("gbp.address.unexpected", "P2", "Adresse im Profil sichtbar, laut business.json nicht öffentlich", "Abgleichen."))
    for w in ("c/o", "postfach", "virtual", "coworking", "business center", "businesscenter"):
        if w in json.dumps(p.get("address") or {}, ensure_ascii=False).lower():
            out.append(_f("gbp.address.virtual", "P1", "Adresse wirkt wie Postfach oder virtuelles Büro", "Fund: „%s“. Hohe Sperrgefahr." % w))
    from twwa_lib.textde import norm_phone
    if p.get("phone") and business.get("phone") and norm_phone(p["phone"]) not in [norm_phone(business["phone"])] + [norm_phone(t) for t in business.get("tracking_numbers") or []]:
        out.append(_f("gbp.phone.mismatch", "P2", "Telefonnummer weicht ab", "Profil %s, business.json %s." % (p["phone"], business["phone"])))
    return out


def _snap(args: Any, state: Path) -> Optional[Dict[str, Any]]:
    return st.load_json(args.file) if getattr(args, "file", None) else st.load_latest_snapshot(state, "gbp")


def _winners(state: Path) -> List[Dict[str, Any]]:
    tds = sorted((state / "teardowns").glob("*/summary.json")) if (state / "teardowns").is_dir() else []
    if not tds:
        return []
    return (st.load_json(tds[-1]) or {}).get("pack_winners", [])


def cmd_audit(args: Any) -> int:
    state = st.require_state(args)
    found = audit(_snap(args, state), st.load_business(state) or {}, _winners(state))
    cli.emit(found, args, cli.render_findings_de(found, "GBP-Audit"))
    return cli.EXIT_FAIL if cli.at_or_above(found, args.fail_on) else cli.EXIT_OK


def cmd_lint(args: Any) -> int:
    state = st.require_state(args)
    found = lint(_snap(args, state) or {}, st.load_business(state) or {})
    cli.emit(found, args, cli.render_findings_de(found, "GBP-Sperrrisiko"))
    return cli.EXIT_FAIL if any(f["severity"] == "P1" for f in found) else cli.EXIT_OK


# ---------------------------------------------------------------- pacing and writes

def _ledger(state: Path) -> Path:
    return state / "gbp-ledger.jsonl"


def pacing_ok(state: Path, identity: bool, hours: int) -> Optional[str]:
    rows = st.read_jsonl(_ledger(state))
    now = time.time()
    recent = [r for r in rows if now - (st.parse_ts(r.get("ts")) or _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)).timestamp() < 60]
    if len(recent) >= 10:
        return "10 edits per minute per profile reached"
    if identity:
        last = [r for r in rows if r.get("identity")]
        if last:
            ts = st.parse_ts(last[-1]["ts"])
            if ts and now - ts.timestamp() < hours * 3600:
                return "identity-level edit within the last %d h (%s)" % (hours, last[-1]["ts"])
    return None


def cmd_pacing(args: Any) -> int:
    state = st.require_state(args)
    hours = (st.load_config(state).get("gbp") or {}).get("pacing_hours", 48)
    block = pacing_ok(state, True, hours)
    cli.emit({"identity_edit_allowed": block is None, "reason": block, "ledger": st.read_jsonl(_ledger(state))[-10:]}, args,
             "Identity edit allowed now." if block is None else "Blocked: %s" % block)
    return cli.EXIT_OK if block is None else cli.EXIT_BLOCKED


def _verify(action: str, state: Path) -> None:
    p = subprocess.run([sys.executable, str(SCRIPTS / "twwa_actions.py"), "verify", action, "--state", str(state)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        cli.die(cli.EXIT_BLOCKED, "Approval for %s does not verify; nothing is written.\n%s" % (action, (p.stderr or p.stdout).strip()))


def _gate(args: Any, identity: bool = False) -> Path:
    state = st.require_state(args)
    st.require_not_stopped(state)
    cfg = st.load_config(state)
    if (cfg.get("gbp") or {}).get("writes", "approved") != "approved":
        cli.die(cli.EXIT_BLOCKED, "config.gbp.writes is not 'approved': GBP writes are disabled.")
    if not args.action:
        cli.die(cli.EXIT_USAGE, "--action <action_id> is required for every write")
    _verify(args.action, state)
    block = pacing_ok(state, identity, (cfg.get("gbp") or {}).get("pacing_hours", 48))
    if block:
        cli.die(cli.EXIT_BLOCKED, "Pacing: %s" % block)
    return state


def _do_write(args: Any, state: Path, method: str, url: str, body: Dict[str, Any], identity: bool, reread: str) -> int:
    plan = {"method": method, "url": url.split("?")[0], "body": body, "action": args.action}
    if not args.execute:
        cli.emit({"dry_run": True, **plan}, args, "Dry run: %s %s\n%s\nRe-run with --execute." % (method, plan["url"], json.dumps(body, ensure_ascii=False, indent=1)))
        return cli.EXIT_OK
    tok = token()
    res = connect.get_json(url, tok, method, body)
    st.append_jsonl(_ledger(state), {"ts": st.now_iso(), "action_id": args.action, "method": method, "url": plan["url"], "identity": identity})
    after = connect.get_json(reread, tok) if reread else None
    st.append_jsonl(state / "actions.jsonl", {"ts": st.now_iso(), "action_id": args.action, "event": "connector_write",
                                              "connector": "gbp", "request": plan, "confirmed": bool(after or res)})
    cli.emit({"ok": True, "response": res, "reread": after}, args, "Written and re-read.")
    return cli.EXIT_OK


def cmd_reply(args: Any) -> int:
    state = _gate(args)
    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    from legal_lint import lint_text  # type: ignore  # noqa: E402
    issues = [i for i in lint_text(text, "review_reply") if i.get("level") == "block"]
    if issues:
        cli.die(cli.EXIT_BLOCKED, "Reply fails legal lint: %s" % issues)
    url = "%s/%s/locations/%s/reviews/%s/reply" % (V4, args.account, args.location.split("/")[-1], args.review_id)
    return _do_write(args, state, "PUT", url, {"comment": text}, False, "")


def cmd_post(args: Any) -> int:
    state = _gate(args)
    body = st.load_json(args.post_file)
    if not isinstance(body, dict) or "summary" not in body:
        cli.die(cli.EXIT_USAGE, "post file must be a localPost JSON with at least 'summary' (and languageCode 'de')")
    body.setdefault("languageCode", "de")
    url = "%s/%s/locations/%s/localPosts" % (V4, args.account, args.location.split("/")[-1])
    return _do_write(args, state, "POST", url, body, False, "")


def cmd_update(args: Any) -> int:
    fields = [f.strip() for f in args.mask.split(",") if f.strip()]
    bad = [f for f in fields if f.split(".")[0] in FORBIDDEN_FIELDS]
    if bad:
        cli.die(cli.EXIT_BLOCKED, "Refused: %s. Name, address and pin are never written by a script (R3, human only)." % ", ".join(bad))
    unknown = [f for f in fields if f not in ALLOWED_FIELDS]
    if unknown:
        cli.die(cli.EXIT_USAGE, "Unsupported update fields: %s (allowed: %s)" % (", ".join(unknown), ", ".join(sorted(ALLOWED_FIELDS))))
    identity = any(f in IDENTITY_FIELDS for f in fields)
    state = _gate(args, identity)
    body = st.load_json(args.body_file)
    url = "%s/%s?updateMask=%s" % (INFO, args.location, urllib.parse.quote(",".join(fields)))
    return _do_write(args, state, "PATCH", url, body, identity, "%s/%s?readMask=%s" % (INFO, args.location, READ_MASK))


def main() -> int:
    p = cli.base_parser(__doc__, "example:\n  gbp.py snapshot\n  gbp.py reply --action 2026-11-a07 --account accounts/1 --location locations/2 --review-id X --text-file drafts/2026-11-a07/reply.txt --execute")
    subs = cli.add_subcommands(p)
    sp = cli.add_sub(subs, "auth", "OAuth installed-app flow; stores the refresh token outside every repo")
    sp.add_argument("--client-secrets", required=True)
    sp.set_defaults(fn=cmd_auth)
    cli.add_sub(subs, "accounts", "accessible accounts").set_defaults(fn=cmd_accounts)
    cli.add_sub(subs, "locations", "all accessible locations (TWWA's and clients')").set_defaults(fn=cmd_locations)
    for name in ("get", "performance", "reviews", "posts", "media", "notifications"):
        sp = cli.add_sub(subs, name, "read %s for one location" % name)
        sp.add_argument("location", help="locations/<id>")
        sp.add_argument("--days", type=int, default=90)
        sp.set_defaults(fn=cmd_read)
    sp = cli.add_sub(subs, "snapshot", "write snapshots/<date>/gbp.json")
    sp.add_argument("--all", action="store_true", help="every accessible location")
    sp.add_argument("--from-file", default=None, help="filled manual template")
    sp.set_defaults(fn=cmd_snapshot)
    sp = cli.add_sub(subs, "template", "manual snapshot template (no API access needed)")
    sp.add_argument("--out", default=None)
    sp.set_defaults(fn=cmd_template)
    for name, fn in (("audit", cmd_audit), ("lint", cmd_lint)):
        sp = cli.add_sub(subs, name, "field audit against business.json and pack winners" if name == "audit" else "suspension-risk lint")
        sp.add_argument("--file", default=None, help="snapshot file (default: latest)")
        sp.add_argument("--fail-on", default=None)
        sp.set_defaults(fn=fn)
    cli.add_sub(subs, "pacing", "48 h identity pacing and edit rate").set_defaults(fn=cmd_pacing)
    for name, fn in (("reply", cmd_reply), ("post", cmd_post), ("update", cmd_update)):
        sp = cli.add_sub(subs, name, "%s (approval-gated, dry run unless --execute)" % name)
        sp.add_argument("--action", required=False)
        sp.add_argument("--location", required=True)
        sp.add_argument("--execute", action="store_true")
        if name in ("reply", "post"):
            sp.add_argument("--account", required=True)
        if name == "reply":
            sp.add_argument("--review-id", required=True)
            sp.add_argument("--text-file", required=True)
        elif name == "post":
            sp.add_argument("--post-file", required=True)
        else:
            sp.add_argument("--mask", required=True, help="comma-separated update mask")
            sp.add_argument("--body-file", required=True)
        sp.set_defaults(fn=fn)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
