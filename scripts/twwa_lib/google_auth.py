"""Google access tokens without third-party packages.

Order: ``GOOGLE_ACCESS_TOKEN``; else ``GOOGLE_APPLICATION_CREDENTIALS`` (authorized-user file with a
refresh token, or a service-account key signed with the ``openssl`` binary); else
``gcloud auth print-access-token`` when gcloud is installed. Raises ``NoCredentials`` with setup text.
Tokens are never printed or written into a repository.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from typing import Dict, Optional, Sequence, Tuple

from . import http

TOKEN_URL = "https://oauth2.googleapis.com/token"
_CACHE: Dict[Tuple[str, ...], Tuple[str, float]] = {}

SETUP_TEXT = """No Google credentials found. Options (pick one):
  1. GOOGLE_ACCESS_TOKEN=<short-lived token> for a one-off run.
  2. GOOGLE_APPLICATION_CREDENTIALS=<path outside the repo> pointing to
     - an authorized-user JSON (client_id, client_secret, refresh_token), or
     - a service-account key JSON whose e-mail is added as a user to the Search Console property.
  3. Install gcloud and run: gcloud auth application-default login --scopes=<scopes>
Without credentials the step reports "nicht geprüft" and continues."""


class NoCredentials(Exception):
    def __init__(self, msg: str = SETUP_TEXT):
        super().__init__(msg)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign_rs256(message: bytes, private_key_pem: str) -> bytes:
    openssl = shutil.which("openssl")
    if not openssl:
        raise NoCredentials("Service-account signing needs the openssl binary, which was not found on PATH.")
    fd, keypath = tempfile.mkstemp(prefix="twwa-sa-", suffix=".pem")
    try:
        os.chmod(keypath, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(private_key_pem)
        proc = subprocess.run([openssl, "dgst", "-sha256", "-sign", keypath], input=message, capture_output=True, check=False)
        if proc.returncode != 0:
            raise NoCredentials("openssl could not sign the service-account JWT: %s" % proc.stderr.decode("utf-8", "replace")[:200])
        return proc.stdout
    finally:
        try:
            os.unlink(keypath)
        except OSError:
            pass


def _token_request(fields: Dict[str, str]) -> Tuple[str, float]:
    body = urllib.parse.urlencode(fields).encode("ascii")
    r = http.fetch(TOKEN_URL, method="POST", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, follow_redirects=False)
    if r.status != 200:
        raise NoCredentials("Google token endpoint answered %s; check the credentials file (contents not shown)." % r.status)
    data = r.json()
    return data["access_token"], time.time() + float(data.get("expires_in", 3600)) - 60


def _from_file(path: str, scopes: Sequence[str]) -> Tuple[str, float]:
    with open(path, "r", encoding="utf-8") as fh:
        info = json.load(fh)
    kind = info.get("type")
    if kind == "authorized_user" or "refresh_token" in info:
        return _token_request({
            "grant_type": "refresh_token",
            "client_id": info["client_id"],
            "client_secret": info["client_secret"],
            "refresh_token": info["refresh_token"],
        })
    if kind == "service_account":
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        claims = {"iss": info["client_email"], "scope": " ".join(scopes), "aud": info.get("token_uri", TOKEN_URL), "iat": now, "exp": now + 3600}
        signing_input = (_b64(json.dumps(header).encode()) + "." + _b64(json.dumps(claims).encode())).encode("ascii")
        sig = _sign_rs256(signing_input, info["private_key"])
        assertion = signing_input.decode("ascii") + "." + _b64(sig)
        return _token_request({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
    raise NoCredentials("Unsupported credentials file type %r in GOOGLE_APPLICATION_CREDENTIALS." % kind)


def access_token(scopes: Sequence[str], token_file: Optional[str] = None) -> str:
    """Return a bearer token for ``scopes``. ``token_file`` optionally names an authorized-user JSON to try
    after GOOGLE_APPLICATION_CREDENTIALS (for example a token stored outside every repo)."""
    key = tuple(sorted(scopes))
    cached = _CACHE.get(key)
    if cached and cached[1] > time.time():
        return cached[0]
    env_tok = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if env_tok:
        return env_tok.strip()
    for path in (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"), token_file):
        if path and os.path.isfile(os.path.expanduser(path)):
            tok, exp = _from_file(os.path.expanduser(path), scopes)
            _CACHE[key] = (tok, exp)
            return tok
    gcloud = shutil.which("gcloud")
    if gcloud:
        proc = subprocess.run([gcloud, "auth", "print-access-token"], capture_output=True, check=False, timeout=60)
        if proc.returncode == 0 and proc.stdout.strip():
            tok = proc.stdout.decode("ascii", "replace").strip()
            _CACHE[key] = (tok, time.time() + 1800)
            return tok
    raise NoCredentials()
