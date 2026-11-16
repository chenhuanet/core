# -*- coding: utf-8 -*-
"""为照片、绘画和专题生成静态详情页 + sitemap + robots。

预览默认用本地图片；设置 CHENHUA_REMOTE=1 时用世纪图片站的正式 URL。
"""
import datetime
import html
import json
import os
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "next" / "tools"))
import build_preview as bp  # noqa: E402

DIST = ROOT / "next" / "dist"
CORE = ROOT / "next" / "core"
REMOTE = os.environ.get("CHENHUA_REMOTE") == "1"
TODAY = datetime.date.today().isoformat()
BUILD_ID = str(int(datetime.datetime.now().timestamp()))

PHOTO_DOMAIN = "https://photo.chenhua.net"
PAINT_DOMAIN = "https://paint.chenhua.net"
MAIN_DOMAIN = "https://www.chenhua.net"


def esc(s):
    return html.escape(str(s or ""), quote=True)


def img_of(r):
    if REMOTE:
        return r.get("image") or r.get("preview_image") or ""
    return r.get("preview_image") or r.get("image") or ""


def is_paint(r):
    return r.get("collection") == "paintings"


def static_rel(r):
    if is_paint(r):
        return "paint/painting/%s.html" % r["id"]
    return "photo/photo/%s.html" % r["id"]


def canonical(r):
    if is_paint(r):
        return "%s/painting/%s.html" % (PAINT_DOMAIN, r["id"])
    return "%s/photo/%s.html" % (PHOTO_DOMAIN, r["id"])


def type_label(r):
    return {
        "painting": "绘画", "print": "版画", "drawing": "素描", "postcard": "明信片",
        "object": "器物", "document": "文书", "photograph": "照片",
    }.get(r.get("content_type"), "影像")


def gallery_href(r):
    c = r.get("image_century")
    if not c:
        return ""
    if REMOTE:
        return "https://%s.chenhua.net/" % c
    return "../../../images/%s/" % c


def nav_for(kind):
    if kind == "photo":
        return [("摄影", "../"), ("影像轴", "../gallery/"), ("专题", "../stories/"),
                ("主站", "../../main/"), ("绘画", "../../paint/")]
    if kind == "paint":
        return [("绘画", "../"), ("影像轴", "../gallery/"),
                ("主站", "../../main/"), ("摄影", "../../photo/")]
    return [("主站", "../"), ("影像轴", "../gallery/"), ("专题", "../stories/"),
            ("摄影", "../../photo/"), ("绘画", "../../paint/")]


def head(title, desc, url, image, kind, extra_ld=""):
    nav = "".join('<a href="%s">%s</a>' % (h, esc(t)) for t, h in nav_for(kind))
    og = ""
    if image:
        og = ('<meta property="og:image" content="%s">\n'
              '<meta name="twitter:image" content="%s">\n') % (esc(image), esc(image))
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>%s · 尘画</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<meta property="og:type" content="article">
<meta property="og:title" content="%s · 尘画">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
%s<link rel="stylesheet" href="../../assets/app.css?v=%s">
<link rel="stylesheet" href="../../assets/static.css?v=%s">
%s
</head>
<body class="static-body">
<div class="s-shell">
<header class="s-head"><a class="s-brand" href="../">尘画</a><nav>%s</nav></header>
""" % (esc(title), esc(desc), esc(url), esc(title), esc(desc), esc(url), og,
       BUILD_ID, BUILD_ID, extra_ld, nav)


def foot(kind="main"):
    nav = "".join('<a href="%s">%s</a>' % (h, esc(t)) for t, h in nav_for(kind))
    return """<footer class="s-foot">
