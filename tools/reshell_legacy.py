# -*- coding: utf-8 -*-
"""Re-shell legacy pages with the v3.2 header/footer and /en/ mirror.

Keeps legacy body content (bilingual data-l spans), page CSS/JS and inline data
scripts; replaces only the page chrome, metadata and record links.
"""
import html as html_lib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402
import build_v32 as B  # noqa: E402

LINK_RE = re.compile(r'href="([^"]+)"')
CSS_RE = re.compile(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"[^>]*>', re.I)
JS_RE = re.compile(r'<script[^>]+src="([^"]+)"[^>]*>\s*</script>', re.I)
INLINE_RE = re.compile(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", re.S | re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"', re.I)
BODY_RE = re.compile(r"<body([^>]*)>", re.I)
TITLE_ATTR = re.compile(r'data-title-(zh|en)="([^"]*)"', re.I)
DESC_ATTR = re.compile(r'data-desc-(zh|en)="([^"]*)"', re.I)

RECORD_MAP = {}


def build_record_map():
    for rec in B.load_records():
        if rec["collection"] in ("photos", "paintings", "objects"):
            RECORD_MAP[rec["meta"]["id"]] = (B.century_of(rec["meta"]), B.record_kind(rec["collection"]))
        elif rec["collection"] == "links":
            RECORD_MAP[rec["meta"]["id"]] = ("photo", "links")
    return RECORD_MAP


def rewrite_url(url, lang):
    if url.startswith(("mailto:", "#", "javascript:", "tel:")):
        return url
    # old record detail URLs -> century record URLs
    m = re.match(r"https://photo\.chenhua\.net/(photo|painting|object)/([^/?#]+)\.html(.*)$", url)
    if m:
        hit = RECORD_MAP.get(m.group(2))
        if hit:
            century, kind = hit
            return "https://%s.chenhua.net/%s/%s.html" % (century, kind, m.group(2))
    m = re.match(r"https://paint\.chenhua\.net/painting/([^/?#]+)\.html(.*)$", url)
    if m:
        hit = RECORD_MAP.get(m.group(1))
        if hit:
            century, kind = hit
            return "https://%s.chenhua.net/%s/%s.html" % (century, kind, m.group(1))
    if url.startswith("https://") and "chenhua.net" in url:
        from urllib.parse import urlsplit, urlunsplit, parse_qs
        parts = urlsplit(url)
        q = parse_qs(parts.query)
        path = parts.path or "/"
        if q.get("lang", [""])[0] == "en":
            path = "/en" + ("/" if path == "/" else path)
        if lang == "en" and not path.startswith("/en/") and not path.startswith("/en"):
            path = "/en" + ("/" if path == "/" else path)
        if lang == "zh" and path.startswith("/en/"):
            path = path[3:]
        query = "&".join("%s=%s" % (k, v[0]) for k, v in q.items() if k != "lang")
        return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))
    return url


def extra_assets(html):
    css = [u for u in CSS_RE.findall(html) if u.split("?")[0] not in (
        "/assets/app.css", "/assets/static.css", "/assets/history.css", "/assets/site.js")]
    js = [u for u in JS_RE.findall(html) if u.split("?")[0] not in ("/assets/site.js",)]
    inline = []
    for attrs, body in INLINE_RE.findall(html):
        if "application/ld+json" in attrs:
            inline.append('<script%s>%s</script>' % (attrs, body))
        elif "chenhua-lang" in body or "data-lang" in body:
            continue
        elif body.strip():
            inline.append('<script%s>%s</script>' % (attrs, body))
    return css, js, inline


A_TAG_RE = re.compile(r"<a\b([^>]*)>", re.I)
HREF_ATTR = re.compile(r'href="([^"]*)"', re.I)


def strip_internal_target(html):
    def repl(match):
        attrs = match.group(1)
        href_match = HREF_ATTR.search(attrs)
        href = href_match.group(1) if href_match else ""
        internal = href.startswith("/") or ("chenhua.net" in href and href.startswith(("http://", "https://")))
        if internal:
            attrs = re.sub(r'\s+target="_blank"', "", attrs, flags=re.I)
        return "<a%s>" % attrs
    return A_TAG_RE.sub(repl, html)


def reshell(html, site_key, lang, path, repo_root):
    body_attrs = BODY_RE.search(html)
    attrs = body_attrs.group(1) if body_attrs else ""
    zh_title = dict(TITLE_ATTR.findall(attrs)).get("zh") or ""
    en_title = dict(TITLE_ATTR.findall(attrs)).get("en") or ""
    title_match = TITLE_RE.search(html)
    page_title = (en_title if lang == "en" and en_title else zh_title or (title_match.group(1) if title_match else ""))
    page_title = html_lib.unescape(page_title)
    site_zh = K.site_meta(site_key)["zh"]
    site_en = K.site_meta(site_key)["en"]
    for suffix in ("尘画", "Frame & Grain", site_zh, site_en):
        page_title = re.sub(r"\s*·\s*" + re.escape(suffix) + r"\s*$", "", page_title).strip()
    desc_zh = html_lib.unescape(dict(DESC_ATTR.findall(attrs)).get("zh") or (DESC_RE.search(html).group(1) if DESC_RE.search(html) else ""))
    desc_en = html_lib.unescape(dict(DESC_ATTR.findall(attrs)).get("en") or desc_zh)
    desc = desc_en if lang == "en" else desc_zh

    # body content between the legacy header and footer
    start = html.find("</header>")
    if start < 0:
        return None
    start += len("</header>")
    end = html.find("<footer", start)
    if end < 0:
        end = html.find("</body>", start)
    content = html[start:end]

    css, js, inline = extra_assets(html)
    extra = ""
    for href in dict.fromkeys(css):
        extra += '<link rel="stylesheet" href="%s">\n' % href
    for src in dict.fromkeys(js):
        extra += '<script src="%s" defer></script>\n' % src
    for block in inline:
        extra += block + "\n"

    def replace_href(match):
        return 'href="%s"' % K.esc(rewrite_url(match.group(1), lang))

    content = LINK_RE.sub(replace_href, content)
    page = K.page(site_key, lang, path, page_title, desc, content, extra)
    page = page.replace('"staticPhotoBase": "https://photo.chenhua.net/photo/"', '"staticPhotoBase": ""')
    page = page.replace('"staticPaintBase": "https://paint.chenhua.net/painting/"', '"staticPaintBase": ""')
    return strip_internal_target(page)


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: reshell_legacy.py <site> <relative.html> [outdir]")
    site, rel = sys.argv[1], sys.argv[2]
    outdir = Path(sys.argv[3]) if len(sys.argv) > 3 else K.ROOT / "workspace" / "staging" / "reshell"
    build_record_map()
    src = K.ROOT / "repos" / site / rel
    html = src.read_text(encoding="utf-8")
    page_path = "/" + rel
    if page_path.endswith("index.html"):
        page_path = page_path[: -len("index.html")]
    for lang in ("zh", "en"):
        out = reshell(html, site, lang, page_path, src.parent)
        if out is None:
            print("SKIP", rel)
            continue
        target = outdir / (("en/" if lang == "en" else "") + rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out, encoding="utf-8")
        print(lang, target, len(out))


if __name__ == "__main__":
    main()
