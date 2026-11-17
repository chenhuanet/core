# -*- coding: utf-8 -*-
"""为照片、绘画和主题生成静态详情页 + sitemap + robots。

预览默认用本地图片；设置 CHENHUA_REMOTE=1 时用世纪图片站的正式 URL。
页面内同时预渲染中英两份文案，由 [data-l] 与 html[data-lang] 切换。
"""
import datetime
import html
import json
import os
import pathlib
import re
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

STATUS_EN = {"已核验": "Verified", "核验": "Verified", "待核验": "Pending",
             "存疑": "Disputed", "未核验": "Unverified",
             "仅核对权利声明，未取图": "Rights statement checked only; no image retrieved",
             "": "—"}


def status_en(value):
    v = str(value or "").strip()
    if not v:
        return "—"
    if v in STATUS_EN:
        return STATUS_EN[v]
    if "已核对" in v or "已核验" in v:
        return "Verified against the source record"
    if "待核" in v:
        return "Pending verification"
    if "存疑" in v or "争议" in v:
        return "Disputed"
    return STATUS_EN.get(v, v)


def basis_en(value):
    v = str(value or "").strip()
    if not v:
        return "Holding institution's catalog record"
    if "Wikimedia Commons" in v:
        return "Wikimedia Commons file page (title, date and licence checked item by item)"
    if "馆方开放数据" in v:
        return "Holding institution's open data record (CC0)"
    if "Smithsonian" in v:
        return "Smithsonian Open Access collection record"
    if "NASA" in v:
        return "Original NASA Images caption"
    if "Cleveland" in v:
        return "Cleveland Museum of Art open collection record"
    if "权利声明" in v or "使用条款" in v:
        return "Institutional rights statement / terms of use"
    return "Holding institution's catalog record"


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


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


def type_label_zh(r):
    return {
        "painting": "绘画", "print": "版画", "drawing": "素描", "postcard": "明信片",
        "object": "器物", "document": "文书", "photograph": "照片", "link": "外链",
    }.get(r.get("content_type"), "影像")


def type_label_en(r):
    return bp.tx("content_type", r.get("content_type")) or "Image"


def gallery_href(r):
    c = r.get("image_century")
    if not c:
        return ""
    if REMOTE:
        return "https://%s.chenhua.net/" % c
    return "../../../images/%s/" % c


def brand_href(kind):
    return "../" if kind == "main" else "../../main/"


def wordmark_html(kind="main"):
    expr = "curious" if kind == "photo" else ("proud" if kind == "paint" else "joy")
    return ('<img class="leaf-mark brand-mark" src="../../assets/leaf/%s.svg" width="30" height="30" '
            'alt="" aria-hidden="true" decoding="async">' % expr +
            '<span class="wm"><span class="wm-lite">出</span>'
            '<span class="wm-strong">尘</span><span class="wm-lite">入</span>'
            '<span class="wm-strong">画</span></span>')


def nav_for(kind):
    if kind == "main":
        home, atlas, timeline = "../", "../atlas/", "../timeline/"
        session, search, photo, paint = "../today/", "../search/", "../../photo/", "../../paint/"
    elif kind == "photo":
        home, atlas, timeline = "../../main/", "../../main/atlas/", "../../main/timeline/"
        session, search, photo, paint = "../../main/today/", "../../main/search/?scope=photos", "../", "../../paint/"
    else:
        home, atlas, timeline = "../../main/", "../../main/atlas/", "../../main/timeline/"
        session, search, photo, paint = "../../main/today/", "../../main/search/?scope=paintings", "../../photo/", "../"
    return [("尘画", "Chenhua", home), ("图录", "Atlas", atlas),
            ("时间线", "Timeline", atlas + "?view=timeline"), ("历史上的今天", "On This Day", session),
            ("摄影", "Photography", photo),
            ("绘画", "Painting", paint), ("搜索", "Search", search),
            ("导航", "Directory", "https://netcn.org/")]


def tspan(zh, en):
    return '<span data-l="zh">%s</span><span data-l="en">%s</span>' % (esc(zh), esc(en))


