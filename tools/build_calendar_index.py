# -*- coding: utf-8 -*-
"""Build illustrated 366-day calendar indexes for the main and photo sites.

The main calendar keeps the photographic day as the full card and adds the
painting of the day as a small inset; the photo calendar is photographic only.
Run after build_today_pages.py and build_paint_history.py.
"""
import importlib.util
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\chenhua\Desktop\chenhua")
NEXT = ROOT / "next"
DIST = NEXT / "dist"
MAIN = DIST / "main"
PHOTO = DIST / "photo"
BUNDLE = DIST / "data" / "bundle.js"

sys.path.insert(0, str(NEXT / "tools"))
sys.path.insert(0, str(NEXT / "content" / "paint-history"))
import build_atlas_data as bad  # noqa: E402

_spec = importlib.util.spec_from_file_location("ph_calendar", NEXT / "content" / "paint-history" / "calendar.py")
ph_calendar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ph_calendar)


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def tspan(zh, en):
    return '<span data-l="zh">%s</span><span data-l="en">%s</span>' % (esc(zh), esc(en))


def load_bundle():
    raw = BUNDLE.read_text(encoding="utf-8")
    return json.loads(raw[raw.index("{"):].rstrip().rstrip(";"))


BUNDLE_DATA = load_bundle()
RECORDS = {r.get("id"): r for r in BUNDLE_DATA.get("records", []) if r.get("id")}
PAINT = [r for r in RECORDS.values()
         if r.get("collection") == "paintings" and r.get("content_type") == "painting"]
PAINT.sort(key=lambda r: (r.get("year") or 0, r.get("title") or r.get("id") or ""))
PAINT_IDS = [r["id"] for r in PAINT]
PAINT_BY_ID = {r["id"]: r for r in PAINT}

ATLAS = bad.build_data()
PHOTO_STORIES = [s for s in ATLAS.get("stories", []) if s.get("date") and s.get("img")]
BY_DATE = {}
for story in PHOTO_STORIES:
    BY_DATE.setdefault(story["date"], []).append(story)
for date in BY_DATE:
    BY_DATE[date].sort(key=lambda s: (s.get("year") or 0, s.get("title") or ""))


