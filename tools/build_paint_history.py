# -*- coding: utf-8 -*-
"""生成绘画史内容层：章节、流派、艺术家、时期、技法、小径、时间轴、日历。

输出：next/dist/paint/history/*.html（扁平路由，便于 split_repos 的相对路径改写）
"""
import html
import json
import pathlib
import re
import shutil
import sys
import time
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[2]
NEXT = ROOT / "next"
DIST = NEXT / "dist"
CORE = NEXT / "core"
PAINT = DIST / "paint"
HIST = PAINT / "history"
BUNDLE = DIST / "data" / "bundle.js"
DOMAIN = "https://paint.chenhua.net"
BUILD_ID = str(int(time.time()))

sys.path.insert(0, str(NEXT / "content" / "paint-history"))
import chapters  # noqa: E402
import movements  # noqa: E402
import artists  # noqa: E402
import periods  # noqa: E402
import techniques  # noqa: E402
import trails  # noqa: E402
import calendar as ph_calendar  # noqa: E402


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def text(value):
    return html.escape(str(value if value is not None else ""), quote=False)


def tspan(zh, en):
    return '<span data-l="zh">%s</span><span data-l="en">%s</span>' % (esc(zh), esc(en))


def md_inline(value):
    s = esc(value)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def paras(items):
    return "".join("<p>%s</p>" % md_inline(p) for p in (items or []) if str(p).strip())


def ul(items):
    return "<ul class=\"ph-list\">%s</ul>" % "".join("<li>%s</li>" % md_inline(x) for x in (items or []))


def load_records():
    raw = BUNDLE.read_text(encoding="utf-8")
    payload = raw[raw.index("{"):].rstrip().rstrip(";")
    data = json.loads(payload)
    return {r["id"]: r for r in data.get("records", []) if r.get("collection") == "paintings"}


RECORDS = load_records()
WORK_IDS = sorted(RECORDS, key=lambda i: (RECORDS[i].get("year") or 0, RECORDS[i].get("title") or i))
PAINT_WORK_IDS = [i for i in WORK_IDS if RECORDS.get(i, {}).get("content_type") == "painting"]
WORK_BY_ID = RECORDS
CH_BY_SLUG = {c["slug"]: c for c in chapters.CHAPTERS}
MOV_A = {m["slug"]: m for m in movements.MOVEMENTS}
MOV_B = {m["slug"]: m for m in movements.MOVEMENTS_B}
ART_BY_SLUG = {a["slug"]: a for a in artists.ARTISTS}
ART_BY_ZH = {a["zh"]: a for a in artists.ARTISTS}
PER_BY_SLUG = {p["slug"]: p for p in periods.PERIODS}
TECH_BY_SLUG = {t["slug"]: t for t in techniques.TECHNIQUES}
TRAIL_BY_SLUG = {t["slug"]: t for t in trails.TRAILS}


def img_of(rid):
    r = RECORDS.get(rid) or {}
    return r.get("preview_image") or r.get("image") or ""


def og_img(rid):
    r = RECORDS.get(rid) or {}
    return r.get("image") or r.get("preview_image") or ""


def work_title(r):
    return r.get("title") or r.get("id") or ""


def work_title_en(r):
    return r.get("title_en") or work_title(r)


def work_meta(r):
    return " · ".join(x for x in (r.get("date_label") or r.get("year") or "",
                                  r.get("creator") or "") if x)


def work_meta_en(r):
    return " · ".join(x for x in (r.get("date_label_en") or r.get("date_label") or r.get("year") or "",
                                  r.get("creator_en") or r.get("creator") or "") if x)


def work_link(rid, cls="ph-anchor", note_zh="", note_en=""):
    r = RECORDS.get(rid)
    if not r:
        return ""
    image = img_of(rid)
    return ('<a class="%s" href="../painting/%s.html">%s<div class="cap"><b>%s</b><span>%s</span>%s</div></a>'
            % (cls, esc(rid), ('<img src="%s" alt="%s" loading="lazy">' % (esc(image), esc(work_title(r))) if image else ""),
               tspan(work_title(r), work_title_en(r)), tspan(work_meta(r), work_meta_en(r)),
               ("<p class=\"ph-stop-note\">%s</p>" % tspan(note_zh, note_en)) if note_zh else ""))


def work_mini(rid):
    r = RECORDS.get(rid)
    if not r:
        return ""
    return ('<a class="ph-work-mini" href="../painting/%s.html"><img src="%s" alt="%s" loading="lazy">'
            '<div class="c"><b>%s</b>%s</div></a>') % (
        esc(rid), esc(img_of(rid)), esc(work_title(r)),
        tspan(work_title(r), work_title_en(r)),
        tspan(r.get("date_label") or "", r.get("date_label_en") or r.get("date_label") or ""))


def thumbs(work_ids, n=3):
    out = []
    for wid in (work_ids or [])[:n]:
        r = RECORDS.get(wid)
        if not r:
            continue
        out.append('<img src="%s" alt="%s" loading="lazy">' % (
            esc(img_of(wid)), esc(work_title(r))))
    return "".join(out)


def trail_stop(rid, note_zh, note_en):
    r = RECORDS.get(rid)
    if not r:
        return ""
    return """<a class="ph-stop" href="../painting/%s.html"><img src="%s" alt="%s" loading="lazy"><div class="txt"><div class="yr">%s</div><b>%s</b><p>%s</p></div></a>""" % (
        esc(rid), esc(img_of(rid)), esc(work_title(r)),
        tspan(work_meta(r), work_meta_en(r)),
        tspan(work_title(r), work_title_en(r)),
        tspan(note_zh, note_en))


def chapter_link(slug):
    return "chapter-%s.html" % slug


def movement_link(slug):
    if slug in MOV_A:
        return "movement-%s.html" % slug
    return "movements.html#%s" % slug


def movement_name(slug):
    m = MOV_A.get(slug) or MOV_B.get(slug) or {}
    return m.get("zh") or slug, m.get("en") or slug


def chapter_for_movement(slug):
    for c in chapters.CHAPTERS:
        if slug in c.get("movements", []):
            return c
    return None


def artist_years_en(a):
    return str(a.get("years") or "").replace("约", "c. ").replace("  ", " ").strip()


def artist_link(name):
    a = ART_BY_ZH.get(name)
    return "artist-%s.html" % a["slug"] if a else ""


def chapters_sorted():
    return list(chapters.CHAPTERS)


def hero_block(rid, kicker_zh, kicker_en, title_zh, title_en, deck_zh, deck_en, meta=None):
    image = img_of(rid)
    style = ' style="background-image:url(%s)"' % esc(image) if image else ""
    meta_html = "".join("<span>%s</span>" % tspan(z, e) for z, e in (meta or []))
    return """<section class="ph-hero"%s><div class="in">
<div class="ph-kicker">%s</div>
<h1 class="ph-title">%s</h1>
<div class="ph-deck">%s</div>
<div class="ph-meta">%s</div>
</div></section>""" % (
        style, tspan(kicker_zh, kicker_en), tspan(title_zh, title_en),
        tspan(deck_zh, deck_en), meta_html)


