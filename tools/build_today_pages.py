# -*- coding: utf-8 -*-
"""Build the daily 'On This Day' pages plus the calendar index.

Input: next/dist/data/bundle.js (written by build_preview.py)
Output: next/dist/main/today/MM-DD.html and next/dist/main/today/index.html
"""
import html
import json
import re
import shutil
import time
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parents[1]
DIST = BASE / "dist"
MAIN = DIST / "main"
TODAY = MAIN / "today"
BUNDLE = DIST / "data" / "bundle.js"
SITE = "https://chenhua.net"
BUILD_ID = "20261123c"

MONTH_ZH = ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
TODAY_MD = date.today().strftime("%m-%d")


def load_bundle():
    raw = BUNDLE.read_text(encoding="utf-8")
    payload = raw[raw.index("{"):].rstrip().rstrip(";")
    return json.loads(payload)


def esc(value):
    return html.escape(str(value or ""), quote=True)


def text(value):
    return html.escape(str(value or ""), quote=False)


def day_label(md):
    mm, dd = int(md[:2]), int(md[3:])
    return "%d月%d日" % (mm, dd), "%s %d" % (MONTH_EN[mm - 1], dd)


def day_title(md):
    mm, dd = int(md[:2]), int(md[3:])
    return "%d月%d日" % (mm, dd), "%s %d" % (MONTH_EN[mm - 1], dd)


def clean(value, limit=None):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if limit and len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value


def _tspan(zh, en):
    return '<span data-l="zh">%s</span><span data-l="en">%s</span>' % (esc(zh), esc(en))


def primary_links():
    return [
        ("主题", "Themes", "../themes/"),
        ("时间线", "Timeline", "../timeline/"),
        ("历史上的今天", "On This Day", "../today/"),
        ("摄影", "Photography", "https://photo.chenhua.net/"),
        ("绘画", "Painting", "https://paint.chenhua.net/"),
        ("导航", "Directory", "https://netcn.org/"),
    ]


def footer_links():
    return [
        ("尘画", "Frame & Grain", "../"),
        ("主题", "Themes", "../themes/"),
        ("时间线", "Timeline", "../timeline/"),
        ("日历", "Calendar", "../today/"),
        ("摄影", "Photography", "https://photo.chenhua.net/"),
        ("绘画", "Painting", "https://paint.chenhua.net/"),
        ("导航", "Directory", "https://netcn.org/"),
    ]


def nav_html(current="", links=None):
    return "".join('<a href="%s"%s>%s</a>' % (
        h, ' aria-current="page"' if current and z == current else "", _tspan(z, e))
        for z, e, h in (links or primary_links()))


def appbar(prefix="../", expr="joy"):
    return """<header class="appbar s-appbar">
<a class="brand" href="{p}"><img class="leaf-mark brand-mark" src="../../assets/leaf/{expr}.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="sub"><span data-l="zh">尘归尘，画归画</span><span data-l="en">Image as history</span></span></a>
<nav class="desknav">{nav}</nav>
<div class="right"><button class="langbtn" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button><button class="iconbtn themebtn" type="button" data-themebtn aria-label="切换明暗"><svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg></button></div>
</header>""".format(p=prefix, expr=expr, nav=nav_html("历史上的今天"))


def footer(prefix="../"):
    links = []
    for z, e, h in footer_links():
        if z == "搜索":
            continue
        if z == "尘画":
            label = ('<span data-l="zh">出尘入画</span><span data-l="en">'
                     '<span class="sf-brand-long">Frame &amp; Grain</span>'
                     '<span class="sf-brand-short">Frame</span></span>')
        else:
            label = _tspan(z, e)
        links.append('<a href="%s">%s</a>' % (h, label))
    nav = "".join(links)
    left = ('<div class="sf-left"><span data-l="zh">© 2026 尘画 · '
            '<a href="https://chenhua.net">chenhua.net</a></span>'
            '<span data-l="en">© 2026 <span class="sf-brand-long">Frame &amp; Grain</span>'
            '<span class="sf-brand-short">Frame</span> · '
            '<a href="https://chenhua.net">chenhua.net</a></span></div>')
    return """<footer class="site-foot">
{left}
<nav class="sf-nav" aria-label="站内导航">{nav}</nav>
<div class="sf-right"><a href="../legal/">{disclaimer}</a></div>
</footer>""".format(
        left=left,
        nav=nav,
        disclaimer=_tspan("免责条款", "Disclaimer"),
    )


def story_image(story, records):
    cover = story.get("cover")
    if cover and cover in records:
        rec = records[cover]
        return rec.get("image") or rec.get("preview_image") or ""
    for rid in story.get("photo_ids") or []:
        rec = records.get(rid)
        if rec:
            image = rec.get("image") or rec.get("preview_image")
            if image:
                return image
    return ""