CAL_CSS = """
<style>
.cal-main{max-width:1240px;margin:0 auto;padding:0 0 62px}
.cal-hero{padding:54px 28px 30px;border-bottom:1px solid var(--line)}
.cal-kicker{font-family:var(--sans,ui-sans-serif,sans-serif);font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:var(--accent);margin:0 0 12px}
.cal-hero h1{font-family:var(--serif,"Noto Serif SC",serif);font-weight:400;font-size:clamp(38px,5.8vw,76px);line-height:1.05;letter-spacing:-.03em;margin:0 0 16px;max-width:900px}
.cal-hero h1 i{font-style:normal;color:var(--accent)}
.cal-sub{max-width:780px;color:var(--muted);font-size:14px;line-height:1.9;margin:0}
.cal-meta{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:18px;color:var(--muted);font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.cal-meta b{font-family:var(--serif);font-size:20px;font-weight:400;color:var(--text);letter-spacing:0;margin-right:4px}
.cal-meta a{color:var(--accent);text-decoration:none}
.cal-jump{display:flex;flex-wrap:wrap;gap:6px;padding:18px 28px 4px}
.cal-jump a{border:1px solid var(--line);padding:5px 9px;text-decoration:none;color:var(--muted);font-size:10px;line-height:1.2}
.cal-jump a:hover{border-color:var(--accent);color:var(--text)}
.cal-month{padding:24px 28px 16px;border-top:1px solid var(--line)}
.cal-month:first-of-type{border-top:0}
.cal-head{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin:0 0 12px}
.cal-head h2{font-family:var(--serif,"Noto Serif SC",serif);font-weight:400;font-size:clamp(26px,3vw,38px);line-height:1.1;margin:0}
.cal-head h2 em{font-style:normal;font-size:11px;letter-spacing:.12em;color:var(--muted);margin-left:10px;vertical-align:.35em}
.cal-head .cal-count{color:var(--muted);font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.cal-week{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;margin:0 0 5px}
.cal-week span{font-size:9px;letter-spacing:.1em;color:var(--muted);text-align:center;padding:3px 0}
.cal-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}
.cal-blank{aspect-ratio:4/3;background:transparent}
.cal-day{position:relative;display:block;aspect-ratio:4/3;overflow:hidden;background:#151311;border:1px solid rgba(255,255,255,.04);text-decoration:none;color:#fff;min-width:0}
.cal-day:hover{border-color:var(--accent)}
.cal-photo{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;filter:saturate(.86);transition:transform .45s ease,filter .45s ease}
.cal-day:hover .cal-photo{transform:scale(1.035);filter:saturate(1)}
.cal-shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.14) 35%,rgba(0,0,0,.76) 100%);pointer-events:none}
.cal-num{position:absolute;top:6px;left:8px;font-family:var(--serif);font-size:16px;line-height:1;color:#fff;text-shadow:0 1px 8px rgba(0,0,0,.7)}
.cal-caption{position:absolute;left:8px;right:8px;bottom:7px;z-index:2}
.cal-caption b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-family:var(--serif);font-weight:400;font-size:12px;line-height:1.35;text-shadow:0 1px 5px rgba(0,0,0,.8)}
.cal-caption span{display:block;margin-top:3px;font-size:8px;letter-spacing:.06em;color:rgba(255,255,255,.74);text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cal-paint{position:absolute;z-index:3;top:6px;right:6px;width:35%;height:52%;object-fit:cover;border:1px solid rgba(255,255,255,.7);box-shadow:0 2px 10px rgba(0,0,0,.35);background:#0d0c0b}
.cal-paint-label{position:absolute;z-index:4;top:6px;right:6px;width:35%;text-align:right;font-size:7px;letter-spacing:.08em;color:#fff;text-shadow:0 1px 4px #000;pointer-events:none}
.cal-day.is-today{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.cal-foot{padding:24px 28px 0;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px}
.cal-foot a{border:1px solid var(--line);padding:7px 11px;text-decoration:none;color:var(--muted);font-size:10px}
.cal-foot a:hover{border-color:var(--accent);color:var(--text)}
@media(max-width:900px){
 .cal-hero{padding:32px 20px 22px}.cal-hero h1{font-size:34px}.cal-sub{font-size:12px}
 .cal-jump{padding:12px 20px 2px}.cal-month{padding:19px 20px 10px}
 .cal-caption b{font-size:9px;-webkit-line-clamp:1}.cal-caption span{display:none}.cal-num{font-size:12px;top:5px;left:6px}
 .cal-paint{width:30%;height:45%;top:4px;right:4px}.cal-paint-label{display:none}
 .cal-week span{font-size:8px}
}
@media(max-width:600px){
 .cal-grid,.cal-week{gap:3px}.cal-month{padding:16px 14px 8px}.cal-hero{padding:26px 14px 18px}
 .cal-caption{left:5px;right:5px;bottom:4px}.cal-caption b{font-size:8px}.cal-num{font-size:10px}
 .cal-paint{display:none}
}
</style>
"""