def block(tag, zh, en, cls=""):
    c = (' class="%s"' % cls) if cls else ""
    return ('<%s%s data-l="zh">%s</%s><%s%s data-l="en">%s</%s>' %
            (tag, c, zh, tag, tag, c, en, tag))


def paragraphs(text, en=False):
    parts = [p.strip() for p in str(text or "").split("\n\n") if p.strip()]
    if not parts:
        return ""
    if en:
        return "".join("<p>%s</p>" % esc(p) for p in parts)
    return "".join("<p>%s</p>" % p for p in parts)


SUN = '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
MOON = '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg>'


def head(title_zh, title_en, desc_zh, desc_en, url, image, kind, extra_ld=""):
    nav = "".join('<a href="%s">%s</a>' % (h, tspan(z, e)) for z, e, h in nav_for(kind))
    og = ""
    if image:
        og = ('<meta property="og:image" content="%s">\n'
              '<meta name="twitter:image" content="%s">\n') % (esc(image), esc(image))
    return """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>%s · 尘画</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<link rel="alternate" hreflang="zh-CN" href="%s">
<link rel="alternate" hreflang="en" href="%s?lang=en">
<link rel="icon" type="image/svg+xml" href="../../assets/leaf/favicon.svg">
<meta property="og:type" content="article">
<meta property="og:title" content="%s · 尘画">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<meta property="og:locale" content="zh_CN">
<meta property="og:locale:alternate" content="en_US">
<script>(function(){try{var q=new URLSearchParams(location.search).get("lang");var l=q||localStorage.getItem("chenhua-lang");if(l==="en"){document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en";}var t=localStorage.getItem("chenhua-theme");if(!t&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)t="light";if(t==="light"){document.documentElement.setAttribute("data-theme","light");}}catch(e){}})();</script>
%s<link rel="stylesheet" href="../../assets/app.css?v=%s">
<link rel="stylesheet" href="../../assets/static.css?v=%s">
%s
</head>
<body class="static-body" data-title-zh="%s" data-title-en="%s" data-desc-zh="%s" data-desc-en="%s">
<div class="s-shell">
<header class="appbar s-appbar">
<a class="brand" href="%s">%s<span class="sub">%s</span></a>
<nav class="desknav">%s</nav>
<div class="right">
<button class="langbtn" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button>
<button class="iconbtn themebtn" type="button" data-themebtn aria-label="切换明暗">%s%s</button>
</div>
</header>
""" % (esc(title_zh), esc(desc_zh), esc(url), esc(url), esc(url),
       esc(title_zh), esc(desc_zh), esc(url), og,
       BUILD_ID, BUILD_ID, extra_ld,
       esc(title_zh), esc(title_en), esc(desc_zh), esc(desc_en),
       brand_href(kind), wordmark_html(kind), tspan("尘归尘，画归画", "Image as history"),
       nav, SUN, MOON)


def foot(kind="main"):
    nav = "".join('<a href="%s">%s</a>' % (h, tspan(z, e)) for z, e, h in nav_for(kind))
    utility = "".join('<a href="%s">%s</a>' % (h, tspan(z, e)) for z, e, h in [
        ("关于", "About", "../about/"),
        ("授权", "Rights", "../rights/"),
        ("法律", "Legal", "../legal/"),
    ])
    return """<footer class="s-foot">
<p class="s-foot-mark"><img src="../../assets/leaf/calm.svg" width="24" height="24" alt="" aria-hidden="true" decoding="async"></p>
<p class="brandline">%s</p>
<p class="motto">%s</p>
<nav class="foot-primary">%s</nav>
<nav class="foot-utility">%s</nav>
<p>%s</p>
</footer>
</div>
<script src="../../assets/site.js?v=%s"></script>
</body></html>
""" % (tspan("尘画 · 出尘入画 · 尘归尘，画归画", "Chenhua · Out of dust, into the image"),
       tspan("尘归尘，画归画", "Dust to dust, image to image"),
       nav, utility,
       tspan("影像版权归原作者与收藏机构；本站仅作非商业索引与展示",
             "Image rights belong to their authors and holding institutions; this site is a non-commercial index and display."),
       BUILD_ID)