def card(story, records):
    image = story_image(story, records)
    sid = story.get("id") or ""
    title = story.get("title") or sid
    title_en = story.get("title_en") or title
    subtitle = clean(story.get("subtitle") or story.get("intro") or "", 220)
    subtitle_en = clean(story.get("subtitle_en") or story.get("intro_en") or subtitle, 220)
    label = story.get("date_label") or (story.get("date") or "")
    label_en = story.get("date_label_en") or label
    image_html = (
        '<img src="%s" alt="%s" loading="eager">' % (esc(image), esc(title))
        if image
        else '<div class="today-noimg"><span data-l="zh">影像整理中</span><span data-l="en">Image pending</span></div>'
    )
    return """<article class="today-card">
<a class="today-cover" href="../story/{sid}.html" aria-label="{title_alt}">{image_html}</a>
<div class="today-copy"><div class="eyebrow"><span data-l="zh">{label}</span><span data-l="en">{label_en}</span></div>
<h2><a href="../story/{sid}.html"><span data-l="zh">{title}</span><span data-l="en">{title_en}</span></a></h2>
<p><span data-l="zh">{subtitle}</span><span data-l="en">{subtitle_en}</span></p>
<a class="today-more" href="../story/{sid}.html"><span data-l="zh">阅读全文 →</span><span data-l="en">Read the story →</span></a></div>
</article>""".format(
        sid=esc(sid), title_alt=esc(title), image_html=image_html,
        label=text(label), label_en=text(label_en), title=text(title), title_en=text(title_en),
        subtitle=text(subtitle), subtitle_en=text(subtitle_en),
    )


def page(md, stories, records, days):
    mm, dd = int(md[:2]), int(md[3:])
    zh, en = day_title(md)
    count = len(stories)
    first = stories[0]
    meta_title = "%s · 历史上的今天 · 尘画" % zh
    meta_title_en = "%s · On This Day · Frame & Grain" % en
    desc = clean(first.get("subtitle") or first.get("intro") or "", 180)
    desc_en = clean(first.get("subtitle_en") or first.get("intro_en") or desc, 180)
    image = story_image(first, records)
    index = days.index(md)
    prev_md = days[(index - 1) % len(days)]
    next_md = days[(index + 1) % len(days)]
    prev_zh, prev_en = day_title(prev_md)
    next_zh, next_en = day_title(next_md)
    cards = "\n".join(card(s, records) for s in stories)
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": meta_title_en,
        "alternateName": meta_title,
        "description": desc_en,
        "url": "%s/today/%s.html" % (SITE, md),
        "isPartOf": SITE + "/",
        "hasPart": [{"@type": "Article", "name": s.get("title_en") or s.get("title"),
                     "url": "%s/story/%s.html" % (SITE, s.get("id"))} for s in stories],
    }
    return """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>{meta_title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="zh-CN" href="{canonical}">
<link rel="alternate" hreflang="en" href="{canonical}?lang=en">
<link rel="icon" type="image/svg+xml" href="../../assets/leaf/favicon.svg">
<meta property="og:type" content="website">
<meta property="og:title" content="{meta_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="zh_CN">
<meta property="og:locale:alternate" content="en_US">
{ogimage}
<script>(function(){{try{{function ck(n){{var m=document.cookie.match(new RegExp("(?:^|; )"+n+"=([^;]*)"));return m?decodeURIComponent(m[1]):""}}var q=new URLSearchParams(location.search).get("lang");var l=q||ck("chenhua-lang")||localStorage.getItem("chenhua-lang")||"zh";if(l==="en"){{document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en"}}else{{document.documentElement.setAttribute("data-lang","zh");document.documentElement.lang="zh-CN"}}var t=ck("chenhua-theme")||localStorage.getItem("chenhua-theme");if(t!=="light"&&t!=="dark")t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}}})();</script>
<link rel="stylesheet" href="../../assets/app.css?v={build}">
<link rel="stylesheet" href="../../assets/static.css?v={build}">
<link rel="stylesheet" href="../../assets/today.css?v={build}">
<script type="application/ld+json">{ld}</script>
</head>
<body class="static-body today-body" data-title-zh="{meta_title}" data-title-en="{meta_title_en}" data-desc-zh="{desc}" data-desc-en="{desc_en}">
<div class="s-shell">
{appbar}
<main class="today-main">
<section class="day-hero">
<div class="eyebrow"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></div>
<h1><span data-l="zh">{zh}</span><span data-l="en">{en}</span></h1>
</section>
<section class="today-list">{cards}</section>
<nav class="today-nav"><a href="{prev_md}.html"><span data-l="zh">← {prev_zh}</span><span data-l="en">← {prev_en}</span></a><a class="center" href="index.html"><span data-l="zh">全年日历</span><span data-l="en">Full calendar</span></a><a href="{next_md}.html"><span data-l="zh">{next_zh} →</span><span data-l="en">{next_en} →</span></a></nav>
</main>
</div>
{footer}
<script src="../../assets/site.js?v={build}"></script>
</body></html>
""".format(
        meta_title=esc(meta_title), meta_title_en=esc(meta_title_en), desc=esc(desc), desc_en=esc(desc_en),
        canonical=esc("%s/today/%s.html" % (SITE, md)), ogimage=('<meta property="og:image" content="%s">' % esc(image) if image else ""),
        build=BUILD_ID, ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
        appbar=appbar(), footer=footer(), zh=text(zh), en=text(en), count=count, story_word=('story' if count == 1 else 'stories'), cards=cards,
        prev_md=prev_md, next_md=next_md, prev_zh=text(prev_zh), prev_en=text(prev_en), next_zh=text(next_zh), next_en=text(next_en),
    )


