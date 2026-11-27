# -*- coding: utf-8 -*-
"""v3.2 release audit: UI contract, /en/ pairs, canonical/hreflang, record ownership."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402

ROOT = K.ROOT
RELEASE = ROOT / "workspace" / "release"
SITES = list(K.SITE_META.keys())
RECORD_SITES = {"pre19century", "19century", "20century", "21century", "aiera"}

NAV_RE = re.compile(r'<nav class="desknav"[^>]*>(.*?)</nav>', re.S)
FOOT_RE = re.compile(r'<nav class="sf-nav"[^>]*>(.*?)</nav>', re.S)
TAB_RE = re.compile(r'<nav class="tabbar[^"]*"[^>]*>(.*?)</nav>', re.S)
LINK_RE = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]+)">')
ALT_RE = re.compile(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">')
H1_RE = re.compile(r"<h1[ >]")
VER_RE = re.compile(r'(?:href|src)="[^"]+\?v=([^"]+)"')


def labels(html):
    return [re.sub(r"<[^>]+>", "", t).strip() for _, t in LINK_RE.findall(html)]


def expected(lang, kind):
    items = {"nav": K.NAV, "footer": K.FOOTER, "tabbar": K.TABBAR}[kind]
    out = []
    for item in items:
        out.append((item["en"] if lang == "en" else item["zh"], K.nav_href(item, lang)))
    return out


def actual(html, kind):
    block = {"nav": NAV_RE, "footer": FOOT_RE, "tabbar": TAB_RE}[kind].search(html)
    if not block:
        return []
    return [(re.sub(r"<[^>]+>", "", t).strip(), href) for href, t in LINK_RE.findall(block.group(1))]


def check_site(site, report):
    base = RELEASE / site
    if not base.exists():
        report["missing_sites"].append(site)
        return
    for p in base.rglob("*.html"):
        rel = p.relative_to(base).as_posix()
        if rel == "404.html":
            continue
        lang = "en" if rel.startswith("en/") else "zh"
        path = "/" + (rel[len("en/"):] if lang == "en" else rel)
        if path.endswith("index.html"):
            path = path[: -len("index.html")]
        html = p.read_text(encoding="utf-8")
        page = {"site": site, "path": path, "lang": lang, "file": rel}

        for kind, needle in (("appbar", 'class="appbar'), ("desknav", 'class="desknav'),
                             ("site-foot", 'class="site-foot'), ("sf-nav", 'class="sf-nav'),
                             ("tabbar", 'class="tabbar')):
            n = html.count(needle)
            if n != 1:
                report["bad_counts"].append(dict(page, element=kind, count=n))

        for kind in ("nav", "footer", "tabbar"):
            got = actual(html, kind)
            want = expected(lang, kind)
            if got != want:
                report["nav_mismatch"].append(dict(page, kind=kind, got=got, want=want))

        if len(H1_RE.findall(html)) != 1:
            report["bad_h1"].append(page)

        canon = CANON_RE.search(html)
        want_canon = K.page_url(site, path, lang)
        if not canon or canon.group(1) != want_canon:
            report["bad_canonical"].append(dict(page, got=canon.group(1) if canon else "", want=want_canon))

        alts = dict(ALT_RE.findall(html))
        want_zh = K.page_url(site, path, "zh")
        want_en = K.page_url(site, path, "en")
        if alts.get("zh-CN") != want_zh or alts.get("en") != want_en or alts.get("x-default") != want_zh:
            report["bad_hreflang"].append(dict(page, got=alts, want={"zh-CN": want_zh, "en": want_en, "x-default": want_zh}))

        other = K.counterpart(path, lang)
        other_rel = other.lstrip("/")
        if other.endswith("/"):
            other_rel += "index.html"
        other_file = base / other_rel
        if not other_file.exists():
            report["missing_pair"].append(dict(page, other=other_rel))

        for v in VER_RE.findall(html):
            if v != K.BUILD_ID:
                report["bad_version"].append(dict(page, version=v))

        if "?lang=" in html:
            report["lang_query"].append(page)

        for kind in ("nav", "footer", "tabbar"):
            for href, _ in actual(html, kind):
                if href.startswith("https://") and "chenhua.net" in href and 'target="_blank"' in html[:0]:
                    pass

        if site not in RECORD_SITES:
            if re.search(r"/(photo|painting|object)/[^/]+\.html$", path):
                report["record_in_content_site"].append(page)
        else:
            if path.startswith("/links/"):
                report["link_in_record_site"].append(page)


def main():
    report = {k: [] for k in (
        "missing_sites", "bad_counts", "nav_mismatch", "bad_h1", "bad_canonical",
        "bad_hreflang", "missing_pair", "bad_version", "lang_query",
        "record_in_content_site", "link_in_record_site",
    )}
    for site in SITES:
        check_site(site, report)
    report["ok"] = all(not v for k, v in report.items())
    out = ROOT / "workspace" / "data" / "v32-audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("AUDIT_OK", report["ok"])
    for key in ("nav_mismatch", "bad_counts", "missing_pair", "bad_canonical", "bad_hreflang", "bad_h1"):
        if report[key]:
            print("SAMPLE", key, json.dumps(report[key][:3], ensure_ascii=False))
            break
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