LEGAL_SECTIONS = [
    (("一、项目性质", "1. Nature of the project"), [
        ("尘画（出尘入画）是一个非商业性、开放的历史影像索引与展示项目。"
         "本站不设账号、不投放广告、不出售图片，不以影像本身直接营利。",
         "Chenhua (Out of dust, into the image) is a non-commercial, open index and display of historical images. "
         "The site has no accounts, no advertising and does not sell images; it does not profit directly from the images themselves."),
        ("尘归尘，画归画：影像来自历史，也终将回到历史；本站只做整理、索引与展示，"
         "不主张对历史影像本身的著作权。",
         "Dust to dust, image to image: images come from history and return to it. The site only organises, indexes and displays them, "
         "and claims no copyright in the historical images themselves."),
    ]),
    (("二、版权与授权", "2. Copyright and licensing"), [
        ("站内影像的著作权、邻接权及其他权利归原作者、收藏机构或其他权利人所有。"
         "每条记录均标注来源、作者、许可与使用性质（U1–U5），并以详情页的许可信息为准。",
         "Copyright, neighbouring rights and other rights in the images belong to their authors, holding institutions or other rights holders. "
         "Every record states its source, creator, licence and usage class (U1–U5); the licence information on the detail page prevails."),
        ("U1 表示可自由商用；U2/U3 可商用但须署名（U3 还须以同一许可发布衍生作品）；"
         "U4 仅限非商业使用；U5 仅提供外链、不转载图片。"
         "商用前请逐条核对源站许可与署名要求。本站不构成法律意见；涉及商业使用或权属争议时，请咨询专业律师。",
         "U1 may be used commercially without conditions; U2/U3 may be used commercially with credit (U3 also requires derivative works to carry the same licence); "
         "U4 is non-commercial use only; U5 is an external link only, with no image reproduced here. "
         "Check each source's licence and credit requirements before commercial use. Nothing here is legal advice; consult a qualified lawyer for commercial use or ownership disputes."),
    ]),
    (("三、准确性与免责", "3. Accuracy and disclaimer"), [
        ("本站尽力核对馆藏著录、年代、作者与史实依据，但不保证内容完整、准确或最新。"
         "历史记录可能存在争议、缺漏或错误，欢迎通过导航站提供线索与更正。",
         "The site makes every reasonable effort to verify catalog records, dates, creators and supporting evidence, but does not warrant that the content is complete, accurate or current. "
         "Historical records may be disputed, incomplete or wrong; corrections and leads are welcome through the directory site."),
        ("在适用法律允许的范围内，因使用或依赖本站内容产生的直接或间接损失，本站不承担责任。",
         "To the extent permitted by applicable law, the site accepts no liability for direct or indirect loss arising from use of, or reliance on, its content."),
    ]),
    (("四、外部链接", "4. External links"), [
        ("本站包含指向第三方馆藏、许可原文与导航站的链接。外部内容不受本站控制，"
         "其可用性、准确性、合法性与隐私做法由第三方负责；访问外部链接的风险由访问者自行承担。",
         "The site links to third-party collections, licence deeds and the directory site. External content is not under our control; "
         "its availability, accuracy, legality and privacy practices are the responsibility of the third party, and visitors follow external links at their own risk."),
    ]),
    (("五、权利人通知与下架", "5. Rights-holder notices and takedown"), [
        ("如您是影像、文字或页面设计的权利人，认为本站内容侵犯您的权利，"
         "请通过 https://netcn.org/ 联系，并提供权属证明、具体页面 URL 与联系方式。",
         "If you hold rights in an image, text or page design and believe this site infringes them, please contact us through https://netcn.org/ "
         "with proof of ownership, the specific page URL and your contact details."),
        ("我们核实后将及时更正、补充署名、替换来源或下架相关记录。",
         "Once verified, we will promptly correct the record, add credit, replace the source or remove it."),
    ]),
    (("六、隐私与日志", "6. Privacy and logs"), [
        ("本站不使用第三方统计、不投放广告、不设置追踪 Cookie，也不要求用户注册或登录。",
         "The site uses no third-party analytics, serves no advertising, sets no tracking cookies and requires no account or login."),
        ("站点由 GitHub Pages 托管、Cloudflare 提供 DNS 与加速。二者可能记录访问日志、IP 地址、"
         "请求路径与浏览器信息，用于安全防护、性能优化与滥用治理；Cloudflare 也可能设置"
         "安全防护所必需的安全 Cookie。",
         "The site is hosted on GitHub Pages, with DNS and acceleration by Cloudflare. Both may log access records, IP addresses, "
         "request paths and browser information for security, performance and abuse control; Cloudflare may also set security cookies strictly necessary for protection."),
    ]),
    (("七、版权标识", "7. Copyright notice"), [
        ("© 2026 尘画 · 出尘入画 · 尘归尘，画归画。站内文字、页面设计与整理成果归尘画项目所有；"
         "影像版权按各记录标注。",
         "© 2026 Chenhua · Out of dust, into the image · Dust to dust, image to image. Text, page design and compilation belong to the Chenhua project; "
         "image rights are stated record by record."),
    ]),
]