def appbar(current="history"):
    links = [
        ("尘画", "Frame & Grain", "../../main/"),
        ("主题", "Themes", "../../main/themes/"),
        ("时间线", "Timeline", "../../main/timeline/"),
        ("绘画史", "Painting History", "../../paint/history/"),
        ("画廊", "Gallery", "../../paint/gallery/"),
        ("日历", "Calendar", "../../main/today/"),
        ("搜索", "Search", "../../main/search/?scope=paintings"),
    ]
    nav = "".join('<a href="%s"%s>%s</a>' % (
        h, ' aria-current="page"' if key == current else "", tspan(z, e))
        for key, (z, e, h) in zip(("home", "themes", "timeline", "history", "gallery", "calendar", "search"), links))
    return """<header class="appbar s-appbar">
<a class="brand" href="../"><img class="leaf-mark brand-mark" src="../../assets/leaf/proud.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="sub"><span data-l="zh">绘画史 · 400–1930</span><span data-l="en">A History of Painting</span></span></a>
<nav class="desknav">%s</nav>
<div class="right"><button class="langbtn" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button><button class="iconbtn themebtn" type="button" data-themebtn aria-label="切换明暗"><svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg></button></div>
</header>""" % nav


def foot():
    nav = [
        ("尘画", "Frame & Grain", "../../main/"),
        ("主题", "Themes", "../../main/themes/"),
        ("时间线", "Timeline", "../../main/timeline/"),
        ("绘画史", "Painting History", "../../paint/history/"),
        ("日历", "Calendar", "../../main/today/"),
        ("摄影", "Photography", "../../photo/"),
        ("免责条款", "Disclaimer", "../../paint/legal/"),
    ]
    links = "".join('<a href="%s">%s</a>' % (h, tspan(z, e)) for z, e, h in nav)
    left = ('<div class="sf-left"><span data-l="zh">© 2026 尘画 · '
            '<a href="https://www.chenhua.net">chenhua.net</a></span>'
            '<span data-l="en">© 2026 <span class="sf-brand-long">Frame &amp; Grain</span>'
            '<span class="sf-brand-short">Frame</span> · '
            '<a href="https://www.chenhua.net">chenhua.net</a></span></div>')
    return """</div><footer class="site-foot">
%s
<nav class="sf-nav" aria-label="站内导航">%s</nav>
<div class="sf-right"><a href="../../paint/legal/">%s</a></div>
</footer>
<script src="../../assets/site.js?v=%s"></script>
</body></html>""" % (left, links, tspan("免责条款", "Disclaimer"), BUILD_ID)