def index_page(stories_by_day, days, records):
    def month_cover(month):
        for day_key in days:
            if int(day_key[:2]) != month:
                continue
            for story in stories_by_day.get(day_key, []):
                image = story_image(story, records)
                if image:
                    return image
        for rec in records.values():
            label = str(rec.get("date_label") or "")
            found = re.search(r"(\d{1,2})月", label)
            if found and int(found.group(1)) == month:
                image = rec.get("image") or rec.get("preview_image") or ""
                if image:
                    return image
        return ""
    cards = []
    for m in range(1, 13):
        month_days = [d for d in days if int(d[:2]) == m]
        if not month_days:
            continue
        month_stories = sum(len(stories_by_day.get(d, [])) for d in month_days)
        first_weekday = (date(2024, m, 1).weekday() + 1) % 7
        cells = ['<span class="today-day is-blank" aria-hidden="true"></span>' for _ in range(first_weekday)]
        days_in_month = (date(2024, m + 1, 1) - date(2024, m, 1)).days if m < 12 else 31
        for day_number in range(1, days_in_month + 1):
            md = "%02d-%02d" % (m, day_number)
            count = len(stories_by_day.get(md, []))
            if count:
                cls = "today-day has-stories" + (" is-today" if md == TODAY_MD else "")
                cells.append('<a class="%s" href="%s.html">%d</a>' % (cls, md, day_number))
            else:
                cells.append('<span class="today-day is-empty">%d</span>' % day_number)
        current = " is-current" if m == int(TODAY_MD[:2]) else ""
        cover = month_cover(m)
        cover_html = ""
        if cover:
            cover_html = '<div class="today-month-cover" aria-hidden="true"><img src="%s" alt="" loading="eager">%s</div>' % (
                esc(cover), '<span class="today-month-flag"><span data-l="zh">本月</span><span data-l="en">This month</span></span>' if current else "")
        cards.append("""<section class="today-month%s">
  %s<h2><span data-l="zh">%s</span><span data-l="en">%s</span></h2>
  <div class="today-weekdays" aria-hidden="true"><span><span data-l="zh">日</span><span data-l="en">S</span></span><span><span data-l="zh">一</span><span data-l="en">M</span></span><span><span data-l="zh">二</span><span data-l="en">T</span></span><span><span data-l="zh">三</span><span data-l="en">W</span></span><span><span data-l="zh">四</span><span data-l="en">T</span></span><span><span data-l="zh">五</span><span data-l="en">F</span></span><span><span data-l="zh">六</span><span data-l="en">S</span></span></div>
  <div class="today-days">%s</div>
</section>""" % (current, cover_html, MONTH_ZH[m - 1], MONTH_EN[m - 1], "".join(cells)))
    today_count = len(stories_by_day.get(TODAY_MD, []))
    # A small visual lead-in: today's image plus the nearest dated images.
    feature = []
    seen = set()
    cursor = days.index(TODAY_MD)
    for offset in (0, 1, -1, 2, -2, 3):
        md = days[(cursor + offset) % len(days)]
        for story in stories_by_day.get(md, []):
            image = story_image(story, records)
            if image and image not in seen:
                seen.add(image)
                feature.append((md, story, image))
                break
        if len(feature) >= 3:
            break
    feature_main = ""
    feature_side = ""
    if feature:
        md, story, image = feature[0]
        feature_main = '<a class="today-feature-main" href="%s.html"><img src="%s" alt="%s" loading="eager"><span class="today-feature-date"><span data-l="zh">%s</span><span data-l="en">%s</span></span></a>' % (
            md, esc(image), esc(story.get("title") or ""), text(day_title(md)[0]), text(day_title(md)[1]))
        side = feature[1:3]
        if side:
            feature_side = '<div class="today-feature-side">%s</div>' % "".join(
                '<a href="%s.html"><img src="%s" alt="%s" loading="eager"><span class="today-feature-label"><span data-l="zh">%s</span><span data-l="en">%s</span></span></a>' % (
                    md, esc(image), esc(story.get("title") or ""), text(day_title(md)[0]), text(day_title(md)[1]))
                for md, story, image in side)
    feature_html = '<div class="today-feature">%s%s</div>' % (feature_main, feature_side) if feature_main else ""
    desc = "按日期浏览尘画收录的历史故事与影像。"
    desc_en = "Browse historical stories and images by date."
    ld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "历史上的今天", "alternateName": "On This Day",
        "description": desc_en, "url": SITE + "/today/",
    }
    return """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>历史上的今天 · 尘画</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/today/">
<link rel="alternate" hreflang="zh-CN" href="{site}/today/">
<link rel="alternate" hreflang="en" href="{site}/today/?lang=en">
<link rel="icon" type="image/svg+xml" href="../../assets/leaf/favicon.svg">
<meta property="og:type" content="website"><meta property="og:title" content="历史上的今天 · 尘画">
<meta property="og:description" content="{desc}"><meta property="og:url" content="{site}/today/">
<script>(function(){{try{{function ck(n){{var m=document.cookie.match(new RegExp("(?:^|; )"+n+"=([^;]*)"));return m?decodeURIComponent(m[1]):""}}var q=new URLSearchParams(location.search).get("lang");var l=q||ck("chenhua-lang")||localStorage.getItem("chenhua-lang")||"zh";if(l==="en"){{document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en"}}else{{document.documentElement.setAttribute("data-lang","zh");document.documentElement.lang="zh-CN"}}var t=ck("chenhua-theme")||localStorage.getItem("chenhua-theme");if(t!=="light"&&t!=="dark")t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}}})();</script>
<link rel="stylesheet" href="../../assets/app.css?v={build}">
<link rel="stylesheet" href="../../assets/static.css?v={build}">
<link rel="stylesheet" href="../../assets/today.css?v={build}">
<script type="application/ld+json">{ld}</script>
</head>
<body class="static-body today-body" data-title-zh="历史上的今天 · 尘画" data-title-en="On This Day · Frame & Grain" data-desc-zh="{desc}" data-desc-en="{desc_en}">
<div class="s-shell">
{appbar}
<main class="today-main today-index">
  <header class="today-intro">
    <div>
      <p class="eyebrow"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></p>
      <h1><span data-l="zh">{today_zh}</span><span data-l="en">{today_en}</span></h1>
      <p class="today-intro-meta"><a href="{today_md}.html"><span data-l="zh">阅读今天的故事 →</span><span data-l="en">Read today's {story_word} →</span></a></p>
    </div>
  </header>
  {feature}
  <div class="year-head"><h2><span data-l="zh">全年日历</span><span data-l="en">Full calendar</span></h2></div>
  <div class="today-months">{cards}</div>
</main>
</div>
{footer}
<script src="../../assets/site.js?v={build}"></script>
</body></html>
""".format(desc=esc(desc), desc_en=esc(desc_en), site=SITE, build=BUILD_ID,
           ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"), appbar=appbar(expr="calm"), footer=footer(),
           cards="".join(cards), today_zh=text(day_title(TODAY_MD)[0]), today_en=text(day_title(TODAY_MD)[1]), today_md=TODAY_MD,
           today_count=today_count, story_word="story" if today_count == 1 else "stories",
           feature=feature_html)