def legal_page(kind):
    domain = {"photo": PHOTO_DOMAIN, "paint": PAINT_DOMAIN, "main": MAIN_DOMAIN}[kind]
    url = domain + "/legal/"
    desc_zh = "尘画法律声明：版权与授权、免责声明、外部链接、权利人通知与下架、隐私与日志。"
    desc_en = "Chenhua legal notice: copyright and licensing, disclaimer, external links, rights-holder notices and takedown, privacy and logs."
    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "法律声明 · Legal notice",
        "description": desc_zh,
        "url": url,
        "inLanguage": "zh-CN",
        "dateModified": TODAY,
        "isPartOf": domain + "/",
    }
    ld_json = '<script type="application/ld+json">%s</script>' % json.dumps(
        ld, ensure_ascii=False).replace("</", "<\\/")
    body = '<div class="s-kicker">%s</div><h1 class="s-title">%s</h1>' % (
        tspan("法律与免责", "Legal and disclaimer"), tspan("法律声明", "Legal notice"))
    body += '<div class="s-sub"><span>%s</span><span>·</span><span>%s</span></div>' % (
        tspan("更新日期 %s" % TODAY, "Updated %s" % TODAY),
        tspan("尘画 · 出尘入画 · 尘归尘，画归画", "Chenhua · Out of dust, into the image"))
    body += ('<div class="s-note">%s</div>' % block(
        "p", "本页说明尘画的内容授权、免责边界、外部链接、权利人下架流程与隐私做法。使用本站即表示您已阅读并理解本声明。",
        "This page explains Chenhua's content licensing, disclaimer, external links, rights-holder takedown process and privacy practices. By using this site you confirm that you have read and understood it."))
    for (title_zh, title_en), paras in LEGAL_SECTIONS:
        body += '<div class="s-usage"><h2>%s</h2>' % tspan(title_zh, title_en)
        body += "".join(block("p", zh, en) for zh, en in paras)
        body += "</div>"
    body += ('<div class="s-actions"><a class="s-btn gold" href="https://netcn.org/">%s</a>'
             '<a class="s-btn" href="../">%s</a></div>') % (
                 tspan("联系与导航", "Contact and directory"), tspan("返回首页", "Back to home"))
    return head("法律声明", "Legal notice", desc_zh, desc_en, url, "", kind, ld_json) + body + foot(kind)


