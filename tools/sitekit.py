# -*- coding: utf-8 -*-
"""Shared shell, navigation and Markdown helpers for the v3.2 static build.

All pages are generated as single-language HTML. Chinese lives at the site root,
English under /en/. Navigation, footer and tabbar come from ui-manifest.json,
so every site renders exactly the same contract.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "repos" / "core"
MANIFEST = json.loads((CORE / "ui-manifest.json").read_text(encoding="utf-8"))
SITES = json.loads((ROOT / "workspace" / "sites.json").read_text(encoding="utf-8"))
BUILD_ID = (ROOT / "workspace" / "BUILD_ID").read_text(encoding="utf-8").strip()

NAV = MANIFEST["nav"]
FOOTER = MANIFEST["footer"]
TABBAR = MANIFEST["tabbar"]
SITE_META = MANIFEST["sites"]

SUN = ('<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
       'stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
       'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>')
MOON = ('<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg>')
LEAF = ('<img class="leaf-mark brand-mark" src="/assets/leaf/curious.svg" width="30" height="30" '
        'alt="" aria-hidden="true" decoding="async">')


def esc(value):
    return html.escape(str(value or ""), quote=True)


def site_meta(key):
    return SITE_META.get(key, SITE_META["main"])


def origin(key):
    return "https://" + site_meta(key)["domain"]


def page_url(site_key, path, lang="zh"):
    path = "/" + str(path).lstrip("/")
    if lang == "en":
        path = "/en" + ("/" if path == "/" else path)
    return origin(site_key) + path


def lang_path(path, lang):
    path = "/" + str(path).lstrip("/")
    if lang == "en":
        return "/en" + ("/" if path == "/" else path)
    return path


def counterpart(path, lang):
    """Return the other-language path for a path in the given language."""
    path = "/" + str(path).lstrip("/")
    if lang == "en":
        if path == "/en/" or path == "/en":
            return "/"
        if path.startswith("/en/"):
            return "/" + path[4:]
        return path
    return "/en" + ("/" if path == "/" else path)


def nav_href(item, lang):
    url = item["url"]
    if item["key"] == "directory":
        return url
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    path = parts.path or "/"
    if lang == "en":
        path = "/en" + ("/" if path == "/" else path)
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _active_key(site_key):
    return "images" if site_key in ("pre19century", "19century", "20century", "21century", "aiera") else site_key


def nav_html(site_key, lang):
    active = _active_key(site_key)
    out = []
    for item in NAV:
        label = item["en"] if lang == "en" else item["zh"]
        cls = ' class="on"' if item["key"] == active else ""
        out.append('<a href="%s"%s>%s</a>' % (esc(nav_href(item, lang)), cls, esc(label)))
    return "".join(out)


def footer_nav_html(site_key, lang):
    active = _active_key(site_key)
    out = []
    for item in FOOTER:
        label = item["en"] if lang == "en" else item["zh"]
        cls = ' class="on"' if item["key"] == active else ""
        out.append('<a href="%s"%s>%s</a>' % (esc(nav_href(item, lang)), cls, esc(label)))
    return "".join(out)


def tabbar_html(site_key, lang):
    active = _active_key(site_key)
    out = []
    for item in TABBAR:
        label = item["en"] if lang == "en" else item["zh"]
        cls = ' class="tab on"' if item["key"] == active else ' class="tab"'
        out.append('<a href="%s"%s>%s</a>' % (esc(nav_href(item, lang)), cls, esc(label)))
    return "".join(out)


def head_html(site_key, lang, path, title, description, extra_head="", og_type="website", image=""):
    meta = site_meta(site_key)
    site_name = meta["en"] if lang == "en" else meta["zh"]
    description = (description or "").strip()
    if len(description) < 20:
        tail = ("尘画历史影像与视觉资料索引" if lang == "zh"
                else "An index of historical images and visual culture")
        description = (description + " · " if description else "") + tail
    canonical = page_url(site_key, path, lang)
    zh_url = page_url(site_key, path, "zh")
    en_url = page_url(site_key, path, "en")
    html_lang = "en" if lang == "en" else "zh-CN"
    full_title = title if title.endswith(site_name) else "%s · %s" % (title, site_name)
    og_image = ""
    if image:
        og_image = ('<meta property="og:image" content="%s">\n'
                    '<meta name="twitter:image" content="%s">\n') % (esc(image), esc(image))
    return """<!doctype html>
