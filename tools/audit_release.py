# -*- coding: utf-8 -*-
"""Audit next/release as a repo-shaped production tree.

This is the post-build gate: broken page links, fragments, missing assets,
missing metadata, duplicate ids, asset versions, and static nav signatures.
"""
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "next" / "release"
IMAGES = ROOT / "next" / "images"
BUILD_ID = "20261123c"
SITES = {
    "chenhua.net": "main",
    "www.chenhua.net": "main",
    "photo.chenhua.net": "photo",
    "paint.chenhua.net": "paint",
}
CENTURIES = {"pre19century", "19century", "20century", "21century"}
SKIP_IMAGE_FILES = os.environ.get("CHENHUA_SKIP_IMAGE_FILES") == "1"
ASSET_EXTS = {".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico",
              ".woff", ".woff2", ".ttf", ".json", ".mp4", ".webm", ".pdf", ".xml", ".txt"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.links = []       # (href, context)
        self.assets = []      # (src, kind)
        self.ids = set()
        self.id_counts = Counter()
        self.alt_missing = 0
        self.alt_empty = 0
        self.alt_empty_meaningful = 0
        self.h1 = 0
        self.lang = ""
        self.viewport = False
        self.charset = False
        self.title = False
        self.canonical = ""
        self.duplicate_of = ""
        self.navs = Counter()
        self.nav_links = defaultdict(list)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = set((d.get("class") or "").split())
        if d.get("id"):
            self.ids.add(d["id"])
            self.id_counts[d["id"]] += 1
        if (d.get("aria-hidden") or "").lower() == "true":
            cls.add("__aria")
        hidden = ((d.get("aria-hidden") or "").lower() == "true" or
                  any(("__aria" in c) if isinstance(c, set) else ("aria" in c) for _, c in self.stack))
        if tag == "html":
            self.lang = d.get("lang") or self.lang
        if tag == "meta":
            if d.get("charset"):
                self.charset = True
            if (d.get("name") or "").lower() == "viewport":
                self.viewport = True
            if (d.get("name") or "").lower() == "chenhua-duplicate-of":
                self.duplicate_of = d.get("content") or ""
        if tag == "title":
            self.title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "link":
            rel = (d.get("rel") or "").lower().split()
            if "canonical" in rel:
                self.canonical = d.get("href") or ""
            if any(x in rel for x in ("stylesheet", "icon", "preload", "apple-touch-icon")):
                if d.get("href"):
                    self.assets.append((d["href"], "asset"))
        if tag == "img":
            if "alt" not in d:
                self.alt_missing += 1
            elif not (d.get("alt") or "").strip():
                self.alt_empty += 1
                if not hidden:
                    self.alt_empty_meaningful += 1
            if d.get("src"):
                self.assets.append((d["src"], "image"))
            if d.get("data-src"):
                self.assets.append((d["data-src"], "image"))
        if tag == "script" and d.get("src"):
            self.assets.append((d["src"], "asset"))
        if tag == "video" and d.get("poster"):
            self.assets.append((d["poster"], "image"))
        if tag == "source" and d.get("src"):
            self.assets.append((d["src"], "asset"))
        if tag == "a" and d.get("href"):
            ctx = set()
            for _, c in self.stack:
                ctx |= set(c.keys()) if isinstance(c, dict) else c
            self.links.append((d["href"], ctx))
        if tag == "nav":
            for name in ("desknav", "sf-nav", "tabbar", "masthead-nav", "g-nav"):
                if name in cls:
                    self.navs[name] += 1
                    self._current_nav = name
                    break
            else:
                self._current_nav = None
            self.stack.append((tag, {"nav": self._current_nav} if getattr(self, "_current_nav", None) else set()))
            return
        if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"):
            self.stack.append((tag, cls))
        if tag == "a" and d.get("href") and self.stack:
            current = None
            for _, c in reversed(self.stack):
                if "nav" in c:
                    current = c["nav"]
                    break
            if current:
                self.nav_links[current].append((d["href"], d.get("aria-current") or ""))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def unique_urls(items):
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def page_url(site, rel):
    rel = rel.replace("\\", "/")
    if rel == "index.html":
        return "https://%s/" % ("chenhua.net" if site == "main" else "%s.chenhua.net" % site)
    path = rel[:-len("index.html")] if rel.endswith("/index.html") else rel
    return "https://%s/%s" % ("chenhua.net" if site == "main" else "%s.chenhua.net" % site, path)


def resolve_file(url, base, current_site):
    """Return (site, relative file path or None, fragment, kind)."""
    low = url.strip().lower()
    if not url or low.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None
    if url.startswith("//"):
        url = "https:" + url
    joined = urljoin(base, url)
    parts = urlsplit(joined)
    host = (parts.netloc or "").lower()
    path = unquote(parts.path)
    fragment = parts.fragment
    if host:
        if host in CENTURIES:
            rel = path.lstrip("/")
            return ("image:" + host.split(".")[0], rel, fragment, "image")
        site = SITES.get(host)
        if not site:
            return ("external", "", fragment, "external")
    else:
        site = current_site
    if path.startswith("/assets/") or path.startswith("/data/"):
        return (site, path.lstrip("/"), fragment, "asset")
    path = path.lstrip("/")
    if not path:
        return (site, "index.html", fragment, "page")
    if path.endswith("/"):
        path += "index.html"
    if not Path(path).suffix:
        path += "/index.html"
    return (site, path, fragment, "page")


def file_exists(site, rel):
    if site.startswith("image:"):
        if SKIP_IMAGE_FILES:
            return True, None
        century = site.split(":", 1)[1]
        target = IMAGES / century / rel
    else:
        target = RELEASE / site / rel
    return target.is_file(), target


def audit(root=RELEASE):
    global RELEASE
    RELEASE = Path(root)
    pages = []
    for site in ("main", "photo", "paint"):
        for p in (RELEASE / site).rglob("*.html"):
            pages.append((site, p, p.relative_to(RELEASE / site).as_posix()))

    broken_links = []
    broken_fragments = []
    missing_assets = []
    duplicate_ids = []
    missing_meta = []
    no_h1 = []
    no_nav = []
    no_footer = []
    canonical_mismatch = []
    alt_missing = 0
    alt_empty = 0
    alt_empty_meaningful = 0
    duplicate_ids = 0
    www = 0
    js_versions = Counter()
    css_versions = Counter()
    nav_sets = Counter()
    tab_sets = Counter()
    ids_cache = {}
    pages_count = len(pages)

    def get_ids(site, rel):
        key = (site, rel)
        if key not in ids_cache:
            p = RELEASE / site / rel
            if not p.is_file():
                ids_cache[key] = set()
            else:
                parser = PageParser()
                parser.feed(p.read_text(encoding="utf-8", errors="ignore"))
                ids_cache[key] = parser.ids
        return ids_cache[key]

    for site, path_obj, rel in pages:
        text = path_obj.read_text(encoding="utf-8", errors="ignore")
        parser = PageParser()
        parser.feed(text)
        base = page_url(site, rel)
        if "www.chenhua.net" in text:
            www += text.count("www.chenhua.net")
        if not parser.lang or not parser.viewport or not parser.charset or not parser.title:
            missing_meta.append((site, rel))
        if parser.h1 == 0 and not rel.startswith("search/"):
            no_h1.append((site, rel))
        is_redirect = bool(re.search(r'http-equiv="refresh"', text, re.I))
        if not is_redirect and parser.navs.get("desknav", 0) != 1:
            no_nav.append((site, rel))
        if not is_redirect and parser.navs.get("sf-nav", 0) != 1:
            no_footer.append((site, rel))
        if parser.alt_missing:
            alt_missing += parser.alt_missing
        alt_empty += parser.alt_empty
        alt_empty_meaningful += parser.alt_empty_meaningful
        if any(v > 1 for v in parser.id_counts.values()):
            duplicate_ids += 1
        descriptor = parser.nav_links.get("desknav")
        if descriptor:
            nav_sets[tuple(descriptor)] += 1
        descriptor_tab = parser.nav_links.get("tabbar")
        if descriptor_tab:
            tab_sets[tuple(descriptor_tab)] += 1
        if parser.canonical:
            expected = base
            if parser.canonical.rstrip("/") != expected.rstrip("/"):
                alias = (parser.duplicate_of or "").rstrip("/")
                if not (alias and alias == parser.canonical.rstrip("/")):
                    canonical_mismatch.append((site, rel, parser.canonical))
        for url, ctx in parser.links:
            target = resolve_file(url, base, site)
            if not target or target[0] in ("external",):
                continue
            target_site, target_rel, fragment, kind = target
            exists, target_path = file_exists(target_site, target_rel)
            if not exists:
                if kind == "asset":
                    missing_assets.append((site, rel, url))
                else:
                    broken_links.append((site, rel, url))
                continue
            if fragment and kind != "external":
                ids = get_ids(target_site, target_rel) if not target_site.startswith("image:") else set()
                if fragment not in ids:
                    broken_fragments.append((site, rel, url))
        for url, kind in parser.assets:
            target = resolve_file(url, base, site)
            if not target or target[0] in ("external",):
                continue
            target_site, target_rel, _, _ = target
            exists, _ = file_exists(target_site, target_rel)
            if not exists:
                missing_assets.append((site, rel, url))
        for m in re.finditer(r'(?:src|href)="([^"]*\.(?:js|css)\?v=)([^"&]+)', text):
            name = m.group(1)
            if "site.js" in name:
                js_versions[m.group(2)] += 1
            else:
                css_versions[m.group(2)] += 1

    bad_versions = (
        any(v != BUILD_ID for v in js_versions)
        or any(v != BUILD_ID for v in css_versions)
    )
    result = {
        "ok": not (
            broken_links or broken_fragments or missing_assets or missing_meta or www
            or duplicate_ids or no_h1 or no_nav or no_footer
            or alt_missing or alt_empty_meaningful or bad_versions
        ),
        "pages": pages_count,
        "broken_links": len(unique_urls(broken_links)),
        "broken_fragments": len(unique_urls(broken_fragments)),
        "missing_assets": len(unique_urls(missing_assets)),
        "missing_meta": len(unique_urls(missing_meta)),
        "duplicate_id_pages": duplicate_ids,
        "no_h1": len(unique_urls(no_h1)),
        "no_desknav": len(unique_urls(no_nav)),
        "no_footer_nav": len(unique_urls(no_footer)),
        "alt_missing": alt_missing,
        "alt_empty": alt_empty,
        "alt_empty_meaningful": alt_empty_meaningful,
        "www_refs": www,
        "canonical_mismatch": len(canonical_mismatch),
        "js_versions": dict(js_versions),
        "css_versions": dict(css_versions),
        "bad_versions": bad_versions,
        "desknav_sets": len(nav_sets),
        "tab_sets": len(tab_sets),
        "samples": {
            "broken_links": unique_urls(broken_links)[:8],
            "broken_fragments": unique_urls(broken_fragments)[:8],
            "missing_assets": unique_urls(missing_assets)[:8],
            "no_h1": unique_urls(no_h1)[:8],
            "canonical_mismatch": canonical_mismatch[:8],
        },
    }
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
