"""Shared helpers for the twwa-growth unittest suites (no network, temporary folders only)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIX = ROOT / "tests" / "fixtures" / "musterbetrieb"
TODAY = "2026-11-17"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("TWWA_TODAY", TODAY)


def env(**extra: str) -> Dict[str, str]:
    e = dict(os.environ)
    e["TWWA_TODAY"] = TODAY
    e.pop("TWWA_STATE_DIR", None)
    e.update(extra)
    return e


def run(script: str, *args: str, cwd: Optional[str] = None, extra_env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    p = subprocess.run([sys.executable, str(SCRIPTS / script)] + list(args), capture_output=True, text=True, cwd=cwd, env=env(**(extra_env or {})))
    return p.returncode, p.stdout, p.stderr


def run_json(script: str, *args: str, **kw: Any) -> Tuple[int, Any]:
    code, out, err = run(script, *(list(args) + ["--json"]), **kw)
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        raise AssertionError("not JSON (exit %s): %s\nstderr: %s" % (code, out[:500], err[:500]))


class TempClient:
    """A temporary client repo: fixture repo plus the fixture state folder inside it."""

    def __init__(self, git: bool = False):
        self.tmp = Path(tempfile.mkdtemp(prefix="twwa-test-"))
        self.repo = self.tmp / "repo"
        shutil.copytree(FIX / "repo", self.repo)
        shutil.copytree(FIX / ".twwa-growth", self.repo / ".twwa-growth")
        self.state = self.repo / ".twwa-growth"
        if git:
            self.git("init", "-q", "-b", "main")
            self.git("config", "user.name", "Test")
            self.git("config", "user.email", "test@musterbetrieb.example")
            self.git("config", "commit.gpgsign", "false")
            self.git("add", "-A")
            self.git("commit", "-q", "-m", "init")

    def git(self, *args: str) -> str:
        p = subprocess.run(["git", "-C", str(self.repo)] + list(args), capture_output=True, text=True)
        if p.returncode != 0:
            raise AssertionError("git %s: %s" % (" ".join(args), p.stderr))
        return p.stdout.strip()

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


def ids(findings: List[Dict[str, Any]]) -> List[str]:
    return [f["id"] for f in findings]