def photo_page(r, all_records):
    src = img_of(r)
    title_zh = r.get("title") or r["id"]
    title_en = r.get("title_en") or title_zh
    note_zh = r.get("note") or ""
    note_en = r.get("note_en") or note_zh
    desc_zh = (note_zh or title_zh)[:180]
    desc_en = (note_en or title_en)[:180]
    url = canonical(r)
    kind = "paint" if is_paint(r) else "photo"
    ld = {
        "@context": "https://schema.org",
        "@type": "ImageObject",
        "name": title_en,
        "alternateName": title_zh,
        "description": desc_en,
        "contentUrl": r.get("image") or r.get("source_image") or "",
        "thumbnailUrl": r.get("image") or "",
        "datePublished": r.get("date_label_en") or bp.english_date(r.get("date_label") or r.get("year")),
        "creator": bp.creator_en(r.get("creator")),
        "creditText": r.get("credit_line_en") or "",
        "license": r.get("license_url") or "",
        "isPartOf": MAIN_DOMAIN + "/",
        "inLanguage": ["zh-CN", "en"],
    }
    ld_json = '<script type="application/ld+json">%s</script>' % json.dumps(
        ld, ensure_ascii=False).replace("</", "<\\/")

    figure = ""
    if src:
        caption_zh = "%s · %s" % (r.get("credit_line") or "", r.get("medium") or "")
        caption_en = "%s · %s" % (r.get("credit_line_en") or "", r.get("medium_en") or "")
        figure = ('<figure class="s-figure"><a href="%s" target="_blank" rel="noopener">'
                  '<img src="%s" alt="%s" data-alt-zh="%s" data-alt-en="%s"></a>'
                  '<figcaption>%s</figcaption></figure>') % (
                      esc(src), esc(src), esc(title_zh), esc(title_zh), esc(title_en),
                      tspan(caption_zh, caption_en))

    ev = r.get("evidence") if isinstance(r.get("evidence"), dict) else {}
    creator_zh = r.get("creator") or "不详"
    region_zh = r.get("region") or ""
    region_en = r.get("region_en") or bp.tx("region", region_zh)
    theme_zh = "%s / %s" % (r.get("theme") or "", r.get("topic") or "")
    theme_en = "%s / %s" % (r.get("theme_en") or "", r.get("topic_en") or "")
    usage_zh = "%s %s" % (r.get("usage_code") or "", r.get("usage_label") or "")
    usage_en = "%s %s" % (r.get("usage_code") or "", r.get("usage_label_en") or "")
    date_zh = r.get("date_label") or r.get("year") or ""
    date_en = r.get("date_label_en") or bp.english_date(date_zh)
    rows = [
        (tspan("作者", "Creator"), tspan(creator_zh, bp.creator_en(creator_zh))),
        (tspan("来源", "Source"), tspan(r.get("source_short") or r.get("source") or "",
                                       r.get("source_short_en") or r.get("source_short") or "")),
        (tspan("年代", "Date"), tspan(date_zh, date_en)),
        (tspan("地域", "Region"), tspan(region_zh, region_en or "—")),
        (tspan("类型", "Type"), tspan(type_label_zh(r) + " / " + (r.get("medium") or ""),
                                     type_label_en(r) + " / " + (r.get("medium_en") or ""))),
        (tspan("主题", "Theme"), tspan(theme_zh, theme_en)),
        (tspan("许可", "Licence"), tspan(r.get("license") or "", bp.license_en(r.get("license")))),
        (tspan("使用性质", "Usage"), tspan(usage_zh, usage_en)),
        (tspan("馆藏编号", "Catalog ID"), tspan(ev.get("catalog_id") or "", ev.get("catalog_id") or "")),
        (tspan("抓取时间", "Retrieved"), tspan(r.get("fetched_at") or "", r.get("fetched_at") or "")),
        (tspan("原图哈希", "Original hash"),
         tspan((r.get("image_original_sha256") or "")[:16], (r.get("image_original_sha256") or "")[:16])),
    ]
    meta = '<div class="s-meta">' + "".join(
        "<div><b>%s</b>%s</div>" % (k, v or "—") for k, v in rows) + "</div>"

    status_zh = ev.get("status") or "—"
    status_en_text = status_en(status_zh)
    checked = ev.get("checked_at") or "—"
    evidence = ('<div class="s-evidence"><h2>%s</h2>' % tspan("史实依据", "Source verification"))
    evidence += '<div data-l="zh"><p><b>陈述：</b>%s</p><p><b>依据：</b>%s</p><p><b>核验：</b>%s · %s</p></div>' % (
        esc(ev.get("claim") or "—"), esc(ev.get("basis") or "—"), esc(checked), esc(status_zh))
    creator_en_text = bp.creator_en(creator_zh)
    source_en_text = r.get("source_short_en") or r.get("source_short") or ""
    claim_en = ", ".join(x for x in (
        date_en,
        "“%s”" % title_en if title_en else "",
        creator_en_text if creator_en_text != source_en_text else "",
        source_en_text,
    ) if x)
    if ev.get("catalog_id"):
        claim_en += ", catalog no. " + str(ev["catalog_id"])
    if claim_en:
        claim_en += "."
    evidence += ('<div data-l="en"><p><b>Statement:</b> %s</p><p><b>Basis:</b> %s</p>'
                 '<p><b>Status:</b> %s · checked %s</p></div></div>') % (
                     esc(claim_en or "—"), esc(basis_en(ev.get("basis"))),
                     esc(status_en_text), esc(checked))

    links = []
    if r.get("page_url"):
        links.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">%s</a>' % (
            esc(r["page_url"]), tspan("对象页 ↗", "Object page ↗")))
    if r.get("license_url"):
        links.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">%s</a>' % (
            esc(r["license_url"]), tspan("许可原文 ↗", "Licence deed ↗")))
    if r.get("image_century"):
        links.append('<a class="s-btn" href="%s">%s</a>' % (
            esc(gallery_href(r)), tspan("图片站 ↗", "Image index ↗")))
    links.append('<a class="s-btn gold" href="%s">%s</a>' % (
        esc("../gallery/"), tspan("返回影像轴", "Back to the archive")))

    related = [x for x in all_records
               if x["id"] != r["id"] and x.get("topic") == r.get("topic")
               and x.get("preview_image")]
    if not is_paint(r):
        related = [x for x in related if x["collection"] in ("photos", "links")]
    related = related[:4]
    rel_html = ""
    if related:
        rel_html = '<section class="s-related"><h2>%s</h2><div class="s-grid">' % tspan(
            "同一主题", "More on this theme") + "".join(
            '<a class="s-card" href="%s.html"><img src="%s" alt="%s" data-alt-zh="%s" data-alt-en="%s" loading="lazy">'
            '<div class="c"><b>%s</b>%s</div></a>'
            % (esc(x["id"]), esc(img_of(x)), esc(x.get("title")),
               esc(x.get("title")), esc(x.get("title_en") or x.get("title")),
               tspan(x.get("title") or "", x.get("title_en") or x.get("title") or ""),
               esc(x.get("year") or ""))
            for x in related) + "</div></section>"

    html_out = head(title_zh, title_en, desc_zh, desc_en, url, r.get("image") or src, kind, ld_json)
    html_out += '<div class="s-kicker">%s</div><h1 class="s-title">%s</h1>' % (
        tspan("%s记录 · %s" % (type_label_zh(r), r.get("year") or ""),
              "%s record · %s" % (type_label_en(r), r.get("year") or "")),
        tspan(title_zh, title_en))
    html_out += '<div class="s-sub"><span>%s</span><span>·</span><span>%s</span>' % (
        tspan(r.get("place") or r.get("region") or "", r.get("place_en") or region_en or ""),
        tspan(r.get("medium") or "", r.get("medium_en") or ""))
    html_out += '<span class="tag">%s</span><span class="tag">%s</span></div>' % (
        esc(r.get("usage_code") or ""), tspan(type_label_zh(r), type_label_en(r)))
    html_out += figure
    html_out += '<div class="s-note"><div data-l="zh">%s</div><div data-l="en">%s</div></div>' % (
        r.get("note_html") or "", paragraphs(note_en, en=True))
    html_out += meta
    html_out += ('<div class="s-usage"><h2>%s · %s</h2>'
                 '<div data-l="zh"><p>%s</p><div class="s-credit">%s</div></div>'
                 '<div data-l="en"><p>%s</p><div class="s-credit">%s</div></div></div>') % (
        tspan("使用性质", "Usage"), esc(r.get("usage_code") or ""),
        esc(r.get("usage_obligation") or ""), esc(r.get("credit_line") or ""),
        esc(r.get("usage_obligation_en") or ""), esc(r.get("credit_line_en") or ""))
    html_out += evidence
    html_out += '<div class="s-actions">%s</div>' % "".join(links)
    html_out += rel_html
    html_out += foot(kind)
    return html_out