MONTH_ZH = ["一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"]
MONTH_EN = ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"]
WEEK_ZH = ["一", "二", "三", "四", "五", "六", "日"]
WEEK_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def day_card(date, story, painting=None, combined=False):
    day = int(date[3:])
    image = story.get("img") if story else ""
    title = story.get("title") if story else ""
    title_en = story.get("title_en") if story else ""
    year = story.get("year") if story else ""
    count = len(BY_DATE.get(date, []))
    extra = ""
    if count > 1:
        extra = " +%d" % (count - 1)
    paint_html = ""
    if combined and painting:
        paint_src = painting.get("image") or painting.get("preview_image") or ""
        if paint_src:
            paint_html = ('<img class="cal-paint" src="%s" alt="%s" loading="lazy">'
                          '<span class="cal-paint-label">%s</span>' % (
                              esc(paint_src), esc(painting.get("title")),
                              esc("PAINTING")))
    img_html = ('<img class="cal-photo" src="%s" alt="%s" loading="lazy">'
                % (esc(image), esc(title)) if image else '<span class="cal-photo"></span>')
    caption = ""
    if story:
        meta = " · ".join(str(x) for x in (year, story.get("theme") or "") if x)
        caption = ('<div class="cal-caption"><b>%s</b><span>%s%s</span></div>'
                   % (tspan(title, title_en), esc(meta), extra))
    return ('<a class="cal-day" href="%s.html" data-date="%s" title="%s">%s<span class="cal-shade"></span>'
            '<span class="cal-num">%02d</span>%s%s</a>') % (
        date, date, esc(title or date), img_html, day, caption, paint_html)