<nav>%s</nav>
<p>尘画 · 以图为史 · 非商业开放档案</p>
</footer>
</div></body></html>
""" % nav


def photo_page(r, all_records):
    src = img_of(r)
    title = r.get("title") or r["id"]
    desc = (r.get("note") or title)[:180]
    url = canonical(r)
    kind = "paint" if is_paint(r) else "photo"
    ld = {
        "@context": "https://schema.org",
        "@type": "ImageObject",
        "name": title,
        "description": desc,
        "contentUrl": r.get("image") or r.get("source_image") or "",
        "thumbnailUrl": r.get("image") or "",
        "datePublished": str(r.get("date_label") or r.get("year") or ""),
        "creator": r.get("creator") or "不详",
        "creditText": r.get("credit_line") or "",
        "license": r.get("license_url") or "",
        "isPartOf": MAIN_DOMAIN + "/",
    }
    ld_json = '<script type="application/ld+json">%s</script>' % json.dumps(
        ld, ensure_ascii=False).replace("</", "<\\/")

    figure = ""
    if src:
        caption = "%s · %s" % (r.get("credit_line") or "", r.get("medium") or "")
        figure = ('<figure class="s-figure"><a href="%s" target="_blank" rel="noopener">'
                  '<img src="%s" alt="%s"></a><figcaption>%s</figcaption></figure>'
                  % (esc(src), esc(src), esc(title), esc(caption)))

    ev = r.get("evidence") if isinstance(r.get("evidence"), dict) else {}
    rows = [
        ("作者", r.get("creator") or "不详"),
        ("来源", r.get("source_short") or r.get("source") or ""),
        ("年代", r.get("date_label") or r.get("year") or ""),
        ("地域", r.get("region") or ""),
        ("类型", type_label(r) + " / " + (r.get("medium") or "")),
        ("主题", (r.get("theme") or "") + " / " + (r.get("topic") or "")),
        ("许可", r.get("license") or ""),
        ("使用性质", (r.get("usage_code") or "") + " " + (r.get("usage_label") or "")),
        ("馆藏编号", ev.get("catalog_id") or ""),
        ("抓取时间", r.get("fetched_at") or ""),
        ("原图哈希", (r.get("image_original_sha256") or "")[:16]),
    ]
    meta = '<div class="s-meta">' + "".join(
        "<div><b>%s</b>%s</div>" % (esc(k), esc(v or "—")) for k, v in rows) + "</div>"
    evidence = ('<div class="s-evidence"><h2>史实依据</h2>'
                "<p><b>陈述：</b>%s</p><p><b>依据：</b>%s</p>"
                "<p><b>核验：</b>%s · %s</p></div>") % (
        esc(ev.get("claim") or "—"), esc(ev.get("basis") or "—"),
        esc(ev.get("checked_at") or "—"), esc(ev.get("status") or "—"))

    links = []
    if r.get("page_url"):
        links.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">对象页 ↗</a>' % esc(r["page_url"]))
    if r.get("license_url"):
        links.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">许可原文 ↗</a>' % esc(r["license_url"]))
    if r.get("image_century"):
        links.append('<a class="s-btn" href="%s">图片站 ↗</a>' % esc(gallery_href(r)))
    links.append('<a class="s-btn gold" href="%s">返回影像轴</a>' % esc("../gallery/"))

    related = [x for x in all_records
               if x["id"] != r["id"] and x.get("topic") == r.get("topic")
               and x.get("preview_image")]
    if not is_paint(r):
        related = [x for x in related if x["collection"] in ("photos", "links")]
    related = related[:4]
    rel_html = ""
    if related:
        rel_html = '<section class="s-related"><h2>同一主题</h2><div class="s-grid">' + "".join(
            '<a class="s-card" href="%s.html"><img src="%s" alt="%s" loading="lazy"><div class="c"><b>%s</b>%s</div></a>'
            % (esc(x["id"]), esc(img_of(x)), esc(x.get("title")),
               esc(x.get("title")), esc(x.get("year") or ""))
            for x in related) + "</div></section>"

    html_out = head(title, desc, url, r.get("image") or src, kind, ld_json)
    html_out += '<div class="s-kicker">%s记录 · %s</div><h1 class="s-title">%s</h1>' % (
        esc(type_label(r)), esc(r.get("year") or ""), esc(title))
    html_out += '<div class="s-sub"><span>%s</span><span>·</span><span>%s</span>' % (
        esc(r.get("place") or r.get("region") or ""), esc(r.get("medium") or ""))
    html_out += '<span class="tag">%s</span><span class="tag">%s</span></div>' % (
        esc(r.get("usage_code") or ""), esc(type_label(r)))
    html_out += figure
    html_out += '<div class="s-note">%s</div>' % (r.get("note_html") or "")
    html_out += meta
    html_out += ('<div class="s-usage"><h2>%s · %s</h2><p>%s</p>'
                 '<div class="s-credit">%s</div></div>') % (
        esc(r.get("usage_label") or ""), esc(r.get("usage_code") or ""),
        esc(r.get("usage_obligation") or ""), esc(r.get("credit_line") or ""))
    html_out += evidence
    html_out += '<div class="s-actions">%s</div>' % "".join(links)
    html_out += rel_html
    html_out += foot(kind)
    return html_out


def story_page(s, records):
    by_id = {r["id"]: r for r in records}
    cover = by_id.get(s.get("cover"))
    url = "%s/story/%s.html" % (MAIN_DOMAIN, s["id"])
    desc = s.get("subtitle") or s.get("intro", "")[:180]
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": s.get("title"),
        "description": desc,
        "image": cover.get("image") if cover else "",
        "isPartOf": MAIN_DOMAIN + "/",
        "dateModified": TODAY,
    }
    ld_json = '<script type="application/ld+json">%s</script>' % json.dumps(
        ld, ensure_ascii=False).replace("</", "<\\/")
    hero = ('<div class="s-story-hero" style="background-image:url(\'%s\')"><div class="in">'
            '<div class="eyebrow" style="color:#c8a24a">已刊</div><h1>%s</h1><p>%s</p></div></div>'
            % (esc(img_of(cover) if cover else ""), esc(s.get("title")), esc(s.get("subtitle"))))
    body = '<div class="s-note">' + "".join(
        "<p>%s</p>" % esc(p) for p in str(s.get("intro") or "").split("\n\n") if p.strip()) + "</div>"
    for i, ch in enumerate(s.get("chapters") or []):
        body += '<section class="s-chapter"><div class="eyebrow">第 %d 章</div><h2>%s</h2><p class="txt">%s</p>' % (
            i + 1, esc(ch.get("title")), esc(ch.get("text")))
        body += '<div class="s-story-grid">'
        for it in ch.get("items") or []:
            r = by_id.get(it.get("id"))
            if not r:
                continue
            href = ("../../paint/painting/%s.html" % r["id"]) if is_paint(r) else (
                "../../photo/photo/%s.html" % r["id"])
            body += ('<a class="s-story-item" href="%s"><img src="%s" alt="%s" loading="lazy">'
                     '<div class="cap"><b>%s</b>%s<span class="dim">%s · %s</span></div></a>') % (
                esc(href), esc(img_of(r)), esc(r.get("title")),
                esc(r.get("title")), esc(it.get("caption") or ""),
                esc(r.get("year") or ""), esc(r.get("source_short") or ""))
        body += "</div></section>"
    rights = s.get("rights_summary") or ""
    body += '<div class="s-rights"><b>权利摘要</b><span>%s</span></div>' % esc(rights)
    body += '<div class="s-actions"><a class="s-btn gold" href="../stories/">全部专题</a>'
    body += '<a class="s-btn" href="../">主站首页</a><a class="s-btn" href="../../photo/">摄影站</a><a class="s-btn" href="../../paint/">绘画站</a></div>'
    return head(s.get("title"), desc, url, cover.get("image") if cover else "", "main", ld_json) + hero + body + foot("main")


def sitemap(site, urls):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        out.append("<url><loc>%s</loc><lastmod>%s</lastmod></url>" % (esc(u), TODAY))
    out.append("</urlset>")
    (DIST / site / "sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    domain = {"photo": PHOTO_DOMAIN, "paint": PAINT_DOMAIN, "main": MAIN_DOMAIN}[site]
    (DIST / site / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % domain,
        encoding="utf-8", newline="\n")


def main():
    records = bp.load_records()
    stories = bp.load_story_files(records)
    shutil.copy2(CORE / "static" / "static.css", DIST / "assets" / "static.css")
    photos = [r for r in records if r["collection"] in ("photos", "links")]
    paints = [r for r in records if r["collection"] == "paintings"]
    for d in (DIST / "photo" / "photo", DIST / "paint" / "painting", DIST / "main" / "story"):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    for r in photos:
        (DIST / "photo" / "photo" / ("%s.html" % r["id"])).write_text(
            photo_page(r, records), encoding="utf-8", newline="\n")
    for r in paints:
        (DIST / "paint" / "painting" / ("%s.html" % r["id"])).write_text(
            photo_page(r, paints), encoding="utf-8", newline="\n")
    for s in stories:
        (DIST / "main" / "story" / ("%s.html" % s["id"])).write_text(
            story_page(s, records), encoding="utf-8", newline="\n")

    sitemap("photo", [PHOTO_DOMAIN + "/", PHOTO_DOMAIN + "/gallery/",
                      PHOTO_DOMAIN + "/stories/", PHOTO_DOMAIN + "/about/"] +
            [canonical(r) for r in photos])
    sitemap("paint", [PAINT_DOMAIN + "/", PAINT_DOMAIN + "/gallery/",
                      PAINT_DOMAIN + "/about/"] + [canonical(r) for r in paints])
    sitemap("main", [MAIN_DOMAIN + "/", MAIN_DOMAIN + "/gallery/",
                     MAIN_DOMAIN + "/stories/", MAIN_DOMAIN + "/about/"] +
            ["%s/story/%s.html" % (MAIN_DOMAIN, s["id"]) for s in stories])
    print("静态页完成：照片 %d · 绘画 %d · 专题 %d · sitemap/robots 3 套" % (
        len(photos), len(paints), len(stories)))


if __name__ == "__main__":
    main()
