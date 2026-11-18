"""German text helpers: sentences, tokens, shingles, normalisation of phone, address, name and towns.

Additive helpers beyond the 8.1 contract: ``words``, ``numbers``, ``town_runs``, ``contains_term``.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Optional, Sequence, Set, Tuple

_UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss", "ẞ": "SS"}

_ABBREV = [
    "z. B.", "z.B.", "u. a.", "u.a.", "d. h.", "d.h.", "bzw.", "ca.", "Nr.", "inkl.", "ggf.", "evtl.", "usw.", "etc.",
    "Str.", "St.", "Dr.", "Dipl.", "Ing.", "e. V.", "e.V.", "Tel.", "Fax.", "gem.", "lt.", "vgl.", "max.", "min.", "mind.",
    "zzgl.", "Std.", "Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So.", "Jan.", "Feb.", "Okt.", "Nov.", "Dez.", "Abs.", "Art.",
]
_PLACEHOLDER = "⁣"


def fold_umlauts(s: str) -> str:
    """ä->ae, ö->oe, ü->ue, ß->ss; strips other diacritics."""
    out = "".join(_UMLAUTS.get(ch, ch) for ch in (s or ""))
    out = unicodedata.normalize("NFKD", out)
    return "".join(ch for ch in out if not unicodedata.combining(ch))


def sentences(text: str) -> List[str]:
    """Split German text into sentences; newlines are hard boundaries; common abbreviations are protected."""
    out: List[str] = []
    for block in re.split(r"\n\s*\n|\n", text or ""):
        b = block.strip()
        if not b:
            continue
        for ab in _ABBREV:
            b = b.replace(ab, ab.replace(".", _PLACEHOLDER))
        # ordinal numbers like "1." before a lowercase word or a month are not sentence ends
        b = re.sub(r"(\d)\.(?=\s+(?:[a-zäöü]|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember))", "\\1" + _PLACEHOLDER, b)
        parts = re.split(r"(?<=[.!?])\s+(?=[\"„»(\[]?[A-ZÄÖÜ0-9])", b)
        for part in parts:
            s = part.replace(_PLACEHOLDER, ".").strip()
            if s:
                out.append(s)
    return out


_TOKEN = re.compile(r"[0-9a-zäöüß]+(?:[.,][0-9]+)*", re.IGNORECASE)


def tokens(text: str) -> List[str]:
    """Lowercase word and number tokens."""
    return [t.lower() for t in _TOKEN.findall(text or "")]


def words(text: str) -> List[str]:
    return re.findall(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]*|\d+(?:[.,]\d+)*", text or "")


def shingles(text: str, n: int = 5) -> Set[Tuple[str, ...]]:
    toks = tokens(text)
    if not toks:
        return set()
    if len(toks) < n:
        return {tuple(toks)}
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a: Iterable, b: Iterable) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def norm_phone(s: Optional[str], default_cc: str = "49") -> str:
    """'07000 / 12 34 56', '+49 (0) 7000 123456', 'tel:+497000123456' -> '+497000123456'."""
    if not s:
        return ""
    t = str(s).strip()
    t = re.sub(r"^(tel|callto|https?://wa\.me/|whatsapp)[:/]*", "", t, flags=re.IGNORECASE)
    t = t.replace("(0)", "")
    plus = t.startswith("+")
    digits = re.sub(r"\D", "", t)
    if not digits:
        return ""
    if plus:
        return "+" + digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith("0"):
        return "+" + default_cc + digits[1:]
    if digits.startswith(default_cc) and len(digits) > 10:
        return "+" + digits
    return "+" + default_cc + digits


def norm_address(s: Optional[str]) -> str:
    t = fold_umlauts(s or "").lower()
    t = re.sub(r"stra(ss|ß)e\b|str\.", "str", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_LEGAL_FORMS = r"\b(gmbh\s*&\s*co\.?\s*kg|gmbh|ug(\s*\(haftungsbeschraenkt\))?|ag|kg|ohg|gbr|e\.?\s?k\.?|e\.?\s?v\.?|mbh|partg(mbb)?)\b"


def norm_name(s: Optional[str], strip_legal_form: bool = False) -> str:
    t = fold_umlauts(s or "").lower().replace("&", " und ").replace("+", " und ")
    if strip_legal_form:
        t = re.sub(_LEGAL_FORMS, " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def town_variants(town: str) -> List[str]:
    """Spellings under which a town may appear: original, folded, hyphen/space, St./Sankt, without 'am X' suffix."""
    if not town:
        return []
    base = {town.strip()}
    t = town.strip()
    base.add(t.replace("-", " "))
    base.add(t.replace(" ", "-"))
    if t.startswith("St. "):
        base.add("Sankt " + t[4:])
    if t.startswith("Sankt "):
        base.add("St. " + t[6:])
    m = re.match(r"^(.+?)\s+(am|an der|im|ob der|in der|bei)\s+.+$", t)
    if m and len(m.group(1)) >= 4:
        base.add(m.group(1))
    more = set()
    for b in base:
        more.add(fold_umlauts(b))
    base |= more
    return sorted(v for v in base if v)


def contains_term(text: str, term: str) -> bool:
    """Case-insensitive whole-word containment, umlaut-insensitive."""
    if not term:
        return False
    t = fold_umlauts(text or "").lower()
    w = fold_umlauts(term).lower()
    return re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t) is not None


def contains_town(text: str, town: str) -> bool:
    return any(contains_term(text, v) for v in town_variants(town))


_NUM = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(?![\w])")


def numbers(text: str) -> List[float]:
    """German numbers: '1.200' -> 1200, '2,5' -> 2.5, '12' -> 12."""
    out = []
    for m in _NUM.finditer(text or ""):
        whole = m.group(1).replace(".", "")
        frac = m.group(2)
        try:
            out.append(float(whole + ("." + frac if frac else "")))
        except ValueError:
            continue
    return out


_TOWN_SUFFIX = re.compile(
    r"(heim|hausen|ingen|ungen|dorf|burg|berg|stadt|bach|feld|felden|au|rode|weiler|hofen|kirchen|kirch|born|furt|tal|see|"
    r"brück|brücken|haus|statt|leben|wald|stetten|weil|zell|hof|beuren|reuth|reut|sheim|stein|wangen|lingen)$",
    re.IGNORECASE,
)
_CONNECTORS = {"am", "an", "der", "die", "im", "in", "ob", "bei", "vor", "auf", "unter", "ober", "bad", "st.", "sankt", "-"}


def _name_like(item: str) -> bool:
    w = item.strip().split()
    if not w or len(w) > 4:
        return False
    for x in w:
        if x.lower() in _CONNECTORS:
            continue
        if not re.match(r"^[A-ZÄÖÜ][\wäöüß\-.]*$", x):
            return False
    return True


def town_like(item: str, known: Sequence[str] = ()) -> bool:
    it = item.strip()
    if any(contains_term(it, k) and len(it) <= len(k) + 12 for k in known if k):
        return True
    last = it.split()[-1] if it.split() else ""
    return _name_like(it) and (bool(_TOWN_SUFFIX.search(last)) or it.lower().startswith(("bad ", "st. ", "sankt ")))


def town_runs(text: str, known: Sequence[str] = (), min_known: int = 2) -> List[List[str]]:
    """Plain-text runs of town names: items separated by commas, middots, pipes, slashes or 'und'.

    A run counts when most items look like towns (known service-area towns or typical German
    place-name endings) and at least ``min_known`` known towns occur (or, without known towns,
    every item has a place-name ending). Returns the town-like items of each run.
    """
    runs: List[List[str]] = []
    for seg in re.split(r"[\n.;:!?()]", text or ""):
        parts = re.split(r"\s*(?:,|·|\||/|•|\bund\b|\bsowie\b)\s*", seg)
        cur: List[str] = []

        def flush() -> None:
            if len(cur) >= 3:
                tl = [c for c in cur if town_like(c, known)]
                kn = [c for c in cur if any(contains_term(c, k) for k in known if k)]
                if len(tl) >= max(3, int(0.6 * len(cur))) and (len(kn) >= min_known or (not known and len(tl) == len(cur))):
                    runs.append(tl)
            cur.clear()

        for raw in parts:
            p = raw.strip()
            # strip a leading phrase like "Wir arbeiten in" from the first item
            m = re.match(r"^.*\b(?:in|nach|für|rund um|um)\s+([A-ZÄÖÜ][\wäöüß\-. ]+)$", p)
            if m and not _name_like(p):
                p = m.group(1)
            if p and _name_like(p):
                cur.append(p)
            else:
                flush()
        flush()
    return runs


def list_town_run(items: Sequence[str], known: Sequence[str] = (), min_known: int = 2) -> List[str]:
    """Town-like entries of an HTML list (one item per <li>), if the list is a town list."""
    clean = [i.strip() for i in items if i and i.strip()]
    if len(clean) < 3:
        return []
    tl = [c for c in clean if town_like(c, known)]
    kn = [c for c in clean if any(contains_term(c, k) for k in known if k)]
    if len(tl) >= max(3, int(0.6 * len(clean))) and (len(kn) >= min_known or (not known and len(tl) == len(clean))):
        return tl
    return []