def story_page(s, records):
    by_id = {r["id"]: r for r in records}
    cover = by_id.get(s.get("cover"))
    url = "%s/story/%s.html" % (MAIN_DOMAIN, s["id"])
    title_zh = s.get("title") or s["id"]
    title_en = s.get("title_en") or title_zh
    subtitle_zh = s.get("subtitle") or ""
    subtitle_en = s.get("subtitle_en") or subtitle_zh
    desc_zh = subtitle_zh or str(s.get("intro") or "")[:180]
    desc_en = subtitle_en or str(s.get("intro_en") or "")[:180]
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title_en,
        "alternateName": title_zh,
        "description": desc_en,
        "image": cover.get("image") if cover else "",
        "isPartOf": MAIN_DOMAIN + "/",
        "dateModified": TODAY,
        "inLanguage": ["zh-CN", "en"],
    }
    if s.get("date"):
        ld["datePublished"] = s["date"]
    ld_json = '<script type="application/ld+json">%s</script>' % json.dumps(
        ld, ensure_ascii=False).replace("</", "<\\/")

    kicker_zh, kicker_en = "已刊", "Published"
    if s.get("date_label") or s.get("date"):
        kicker_zh = s.get("date_label") or s.get("date")
        kicker_en = s.get("date_label_en") or bp.english_date(kicker_zh)
        if s.get("place"):
            kicker_zh += " · " + s.get("place")
            kicker_en += " · " + (s.get("place_en") or s.get("place"))
    hero = ('<div class="s-story-hero" style="background-image:url(\'%s\')"><div class="in">'
            '<div class="eyebrow">%s</div><h1>%s</h1><p>%s</p></div></div>') % (
                esc(img_of(cover) if cover else ""), tspan(kicker_zh, kicker_en),
                tspan(title_zh, title_en), tspan(subtitle_zh, subtitle_en))
    body = '<div class="s-note"><div data-l="zh">%s</div><div data-l="en">%s</div></div>' % (
        paragraphs(s.get("intro") or ""), paragraphs(s.get("intro_en") or "", en=True))
    for i, ch in enumerate(s.get("chapters") or []):
        body += '<section class="s-chapter"><div class="eyebrow">%s</div><h2>%s</h2>' % (
            tspan("第 %d 章" % (i + 1), "Chapter %d" % (i + 1)),
            tspan(ch.get("title") or "", ch.get("title_en") or ch.get("title") or ""))
        body += '<div data-l="zh"><p class="txt">%s</p></div>' % esc(ch.get("text") or "")
        body += '<div data-l="en"><p class="txt">%s</p></div>' % esc(ch.get("text_en") or "")
        body += '<div class="s-story-grid">'
        for it in ch.get("items") or []:
            r = by_id.get(it.get("id"))
            if not r:
                continue
            href = ("../../paint/painting/%s.html" % r["id"]) if is_paint(r) else (
                "../../photo/photo/%s.html" % r["id"])
            body += ('<a class="s-story-item" href="%s"><img src="%s" alt="%s" data-alt-zh="%s" data-alt-en="%s" loading="lazy">'
                     '<div class="cap"><b>%s</b>%s<span class="dim">%s · %s</span></div></a>') % (
                esc(href), esc(img_of(r)), esc(r.get("title")),
                esc(r.get("title")), esc(r.get("title_en") or r.get("title")),
                tspan(r.get("title") or "", r.get("title_en") or r.get("title") or ""),
                tspan(it.get("caption") or "", it.get("caption_en") or it.get("caption") or ""),
                esc(r.get("year") or ""), tspan(r.get("source_short") or "", r.get("source_short_en") or r.get("source_short") or ""))
        body += "</div></section>"
    rights = s.get("rights_summary") or ""
    rights_en = s.get("rights_summary_en") or rights
    rights_zh = " · ".join(
        "%s · %s 张" % tuple(part.split(" ", 1)) if " " in part else part
        for part in rights.split(" · "))
    body += '<div class="s-rights"><b>%s</b><span>%s</span></div>' % (
        tspan("权利摘要", "Rights summary"), tspan(rights_zh, rights_en))
    sources = s.get("sources") or []
    if sources:
        links = []
        for src in sources:
            if isinstance(src, dict):
                st, su = src.get("title") or src.get("url") or "", src.get("url") or ""
            else:
                st, su = str(src), str(src)
            if su:
                links.append('<li><a href="%s" target="_blank" rel="noopener">%s</a></li>' % (esc(su), esc(st)))
        if links:
            body += '<div class="s-evidence"><h2>%s</h2><ul>%s</ul></div>' % (
                tspan("史实依据", "Sources"), "".join(links))
    body += '<div class="s-actions"><a class="s-btn gold" href="../atlas/">%s</a>' % tspan(
        "图录总览", "Atlas")
    body += '<a class="s-btn" href="../stories/">%s</a>' % tspan(
        "全部主题", "All stories")
    body += '<a class="s-btn" href="../">%s</a><a class="s-btn" href="../../photo/">%s</a><a class="s-btn" href="../../paint/">%s</a></div>' % (
        tspan("主站首页", "Home"), tspan("摄影站", "Photography"), tspan("绘画站", "Painting"))
    return head(title_zh, title_en, desc_zh, desc_en, url, cover.get("image") if cover else "", "main", ld_json) + hero + body + foot("main")


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
    day_keys = sorted({str(s.get("date"))[5:10] for s in stories
                       if re.match(r"^\d{4}-\d{2}-\d{2}$", str(s.get("date") or ""))})
    shutil.copy2(CORE / "static" / "static.css", DIST / "assets" / "static.css")
    if (CORE / "assets" / "site.js").exists():
        shutil.copy2(CORE / "assets" / "site.js", DIST / "assets" / "site.js")
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
    for site, kind in (("main", "main"), ("photo", "photo"), ("paint", "paint")):
        legal = DIST / site / "legal"
        legal.mkdir(parents=True, exist_ok=True)
        (legal / "index.html").write_text(legal_page(kind), encoding="utf-8", newline="\n")

    sitemap("photo", [PHOTO_DOMAIN + "/", PHOTO_DOMAIN + "/gallery/",
                      PHOTO_DOMAIN + "/stories/", PHOTO_DOMAIN + "/about/",
                      PHOTO_DOMAIN + "/legal/"] + [canonical(r) for r in photos])
    sitemap("paint", [PAINT_DOMAIN + "/", PAINT_DOMAIN + "/gallery/",
                      PAINT_DOMAIN + "/about/",
                      PAINT_DOMAIN + "/legal/"] + [canonical(r) for r in paints])
    sitemap("main", [MAIN_DOMAIN + "/", MAIN_DOMAIN + "/atlas/", MAIN_DOMAIN + "/gallery/",
                     MAIN_DOMAIN + "/stories/", MAIN_DOMAIN + "/timeline/",
                     MAIN_DOMAIN + "/today/",
                     MAIN_DOMAIN + "/about/", MAIN_DOMAIN + "/legal/"] +
            ["%s/story/%s.html" % (MAIN_DOMAIN, s["id"]) for s in stories] +
            ["%s/today/%s.html" % (MAIN_DOMAIN, d) for d in day_keys])
    print("静态页完成：照片 %d · 绘画 %d · 主题 %d · sitemap/robots 3 套" % (
        len(photos), len(paints), len(stories)))


if __name__ == "__main__":
    main()