def build_calendar(site):
    if site == "main":
        source = MAIN / "today" / "index.html"
        target = MAIN / "today" / "calendar.html"
        title_zh = "366 天 · 摄影与绘画 · 尘画"
        title_en = "366 Days · Photography & Painting · Frame & Grain"
        data_zh = "366 天，每天一张照片与一幅画。"
        data_en = "366 days, each with a photograph and a painting."
        kicker = "CALENDAR / PHOTOGRAPHY × PAINTING"
        h1 = tspan("每一天，<br>一张照片，<i>一幅画</i>。",
                   "Every day,<br>one photograph, <i>one painting</i>.")
        h1 = h1.replace("&lt;br&gt;", "<br>").replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        sub = tspan("摄影把当天发生的事留在光里，绘画把另一段时间放进同一格。"
                    "三百六十六天，每天一张事件照片作底，一幅绘画作旁注；点开任何一天，读当天的故事。",
                    "Photography keeps what happened that day in light; painting places another time in the same square. "
                    "Three hundred and sixty-six days, each with an event photograph as the ground and a painting as a margin; open any day to read its story.")
        stats = ('<div class="cal-meta"><span><b>366</b>天</span><span><b>379</b>篇摄影故事</span>'
                 '<span><b>101</b>件绘画</span><span><a href="../">今天</a> / <a href="../timeline/">时间线</a> / <a href="../themes/">主题</a></span></div>')
        combined = True
    else:
        source = PHOTO / "today" / "index.html"
        target = PHOTO / "today" / "calendar.html"
        title_zh = "366 天 · 摄影日历 · 尘画"
        title_en = "366 Days · Photography Calendar · Frame & Grain"
        data_zh = "366 天，每天一张照片。"
        data_en = "366 days, one photograph a day."
        kicker = "CALENDAR / PHOTOGRAPHY"
        h1 = tspan("每一天，<br>都有一张照片。", "Every day,<br>a photograph.")
        h1 = h1.replace("&lt;br&gt;", "<br>")
        sub = tspan("三百七十九篇摄影故事落在三百六十六天里。每一天选一张当天事件的影像作背景，"
                    "点开它，读这一天发生的完整故事。",
                    "Three hundred and seventy-nine photographic stories fall across three hundred and sixty-six days. "
                    "Each day has the image of its event as a background; open it to read the full story.")
        stats = ('<div class="cal-meta"><span><b>366</b>天</span><span><b>379</b>篇故事</span>'
                 '<span><b>9</b>个摄影主题</span><span><a href="../">今天</a> / <a href="../timeline/">时间线</a> / <a href="../themes/">主题</a></span></div>')
        combined = False

    body = ['<section class="cal-hero"><p class="cal-kicker">%s</p><h1>%s</h1><p class="cal-sub">%s</p>%s'
            '<div class="cal-jump">%s</div></section>' % (
                esc(kicker), h1, sub, stats,
                "".join('<a href="#month-%02d">%s</a>' % (m, tspan(MONTH_ZH[m - 1][:2], MONTH_EN[m - 1][:3]))
                        for m in range(1, 13)))]
    slots = ph_calendar.build_slots(PAINT_IDS)
    painting_by_date = {s["date"]: PAINT_BY_ID.get(s["work"]) for s in slots}
    for month in range(1, 13):
        days = ph_calendar.month_days(month)
        first_weekday = __import__("datetime").date(2024, month, 1).weekday()
        cells = ['<span class="cal-blank" aria-hidden="true"></span>'] * first_weekday
        for d in range(1, days + 1):
            md = "%02d-%02d" % (month, d)
            stories = BY_DATE.get(md) or []
            cells.append(day_card(md, stories[0] if stories else None,
                                  painting_by_date.get(md) if combined else None, combined))
        body.append('<section class="cal-month" id="month-%02d"><div class="cal-head"><h2>%s<em>%s</em></h2>'
                    '<span class="cal-count">%s</span></div><div class="cal-week">%s</div>'
                    '<div class="cal-grid">%s</div></section>' % (
                        month, tspan(MONTH_ZH[month - 1], MONTH_EN[month - 1]),
                        tspan("2024", "2024"),
                        tspan("%d 天" % days, "%d days" % days),
                        "".join('<span>%s</span>' % tspan(z, e) for z, e in zip(WEEK_ZH, WEEK_EN)),
                        "".join(cells)))
    body.append('<div class="cal-foot"><a href="../">%s</a><a href="../timeline/">%s</a>'
                '<a href="../themes/">%s</a><a href="https://paint.chenhua.net/history/calendar.html">%s</a></div>'
                % (tspan("回到今天", "Back to today"), tspan("摄影时间线", "Photography timeline"),
                   tspan("摄影主题", "Photography themes"), tspan("绘画史日历", "Painting calendar")))
    body.append('<script>(function(){var d=new Date();var md=String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");var el=document.querySelector(\'.cal-day[data-date="\'+md+\'"]\');if(el)el.classList.add("is-today")})();</script>')

    page = source.read_text(encoding="utf-8")
    page = re.sub(r"<title>.*?</title>", "<title>%s</title>" % esc(title_zh), page, count=1, flags=re.S)
    page = re.sub(r'data-title-zh="[^"]*"', 'data-title-zh="%s"' % esc(title_zh), page, count=1)
    page = re.sub(r'data-title-en="[^"]*"', 'data-title-en="%s"' % esc(title_en), page, count=1)
    page = re.sub(r'data-desc-zh="[^"]*"', 'data-desc-zh="%s"' % esc(data_zh), page, count=1)
    page = re.sub(r'data-desc-en="[^"]*"', 'data-desc-en="%s"' % esc(data_en), page, count=1)
    page = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="%s">' % esc(data_zh), page, count=1)
    page = page.replace("https://www.chenhua.net/today/", "https://www.chenhua.net/today/calendar.html")
    page = page.replace("https://photo.chenhua.net/today/", "https://photo.chenhua.net/today/calendar.html")
    page = page.replace("<main class=\"today-main today-index\">", "<main class=\"today-main cal-main\">")
    page = re.sub(r"<main[^>]*>.*?</main>", "<main class=\"today-main cal-main\">" + "".join(body) + "</main>",
                  page, count=1, flags=re.S)
    page = page.replace("</head>", CAL_CSS + "</head>", 1)
    page = page.replace('href="../today/" aria-current="page"', 'href="../today/calendar.html" aria-current="page"')
    page = page.replace('href="../today/"', 'href="../today/calendar.html"')
    target.write_text(page, encoding="utf-8", newline="\n")
    return target


def main():
    for site in ("main", "photo"):
        print(build_calendar(site))


if __name__ == "__main__":
    main()