def main():
    data = load_bundle()
    records = {r["id"]: r for r in data["records"] if r.get("id")}
    stories = [s for s in data["stories"] if s.get("date")]
    by_day = {}
    for s in stories:
        md = str(s["date"])[5:10]
        if re.match(r"^\d{2}-\d{2}$", md):
            by_day.setdefault(md, []).append(s)
    for md in by_day:
        by_day[md].sort(key=lambda s: (int(s.get("today_rank") or 1), str(s.get("date") or "")))
    days = []
    for m in range(1, 13):
        for d in range(1, 32):
            md = "%02d-%02d" % (m, d)
            if md == "02-30" or md == "02-31":
                continue
            days.append(md)
    days = [d for d in days if d in by_day]
    missing = [d for d in days if d not in by_day]
    if missing:
        raise SystemExit("missing dates: %s" % missing)
    TODAY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASE / "core" / "static" / "today.css", DIST / "assets" / "today.css")
    for md in days:
        (TODAY / (md + ".html")).write_text(page(md, by_day[md], records, days), encoding="utf-8", newline="\n")
    (TODAY / "index.html").write_text(index_page(by_day, days, records), encoding="utf-8", newline="\n")
    print("today pages: %d days, %d stories" % (len(days), sum(len(v) for v in by_day.values())))


if __name__ == "__main__":
    main()
