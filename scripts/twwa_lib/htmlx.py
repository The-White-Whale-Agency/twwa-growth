"""HTML extraction with the standard library parser.

``parse(html, base_url) -> Page`` with title, metas, canonical, robots, lang, headings, links, images,
jsonld (parsed objects; parse errors in ``jsonld_errors``), forms, text (main content without nav,
header, footer, aside, script, style), text_blocks, tel_links, wa_links, mailto_links.

Additive fields: canonicals, iframes, stylesheets, scripts, ids, full_text, shared_words, body_words,
lists (items of each ul/ol), buttons, first_screen_chars, preloads.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "blockquote", "figcaption", "dd", "dt", "div",
         "section", "article", "header", "footer", "nav", "main", "aside", "ul", "ol", "table", "tr", "form", "label",
         "address", "pre", "figure", "summary", "details", "button", "option", "select", "textarea", "br"}
SKIP = {"script", "style", "noscript", "template", "svg", "head", "title"}
CHROME = {"nav", "header", "footer", "aside"}
FIRST_SCREEN_CHARS = 700


class Page:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.title: Optional[str] = None
        self.metas: Dict[str, str] = {}
        self.canonical: Optional[str] = None
        self.canonicals: List[str] = []
        self.robots: str = ""
        self.lang: Optional[str] = None
        self.headings: List[Dict[str, Any]] = []
        self.links: List[Dict[str, Any]] = []
        self.images: List[Dict[str, Any]] = []
        self.jsonld: List[Any] = []
        self.jsonld_errors: List[str] = []
        self.forms: List[Dict[str, Any]] = []
        self.text: str = ""
        self.full_text: str = ""
        self.text_blocks: List[Dict[str, Any]] = []
        self.tel_links: List[str] = []
        self.wa_links: List[str] = []
        self.mailto_links: List[str] = []
        self.iframes: List[Dict[str, Any]] = []
        self.stylesheets: List[str] = []
        self.preloads: List[str] = []
        self.scripts: List[str] = []
        self.ids: set = set()
        self.lists: List[Dict[str, Any]] = []
        self.buttons: List[Dict[str, Any]] = []
        self.shared_words = 0
        self.body_words = 0
        self.meta_refresh: Optional[str] = None

    @property
    def h1(self) -> List[str]:
        return [h["text"] for h in self.headings if h["level"] == 1]

    def jsonld_nodes(self) -> List[Dict[str, Any]]:
        """Every JSON-LD object, with @graph flattened."""
        out: List[Dict[str, Any]] = []

        def walk(o: Any) -> None:
            if isinstance(o, list):
                for x in o:
                    walk(x)
            elif isinstance(o, dict):
                if "@graph" in o:
                    walk(o["@graph"])
                if "@type" in o:
                    out.append(o)

        walk(self.jsonld)
        return out

    def schema_types(self) -> List[str]:
        types: List[str] = []
        for n in self.jsonld_nodes():
            t = n.get("@type")
            for x in (t if isinstance(t, list) else [t]):
                if isinstance(x, str) and x not in types:
                    types.append(x)
        return types

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["ids"] = sorted(self.ids)
        return d


class _P(HTMLParser):
    def __init__(self, page: Page):
        super().__init__(convert_charrefs=True)
        self.p = page
        self.stack: List[Dict[str, Any]] = []
        self.skip = 0
        self.chrome = 0
        self.main_depth = 0
        self.has_main = False
        self.shared = 0
        self.buf: List[str] = []
        self.full: List[str] = []
        self.chars = 0
        self.in_title = False
        self.title_buf: List[str] = []
        self.jsonld_buf: Optional[List[str]] = None
        self.link: Optional[Dict[str, Any]] = None
        self.button: Optional[Dict[str, Any]] = None
        self.heading: Optional[Dict[str, Any]] = None
        self.form: Optional[Dict[str, Any]] = None
        self.label: Optional[Dict[str, Any]] = None
        self.select: Optional[Dict[str, Any]] = None
        self.option_buf: Optional[List[str]] = None
        self.lists: List[Dict[str, Any]] = []
        self.li_buf: Optional[List[str]] = None
        self.block_tag = "body"

    # -- helpers
    def _abs(self, href: str) -> str:
        return urllib.parse.urljoin(self.p.base_url, href.strip())

    def _ctx(self) -> Dict[str, bool]:
        return {
            "in_chrome": self.chrome > 0,
            "in_nav": any(e["tag"] == "nav" for e in self.stack),
            "in_footer": any(e["tag"] == "footer" for e in self.stack),
            "in_header": any(e["tag"] == "header" for e in self.stack),
            "shared": self.shared > 0,
        }

    def _in_main(self) -> bool:
        if self.chrome > 0:
            return False
        return self.main_depth > 0 or not self.has_main

    def _flush(self) -> None:
        txt = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if txt:
            self.p.text_blocks.append({"tag": self.block_tag, "text": txt, "shared": self.shared > 0, "main": self._in_main()})

    # -- parser callbacks
    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        tag = tag.lower()
        if a.get("id"):
            self.p.ids.add(a["id"])
        if tag == "html" and a.get("lang"):
            self.p.lang = a["lang"]
        if tag in BLOCK:
            self._flush()
            if tag not in ("br",):
                self.block_tag = tag
        if tag == "title" and self.p.title is None:
            self.in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if name:
                self.p.metas[name] = a.get("content", "")
                if name in ("robots", "googlebot"):
                    self.p.robots = ", ".join(x for x in (self.p.robots, a.get("content", "").lower()) if x)
                if name == "refresh":
                    self.p.meta_refresh = a.get("content", "")
        elif tag == "link":
            rel = (a.get("rel") or "").lower().split()
            href = a.get("href", "")
            if "canonical" in rel and href:
                self.p.canonicals.append(href.strip())
            if "stylesheet" in rel and href:
                self.p.stylesheets.append(self._abs(href))
            if ("preload" in rel or "preconnect" in rel) and href:
                self.p.preloads.append(self._abs(href))
        elif tag == "script":
            if a.get("src"):
                self.p.scripts.append(self._abs(a["src"]))
            if (a.get("type") or "").lower() == "application/ld+json":
                self.jsonld_buf = []
        elif tag == "img":
            ctx = self._ctx()
            self.p.images.append({
                "src": self._abs(a.get("src", "")) if a.get("src") else "",
                "alt": a.get("alt") if "alt" in a else None,
                "width": a.get("width"),
                "height": a.get("height"),
                "loading": (a.get("loading") or "").lower() or None,
                "fetchpriority": (a.get("fetchpriority") or "").lower() or None,
                "pos": self.chars,
                "main": self._in_main(),
                "index": len(self.p.images),
                **ctx,
            })
        elif tag == "iframe":
            self.p.iframes.append({"src": self._abs(a.get("src", "")) if a.get("src") else "", "data_src": a.get("data-src"), "pos": self.chars})
        elif tag == "a":
            href = a.get("href", "")
            rel = (a.get("rel") or "").lower()
            self.link = {"href": self._abs(href) if href and not href.startswith(("tel:", "mailto:", "javascript:")) else href,
                         "raw": href, "rel": rel, "nofollow": "nofollow" in rel or "sponsored" in rel or "ugc" in rel,
                         "text": [], "pos": self.chars, "main": self._in_main(), "cls": a.get("class", ""), **self._ctx()}
            low = href.lower()
            if low.startswith("tel:"):
                self.p.tel_links.append(href[4:])
            elif low.startswith("mailto:"):
                self.p.mailto_links.append(href[7:])
            elif "wa.me/" in low or "api.whatsapp.com" in low or low.startswith("whatsapp:"):
                self.p.wa_links.append(href)
        elif tag == "button":
            self.button = {"text": [], "type": a.get("type", ""), "pos": self.chars, "main": self._in_main()}
        elif tag == "form":
            self.form = {"action": self._abs(a.get("action", "")) if a.get("action") else "", "raw_action": a.get("action", ""),
                         "method": (a.get("method") or "get").lower(), "fields": [], "labels": [], "pos": self.chars, "text": []}
        elif tag in ("input", "textarea", "select") and self.form is not None:
            fld = {"tag": tag, "name": a.get("name"), "type": (a.get("type") or tag).lower(), "id": a.get("id"),
                   "required": "required" in a, "placeholder": a.get("placeholder"), "aria_label": a.get("aria-label"), "options": []}
            self.form["fields"].append(fld)
            if tag == "select":
                self.select = fld
        elif tag == "option" and self.select is not None:
            self.option_buf = []
        elif tag == "label" and self.form is not None:
            self.label = {"for": a.get("for"), "text": []}
        elif tag in ("ul", "ol"):
            self.lists.append({"tag": tag, "items": [], "main": self._in_main(), **self._ctx()})
        elif tag == "li" and self.lists:
            self.li_buf = []
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = {"level": int(tag[1]), "text": [], "main": self._in_main(), "pos": self.chars, "id": a.get("id")}

        if tag in VOID:
            return
        entry = {"tag": tag, "skip": tag in SKIP, "chrome": tag in CHROME, "main": tag == "main",
                 "shared": "data-twwa-shared" in a}
        if entry["skip"]:
            self.skip += 1
        if entry["chrome"]:
            self.chrome += 1
        if entry["main"]:
            self.main_depth += 1
            self.has_main = True
        if entry["shared"]:
            self.shared += 1
        self.stack.append(entry)

    def _close(self, entry: Dict[str, Any]) -> None:
        if entry["skip"]:
            self.skip -= 1
        if entry["chrome"]:
            self.chrome -= 1
        if entry["main"]:
            self.main_depth -= 1
        if entry["shared"]:
            self.shared -= 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in BLOCK:
            self._flush()
        if tag == "title" and self.in_title:
            self.in_title = False
            self.p.title = re.sub(r"\s+", " ", "".join(self.title_buf)).strip()
        elif tag == "script" and self.jsonld_buf is not None:
            raw = "".join(self.jsonld_buf).strip()
            self.jsonld_buf = None
            if raw:
                try:
                    self.p.jsonld.append(json.loads(raw))
                except json.JSONDecodeError as exc:
                    self.p.jsonld_errors.append("JSON-LD: %s" % exc)
        elif tag == "a" and self.link is not None:
            self.link["text"] = re.sub(r"\s+", " ", "".join(self.link["text"])).strip()
            self.p.links.append(self.link)
            self.link = None
        elif tag == "button" and self.button is not None:
            self.button["text"] = re.sub(r"\s+", " ", "".join(self.button["text"])).strip()
            self.p.buttons.append(self.button)
            self.button = None
        elif tag == "option" and self.option_buf is not None and self.select is not None:
            self.select["options"].append(re.sub(r"\s+", " ", "".join(self.option_buf)).strip())
            self.option_buf = None
        elif tag == "select":
            self.select = None
        elif tag == "label" and self.label is not None and self.form is not None:
            self.label["text"] = re.sub(r"\s+", " ", "".join(self.label["text"])).strip()
            self.form["labels"].append(self.label)
            self.label = None
        elif tag == "form" and self.form is not None:
            self.form["text"] = re.sub(r"\s+", " ", " ".join(self.form["text"])).strip()
            self.p.forms.append(self.form)
            self.form = None
        elif tag == "li" and self.li_buf is not None and self.lists:
            self.lists[-1]["items"].append(re.sub(r"\s+", " ", "".join(self.li_buf)).strip())
            self.li_buf = None
        elif tag in ("ul", "ol") and self.lists:
            self.p.lists.append(self.lists.pop())
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self.heading is not None:
            self.heading["text"] = re.sub(r"\s+", " ", "".join(self.heading["text"])).strip()
            self.p.headings.append(self.heading)
            self.heading = None
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                for e in self.stack[i:]:
                    self._close(e)
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_buf.append(data)
            return
        if self.jsonld_buf is not None:
            self.jsonld_buf.append(data)
            return
        if self.skip > 0:
            return
        self.full.append(data)
        self.chars += len(data.strip())
        for target in (self.link, self.button, self.heading, self.option_buf, self.label, self.li_buf):
            if target is None:
                continue
            if isinstance(target, dict):
                target["text"].append(data)
            else:
                target.append(data)
        if self.form is not None:
            self.form["text"].append(data)
        if self._in_main():
            self.buf.append(data)
        else:
            # chrome text still becomes a (non-main) block for town-list and NAP checks
            self.buf.append(data)

    def close(self) -> None:
        super().close()
        self._flush()
        while self.lists:
            self.p.lists.append(self.lists.pop())


def parse(html: str, base_url: str = "") -> Page:
    page = Page(base_url)
    parser = _P(page)
    try:
        parser.feed(html or "")
        parser.close()
    except Exception as exc:  # malformed markup should not crash an audit
        page.jsonld_errors.append("HTML parse error: %s" % exc)
    if page.canonicals:
        page.canonical = urllib.parse.urljoin(base_url, page.canonicals[0]) if base_url else page.canonicals[0]
    main_blocks = [b for b in page.text_blocks if b["main"]]
    page.text = "\n".join(b["text"] for b in main_blocks)
    page.full_text = "\n".join(b["text"] for b in page.text_blocks)
    page.body_words = sum(len(b["text"].split()) for b in main_blocks)
    page.shared_words = sum(len(b["text"].split()) for b in main_blocks if b["shared"])
    return page


def bare_host(netloc: str) -> str:
    h = (netloc or "").lower().split("@")[-1].split(":")[0]
    return h[4:] if h.startswith("www.") else h


def same_site_path(url: str, site: str) -> Optional[str]:
    """Path of ``url`` if it is on the same host as ``site`` (www and apex count as one), else None."""
    u = urllib.parse.urlsplit(url)
    s = urllib.parse.urlsplit(site)
    if u.scheme and u.scheme not in ("http", "https"):
        return None
    if u.netloc and s.netloc and bare_host(u.netloc) != bare_host(s.netloc):
        return None
    if not u.netloc and not url.startswith("/"):
        return None
    return u.path or "/"
