"""Small statistics: Wilson interval, percentage change, median, difference in differences."""
from __future__ import annotations

import math
from typing import Dict, Iterable, Optional, Tuple


def wilson(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a proportion. n == 0 gives (0.0, 1.0): nothing is known."""
    if n <= 0:
        return (0.0, 1.0)
    p = successes / float(n)
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def pct_change(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Change from a to b in percent; None when a is 0 or missing."""
    if a is None or b is None or a == 0:
        return None
    return (b - a) / float(a) * 100.0


def median(xs: Iterable[float]) -> Optional[float]:
    v = sorted(x for x in xs if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return float(v[m]) if len(v) % 2 else (v[m - 1] + v[m]) / 2.0


def diff_in_diff(treat_before: float, treat_after: float, ctrl_before: float, ctrl_after: float) -> Dict[str, Optional[float]]:
    """Absolute and relative difference in differences.

    Returns {treat_change, ctrl_change, did (absolute), treat_pct, ctrl_pct, did_pct (percentage points)}.
    """
    tc = treat_after - treat_before
    cc = ctrl_after - ctrl_before
    tp = pct_change(treat_before, treat_after)
    cp = pct_change(ctrl_before, ctrl_after)
    return {
        "treat_change": tc,
        "ctrl_change": cc,
        "did": tc - cc,
        "treat_pct": tp,
        "ctrl_pct": cp,
        "did_pct": (tp - cp) if (tp is not None and cp is not None) else None,
    }


def intervals_overlap(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])
