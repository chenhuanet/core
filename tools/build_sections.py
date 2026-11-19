# -*- coding: utf-8 -*-
"""Build the cross-media section pages.

Run AFTER build_atlas.py and build_paint_history.py, AFTER build_today_pages.py.
It does four things:
  1. copies the existing photographic atlas into photo/themes and
     photo/timeline, with photographic-only navigation and no paint bridge;
  2. copies the photographic daily pages into photo/today, strips the painting
     block and gives every day a full-bleed cover image;
  3. adds the real combined themes / dual-track timeline to the main site;
  4. creates paint/themes/index.html (8 trails + 15 movements).
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\chenhua\Desktop\chenhua")
NEXT = ROOT / "next"
DIST = NEXT / "dist"
CORE = NEXT / "core"
MAIN = DIST / "main"
PHOTO = DIST / "photo"
PAINT = DIST / "paint"
BUNDLE = DIST / "data" / "bundle.js"

sys.path.insert(0, str(NEXT / "tools"))
sys.path.insert(0, str(NEXT / "content" / "paint-history"))
import build_atlas_data as bad  # noqa: E402
import movements as ph_movements  # noqa: E402
import periods as ph_periods  # noqa: E402
import trails as ph_trails  # noqa: E402


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def text(value):
    return html.escape(str(value if value is not None else ""), quote=False)


def tspan(zh, en):
    return '<span data-l="zh">%s</span><span data-l="en">%s</span>' % (esc(zh), esc(en))


def load_bundle():
    raw = BUNDLE.read_text(encoding="utf-8")
    return json.loads(raw[raw.index("{"):].rstrip().rstrip(";"))


BUNDLE_DATA = load_bundle()
RECORDS = {r.get("id"): r for r in BUNDLE_DATA.get("records", []) if r.get("id")}
PAINT_WORKS = [r for r in RECORDS.values()
               if r.get("collection") == "paintings" and r.get("content_type") == "painting"]
PAINT_WORK_IDS = sorted(PAINT_WORKS, key=lambda r: (r.get("year") or 0, r.get("title") or r.get("id") or ""))
PAINT_BY_ID = {r["id"]: r for r in PAINT_WORKS}

ATLAS = bad.build_data()
SERIES = ATLAS["series"]
SERIES_EN = {s["name"]: s["name_en"] for s in SERIES}
PHOTO_STORIES = [s for s in ATLAS["stories"] if s.get("img")]
PHOTO_STORY_BY_ID = {s["id"]: s for s in PHOTO_STORIES}

TRAILS = ph_trails.TRAILS
MOVEMENTS = ph_movements.MOVEMENTS
MOVEMENTS_B = ph_movements.MOVEMENTS_B
PERIODS = ph_periods.PERIODS
MOVEMENT_BY_SLUG = {m["slug"]: m for m in MOVEMENTS}
PERIOD_BY_SLUG = {p["slug"]: p for p in PERIODS}

PHOTO_COUNT = len(ATLAS.get("stories") or [])
PAINT_COUNT = len(PAINT_WORKS)


def paint_img(work_id):
    r = PAINT_BY_ID.get(work_id) or {}
    return r.get("image") or r.get("preview_image") or ""


def paint_meta(work_id):
    r = PAINT_BY_ID.get(work_id) or {}
    return " · ".join(str(x) for x in (r.get("creator"), r.get("date_label") or r.get("year"), r.get("holding")) if x)


def photo_year(s):
    if s.get("year"):
        return int(s["year"])
    date = str(s.get("date") or "")
    return int(date[:4]) if date[:4].isdigit() else 0


def story_href(sid, prefix="/story/"):
    return prefix + sid + ".html"


def trail_cover(t):
    return paint_img(t.get("hero") or (t.get("stops") or [{}])[0].get("work"))


def period_cover(p):
    return paint_img(p.get("hero") or (p.get("works") or [""])[0])


def movement_link(slug):
    if slug in MOVEMENT_BY_SLUG:
        return "https://paint.chenhua.net/history/movement-%s.html" % slug
    return "https://paint.chenhua.net/history/movements.html#%s" % slug


SECTION_CSS = """
<style>
/* ---------- 摄影 / 绘画 分栏 ---------- */
.split-lead{max-width:1240px;margin:0 auto;padding:44px 28px 16px}
.split-kicker{font-size:9px;letter-spacing:.24em;text-transform:uppercase;color:var(--accent);margin:0 0 12px}
.split-lead h1{font-family:var(--serif);font-weight:400;font-size:clamp(34px,5vw,68px);line-height:1.04;letter-spacing:-.03em;margin:0 0 14px;max-width:980px}
.split-lead .intro{max-width:780px;color:var(--muted);font-size:13px;line-height:1.9;margin:0}
.split-index{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);margin:26px 0 0}
.split-index a{display:grid;grid-template-columns:36px 1fr;gap:12px;align-items:start;background:var(--paper);padding:17px 18px;text-decoration:none;color:var(--text);min-width:0}
.split-index a:hover{background:var(--panel)}
.split-index .no{font-size:10px;color:var(--accent);letter-spacing:.12em;padding-top:4px}
.split-index b{display:block;font-family:var(--serif);font-weight:400;font-size:19px;line-height:1.3}
.split-index em{display:block;font-style:normal;color:var(--muted);font-size:10px;line-height:1.6;margin-top:3px}
.part-head{max-width:1240px;margin:0 auto;padding:30px 28px 12px;display:flex;align-items:baseline;justify-content:space-between;gap:18px;border-top:1px solid var(--line)}
.part-head h2{font-family:var(--serif);font-weight:400;font-size:clamp(24px,3vw,38px);line-height:1.1;margin:0}
.part-head p{margin:0;color:var(--muted);font-size:11px;line-height:1.7;max-width:520px;text-align:right}
.part-head .part-kicker{display:block;font-size:9px;letter-spacing:.2em;color:var(--accent);margin-bottom:7px}
.paint-part{max-width:1240px;margin:10px auto 0;padding:8px 28px 34px;border-top:1px solid var(--line)}
.trail-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin-top:18px}
.trail-card{display:flex;flex-direction:column;min-width:0;background:var(--paper);color:var(--text);text-decoration:none;overflow:hidden}
.trail-card:hover{background:var(--panel)}
.trail-card img{width:100%;height:148px;object-fit:cover;display:block}
.trail-card .tc-body{padding:15px 16px 16px;display:flex;flex-direction:column;min-height:150px}
.trail-card .tc-meta{display:flex;justify-content:space-between;gap:10px;font-size:9px;letter-spacing:.12em;color:var(--accent);text-transform:uppercase;margin-bottom:8px}
.trail-card h3{font-family:var(--serif);font-weight:400;font-size:22px;line-height:1.2;margin:0 0 5px}
.trail-card .tc-en{font-size:9px;letter-spacing:.12em;color:var(--muted);margin-bottom:9px}
.trail-card p{font-size:11px;line-height:1.75;color:var(--muted);margin:0 0 12px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.trail-card .tc-more{margin-top:auto;font-size:10px;color:var(--accent);letter-spacing:.06em}
.movement-strip{border-top:1px solid var(--line);margin-top:24px;padding-top:18px}
.movement-strip h3{font-family:var(--serif);font-weight:400;font-size:20px;margin:0 0 12px}
.movement-links{display:flex;flex-wrap:wrap;gap:7px}
.movement-links a{display:inline-flex;align-items:baseline;gap:6px;border:1px solid var(--line);padding:6px 9px;text-decoration:none;color:var(--muted);font-size:10px;line-height:1.2}
.movement-links a:hover{border-color:var(--accent);color:var(--text)}
.movement-links a b{font-weight:400;color:var(--text);font-family:var(--serif);font-size:13px}
.paint-more{display:inline-flex;margin-top:16px;border:1px solid var(--accent);color:var(--accent);padding:9px 15px;font-size:11px;text-decoration:none}
.paint-more:hover{background:var(--accent);color:var(--paper)}

/* ---------- 双轨时间线 ---------- */
.combined-timeline{max-width:1240px;margin:0 auto;padding:20px 28px 6px}
.ct-lead{display:flex;justify-content:space-between;gap:20px;align-items:end;border-bottom:1px solid var(--line);padding:26px 0 14px}
.ct-lead h2{font-family:var(--serif);font-weight:400;font-size:clamp(26px,3.6vw,44px);line-height:1.1;margin:0}
.ct-lead p{max-width:520px;margin:0;color:var(--muted);font-size:11px;line-height:1.8;text-align:right}
.ct-legend{display:flex;gap:18px;font-size:9px;letter-spacing:.14em;color:var(--muted);padding:10px 0 4px}
.ct-legend i{display:inline-block;width:7px;height:7px;margin-right:6px;background:var(--accent)}
.ct-legend i.paint{background:#8b6b45}
.ct-row{display:grid;grid-template-columns:minmax(0,1fr) 96px minmax(0,1fr);gap:16px;border-top:1px solid var(--line);padding:18px 0}
.ct-side{min-width:0}
.ct-side-label{font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.ct-side-label.photo{color:var(--accent)}
.ct-side-label.paint{color:#b28b5d}
.ct-axis{display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding-top:20px;color:var(--muted)}
.ct-axis b{font-family:var(--serif);font-weight:400;font-size:14px;white-space:nowrap}
.ct-axis em{font-style:normal;font-size:9px;letter-spacing:.08em;margin-top:4px}
.ct-axis .ct-line{width:1px;height:46px;background:var(--line);margin-top:8px}
.ct-photo-card,.ct-paint-card{display:grid;grid-template-columns:76px minmax(0,1fr);gap:10px;text-decoration:none;color:var(--text);border-bottom:1px solid var(--line);padding:8px 0;min-width:0}
.ct-photo-card:last-child,.ct-paint-card:last-child{border-bottom:0}
.ct-photo-card img,.ct-paint-card img{width:76px;height:60px;object-fit:cover;display:block;filter:saturate(.9)}
.ct-photo-card .cc,.ct-paint-card .cc{min-width:0;display:flex;flex-direction:column;justify-content:center}
.ct-photo-card h3,.ct-paint-card h3{font-family:var(--serif);font-weight:400;font-size:16px;line-height:1.3;margin:0 0 3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ct-photo-card span,.ct-paint-card span{font-size:9px;color:var(--muted);letter-spacing:.04em}
.ct-empty{border:1px dashed var(--line);padding:14px;color:var(--dim);font-size:10px;line-height:1.7;min-height:68px;display:flex;align-items:center}
.ct-more{font-size:9px;color:var(--accent);text-decoration:none;margin-top:7px;display:inline-block}
@media(max-width:1050px){.trail-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.ct-row{grid-template-columns:1fr 70px 1fr;gap:10px}.ct-lead{display:block}.ct-lead p{text-align:left;margin-top:10px}}
@media(max-width:680px){.split-index{grid-template-columns:1fr}.trail-grid{grid-template-columns:1fr}.ct-row{grid-template-columns:1fr;padding:16px 0}.ct-axis{flex-direction:row;gap:8px;padding:0;align-items:center;justify-content:flex-start}.ct-axis .ct-line{width:30px;height:1px;margin:0}.ct-lead h2{font-size:28px}.part-head{display:block}.part-head p{text-align:left;margin-top:7px}}
</style>
"""


def remove_bridge(source):
    return re.sub(r"<!-- paint-bridge -->.*?<!-- /paint-bridge -->\n?", "", source, flags=re.S)


def patch_photo_page(source, kind):
    source = remove_bridge(source)
    source = source.replace("../story/", "https://www.chenhua.net/story/")
    source = source.replace("../../photo/", "../")
    source = source.replace("../photo/", "../")
    source = source.replace("../../paint/", "https://paint.chenhua.net/")
    source = source.replace("https://www.chenhua.net/themes/", "https://photo.chenhua.net/themes/")
    source = source.replace("https://www.chenhua.net/timeline/", "https://photo.chenhua.net/timeline/")
    source = source.replace("https://www.chenhua.net/today/", "https://photo.chenhua.net/today/")
    if kind == "themes":
        source = source.replace('data-title-zh="主题 · 尘画"', 'data-title-zh="摄影主题 · 尘画"')
        source = source.replace('data-title-en="Themes · Frame &amp; Grain"', 'data-title-en="Photography Themes · Frame &amp; Grain"')
        source = source.replace("<title>主题 · 尘画</title>", "<title>摄影主题 · 尘画</title>")
        source = source.replace("<title>Themes · Frame &amp; Grain</title>", "<title>Photography Themes · Frame &amp; Grain</title>")
    else:
        source = source.replace('data-title-zh="时间线 · 尘画"', 'data-title-zh="摄影时间线 · 尘画"')
        source = source.replace("<title>时间线 · 尘画</title>", "<title>摄影时间线 · 尘画</title>")
    return add_photo_lead(source, kind)


def copy_photo_sections():
    for kind in ("themes", "timeline"):
        src = MAIN / kind / "index.html"
        dst = PHOTO / kind / "index.html"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(patch_photo_page(src.read_text(encoding="utf-8"), kind), encoding="utf-8", newline="\n")


def patch_photo_today(source):
    source = re.sub(r"<!-- paint-today -->.*?<!-- /paint-today -->\n?", "", source, flags=re.S)
    source = source.replace("../../photo/", "../")
    source = source.replace("../../paint/", "https://paint.chenhua.net/")
    source = source.replace("../story/", "https://www.chenhua.net/story/")
    source = source.replace("https://www.chenhua.net/today/", "https://photo.chenhua.net/today/")
    source = source.replace("https://www.chenhua.net/search/", "https://photo.chenhua.net/search/")
    return source


def add_hero_cover(source):
    """Put the day's first photograph behind the day heading."""
    if 'class="day-hero has-cover"' in source or 'class="day-hero has-cover' in source:
        return source.replace("&amp;amp;", "&amp;")
    first_img = re.search(r'<article class="today-card">.*?<img[^>]+src="([^"]+)"', source, re.S)
    if not first_img:
        first_img = re.search(r'<a class="today-cover"[^>]*>.*?<img[^>]+src="([^"]+)"', source, re.S)
    if not first_img:
        return source
    image = html.unescape(first_img.group(1))
    hero = '<section class="day-hero">'
    if hero not in source:
        return source
    replacement = ('<section class="day-hero has-cover">'
                   '<div class="day-hero-cover" aria-hidden="true"><img src="%s" alt="" loading="eager"></div>'
                   % esc(image))
    return source.replace(hero, replacement, 1)


def copy_photo_today():
    src = MAIN / "today"
    dst = PHOTO / "today"
    dst.mkdir(parents=True, exist_ok=True)
    for page in sorted(src.glob("*.html")):
        source = patch_photo_today(page.read_text(encoding="utf-8"))
        if page.name != "index.html":
            source = add_hero_cover(source)
        (dst / page.name).write_text(source, encoding="utf-8", newline="\n")


def photo_series_cards():
    cards = []
    for s in SERIES:
        stories = [x for x in PHOTO_STORIES if x.get("theme") == s["name"]]
        cover = stories[0]["img"] if stories else ""
        cards.append("""<a class="trail-card" href="/themes/#%s">
<img src="%s" alt="%s" loading="lazy">
<div class="tc-body"><div class="tc-meta"><span>%s</span><span>%d 篇</span></div>
<h3>%s</h3><div class="tc-en">%s</div>
<p>%s</p><span class="tc-more">进入主题 →</span></div></a>""" % (
            esc(s["key"]), esc(cover), esc(s["name"]), esc(s["glyph"]), len(stories),
            esc(s["name"]), esc(s["name_en"]), esc(s.get("desc"))))
    return "\n".join(cards)


def paint_trail_cards():
    cards = []
    for t in TRAILS:
        cover = trail_cover(t)
        cards.append("""<a class="trail-card" href="https://paint.chenhua.net/history/trail-%s.html">
<img src="%s" alt="%s" loading="lazy">
<div class="tc-body"><div class="tc-meta"><span>PAINTING TRAIL</span><span>%d %s</span></div>
<h3>%s</h3><div class="tc-en">%s</div>
<p>%s</p><span class="tc-more">%s</span></div></a>""" % (
            esc(t["slug"]), esc(cover), esc(t["zh"]), len(t.get("stops") or []),
            tspan("站", "stops"), tspan(t["zh"], t["en"]), esc(t["en"]),
            tspan(t.get("intro_zh"), t.get("intro_en")), tspan("走这条小径 →", "Walk this trail →")))
    return "\n".join(cards)


def movement_links():
    return "".join('<a href="%s"><b>%s</b></a>' % (
        esc(movement_link(m["slug"])), tspan(m["zh"], m["en"])) for m in MOVEMENTS)


def combined_themes():
    return """<!-- combined-sections -->
%s
<section class="split-lead">
<p class="split-kicker">%s</p>
<h1>%s</h1>
<p class="intro">%s</p>
<div class="split-index">
<a href="#photo-themes"><span class="no">01</span><span><b>%s</b><em>%s</em></span></a>
<a href="#paint-themes"><span class="no">02</span><span><b>%s</b><em>%s</em></span></a>
</div>
</section>
<section class="part-head" id="photo-themes">
<div><span class="part-kicker">PHOTOGRAPHY / 9 THEMES</span><h2>%s</h2></div>
<p>%s</p>
</section>
<!-- /combined-sections -->
""" % (
        SECTION_CSS,
        tspan("ARCHIVE ATLAS / 摄影 · 绘画", "ARCHIVE ATLAS / PHOTOGRAPHY · PAINTING"),
        tspan("摄影与绘画，<br>两种观看世界的方法。", "Photography and painting,<br>two ways of seeing the world.").replace("&lt;br&gt;", "<br>"),
        tspan("摄影把世界留在感光层上，绘画把世界放回构图里。这里不再把绘画当作一条附注：九个摄影主题与八条绘画小径并排展开，先看照片，再看画。",
              "Photography fixes the world onto a sensitive surface; painting puts it back into a composition. Painting is no longer an appendix: nine photographic themes and eight painted trails are laid out side by side."),
        tspan("摄影 · 九个主题", "Photography · Nine themes"),
        tspan("%d 篇故事 / 9 个系列 / 366 天" % PHOTO_COUNT, "%d stories / 9 series / 366 days" % PHOTO_COUNT),
        tspan("绘画 · 八条小径", "Painting · Eight trails"),
        tspan("%d 件作品 / 15 个流派 / 400–1930" % PAINT_COUNT, "%d works / 15 movements / 400–1930" % PAINT_COUNT),
        tspan("摄影：九个主题", "Photography: nine themes"),
        tspan("点一张主题卡进入摄影叙事；下面的年代尺会把同一个主题放回它发生的年代。",
              "Choose a theme card to enter the photographic narrative; the decade ruler below puts it back into its own time."),
    )


def combined_paint_section():
    return """<!-- paint-themes-section -->
<section class="paint-part" id="paint-themes">
<div class="part-head" style="padding-left:0;padding-right:0;border-top:0">
<div><span class="part-kicker">PAINTING / 8 TRAILS</span><h2>%s</h2></div>
<p>%s</p>
</div>
<div class="trail-grid">%s</div>
<div class="movement-strip"><h3>%s</h3><div class="movement-links">%s</div></div>
<a class="paint-more" href="https://paint.chenhua.net/history/">%s</a>
</section>
<!-- /paint-themes-section -->
""" % (
        tspan("绘画：八条可以走的小径", "Painting: eight trails you can walk"),
        tspan("光、身体、城市、自然、信仰、战争、肖像、日常。每一条都从一件作品走到另一件作品。",
              "Light, body, city, nature, faith, war, portrait, everyday. Each trail moves from one work to another."),
        paint_trail_cards(),
        tspan("十五个流派，作为索引", "Fifteen movements, as an index"),
        movement_links(),
        tspan("进入绘画史 →", "Enter painting history →"),
    )


def insert_combined_themes():
    path = MAIN / "themes" / "index.html"
    source = path.read_text(encoding="utf-8")
    source = remove_bridge(source)
    source = re.sub(r"<!-- combined-sections -->.*?<!-- /combined-sections -->\n?", "", source, flags=re.S)
    source = re.sub(r"<!-- paint-themes-section -->.*?<!-- /paint-themes-section -->\n?", "", source, flags=re.S)
    head = combined_themes()
    if '<main class="shell">' in source:
        source = source.replace('<main class="shell">', head + '<main class="shell">', 1)
    else:
        source = source.replace("</section>", "</section>" + head, 1)
    if "</main>" in source:
        source = source.replace("</main>", "</main>\n" + combined_paint_section(), 1)
    else:
        source = source.replace("</body>", combined_paint_section() + "</body>", 1)
    path.write_text(source, encoding="utf-8", newline="\n")


def period_card(p):
    return """<a class="ct-paint-card" href="https://paint.chenhua.net/history/period-%s.html">
<img src="%s" alt="%s" loading="lazy"><div class="cc"><h3>%s</h3><span>%s</span></div></a>""" % (
        esc(p["slug"]), esc(period_cover(p)), esc(p.get("title_zh")),
        tspan(p.get("title_zh"), p.get("title_en")), tspan(p.get("sub_zh"), p.get("sub_en")))


def photo_card(s):
    theme_en = SERIES_EN.get(s.get("theme"), s.get("theme") or "")
    return """<a class="ct-photo-card" href="/story/%s.html">
<img src="%s" alt="%s" loading="lazy"><div class="cc"><h3>%s</h3><span>%s</span></div></a>""" % (
        esc(s["id"]), esc(s["img"]), esc(s.get("title")), tspan(s.get("title"), s.get("title_en")),
        tspan("%s · %s" % (s.get("year") or "", s.get("theme") or ""),
              "%s · %s" % (s.get("year") or "", theme_en)))


ERAS = [
    (400, 1300, ["400-1300"], "400–1300", "线的宗教", "The religion of line"),
    (1300, 1500, ["1300-1500"], "1300–1500", "文艺复兴", "Renaissance"),
    (1500, 1600, ["1500-1600"], "1500–1600", "盛期与北方", "High Renaissance and the North"),
    (1600, 1700, ["1600-1700"], "1600–1700", "巴洛克", "Baroque"),
    (1700, 1800, ["1700-1800"], "1700–1800", "启蒙与洛可可", "Enlightenment and Rococo"),
    (1800, 1880, ["1800-1880"], "1800–1880", "摄影术出现", "Photography arrives"),
    (1880, 1914, ["1880-1914"], "1880–1914", "现代前夜", "The eve of modernity"),
    (1914, 1930, ["1914-1930"], "1914–1930", "现代主义", "Modernism"),
    (1930, 1970, [], "1930–1970", "摄影成为日常", "Photography becomes everyday"),
    (1970, 2000, [], "1970–2000", "图像爆炸", "The image explosion"),
    (2000, 2027, [], "2000–2026", "数字与网络", "Digital and networked"),
]


def combined_timeline_rows():
    rows = []
    for start, end, pslugs, label, note, note_en in ERAS:
        photo = [s for s in PHOTO_STORIES if start <= photo_year(s) < end]
        photo.sort(key=lambda s: (photo_year(s), s.get("date") or ""))
        photo_cards = "".join(photo_card(s) for s in photo[:3])
        if not photo:
            photo_cards = '<div class="ct-empty"><span>%s</span></div>' % tspan(
                "摄影术尚未出现；这一段只有绘画。", "Photography had not yet arrived; this span belongs to painting alone.")
        paint_cards = "".join(period_card(PERIOD_BY_SLUG[x]) for x in pslugs if x in PERIOD_BY_SLUG)
        if not paint_cards:
            paint_cards = '<div class="ct-empty"><span>%s</span></div>' % tspan(
                "绘画史章节止于 1930；这一段由摄影接管。", "The painting chapters end at 1930; photography takes over from here.")
        rows.append("""<div class="ct-row">
<div class="ct-side"><div class="ct-side-label photo">%s %s</div>%s%s</div>
<div class="ct-axis"><b>%s</b><em>%s</em><div class="ct-line"></div></div>
<div class="ct-side"><div class="ct-side-label paint">%s %s</div>%s%s</div>
</div>""" % (
            tspan("摄影", "Photography"), ("%d %s" % (len(photo), tspan("篇", "story" if len(photo) == 1 else "stories"))) if photo else "—",
            photo_cards,
            '<a class="ct-more" href="/timeline/#photo-full">%s</a>' % tspan("看摄影完整时间线 →", "See the full photographic timeline →") if photo else "",
            esc(label), tspan(note, note_en),
            tspan("绘画", "Painting"), ("%d %s" % (len(pslugs), tspan("个时期", "period" if len(pslugs) == 1 else "periods"))) if pslugs else "—",
            paint_cards,
            '<a class="ct-more" href="https://paint.chenhua.net/history/timeline.html">%s</a>' % tspan("看绘画完整时间线 →", "See the full painting timeline →") if pslugs else "",
        ))
    return "".join(rows)


def combined_timeline():
    return """<!-- combined-sections -->
%s
<section class="combined-timeline">
<div class="ct-lead">
<div><span class="part-kicker">TIMELINE / PHOTOGRAPHY × PAINTING</span><h2>%s</h2></div>
<p>%s</p>
</div>
<div class="ct-legend"><span><i></i>%s</span><span><i class="paint"></i>%s</span></div>
%s
</section>
<section class="part-head" id="photo-full">
<div><span class="part-kicker">PHOTOGRAPHY / FULL TIMELINE</span><h2>%s</h2></div>
<p>%s</p>
</section>
<!-- /combined-sections -->
""" % (
        SECTION_CSS,
        tspan("同一时代，两种观看。", "One age, two ways of seeing."),
        tspan("左边是摄影在拍什么，右边是绘画在画什么。四千年的绘画史先独自走了很久，1820 年代以后，摄影才进入同一条时间轴。",
              "On the left, what photography was recording; on the right, what painting was painting. Painting walked alone for centuries; from the 1820s photography enters the same timeline."),
        tspan("摄影", "Photography"), tspan("绘画", "Painting"),
        combined_timeline_rows(),
        tspan("摄影：完整年代", "Photography: the full span"),
        tspan("下面是摄影故事的完整年代尺；点一个年代，看这一段时间里的全部影像。",
              "The complete decade ruler of photographic stories; choose a span to see every image within it."),
    )


def insert_combined_timeline():
    path = MAIN / "timeline" / "index.html"
    source = path.read_text(encoding="utf-8")
    source = remove_bridge(source)
    source = re.sub(r"<!-- combined-sections -->.*?<!-- /combined-sections -->\n?", "", source, flags=re.S)
    head = combined_timeline()
    if '<main class="shell">' in source:
        source = source.replace('<main class="shell">', head + '<main class="shell">', 1)
    else:
        source = source.replace("</section>", "</section>" + head, 1)
    path.write_text(source, encoding="utf-8", newline="\n")


def build_paint_themes():
    src = PAINT / "history" / "trails.html"
    dst = PAINT / "themes" / "index.html"
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = src.read_text(encoding="utf-8")
    source = source.replace('href="trail-', 'href="../history/trail-')
    source = source.replace('href="movement-', 'href="../history/movement-')
    source = source.replace('href="timeline.html"', 'href="../history/timeline.html"')
    source = source.replace('href="calendar.html"', 'href="../history/calendar.html"')
    source = source.replace('href="movements.html"', 'href="../history/movements.html"')
    source = source.replace('href="periods.html"', 'href="../history/periods.html"')
    source = source.replace('href="trails.html"', 'href="../history/trails.html"')
    source = source.replace("https://paint.chenhua.net/history/trails.html", "https://paint.chenhua.net/themes/")
    source = source.replace("<title>小径索引 · 尘画</title>", "<title>绘画主题 · 尘画</title>")
    source = source.replace('data-title-zh="小径索引"', 'data-title-zh="绘画主题 · 尘画"')
    source = source.replace('data-title-en="Trails"', 'data-title-en="Painting Themes · Frame &amp; Grain"')
    source = source.replace("<title>Trails · Frame &amp; Grain</title>", "<title>Painting Themes · Frame &amp; Grain</title>")
    insert = """<section class="ph-section" id="movements"><h2>%s</h2><div class="movement-links" style="display:flex;flex-wrap:wrap;gap:8px">%s</div></section>""" % (
        tspan("十五个流派，作为索引", "Fifteen movements, as an index"), movement_links())
    if "</main>" in source:
        source = source.replace("</main>", insert + "</main>", 1)
    else:
        source = source.replace("</body>", insert + "</body>", 1)
    dst.write_text(source, encoding="utf-8", newline="\n")


def patch_today_heroes():
    for base in (MAIN / "today", PHOTO / "today"):
        if not base.exists():
            continue
        for page in sorted(base.glob("*.html")):
            if page.name == "index.html":
                continue
            source = page.read_text(encoding="utf-8")
            new = add_hero_cover(source)
            if new != source:
                page.write_text(new, encoding="utf-8", newline="\n")


def add_photo_lead(source, kind):
    if 'class="photo-lead"' in source:
        return source
    if kind == "themes":
        kicker = "PHOTOGRAPHY / NINE THEMES"
        heading = tspan("摄影：九个主题", "Photography: nine themes")
        intro = tspan("三百七十九篇故事，九个系列，覆盖三百六十六天。每一张照片都从一个具体日子出发，再回到它的年代。",
                      "Three hundred and seventy-nine stories, nine series, across three hundred and sixty-six days. Each photograph starts from a particular day and returns to its own time.")
    else:
        kicker = "PHOTOGRAPHY / FULL TIMELINE"
        heading = tspan("摄影：完整年代", "Photography: the full span")
        intro = tspan("从 1800 年代到当代，按年代看摄影如何记录世界。",
                      "From the 1800s to the present, a decade-by-decade view of how photography recorded the world.")
    lead = """<section class="photo-lead">
<p class="photo-kicker">%s</p>
<h2>%s</h2>
<p class="photo-intro">%s</p>
</section>
""" % (esc(kicker), heading, intro)
    if '<main class="shell">' in source:
        source = source.replace('<main class="shell">', '<main class="shell">\n' + lead, 1)
    if '</head>' in source:
        source = source.replace('</head>', """<style>
.photo-lead{max-width:1184px;margin:0 auto;padding:44px 0 10px}
.photo-kicker{font-family:var(--sans,ui-sans-serif,sans-serif);font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:#b08a52;margin:0 0 12px}
.photo-lead h2{font-family:var(--serif,"Noto Serif SC",serif);font-size:clamp(32px,4vw,56px);font-weight:400;line-height:1.15;letter-spacing:-.02em;margin:0 0 14px;color:var(--ink,#e9e1d5)}
.photo-intro{max-width:760px;font-size:15px;line-height:1.8;color:var(--muted,#a79d8f);margin:0}
@media(max-width:900px){.photo-lead{padding:30px 23.5px 8px}.photo-lead h2{font-size:34px}}
</style></head>""", 1)
    return source
    src = CORE / "static" / "today.css"
    dst = DIST / "assets" / "today.css"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def relabel_calendar_pages():
    old_plain = '<a href="../today/"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></a>'
    old_current = '<a href="../today/" aria-current="page"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></a>'
    new_plain = '<a href="../today/"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
    new_current = '<a href="../today/" aria-current="page"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
    for base, sub in ((MAIN, "themes"), (MAIN, "timeline"), (MAIN, "today"),
                      (PHOTO, "themes"), (PHOTO, "timeline"), (PHOTO, "today")):
        folder = base / sub
        if not folder.exists():
            continue
        for page in sorted(folder.glob("*.html")):
            source = page.read_text(encoding="utf-8")
            new = source.replace(old_plain, new_plain).replace(old_current, new_current)
            if new != source:
                page.write_text(new, encoding="utf-8", newline="\n")


def main():
    copy_photo_sections()
    copy_photo_today()
    insert_combined_themes()
    insert_combined_timeline()
    build_paint_themes()
    patch_today_heroes()
    relabel_calendar_pages()
    copy_today_css()
    print("sections: photo themes/timeline/today copied; main combined themes/timeline; paint/themes")


if __name__ == "__main__":
    main()