<html lang="%s" data-theme="dark" data-lang="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<link rel="alternate" hreflang="zh-CN" href="%s">
<link rel="alternate" hreflang="en" href="%s">
<link rel="alternate" hreflang="x-default" href="%s">
<link rel="icon" type="image/svg+xml" href="/assets/leaf/favicon.svg">
<meta property="og:type" content="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<meta property="og:locale" content="%s">
<meta property="og:locale:alternate" content="%s">
%s<script>(function(){try{var t=localStorage.getItem("chenhua-theme")||"";if(t!=="light"&&t!=="dark"){var m=document.cookie.match(/(?:^|; )chenhua-theme=([^;]*)/);t=m?decodeURIComponent(m[1]):""}if(t!=="light"&&t!=="dark")t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}catch(e){}})();</script>
%s<link rel="stylesheet" href="/assets/app.css?v=%s">
<link rel="stylesheet" href="/assets/static.css?v=%s">
</head>
<body class="static-body" data-site="%s" data-lang="%s">
""" % (
        html_lang, "en" if lang == "en" else "zh",
        esc(full_title), esc(description), esc(canonical), esc(zh_url), esc(en_url), esc(zh_url),
        og_type, esc(full_title), esc(description), esc(canonical),
        "en_US" if lang == "en" else "zh_CN", "zh_CN" if lang == "en" else "en_US",
        og_image, extra_head,
        BUILD_ID, BUILD_ID, esc(site_key), "en" if lang == "en" else "zh",
    )


def header_html(site_key, lang, path):
    meta = site_meta(site_key)
    name = meta["en"] if lang == "en" else meta["zh"]
    tagline = meta["tagline_en"] if lang == "en" else meta["tagline_zh"]
    other = counterpart(path, lang)
    lang_label = "中文" if lang == "en" else "EN"
    lang_aria = "Switch to Chinese" if lang == "en" else "切换到英文"
    home = origin(site_key) + ("/en/" if lang == "en" else "/")
    return """<div class="s-shell">
<header class="appbar s-appbar">
<a class="brand" href="%s">%s<span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="wm-en">Frame &amp; Grain</span><span class="sub">%s</span></a>
<nav class="desknav" aria-label="%s">%s</nav>
<div class="right">
<a class="langbtn" href="%s" data-lang-link aria-label="%s">%s</a>
<button class="iconbtn themebtn" type="button" data-themebtn aria-label="%s">%s%s</button>
</div>
</header>
""" % (
        esc(home), LEAF, esc(tagline),
        "Site navigation" if lang == "en" else "站内导航",
        nav_html(site_key, lang),
        esc(other), esc(lang_aria), esc(lang_label),
        "Switch theme" if lang == "en" else "切换明暗", SUN, MOON,
    )


def footer_html(site_key, lang):
    year = "2026"
    brand = "Frame &amp; Grain" if lang == "en" else "尘画"
    legal = "/en/legal/" if lang == "en" else "/legal/"
    return """<footer class="site-foot">
<div class="sf-left">© %s %s · <a href="https://chenhua.net">chenhua.net</a></div>
<nav class="sf-nav" aria-label="%s">%s</nav>
<div class="sf-right"><a href="%s">%s</a></div>
</footer>
<nav class="tabbar site-tabbar" aria-label="%s">%s</nav>
</div>
<script src="/assets/site.js?v=%s"></script>
</body></html>
""" % (
        year, brand,
        "Site navigation" if lang == "en" else "站内导航",
        footer_nav_html(site_key, lang),
        legal, "Disclaimer" if lang == "en" else "免责条款",
        "Mobile navigation" if lang == "en" else "移动导航",
        tabbar_html(site_key, lang), BUILD_ID,
    )


def page(site_key, lang, path, title, description, body, extra_head="", og_type="website", image=""):
    return (head_html(site_key, lang, path, title, description, extra_head, og_type, image)
            + header_html(site_key, lang, path)
            + body
            + footer_html(site_key, lang))


INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")


def inline_md(text):
    text = esc(text)
    return INLINE_BOLD.sub(r"<strong>\1</strong>", text)


def md_to_html(text):
    """Small Markdown subset: headings, paragraphs, bullets, bold, rules."""
    lines = str(text or "").replace("\r\n", "\n").split("\n")
    out = []
    bullet = False
    para = []

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>%s</p>" % inline_md(" ".join(para).strip()))
            para = []

    def close_bullet():
        nonlocal bullet
        if bullet:
            out.append("</ul>")
            bullet = False

    for line in lines:
        s = line.rstrip()
        if not s.strip():
            flush_para()
            close_bullet()
            continue
        if s.startswith("### "):
            flush_para(); close_bullet()
            out.append("<h3>%s</h3>" % inline_md(s[4:]))
        elif s.startswith("## "):
            flush_para(); close_bullet()
            out.append("<h2>%s</h2>" % inline_md(s[3:]))
        elif s.startswith("# "):
            flush_para(); close_bullet()
            out.append("<h1>%s</h1>" % inline_md(s[2:]))
        elif s.startswith("- "):
            flush_para()
            if not bullet:
                out.append("<ul>")
                bullet = True
            out.append("<li>%s</li>" % inline_md(s[2:]))
        elif s.strip() == "---":
            flush_para(); close_bullet()
        else:
            para.append(s)
    flush_para()
    close_bullet()
    return "".join(out)


def lang_section(body, lang):
    """Split a migrated Markdown body into its zh or en half."""
    if "## English" in body:
        zh, en = body.split("## English", 1)
        zh = zh.replace("## 中文", "", 1)
        return en if lang == "en" else zh
    return body if lang == "zh" else ""


def read_md(path):
    import yaml
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def pick(meta, base, lang, default=""):
    value = meta.get(base + "_" + lang)
    if value in (None, ""):
        value = meta.get(base)
    if value in (None, ""):
        value = default
    return value
