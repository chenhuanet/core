# -*- coding: utf-8 -*-
"""Lightweight a11y / SEO / mobile / page-weight audit for the v3.2 release."""
import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402

RELEASE = K.ROOT / "workspace" / "release"
HTML_RE = re.compile(r"<html([^>]*)>", re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"', re.I)
H1_RE = re.compile(r"<h1[ >]", re.I)
IMG_RE = re.compile(r"<img\b([^>]*)>", re.I)
A_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)


def attr(attrs, name):
    m = re.search(r'\b%s="([^"]*)"' % name, attrs, re.I)
    return m.group(1) if m else None


def main():
    report = {
        "pages": 0, "missing_lang": [], "bad_title": [], "short_desc": [],
        "bad_h1": [], "img_no_alt": [], "empty_links": [], "no_viewport": [],
        "http_links": [], "blank_internal": [], "heavy_pages": [],
        "record_missing_jsonld": [],
    }
    for site in K.SITE_META:
        base = RELEASE / site
        if not base.exists():
            continue
        before = report["pages"]
        for p in base.rglob("*.html"):
            rel = p.relative_to(base).as_posix()
            if rel == "404.html":
                continue
            report["pages"] += 1
            html = p.read_text(encoding="utf-8")
            page = "%s/%s" % (site, rel)
            html_attrs = HTML_RE.search(html)
            attrs = html_attrs.group(1) if html_attrs else ""
            lang = attr(attrs, "lang")
            data_lang = attr(attrs, "data-lang")
            want = "en" if rel.startswith("en/") else "zh"
            if not lang or (want == "en" and lang != "en") or (want == "zh" and not lang.startswith("zh")) or data_lang != want:
                report["missing_lang"].append(page)
            title = TITLE_RE.search(html)
            title = title.group(1).strip() if title else ""
            if not title or len(title) > 500:
                report["bad_title"].append(page)
            desc = DESC_RE.search(html)
            desc = desc.group(1).strip() if desc else ""
            if len(desc) < 15:
                report["short_desc"].append(page)
            if len(H1_RE.findall(html)) != 1:
                report["bad_h1"].append(page)
            if 'name="viewport"' not in html:
                report["no_viewport"].append(page)
            for img in IMG_RE.findall(html):
                if "alt=" not in img.lower():
                    report["img_no_alt"].append(page)
                    break
            for a in A_RE.findall(html):
                attrs_a, text = a
                href = attr(attrs_a, "href")
                if href is None or href.strip() in ("", "#"):
                    report["empty_links"].append(page)
                    break
                if href.startswith("http://") and "chenhua.net" in href:
                    report["http_links"].append(page)
                    break
                if href.startswith("https://") and "chenhua.net" in href and 'target="_blank"' in attrs_a:
                    if not re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip)(\?|$)", href, re.I):
                        report["blank_internal"].append(page)
                        break
            if p.stat().st_size > 600_000:
                report["heavy_pages"].append({"page": page, "kb": round(p.stat().st_size / 1024)})
            if site in ("pre19century", "19century", "20century", "21century", "aiera") and re.search(r"/(photo|painting|object|image)/[^/]+\.html$", rel):
                if 'application/ld+json' not in html:
                    report["record_missing_jsonld"].append(page)
        print("quality", site, report["pages"] - before, flush=True)
    summary = {k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}
    report["ok"] = all(not v for k, v in report.items() if isinstance(v, list) and k != "heavy_pages")
    out = K.ROOT / "workspace" / "data" / "v32-quality.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("QUALITY_OK", report["ok"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