def head(title_zh, title_en, desc_zh, desc_en, canonical, image="", ld=None):
    og = ""
    if image:
        og = '<meta property="og:image" content="%s">\n' % esc(image)
    extra = ""
    if ld:
        extra = '<script type="application/ld+json">%s</script>' % json.dumps(
            ld, ensure_ascii=False).replace("</", "<\\/")
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
%s
<script>(function(){try{function ck(n){var m=document.cookie.match(new RegExp("(?:^|; )"+n+"=([^;]*)"));return m?decodeURIComponent(m[1]):""}var q=new URLSearchParams(location.search).get("lang");var l=q||ck("chenhua-lang")||localStorage.getItem("chenhua-lang")||"zh";if(l==="en"){document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en"}else{document.documentElement.setAttribute("data-lang","zh");document.documentElement.lang="zh-CN"}var t=ck("chenhua-theme")||localStorage.getItem("chenhua-theme");if(t!=="light"&&t!=="dark")t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}catch(e){}})();</script>
%s<link rel="stylesheet" href="../../assets/app.css?v=%s">
<link rel="stylesheet" href="../../assets/static.css?v=%s">
<link rel="stylesheet" href="../../assets/history.css?v=%s">
</head>
<body class="static-body ph-body" data-title-zh="%s" data-title-en="%s" data-desc-zh="%s" data-desc-en="%s">
<div class="s-shell">
""" % (esc(title_zh), esc(desc_zh), esc(canonical), esc(canonical), esc(canonical),
       esc(title_zh), esc(desc_zh), esc(canonical), og, extra, BUILD_ID, BUILD_ID, BUILD_ID,
       esc(title_zh), esc(title_en), esc(desc_zh), esc(desc_en))


def page(title_zh, title_en, desc_zh, desc_en, filename, body, image="", ld=None):
    canonical = DOMAIN + "/history/" + ("" if filename == "index.html" else filename)
    return head(title_zh, title_en, desc_zh, desc_en, canonical, image, ld) + appbar() + \
        '<main class="ph-shell">' + body + "</main>" + foot()


def article_ld(title_en, desc_en, url, image=""):
    return {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title_en, "description": desc_en, "url": url,
        "image": image, "isPartOf": "https://paint.chenhua.net/",
        "inLanguage": ["zh-CN", "en"],
    }


def collection_ld(title_en, desc_en, url):
    return {"@context": "https://schema.org", "@type": "CollectionPage",
            "name": title_en, "description": desc_en, "url": url,
            "isPartOf": "https://paint.chenhua.net/"}


def write(name, content):
    HIST.mkdir(parents=True, exist_ok=True)
    (HIST / name).write_text(content, encoding="utf-8", newline="\n")


def index_page():
    hero = "botticelli-birth-of-venus-1485"
    chapters_html = []
    for c in chapters_sorted():
        thumbs_html = thumbs(c["anchors"], 3)
        chapters_html.append("""<a class="ph-chapter-card" href="%s">
<div class="num">%s</div><div class="yr">%s</div>
<h3>%s</h3><div class="ph-thumbs">%s</div>
<p>%s</p></a>""" % (
            chapter_link(c["slug"]), esc(c["no"]), tspan(c["years_zh"], c["years_en"]),
            tspan(c["title_zh"], c["title_en"]), thumbs_html,
            tspan(c.get("question_zh", ""), c.get("question_en", ""))))
    mov_html = "".join("""<a class="ph-index-card" href="%s"><div class="top"><h3>%s</h3><span class="count">%s</span></div><p>%s</p></a>""" % (
        movement_link(m["slug"]), tspan(m["zh"], m["en"]),
        tspan("%d 件" % len(m.get("works", [])), "%d works" % len(m.get("works", []))),
        tspan(m.get("summary_zh", ""), m.get("summary_en", "")))
        for m in movements.MOVEMENTS)
    artists_html = "".join("""<a class="ph-artist-card" href="artist-%s.html"><img src="%s" alt="%s" loading="lazy"><div class="c"><b>%s</b><span>%s</span></div></a>""" % (
        esc(a["slug"]), esc(img_of(a["hero"])), esc(a["zh"]),
        tspan(a["zh"], a["en"]), tspan(a["country_zh"] + " · " + a["years"], a["country_en"] + " · " + artist_years_en(a)))
        for a in artists.ARTISTS[:24])
    trails_html = "".join("""<a class="ph-trail" href="trail-%s.html"><h3>%s</h3><p>%s</p></a>""" % (
        esc(t["slug"]), tspan(t["zh"], t["en"]), tspan(t["intro_zh"], t["intro_en"]))
        for t in trails.TRAILS)
    periods_html = "".join("""<a class="ph-axis-item" href="period-%s.html"><img src="%s" alt="%s" loading="lazy"><div class="cap"><b>%s</b><span>%s</span></div></a>""" % (
        esc(p["slug"]), esc(img_of(p["hero"])), esc(p["title_zh"]),
        tspan(p["title_zh"], p["title_en"]), tspan(p["sub_zh"], p["sub_en"]))
        for p in periods.PERIODS)
    techniques_html = "".join('<a class="ph-pill" href="technique-%s.html">%s</a>' % (
        esc(t["slug"]), tspan(t["zh"], t["en"])) for t in techniques.TECHNIQUES)

    lead = tspan("先读章节，再读作品。章节回答“为什么这样画”，作品回答“它凭什么重要”。",
                 "Read chapters first, then works. Chapters answer why painting changed; works answer why they matter.")
    stats = [tspan("作品", "works"), tspan("艺术家", "artists"),
             tspan("A 类流派", "movement pages"), tspan("时期", "periods")]
    entries = [
        tspan("章节", "Chapters"), tspan("14 个章节，从线的觉醒到新大陆的寓言。", "14 chapters, from the awakening of line to a New World fable."),
        tspan("流派", "Movements"), tspan("15 个可读的 A 类页，另有 15 个 B 类条目。", "15 readable A-pages, plus 15 B-entries."),
        tspan("艺术家", "Artists"), tspan("24 位核心画家，先看人，再看画。", "24 core painters: the person before the picture."),
        tspan("时间", "Time"), tspan("8 个时期与一条独立的绘画时间轴。", "8 periods and a separate painting timeline."),
    ]
    chapter_block = [tspan("十四章节", "Fourteen chapters"),
                     tspan("按叙事顺序读，不按年代排序。", "Read in narrative order, not chronological order."), "".join(chapters_html)]
    movement_block = [tspan("十五个流派", "Fifteen movements"),
                      tspan("从早期文艺复兴到表现主义。", "From Early Renaissance to Expressionism."),
                      mov_html, tspan("打开流派索引", "Open the movement index")]
    artist_block = [tspan("三十六位艺术家", "Thirty-six artists"),
                    tspan("先看二十四位；完整名单在下一页。", "Twenty-four here; the full list is on the next page."),
                    artists_html, tspan("打开艺术家索引", "Open the artist index")]
    timeline_block = [tspan("八个时期", "Eight periods"), periods_html]
    trail_block = [tspan("八条小径", "Eight trails"),
                   tspan("光、身体、城市、自然、信仰、战争、肖像、日常。",
                         "Light, body, city, nature, faith, war, portrait, everyday."), trails_html]
    tech_block = [tspan("十二种技法", "Twelve techniques"),
                  tspan("媒介与手法，解释“怎么画出来”。", "Media and methods: how the picture was made."), techniques_html]
    final_block = [tspan("两条时间入口", "Two time entries"),
                   tspan("一条章节时间轴，一份 366 天日历。", "A chapter timeline and a 366-day calendar."),
                   tspan("进入时间轴", "Open the timeline"), tspan("进入日历", "Open the calendar")]
    args = (lead,) + tuple(stats) + tuple(entries) + tuple(chapter_block) + \
        tuple(movement_block) + tuple(artist_block) + tuple(timeline_block) + \
        tuple(trail_block) + tuple(tech_block) + tuple(final_block)
    body = hero_block(
        hero, "PAINTING HISTORY / 400–1930", "PAINTING HISTORY / 400–1930",
        "绘画史：把作品串成一条可以走的路",
        "A History of Painting: 106 works, one walkable path",
        "不是 106 张孤立的杰作，而是 14 个章节、15 个流派页、36 位艺术家、8 个时期、12 种技法、8 条小径。先看“为什么重要”，再看“怎么读”，最后看“什么时候”。",
        "Not 106 isolated masterpieces, but 14 chapters, 15 movement pages, 36 artists, 8 periods, 12 techniques and 8 trails. First ask why it matters, then how to read it, then when it happened.",
        [("106 件作品", "106 works"), ("14 章", "14 chapters"), ("400–1930", "400–1930")]) + """
<section class="ph-lead">%s</section>
<div class="ph-stat-grid">
<div class="ph-stat"><b>106</b><span>%s</span></div>
<div class="ph-stat"><b>36</b><span>%s</span></div>
<div class="ph-stat"><b>15</b><span>%s</span></div>
<div class="ph-stat"><b>8</b><span>%s</span></div>
</div>
<div class="ph-entry-grid">
<a class="ph-entry" href="#chapters"><div class="n">01 / READ</div><h3>%s</h3><p>%s</p></a>
<a class="ph-entry" href="movements.html"><div class="n">02 / STYLE</div><h3>%s</h3><p>%s</p></a>
<a class="ph-entry" href="artists.html"><div class="n">03 / PEOPLE</div><h3>%s</h3><p>%s</p></a>
<a class="ph-entry" href="timeline.html"><div class="n">04 / TIME</div><h3>%s</h3><p>%s</p></a>
</div>
<section class="ph-section" id="chapters"><h2>%s</h2><p>%s</p><div class="ph-chapter-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><p>%s</p><div class="ph-index-grid">%s</div><div class="ph-actions"><a class="ph-btn" href="movements.html">%s</a></div></section>
<section class="ph-section"><h2>%s</h2><p>%s</p><div class="ph-artist-grid">%s</div><div class="ph-actions"><a class="ph-btn" href="artists.html">%s</a></div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-timeline-axis">%s</div></section>
<section class="ph-section"><h2>%s</h2><p>%s</p><div class="ph-trail-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><p>%s</p><div class="ph-pill-row">%s</div></section>
<section class="ph-section"><h2>%s</h2><p>%s</p><div class="ph-actions"><a class="ph-btn gold" href="timeline.html">%s</a><a class="ph-btn" href="calendar.html">%s</a></div></section>
""" % args
    return page("绘画史", "A History of Painting", "从 400 到 1930，106 件作品、14 个章节、15 个流派页、36 位艺术家。",
                "From 400 to 1930: 106 works, 14 chapters, 15 movement pages and 36 artists.",
                "index.html", body, og_img(hero), collection_ld("A History of Painting", "106 works, 14 chapters, 15 movements.", DOMAIN + "/history/"))


def chapter_page(c):
    anchors = "".join(work_card for work_card in [work_link(w) for w in c["anchors"]])
    sections = "".join("""<section class="ph-section"><h3>%s</h3>%s%s</section>""" % (
        tspan(s["h_zh"], s["h_en"]), paras(s.get("p_zh")), '<div data-l="en">%s</div>' % paras(s.get("p_en")))
        for s in c["sections"])
    looks = "<div class=\"ph-two\"><div>%s</div><div data-l=\"en\">%s</div></div>" % (ul(c["look_zh"]), ul(c["look_en"]))
    movs = "".join('<a class="ph-pill" href="%s">%s</a>' % (movement_link(m), tspan(*movement_name(m)))
                   for m in c.get("movements", []))
    idx = chapters.CHAPTERS.index(c)
    prev_c = chapters.CHAPTERS[(idx - 1) % len(chapters.CHAPTERS)]
    next_c = chapters.CHAPTERS[(idx + 1) % len(chapters.CHAPTERS)]
    nav = '<div class="ph-next"><a href="%s">← %s</a><a href="%s">%s →</a></div>' % (
        chapter_link(prev_c["slug"]), tspan(prev_c["title_zh"], prev_c["title_en"]),
        chapter_link(next_c["slug"]), tspan(next_c["title_zh"], next_c["title_en"]))
    body = hero_block(c["hero"], "CHAPTER %s / %s" % (c["no"], c["years_zh"]),
                      "CHAPTER %s / %s" % (c["no"], c["years_en"]),
                      c["title_zh"], c["title_en"], c["question_zh"], c["question_en"],
                      [(c["years_zh"], c["years_en"]), ("第 %s 章" % c["no"], "Chapter %s" % c["no"])]) + """
<div class="ph-crumb"><a href="index.html">%s</a> / %s</div>
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-anchor-grid">%s</div></section>
%s
<section class="ph-section"><h2>%s</h2>%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-pill-row">%s</div></section>
%s""" % (
        tspan("绘画史", "Painting History"), tspan("第 %s 章" % c["no"], "Chapter %s" % c["no"]),
        tspan(c["thesis_zh"], c["thesis_en"]),
        tspan("本章锚点", "Anchor works"), anchors, sections,
        tspan("怎么看", "How to look"), looks,
        tspan("关联流派", "Related movements"), movs, nav)
    return page(c["title_zh"], c["title_en"], c["question_zh"], c["question_en"],
                chapter_link(c["slug"]), body, og_img(c["hero"]),
                article_ld(c["title_en"], c["question_en"],
                           DOMAIN + "/history/" + chapter_link(c["slug"]), og_img(c["hero"])))


def movement_page(m):
    works = "".join(work_link(w) for w in m.get("works", []))
    artists_html = "".join(
        ('<a class="ph-pill" href="%s">%s</a>' % (artist_link(a), tspan(a, a)) if artist_link(a)
         else '<span class="ph-pill">%s</span>' % tspan(a, a))
        for a in m.get("artists", []))
    ch = CH_BY_SLUG.get(m.get("chapter"))
    ch_html = ('<a class="ph-btn" href="%s">%s</a>' % (chapter_link(ch["slug"]), tspan(ch["title_zh"], ch["title_en"]))) if ch else ""
    body = hero_block(m["hero"], "MOVEMENT / %s" % m["years_zh"], "MOVEMENT / %s" % m["years_en"],
                      m["zh"], m["en"], m["summary_zh"], m["summary_en"],
                      [(m["years_zh"], m["years_en"]), ("%d 件" % len(m.get("works", [])), "%d works" % len(m.get("works", [])))]) + """
<div class="ph-crumb"><a href="index.html">%s</a> / <a href="movements.html">%s</a></div>
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-two"><div>%s</div><div data-l="en">%s</div></div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-two"><div>%s</div><div data-l="en">%s</div></div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-anchor-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-pill-row">%s</div></section>
<section class="ph-section"><h2>%s</h2><p>%s</p>%s</section>
""" % (
        tspan("绘画史", "Painting History"), tspan("流派", "Movements"),
        tspan("先看三个特征，再看三件作品；最后把它放回它所在的章节。",
              "Start with three traits, then three works; finally put it back into its chapter."),
        tspan("三个特征", "Three traits"), ul(m["traits_zh"]), ul(m["traits_en"]),
        tspan("怎么看", "How to look"), ul(m["look_zh"]), ul(m["look_en"]),
        tspan("代表作品", "Key works"), works,
        tspan("相关艺术家", "Artists"), artists_html,
        tspan("所在章节", "Chapter"), tspan("把它放回叙事里。", "Put it back into the narrative."), ch_html)
    return page(m["zh"], m["en"], m["summary_zh"], m["summary_en"],
                movement_link(m["slug"]), body, og_img(m["hero"]),
                article_ld(m["en"], m["summary_en"],
                           DOMAIN + "/history/" + movement_link(m["slug"]), og_img(m["hero"])))


def artist_page(a):
    works = "".join(work_link(w) for w in a.get("works", []))
    m = MOV_A.get(a["movement"]) or MOV_B.get(a["movement"]) or {}
    m_html = '<a class="ph-pill" href="%s">%s</a>' % (movement_link(a["movement"]), tspan(m.get("zh", a["movement"]), m.get("en", a["movement"])))
    body = hero_block(a["hero"], "ARTIST / %s" % a["years"], "ARTIST / %s" % artist_years_en(a),
                      a["zh"], a["en"], a["bio_zh"][0], a["bio_en"][0],
                      [(a["country_zh"], a["country_en"]), (a["years"], artist_years_en(a))]) + """
<div class="ph-crumb"><a href="index.html">%s</a> / <a href="artists.html">%s</a></div>
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-prose"><div>%s</div><div data-l="en">%s</div></div><p class="ph-note">%s</p></section>
<section class="ph-section"><h2>%s</h2><div class="ph-anchor-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-pill-row">%s</div></section>
""" % (
        tspan("绘画史", "Painting History"), tspan("艺术家", "Artists"),
        tspan("先读小传，再看作品；作品说明解释他/她为什么这样画。",
              "Read the life first, then the works; the notes explain why they painted this way."),
        tspan("小传", "Biography"), paras(a["bio_zh"][1:]), paras(a["bio_en"][1:]),
        tspan(a["note_zh"], a["note_en"]),
        tspan("代表作品", "Key works"), works,
        tspan("流派", "Movement"), m_html)
    return page(a["zh"], a["en"], a["bio_zh"][0], a["bio_en"][0],
                "artist-%s.html" % a["slug"], body, og_img(a["hero"]),
                article_ld(a["en"], a["bio_en"][0],
                           DOMAIN + "/history/artist-%s.html" % a["slug"], og_img(a["hero"])))


def period_page(p):
    works = "".join(work_link(w) for w in p.get("works", []))
    movs = "".join('<a class="ph-pill" href="%s">%s</a>' % (movement_link(m), tspan(*movement_name(m)))
                   for m in p.get("movements", []))
    themes = "<div class=\"ph-two\"><div>%s</div><div data-l=\"en\">%s</div></div>" % (ul(p["themes_zh"]), ul(p["themes_en"]))
    body = hero_block(p["hero"], "PERIOD / %s" % p["title_zh"], "PERIOD / %s" % p["title_en"],
                      p["sub_zh"], p["sub_en"], p["summary_zh"], p["summary_en"],
                      [(p["title_zh"], p["title_en"]), ("%d 件" % len(p.get("works", [])), "%d works" % len(p.get("works", [])))]) + """
<div class="ph-crumb"><a href="index.html">%s</a> / <a href="periods.html">%s</a></div>
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2>%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-anchor-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-pill-row">%s</div></section>
""" % (
        tspan("绘画史", "Painting History"), tspan("时期", "Periods"),
        tspan("先看关键词，再看作品；最后用相邻流派确认这段时间的边界。",
              "Start with the keywords, then the works; use the neighbouring movements to mark the period's edges."),
        tspan("三个关键词", "Three keywords"), themes,
        tspan("代表作品", "Key works"), works,
        tspan("相关流派", "Movements"), movs)
    return page(p["sub_zh"], p["sub_en"], p["summary_zh"], p["summary_en"],
                "period-%s.html" % p["slug"], body, og_img(p["hero"]),
                article_ld(p["sub_en"], p["summary_en"],
                           DOMAIN + "/history/period-%s.html" % p["slug"], og_img(p["hero"])))


def technique_page(t):
    works = "".join(work_link(w) for w in t.get("works", []))
    steps = "<div class=\"ph-two\"><div>%s</div><div data-l=\"en\">%s</div></div>" % (ul(t["steps_zh"]), ul(t["steps_en"]))
    artists_html = "".join(
        ('<a class="ph-pill" href="%s">%s</a>' % (artist_link(a), tspan(a, a)) if artist_link(a)
         else '<span class="ph-pill">%s</span>' % tspan(a, a))
        for a in t.get("artists", []))
    note = '<p class="ph-note">%s</p>' % tspan(t["note_zh"], t["note_en"]) if t.get("note_zh") else ""
    body = hero_block(t["hero"], "TECHNIQUE / %s" % t["kind_zh"], "TECHNIQUE / %s" % t["kind_en"],
                      t["zh"], t["en"], t["summary_zh"], t["summary_en"],
                      [(t["kind_zh"], t["kind_en"]), ("%d 件" % len(t.get("works", [])), "%d works" % len(t.get("works", [])))]) + """
<div class="ph-crumb"><a href="index.html">%s</a> / <a href="techniques.html">%s</a></div>
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2>%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-anchor-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-pill-row">%s</div>%s</section>
""" % (
        tspan("绘画史", "Painting History"), tspan("技法", "Techniques"),
        tspan("先看三步做法，再看作品；技法只有在具体的画里才成立。",
              "Start with the three steps, then the works; a technique only exists inside a specific picture."),
        tspan("怎么做", "How it is done"), steps,
        tspan("代表作品", "Key works"), works,
        tspan("相关艺术家", "Artists"), artists_html, note)
    return page(t["zh"], t["en"], t["summary_zh"], t["summary_en"],
                "technique-%s.html" % t["slug"], body, og_img(t["hero"]),
                article_ld(t["en"], t["summary_en"],
                           DOMAIN + "/history/technique-%s.html" % t["slug"], og_img(t["hero"])))


def trail_page(t):
    stops = "".join(trail_stop(s["work"], s["note_zh"], s["note_en"]) for s in t["stops"])
    body = hero_block(t["hero"], "TRAIL / %s" % t["zh"], "TRAIL / %s" % t["en"],
                      t["zh"], t["en"], t["intro_zh"], t["intro_en"],
                      [("%d 站" % len(t["stops"]), "%d stops" % len(t["stops"]))]) + """
<div class="ph-crumb"><a href="index.html">%s</a> / <a href="trails.html">%s</a></div>
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2>%s</section>
<section class="ph-section"><h2>%s</h2><p class="ph-lead">%s</p></section>
""" % (
        tspan("绘画史", "Painting History"), tspan("小径", "Trails"),
        tspan("按停靠顺序走；每一站只留一条线索，最后回到收束句。",
              "Follow the stops in order; each stop leaves one thread, and the closing sentence ties them together."),
        tspan("沿途", "Along the trail"), stops,
        tspan("走完之后", "After the walk"), tspan(t["closing_zh"], t["closing_en"]))
    return page(t["zh"], t["en"], t["intro_zh"], t["intro_en"],
                "trail-%s.html" % t["slug"], body, og_img(t["hero"]),
                article_ld(t["en"], t["intro_en"],
                           DOMAIN + "/history/trail-%s.html" % t["slug"], og_img(t["hero"])))


def movements_index():
    rows = "".join("""<div class="ph-index-card" id="%s"><div class="top"><h3>%s</h3><span class="count">%s</span></div><p>%s</p><div class="ph-pill-row"><a class="ph-pill" href="%s">%s</a></div></div>""" % (
        esc(m["slug"]), tspan(m["zh"], m["en"]), tspan(m["years_zh"], m["years_en"]),
        tspan(m["summary_zh"], m["summary_en"]), movement_link(m["slug"]), tspan("打开", "Open"))
        for m in movements.MOVEMENTS)
    brows = "".join("""<a class="ph-index-card" href="%s"><div class="top"><h3>%s</h3><span class="count">%s</span></div><p>%s</p></a>""" % (
        movement_link(m["slug"]), tspan(m["zh"], m["en"]), tspan("条目", "Entry"), tspan(m["note_zh"], m["note_en"]))
        for m in movements.MOVEMENTS_B)
    body = hero_block("kandinsky-composition-vii-1913", "INDEX / MOVEMENTS", "INDEX / MOVEMENTS",
                      "流派：十五个可读页，十五个条目", "Movements: fifteen pages, fifteen entries",
                      "A 类页回答“这个流派怎么形成、怎么看”；B 类条目只给一句定位，避免把单件作品硬写成流派史。",
                      "A-pages explain how a movement formed and how to read it; B-entries give one-line positions instead of inflating single works into art history.",
                      [("15 个 A 类", "15 A-pages"), ("15 个 B 类", "15 B-entries")]) + """
<section class="ph-section"><h2>%s</h2><div class="ph-index-grid">%s</div></section>
<section class="ph-section"><h2>%s</h2><div class="ph-index-grid">%s</div></section>
""" % (tspan("A 类：可读页", "A-pages"), rows, tspan("B 类：条目", "B-entries"), brows)
    return page("流派索引", "Movements", "15 个 A 类流派页 + 15 个 B 类条目。", "15 A-pages and 15 B-entries.",
                "movements.html", body, og_img("kandinsky-composition-vii-1913"),
                collection_ld("Movements", "15 A-pages and 15 B-entries.", DOMAIN + "/history/movements.html"))


def artists_index():
    cards = "".join("""<a class="ph-artist-card" href="artist-%s.html"><img src="%s" alt="%s" loading="lazy"><div class="c"><b>%s</b><span>%s</span></div></a>""" % (
        esc(a["slug"]), esc(img_of(a["hero"])), esc(a["zh"]), tspan(a["zh"], a["en"]),
        tspan(a["country_zh"] + " · " + a["years"], a["country_en"] + " · " + artist_years_en(a)))
        for a in artists.ARTISTS)
    body = hero_block("rembrandt-self-portrait-1669", "INDEX / ARTISTS", "INDEX / ARTISTS",
                      "三十六位艺术家", "Thirty-six artists",
                      "不是排行榜，而是一张工作网：谁在什么城市、什么赞助、什么技术条件下工作，又把手艺传给了谁。",
                      "Not a ranking but a working network: who worked in which city, under which patronage and technique, and who passed the craft on.",
                      [("36 位", "36 artists"), ("400–1942", "400–1942")]) + """
<section class="ph-section"><div class="ph-artist-grid">%s</div></section>
""" % cards
    return page("艺术家索引", "Artists", "36 位核心艺术家。", "36 core artists.",
                "artists.html", body, og_img("rembrandt-self-portrait-1669"),
                collection_ld("Artists", "36 core artists.", DOMAIN + "/history/artists.html"))


def periods_index():
    cards = "".join("""<a class="ph-chapter-card" href="period-%s.html"><div class="num">%s</div><div class="yr">%s</div><h3>%s</h3><div class="ph-thumbs">%s</div><p>%s</p></a>""" % (
        esc(p["slug"]), esc(p["title_zh"]), tspan(p["title_zh"], p["title_en"]),
        tspan(p["sub_zh"], p["sub_en"]),
        thumbs(p["works"], 3),
        tspan(p["summary_zh"], p["summary_en"]))
        for p in periods.PERIODS)
    body = hero_block("turner-fighting-temeraire-1839", "INDEX / PERIODS", "INDEX / PERIODS",
                      "八个时期", "Eight periods",
                      "时期不是整齐的抽屉，而是八段可以被讨论的时间。每一段都给出关键词、代表作品和相邻流派。",
                      "Periods are not neat drawers but eight discussable stretches of time, each with keywords, key works and neighbouring movements.",
                      [("8 段", "8 periods"), ("400–1930", "400–1930")]) + """
<section class="ph-section"><div class="ph-chapter-grid ph-period-grid">%s</div></section>
""" % cards
    return page("时期索引", "Periods", "8 个时期页，400–1930。", "Eight periods, 400–1930.",
                "periods.html", body, og_img("turner-fighting-temeraire-1839"),
                collection_ld("Periods", "Eight periods, 400–1930.", DOMAIN + "/history/periods.html"))


def techniques_index():
    cards = "".join("""<a class="ph-index-card" href="technique-%s.html"><div class="top"><h3>%s</h3><span class="count">%s</span></div><p>%s</p></a>""" % (
        esc(t["slug"]), tspan(t["zh"], t["en"]), tspan(t["kind_zh"], t["kind_en"]),
        tspan(t["summary_zh"], t["summary_en"]))
        for t in techniques.TECHNIQUES)
    body = hero_block("van-eyck-arnolfini-1434", "INDEX / TECHNIQUES", "INDEX / TECHNIQUES",
                      "十二种技法与媒介", "Twelve techniques and media",
                      "技法不是配方，而是决定：先画什么、后画什么、哪里留白、哪里堆厚。它决定一张画能说什么。",
                      "Technique is not a recipe but a set of decisions: what comes first, what waits, where to leave blank, where to build thick. It decides what a picture can say.",
                      [("12 种", "12 techniques"), ("媒介 + 技法", "Media + methods")]) + """
<section class="ph-section"><div class="ph-index-grid">%s</div></section>
""" % cards
    return page("技法索引", "Techniques", "12 种绘画技法与媒介。", "Twelve painting techniques and media.",
                "techniques.html", body, og_img("van-eyck-arnolfini-1434"),
                collection_ld("Techniques", "Twelve techniques and media.", DOMAIN + "/history/techniques.html"))


def trails_index():
    cards = "".join("""<a class="ph-trail" href="trail-%s.html"><h3>%s</h3><p>%s</p><span class="ph-pill">%s</span></a>""" % (
        esc(t["slug"]), tspan(t["zh"], t["en"]), tspan(t["intro_zh"], t["intro_en"]),
        tspan("%d 站" % len(t["stops"]), "%d stops" % len(t["stops"])))
        for t in trails.TRAILS)
    body = hero_block("caravaggio-calling-of-matthew-1600", "INDEX / TRAILS", "INDEX / TRAILS",
                      "八条横向小径", "Eight lateral trails",
                      "章节是纵轴，小径是横轴：同一条线索穿过不同年代、不同地域，让 106 件作品彼此照亮。",
                      "Chapters are the vertical axis; trails are horizontal. One thread runs through different periods and regions, letting 106 works illuminate one another.",
                      [("8 条", "8 trails"), ("106 件", "106 works")]) + """
<section class="ph-section"><div class="ph-trail-grid">%s</div></section>
""" % cards
    return page("小径索引", "Trails", "8 条横向小径。", "Eight lateral trails.",
                "trails.html", body, og_img("caravaggio-calling-of-matthew-1600"),
                collection_ld("Trails", "Eight lateral trails.", DOMAIN + "/history/trails.html"))


def timeline_page():
    blocks = []
    for p in periods.PERIODS:
        works = "".join(work_mini(w) for w in p["works"][:6])
        movs = "".join('<a class="ph-pill" href="%s">%s</a>' % (movement_link(m), tspan(*movement_name(m)))
                       for m in p["movements"])
        blocks.append("""<section class="ph-section" id="%s"><div class="ph-chapter-card" style="display:block"><div class="num">%s</div><div class="yr">%s</div><h3>%s</h3><p>%s</p><div class="ph-work-row">%s</div><div class="ph-pill-row">%s</div><div class="ph-actions"><a class="ph-btn" href="period-%s.html">%s</a></div></div></section>""" % (
            esc(p["slug"]), esc(p["title_zh"]), tspan(p["title_zh"], p["title_en"]),
            tspan(p["sub_zh"], p["sub_en"]), tspan(p["summary_zh"], p["summary_en"]),
            works, movs, esc(p["slug"]), tspan("打开时期页", "Open the period")))
    body = hero_block("hokusai-great-wave-1831", "TIMELINE / 400–1930", "TIMELINE / 400–1930",
                      "绘画自己的时间轴", "Painting's own timeline",
                      "摄影与故事的时间轴仍是 1820s–2020s；绘画需要一根单独的轴，从 400 年代一直走到 1930。它不是主站的放大版，而是另一种时间的尺度。",
                      "The photography and story timeline remains 1820s–2020s; painting needs its own axis, from the 400s to 1930. It is not a zoomed-in version of the main timeline but another scale of time.",
                      [("8 个时期", "8 periods"), ("400–1930", "400–1930")]) + """
<section class="ph-lead">%s</section>
<section class="ph-section"><h2>%s</h2><div class="ph-timeline-axis">%s</div></section>
%s
<section class="ph-callout"><h2>%s</h2><p>%s</p><div class="ph-actions"><a class="ph-btn gold" href="calendar.html">%s</a><a class="ph-btn" href="../../main/timeline/">%s</a></div></section>
""" % (
        tspan("从 400 到 1930，八段时期。每一段只给关键词、几件作品和相邻流派；完整论证在章节页。",
              "From 400 to 1930 in eight periods. Each gives keywords, a few works and neighbouring movements; the full argument is in the chapters."),
        tspan("一条可以滑动的轴", "A scrollable axis"),
        "".join('<a class="ph-axis-item" href="#%s"><img src="%s" alt="%s" loading="lazy"><div class="cap"><b>%s</b><span>%s</span></div></a>' % (
            esc(p["slug"]), esc(img_of(p["hero"])), esc(p["title_zh"]),
            tspan(p["title_zh"], p["title_en"]), tspan(p["sub_zh"], p["sub_en"])) for p in periods.PERIODS),
        "".join(blocks),
        tspan("日历不是时间轴的缩写", "The calendar is not a mini timeline"),
        tspan("时间轴回答“在什么时代”，日历回答“今天看哪件”。两者共用作品，但问题不同。",
              "The timeline answers 'in what era'; the calendar answers 'what to look at today'. They share works but ask different questions."),
        tspan("打开 366 天日历", "Open the 366-day calendar"),
        tspan("回到主站时间轴", "Back to the main timeline"))
    return page("绘画时间轴", "Painting timeline", "400–1930，八个时期。", "400–1930 in eight periods.",
                "timeline.html", body, og_img("hokusai-great-wave-1831"),
                collection_ld("Painting timeline", "400–1930 in eight periods.", DOMAIN + "/history/timeline.html"))


def calendar_page():
    slots = ph_calendar.build_slots(PAINT_WORK_IDS)
    n_works = len(PAINT_WORK_IDS)
    counts = {}
    for s in slots:
        counts[s["work"]] = counts.get(s["work"], 0) + 1
    n4 = sum(1 for v in counts.values() if v == 4)
    n3 = sum(1 for v in counts.values() if v == 3)
    months = ph_calendar.calendar_months(slots)
    month_html = []
    for m in range(1, 13):
        month_slots = months.get(m, [])
        first_weekday = (date(2024, m, 1).weekday() + 1) % 7
        cells = ['<span class="ph-day blank" aria-hidden="true"></span>'] * first_weekday
        for s in month_slots:
            r = RECORDS.get(s["work"])
            if not r:
                cells.append('<span class="ph-day">%d</span>' % ph_calendar.day_of(s["date"]))
                continue
            cells.append("""<a class="ph-day" href="../painting/%s.html" data-date="%s" title="%s"><img src="%s" alt="%s" loading="lazy"><span class="d">%d</span><span class="t">%s</span></a>""" % (
                esc(s["work"]), esc(s["date"]), esc(work_title(r)), esc(img_of(s["work"])),
                esc(work_title(r)), ph_calendar.day_of(s["date"]), tspan(work_title(r), work_title_en(r))))
        month_html.append("""<section class="ph-month" id="month-%02d"><h2>%s<span class="ph-pill" style="float:right">%s</span></h2><div class="ph-month-grid">%s</div></section>""" % (
            m, tspan(ph_calendar.MONTH_ZH[m - 1], ph_calendar.MONTH_EN[m - 1]),
            tspan("%d 件" % len(month_slots), "%d works" % len(month_slots), ), "".join(cells)))
    month_nav = "".join('<a class="ph-pill" href="#month-%02d">%s</a>' % (m, tspan(ph_calendar.MONTH_ZH[m - 1][:2], ph_calendar.MONTH_EN[m - 1][:3]))
                        for m in range(1, 13))
    events = sorted(ph_calendar.ART_EVENTS, key=lambda e: (e["date"], e["year"]))
    events_html = "".join("""<div class="ph-event" data-date="%s"><div class="d">%s</div><div class="y">%d</div><div class="t"><b>%s</b></div></div>""" % (
        esc(e["date"]), esc(e["date"]), e["year"], tspan(e["zh"], e["en"]))
        for e in events)
    body = hero_block("vermeer-girl-pearl-earring-1665", "CALENDAR / 366 DAYS", "CALENDAR / 366 DAYS",
                      "今日一画：三百六十六天", "A painting a day: 366 days",
                      "这是一份编辑排期，不是创作日期。它不声称“某年某月某日画了这张画”，只安排“今天看哪一件”。历史事件另立“艺术史上的今天”，宁缺毋滥。",
                      "This is an editorial schedule, not a creation date. It does not claim 'this was painted on this day'; it only decides 'what to look at today'. Historical events belong to a separate 'On This Day in Art', and only when exact.",
                      [("366 天", "366 days"), ("%d 件绘画" % n_works, "%d paintings" % n_works), ("编辑排期", "Editorial schedule")]) + """
<section class="ph-crumb"><a href="index.html">%s</a> / %s</section>
<section class="ph-lead">%s</section>
<p class="ph-calendar-note">%s</p>
<div class="ph-pill-row">%s</div>
<section class="ph-section"><div class="ph-calendar">%s</div></section>
<section class="ph-section" id="art-events"><h2>%s</h2><p class="ph-calendar-note">%s</p><div class="ph-event-list">%s</div></section>
<script>(function(){var d=new Date();var md=String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");document.querySelectorAll('.ph-day[data-date="'+md+'"],.ph-event[data-date="'+md+'"]').forEach(function(el){el.classList.add("today")});})();</script>
""" % (
        tspan("绘画史", "Painting History"), tspan("日历", "Calendar"),
        tspan("每天一件作品，一年三轮多一点。不是“历史上的今天”，而是“今天可以看什么”。",
              "One work a day, just over three cycles a year. Not 'on this day in history' but 'what can I look at today'."),
        tspan("排期规则：%d 件绘画按年代排序，以 37 为步长轮转；%d 件出现 4 次，%d 件出现 3 次，合计 366 个槽位。所有日期均为编辑排期。"
              % (n_works, n4, n3),
              "Schedule: %d paintings sorted by date, rotated with a step of 37; %d works appear four times, %d three times, totalling 366 slots. All dates are editorial."
              % (n_works, n4, n3)),
        month_nav, "".join(month_html),
        tspan("艺术史上的今天", "On This Day in Art"),
        tspan("只收有确切日期的生卒、开幕与完成记录，共 %d 条；不是每天都有。日期以公历计。" % len(events),
              "Only exact birth, death, opening and completion dates, %d entries in all; not every day has one. Dates are Gregorian." % len(events)),
        events_html)
    return page("今日一画 · 366 天", "A painting a day · 366 days", "366 个编辑槽位，每天一件作品。",
                "366 editorial slots, one work a day.",
                "calendar.html", body, og_img("vermeer-girl-pearl-earring-1665"),
                collection_ld("A painting a day", "366 editorial slots, one work a day.", DOMAIN + "/history/calendar.html"))


# ---------------- 全站接线 ----------------

def paint_bridge(view):
    if view == "timeline":
        title_zh, title_en = "绘画有自己的时间轴", "Painting has its own timeline"
        text_zh = "主站时间轴仍是摄影与故事的 1820s–2020s；绘画史从 400 年代走到 1930，需要一根单独的轴。"
        text_en = "The main timeline remains 1820s–2020s for photography and stories; painting runs from the 400s to 1930 on a separate axis."
        href = "../../paint/history/timeline.html"
    else:
        title_zh, title_en = "绘画史：另一种读法", "A history of painting: another way to read"
        text_zh = "14 个章节、15 个流派页、36 位艺术家、8 个时期、12 种技法、8 条小径。作品不只是卡片，它们被串成一条叙事。"
        text_en = "14 chapters, 15 movement pages, 36 artists, 8 periods, 12 techniques and 8 trails. Works are not just cards; they are threaded into a narrative."
        href = "../../paint/history/"
    return """<!-- paint-bridge -->
<section style="max-width:1240px;margin:0 auto 0;padding:0 28px 8px">
<div style="border:1px solid var(--line);border-radius:16px;padding:20px 22px;background:linear-gradient(135deg,var(--surface2),var(--surface));display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center">
<div><p style="font-size:9px;letter-spacing:.22em;color:var(--accent);margin:0 0 7px">PAINTING HISTORY / 400–1930</p>
<h2 style="font-family:var(--serif);font-weight:400;font-size:clamp(21px,3vw,30px);line-height:1.35;margin:0 0 6px">%s</h2>
<p style="font-size:12px;line-height:1.8;color:var(--muted);margin:0;max-width:760px">%s</p></div>
<div><a href="%s" style="display:inline-flex;border:1px solid var(--accent);border-radius:999px;padding:9px 15px;font-size:11px;color:var(--accent);text-decoration:none;white-space:nowrap">%s</a></div>
</div></section>
<!-- /paint-bridge -->
""" % (tspan(title_zh, title_en), tspan(text_zh, text_en), href, tspan("进入绘画史", "Enter painting history"))


def inject_atlas():
    for path, view in ((DIST / "main" / "themes" / "index.html", "theme"),
                       (DIST / "main" / "timeline" / "index.html", "timeline")):
        if not path.exists():
            continue
        html_text = path.read_text(encoding="utf-8")
        html_text = re.sub(r"<!-- paint-bridge -->.*?<!-- /paint-bridge -->\n?", "", html_text, flags=re.S)
        bridge = paint_bridge(view)
        if '<main class="shell">' in html_text:
            html_text = html_text.replace('<main class="shell">', bridge + '<main class="shell">', 1)
        else:
            html_text = html_text.replace("</section>", "</section>" + bridge, 1)
        path.write_text(html_text, encoding="utf-8", newline="\n")


def first_para(text):
    text = (text or "").strip()
    for sep in ("\n\n", "\r\n\r\n"):
        if sep in text:
            return text.split(sep, 1)[0].strip()
    return text.split("\n", 1)[0].strip()


def today_paint_card(md, work_id):
    r = RECORDS.get(work_id) or {}
    if not r:
        return ""
    return """<!-- paint-today -->
<section class="today-paint">
<a class="today-paint-img" href="../../paint/painting/%s.html"><img src="%s" alt="%s" loading="lazy"></a>
<div class="today-paint-copy"><p class="eyebrow">%s</p><h2><a href="../../paint/painting/%s.html">%s</a></h2><p>%s</p><p class="today-paint-note">%s</p><a class="today-more" href="../../paint/history/calendar.html">%s</a></div>
</section>
<!-- /paint-today -->
""" % (
        esc(work_id), esc(img_of(work_id)), esc(work_title(r)),
        tspan("今日一画 / Painting of the Day", "Painting of the Day"),
        esc(work_id), tspan(work_title(r), work_title_en(r)),
        tspan(first_para(r.get("note")), first_para(r.get("note_en"))),
        tspan("编辑排期，非创作日期。", "Editorial schedule, not a creation date."),
        tspan("打开 366 天日历", "Open the 366-day calendar"))


def inject_today():
    slots = ph_calendar.build_slots(PAINT_WORK_IDS)
    by_date = {s["date"]: s["work"] for s in slots}
    for path in sorted((DIST / "main" / "today").glob("*.html")):
        if path.name == "index.html":
            continue
        md = path.stem
        if md not in by_date:
            continue
        html_text = path.read_text(encoding="utf-8")
        html_text = re.sub(r"<!-- paint-today -->.*?<!-- /paint-today -->\n?", "", html_text, flags=re.S)
        card = today_paint_card(md, by_date[md])
        if '<section class="today-list">' in html_text:
            html_text = html_text.replace('<section class="today-list">', card + '<section class="today-list">', 1)
        path.write_text(html_text, encoding="utf-8", newline="\n")
    index_path = DIST / "main" / "today" / "index.html"
    if index_path.exists():
        html_text = index_path.read_text(encoding="utf-8")
        html_text = re.sub(r"<!-- paint-today -->.*?<!-- /paint-today -->\n?", "", html_text, flags=re.S)
        today_md = date.today().strftime("%m-%d")
        card = today_paint_card(today_md, by_date.get(today_md, WORK_IDS[0]))
        if '<div class="year-head">' in html_text:
            html_text = html_text.replace('<div class="year-head">', card + '<div class="year-head">', 1)
        index_path.write_text(html_text, encoding="utf-8", newline="\n")


def append_sitemap(pages):
    path = PAINT / "sitemap.xml"
    if not path.exists():
        return
    text_in = path.read_text(encoding="utf-8")
    block = "<!-- PAINT_HISTORY_START -->\n" + "".join(
        "<url><loc>%s</loc><lastmod>%s</lastmod></url>\n" % (esc(DOMAIN + "/history/" + ("" if p == "index.html" else p)), date.today().isoformat())
        for p in pages) + "<!-- PAINT_HISTORY_END -->\n"
    text_in = re.sub(r"<!-- PAINT_HISTORY_START -->.*?<!-- PAINT_HISTORY_END -->\n?", "", text_in, flags=re.S)
    text_in = text_in.replace("</urlset>", block + "</urlset>")
    path.write_text(text_in, encoding="utf-8", newline="\n")


def main():
    HIST.mkdir(parents=True, exist_ok=True)
    for old in HIST.glob("*.html"):
        old.unlink()
    shutil.copy2(CORE / "static" / "history.css", DIST / "assets" / "history.css")

    pages = []
    write("index.html", index_page()); pages.append("index.html")
    for c in chapters_sorted():
        write(chapter_link(c["slug"]), chapter_page(c)); pages.append(chapter_link(c["slug"]))
    for m in movements.MOVEMENTS:
        write(movement_link(m["slug"]), movement_page(m)); pages.append(movement_link(m["slug"]))
    for a in artists.ARTISTS:
        write("artist-%s.html" % a["slug"], artist_page(a)); pages.append("artist-%s.html" % a["slug"])
    for p in periods.PERIODS:
        write("period-%s.html" % p["slug"], period_page(p)); pages.append("period-%s.html" % p["slug"])
    for t in techniques.TECHNIQUES:
        write("technique-%s.html" % t["slug"], technique_page(t)); pages.append("technique-%s.html" % t["slug"])
    for t in trails.TRAILS:
        write("trail-%s.html" % t["slug"], trail_page(t)); pages.append("trail-%s.html" % t["slug"])
    write("movements.html", movements_index()); pages.append("movements.html")
    write("artists.html", artists_index()); pages.append("artists.html")
    write("periods.html", periods_index()); pages.append("periods.html")
    write("techniques.html", techniques_index()); pages.append("techniques.html")
    write("trails.html", trails_index()); pages.append("trails.html")
    write("timeline.html", timeline_page()); pages.append("timeline.html")
    write("calendar.html", calendar_page()); pages.append("calendar.html")

    inject_atlas()
    inject_today()
    append_sitemap(pages)

    print("绘画史页面：%d 个；作品 %d；艺术家 %d；流派 A/B %d/%d" % (
        len(pages), len(WORK_IDS), len(artists.ARTISTS),
        len(movements.MOVEMENTS), len(movements.MOVEMENTS_B)))
    print("输出：", HIST)


if __name__ == "__main__":
    main()
