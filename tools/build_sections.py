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
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
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
STORY_TRAILS = json.loads((NEXT / "content" / "story-trails.json").read_text(encoding="utf-8"))["trails"]

TRAILS = ph_trails.TRAILS
MOVEMENTS = ph_movements.MOVEMENTS
MOVEMENTS_B = ph_movements.MOVEMENTS_B
PERIODS = ph_periods.PERIODS
MOVEMENT_BY_SLUG = {m["slug"]: m for m in MOVEMENTS}
PERIOD_BY_SLUG = {p["slug"]: p for p in PERIODS}

PHOTO_COUNT = len(ATLAS.get("stories") or [])
PAINT_COUNT = len(PAINT_WORKS)

# Works with explicit nudity are kept in the archive, but never used as a
# theme / timeline cover. "尽量" is handled as a curation rule, not a content
# removal: detail pages and records remain untouched.
UNSAFE_COVER_IDS = {
    "giotto-lamentation-1305",
    "weyden-descent-from-cross-1435",
    "rubens-descent-from-cross-1614",
    "masaccio-expulsion-1427",
    "botticelli-primavera-1480",
    "botticelli-birth-of-venus-1485",
    "bosch-garden-earthly-delights-1500",
    "michelangelo-creation-of-adam-1511",
    "ingres-grande-odalisque-1814",
    "goya-saturn-1820",
    "delacroix-liberty-1830",
    "courbet-painters-studio-1855",
    "manet-olympia-1863",
    "manet-dejeuner-sur-herbe-1863",
    "gauguin-where-do-we-come-from-1898",
    "schiele-self-portrait-1912",
    "moreau-jupiter-semele-1895",
}
SAFE_COVER_BY_MOVEMENT = {
    "早期文艺复兴": "duccio-maesta-1308",
    "盛期文艺复兴": "leonardo-mona-lisa-1503",
    "北方文艺复兴": "van-eyck-arnolfini-1434",
    "矫饰主义": "parmigianino-madonna-long-neck-1535",
    "巴洛克": "rembrandt-night-watch-1642",
    "洛可可": "watteau-pilgrimage-cythera-1717",
    "新古典主义": "david-oath-of-horatii-1784",
    "浪漫主义": "friedrich-wanderer-1818",
    "现实主义": "millet-the-gleaners-1857",
    "印象主义": "monet-impression-sunrise-1872",
    "后印象主义": "van-gogh-starry-night-1889",
    "象征主义": "boecklin-isle-of-the-dead-1883",
    "元代文人山水": "huang-gongwang-fuchun-1350",
    "浮世绘": "hokusai-great-wave-1831",
    "表现主义": "kirchner-street-berlin-1913",
}
SAFE_COVER_FALLBACK_ID = "klimt-the-kiss-1908"
PHOTO_THEME_COVERS = {
    "太空探索": "apollo-11-1969",
    "灾难与调查": "titanic-1912",
    "工程与城市": "brooklyn-bridge-1883",
    "铁路与工业": "auto-ad949d8d",
    "艺术与图像": "china-1850-1930",
}



def paint_img(work_id):
    r = PAINT_BY_ID.get(work_id) or {}
    return r.get("image") or r.get("preview_image") or ""


def paint_meta(work_id):
    r = PAINT_BY_ID.get(work_id) or {}
    return " · ".join(str(x) for x in (r.get("creator"), r.get("date_label") or r.get("year"), r.get("holding")) if x)


def _cover_base(value):
    return (value or "").split("?")[0].rstrip()


UNSAFE_COVER_URLS = set()
for _work in PAINT_WORKS:
    if _work.get("id") in UNSAFE_COVER_IDS:
        for _key in ("image", "preview_image"):
            _u = _cover_base(_work.get(_key))
            if _u:
                UNSAFE_COVER_URLS.add(_u)


def safe_cover_pool(values, fallback_id=None):
    pool = [_cover_base(v) for v in unique_images(values)
            if v and _cover_base(v) not in UNSAFE_COVER_URLS]
    if pool:
        return pool
    return [paint_img(fallback_id or SAFE_COVER_FALLBACK_ID)]



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


def unique_images(values):
    out = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def movement_year_range(m):
    years = [int(x) for x in re.findall(r"\d{3,4}", m.get("years_zh") or "")]
    if not years:
        return 0, 0
    return min(years), max(years)


def movements_for_era(start, end):
    out = []
    for m in MOVEMENTS:
        a, b = movement_year_range(m)
        if not a and not b:
            continue
        mid = (a + b) / 2.0
        if start <= mid < end:
            out.append(m)
    return out


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
    source = source.replace("../story/", "https://chenhua.net/story/")
    source = source.replace("../../photo/", "../")
    source = source.replace("../photo/", "../")
    source = source.replace("../../paint/", "https://paint.chenhua.net/")
    source = source.replace("https://chenhua.net/themes/", "https://photo.chenhua.net/themes/")
    source = source.replace("https://chenhua.net/timeline/", "https://photo.chenhua.net/timeline/")
    source = source.replace("https://chenhua.net/today/", "https://photo.chenhua.net/today/")
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
    source = source.replace("../story/", "https://chenhua.net/story/")
    source = source.replace("https://chenhua.net/today/", "https://photo.chenhua.net/today/")
    source = source.replace("https://chenhua.net/search/", "https://photo.chenhua.net/search/")
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
<img src="%s" alt="%s" loading="eager">
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
<img src="%s" alt="%s" loading="eager">
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
<img src="%s" alt="%s" loading="eager"><div class="cc"><h3>%s</h3><span>%s</span></div></a>""" % (
        esc(p["slug"]), esc(period_cover(p)), esc(p.get("title_zh")),
        tspan(p.get("title_zh"), p.get("title_en")), tspan(p.get("sub_zh"), p.get("sub_en")))


def photo_card(s):
    theme_en = SERIES_EN.get(s.get("theme"), s.get("theme") or "")
    return """<a class="ct-photo-card" href="/story/%s.html">
<img src="%s" alt="%s" loading="eager"><div class="cc"><h3>%s</h3><span>%s</span></div></a>""" % (
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
            esc(label),
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
    source = source.replace("8 条横向小径。", "绘画的横向小径。")
    source = source.replace("Eight lateral trails.", "Lateral trails through painting.")
    source = source.replace('<meta property="og:title" content="小径索引 · 尘画">', '<meta property="og:title" content="绘画主题 · 尘画">')
    source = source.replace('"name": "Trails"', '"name": "Painting Themes"')
    source = re.sub(r'<section class="ph-hero".*?</section>\s*', '', source, count=1, flags=re.S)
    source = re.sub(r'<span class="ph-pill">.*?</span></span>', '', source, flags=re.S)
    source = re.sub(r'<section class="ph-section"><div class="ph-trail-grid">.*?</div></section>\s*', '', source, count=1, flags=re.S)
    trail_cards = "".join(trail_library_card(t) for t in TRAILS)
    trail_section = """<section class="lib-section" id="trails"><div class="lib-head"><h2>%s</h2></div><div class="lib-grid theme-mosaic">%s</div></section>""" % (
        tspan("绘画 · 小径", "Painting · Trails"), trail_cards)
    movement_cards = "".join(movement_library_card(m) for m in MOVEMENTS)
    randomize = ""
    insert = """%s%s<section class="lib-section" id="movements"><div class="lib-head"><h2>%s</h2></div><div class="lib-grid theme-mosaic">%s</div></section>%s""" % (
        LIBRARY_CSS, trail_section, tspan("绘画 · 流派", "Painting · Movements"), movement_cards, randomize)
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
    return source


def copy_today_css():
    src = CORE / "static" / "today.css"
    dst = DIST / "assets" / "today.css"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def relabel_calendar_pages():
    old_plain = '<a href="../today/"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></a>'
    old_current = '<a href="../today/" aria-current="page"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></a>'
    new_plain = '<a href="../today/calendar.html"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
    new_current = '<a href="../today/calendar.html" aria-current="page"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
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


LIBRARY_CSS = """
<style>
/* ---------- 主题库：摄影与绘画共用同一种卡片 ---------- */
.theme-library{max-width:min(100%,1760px);margin:0 auto;padding:28px clamp(18px,3vw,48px) 46px}
.lib-section{border-top:1px solid var(--rule);padding:23px 0 9px}
.lib-section:first-of-type{border-top:0;padding-top:4px}
.lib-head{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin:0 0 14px}
.lib-head h2{font-family:var(--serif);font-weight:400;font-size:clamp(23px,2.8vw,34px);line-height:1.15;letter-spacing:-.01em;margin:0}
.lib-head .lib-sub{font-size:9px;letter-spacing:.2em;color:var(--accent);text-transform:uppercase}
.lib-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule)}
.lib-card{display:flex;flex-direction:column;min-width:0;background:var(--paper);color:var(--ink);text-decoration:none;overflow:hidden}
.lib-card:hover{background:var(--panel)}
.lib-thumb{overflow:hidden;background:var(--panel)}
.lib-thumb img{width:100%;height:150px;object-fit:cover;display:block;transition:transform .45s ease}
.lib-card:hover .lib-thumb img{transform:scale(1.025)}
.lib-body{padding:14px 15px 16px;display:flex;flex-direction:column;min-height:142px}
.lib-meta{font-size:9px;letter-spacing:.14em;color:var(--accent);text-transform:uppercase;margin-bottom:8px}
.lib-card h3{font-family:var(--serif);font-weight:400;font-size:22px;line-height:1.2;margin:0 0 7px}
.lib-card h3 span{display:block}
.lib-card h3 span[data-l="en"]{font-size:10px;letter-spacing:.12em;color:var(--muted);margin-top:4px;font-family:var(--sans,ui-sans-serif,sans-serif);text-transform:none}
.lib-card p{font-size:11px;line-height:1.75;color:var(--muted);margin:0}
.duo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(20px,2.6vw,42px);align-items:start}
.duo-col{min-width:0}
.lib-list{display:grid;grid-template-columns:1fr;gap:1px;background:var(--rule);border:1px solid var(--rule)}
.lib-list .lib-thumb img{height:clamp(180px,16vw,260px)}
.lib-list .lib-body{min-height:0;padding:13px 15px 15px}
.lib-list .lib-card h3{font-size:clamp(22px,2vw,28px)}
.lib-list .lib-card p{font-size:12px;line-height:1.8}
.theme-mosaic .lib-thumb img{height:clamp(170px,14vw,230px)}
.theme-mosaic .lib-body{min-height:150px}
.index-photo{grid-template-columns:repeat(5,minmax(0,1fr))}
.story-trails{margin:24px 0 34px;border-top:1px solid var(--ink);padding-top:18px}
.theme-library .lib-head{align-items:flex-end;flex-wrap:wrap}
.theme-library .lib-head p{font-size:11px;line-height:1.8;color:var(--muted);margin:0;max-width:52em}
.story-trails .lib-head p{font-size:11px;line-height:1.8;color:var(--muted);margin:0;max-width:46em}
.trail-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule)}
.story-trail{background:var(--paper);padding:16px 15px 18px;min-width:0}
.story-trail .lib-meta{margin-bottom:7px}
.story-trail h3{font-family:var(--serif);font-weight:400;font-size:clamp(19px,1.7vw,24px);line-height:1.2;margin:0 0 6px}
.story-trail h3 span[data-l="en"]{display:block;font-size:9px;letter-spacing:.12em;color:var(--muted);font-family:var(--sans,ui-sans-serif,sans-serif);margin-top:4px}
.story-trail p{font-size:11px;line-height:1.75;color:var(--muted);margin:0 0 11px}
.trail-list{list-style:none;margin:0;padding:0;border-top:1px solid var(--rule)}
.trail-list li{display:flex;align-items:baseline;gap:8px;border-bottom:1px solid var(--rule);padding:7px 0}
.trail-list li:last-child{border-bottom:0}
.trail-list a{min-width:0;flex:1;font-size:11px;line-height:1.55;color:var(--ink);text-decoration:none}
.trail-list a:hover{color:var(--accent)}
.trail-list span{font-size:9px;color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
@media(max-width:1050px){.trail-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){.trail-grid{grid-template-columns:1fr}.story-trails{margin-top:24px}}
.movement-index{margin-top:26px;border-top:1px solid var(--rule);padding-top:15px}
.mi-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:0 0 11px}
.mi-head h3{font-family:var(--serif);font-weight:400;font-size:19px;margin:0}
.mi-head span{font-size:9px;letter-spacing:.14em;color:var(--accent);text-transform:uppercase}
.movement-index .movement-links{display:flex;flex-wrap:wrap;gap:7px}
.movement-index .movement-links a{display:inline-flex;align-items:baseline;gap:6px;border:1px solid var(--line);padding:6px 9px;text-decoration:none;color:var(--muted);font-size:10px;line-height:1.2}
.movement-index .movement-links a:hover{border-color:var(--accent);color:var(--text)}
.movement-index .movement-links a b{font-weight:400;color:var(--text);font-family:var(--serif);font-size:13px}
@media(max-width:1050px){.lib-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.duo-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px}}
@media(max-width:760px){.lib-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.lib-thumb img{height:128px}.theme-library{padding:22px 20px 34px}.duo-grid{grid-template-columns:1fr}.lib-list .lib-thumb img{height:160px}}
@media(max-width:460px){.lib-grid{grid-template-columns:1fr}}

/* ---------- 双轨年代轴：左绘画，右摄影 ---------- */
.dual-timeline{max-width:none;width:min(100%,1760px);margin:0 auto;padding:18px clamp(18px,3vw,48px) 54px}
.axis-tools{display:flex;justify-content:flex-end;padding:0 0 2px}
.axis-shuffle{border:0;border-bottom:1px solid var(--line);background:none;color:var(--muted);font:10px/1.4 var(--sans,ui-sans-serif,sans-serif);letter-spacing:.08em;text-transform:uppercase;padding:5px 0;cursor:pointer}
.axis-shuffle:hover{color:var(--accent);border-color:var(--accent)}
.axis-head{display:grid;grid-template-columns:minmax(0,1fr) clamp(96px,8vw,138px) minmax(0,1fr);gap:clamp(16px,2.4vw,36px);border:0;padding:10px 0 4px}
.axis-head span{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}
.axis-head span:nth-child(1){text-align:right;color:#b28b5d}
.axis-head span:nth-child(2){text-align:center}
.axis-head span:nth-child(3){color:var(--accent)}
.dual-axis{position:relative}
.dual-axis:before{content:"";position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--rule-strong);transform:translateX(-.5px)}
.axis-row{display:grid;grid-template-columns:minmax(0,1fr) clamp(96px,8vw,138px) minmax(0,1fr);gap:clamp(16px,2.4vw,36px);border:0;padding:24px 0}
.axis-side{min-width:0;display:flex;flex-direction:column;gap:14px}
.axis-side.paint{padding-right:clamp(4px,1vw,16px)}
.axis-side.photo{padding-left:clamp(4px,1vw,16px)}
.axis-year{display:flex;flex-direction:column;align-items:center;justify-content:flex-start;text-align:center;padding-top:20px;position:relative;z-index:1}
.axis-year:before{content:"";position:absolute;top:7px;left:50%;width:9px;height:9px;border-radius:50%;background:var(--accent);transform:translateX(-50%);box-shadow:0 0 0 5px var(--paper);z-index:2}
.axis-year b{font-family:var(--serif);font-weight:400;font-size:clamp(16px,1.4vw,20px);line-height:1.2;white-space:nowrap;background:var(--paper);padding:3px 8px}
.axis-card{display:grid;grid-template-columns:minmax(0,44%) minmax(0,1fr);gap:16px;align-items:center;text-decoration:none;color:var(--ink);min-width:0;padding:6px 0;border:0}
.axis-card img{width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;display:block;filter:saturate(.92)}
.axis-card .ac{min-width:0;display:flex;flex-direction:column;justify-content:center}
.axis-card h3{font-family:var(--serif);font-weight:400;font-size:clamp(16px,1.35vw,20px);line-height:1.35;margin:0 0 5px}
.axis-card h3 span[data-l="en"]{font-size:10.5px;letter-spacing:.06em;color:var(--muted);font-family:var(--sans,ui-sans-serif,sans-serif);margin-top:3px}
.axis-card .ac span{font-size:11px;color:var(--muted);line-height:1.5}
.axis-side.paint .axis-card{grid-template-columns:minmax(0,1fr) minmax(0,44%);text-align:right}
.axis-side.paint .axis-card img{grid-column:2;grid-row:1}
.axis-side.paint .axis-card .ac{grid-column:1;grid-row:1;align-items:flex-end}
.axis-empty{min-height:1px}
@media(max-width:860px){
  .axis-head{grid-template-columns:1fr 86px 1fr;gap:12px}
  .axis-row{grid-template-columns:1fr 86px 1fr;gap:12px}
  .axis-card{grid-template-columns:minmax(0,40%) minmax(0,1fr);gap:12px}
  .axis-side.paint .axis-card{grid-template-columns:minmax(0,1fr) minmax(0,40%)}
  .axis-card h3{font-size:15px}
}
@media(max-width:620px){
  .dual-timeline{padding:20px 18px 34px}
  .axis-head{display:none}
  .dual-axis:before{display:block;left:8px}
  .axis-row{grid-template-columns:1fr;gap:0;padding:0 0 20px 28px;position:relative}
  .axis-row:before{content:"";position:absolute;left:-1px;top:18px;width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 5px var(--paper)}
  .axis-year{align-items:flex-start;text-align:left;padding:8px 0 10px;border:0;margin-bottom:0}
  .axis-year:before{display:none}
  .axis-year b{background:none;padding:0}
  .axis-side{padding:0}
  .axis-side.paint .axis-card{grid-template-columns:minmax(0,40%) minmax(0,1fr);text-align:left}
  .axis-side.paint .axis-card img{grid-column:1;grid-row:1}
  .axis-side.paint .axis-card .ac{grid-column:2;grid-row:1;align-items:flex-start}
}
</style>
"""


def photo_theme_card(s):
    stories = [x for x in PHOTO_STORIES if x.get("theme") == s["name"]]
    covers = safe_cover_pool([x.get("img") for x in stories])
    chosen = PHOTO_STORY_BY_ID.get(PHOTO_THEME_COVERS.get(s["name"], "")) or RECORDS.get(PHOTO_THEME_COVERS.get(s["name"], ""))
    cover = (chosen or {}).get("img") or (chosen or {}).get("image") or (chosen or {}).get("preview_image") or (covers[0] if covers else "")
    if cover:
        covers = [cover]
    search = "https://photo.chenhua.net/search/?q=%s&scope=photos" % quote(s["name"])
    return """<a class="lib-card" href="%s">
<div class="lib-thumb"><img src="%s" data-covers="%s" alt="%s" loading="lazy"></div>
<div class="lib-body"><div class="lib-meta">PHOTOGRAPHY</div>
<h3>%s</h3><p>%s</p></div></a>""" % (
        esc(search), esc(cover), esc("|".join(covers)), esc(s["name"]),
        tspan(s["name"], s["name_en"]), tspan(s.get("desc"), s.get("desc_en")))


def trail_library_card(t):
    covers = safe_cover_pool(
        [paint_img((x or {}).get("work")) for x in (t.get("stops") or [])] + [trail_cover(t)]
    )
    return """<a class="lib-card" href="https://paint.chenhua.net/history/trail-%s.html">
<div class="lib-thumb"><img src="%s" data-covers="%s" alt="%s" loading="lazy"></div>
<div class="lib-body"><div class="lib-meta">PAINTING TRAIL</div>
<h3>%s</h3><p>%s</p></div></a>""" % (
        esc(t["slug"]), esc(covers[0] if covers else ""), esc("|".join(covers)), esc(t["zh"]),
        tspan(t["zh"], t["en"]), tspan(t.get("intro_zh"), t.get("intro_en")))


def movement_library_card(m):
    covers = safe_cover_pool(
        [paint_img(x) for x in (m.get("works") or [])] + [paint_img(m.get("hero"))],
        SAFE_COVER_BY_MOVEMENT.get(m.get("zh")),
    )
    return """<a class="lib-card" href="%s">
<div class="lib-thumb"><img src="%s" data-covers="%s" alt="%s" loading="lazy"></div>
<div class="lib-body"><div class="lib-meta">PAINTING MOVEMENT</div>
<h3>%s</h3><p>%s</p></div></a>""" % (
        esc(movement_link(m["slug"])), esc(covers[0] if covers else ""), esc("|".join(covers)), esc(m["zh"]),
        tspan(m["zh"], m["en"]), tspan(m.get("summary_zh"), m.get("summary_en")))


def story_trail_card(t):
    items = []
    for sid in t.get("stories") or []:
        s = PHOTO_STORY_BY_ID.get(sid)
        if not s:
            continue
        year = s.get("year") or "长文"
        items.append(
            '<li><a href="https://chenhua.net/story/%s.html">%s</a><span>%s</span></li>' % (
                esc(sid), esc(s.get("title") or sid), esc(year)))
    return """<article class="story-trail">
<div class="lib-meta">%s · %d 篇</div>
<h3>%s</h3>
<p>%s</p>
<ol class="trail-list">%s</ol>
</article>""" % (
        esc(t.get("title_en") or t.get("title")), len(items),
        tspan(t.get("title"), t.get("title_en")), tspan(t.get("intro"), t.get("intro_en") or t.get("intro")),
        "".join(items))


def story_trails_block():
    for t in STORY_TRAILS:
        ids = t.get("stories") or []
        missing = [sid for sid in ids if sid not in PHOTO_STORY_BY_ID]
        if missing:
            raise SystemExit("story trail %s missing stories: %s" % (t.get("key"), missing))
        if not 5 <= len(ids) <= 7:
            raise SystemExit("story trail %s must have 5-7 stories, got %d" % (t.get("key"), len(ids)))
    cards = "".join(story_trail_card(t) for t in STORY_TRAILS)
    return """<section class="story-trails" aria-label="主题串读">
<div class="lib-head"><h2>%s</h2><p>%s</p></div>
<div class="trail-grid">%s</div>
</section>""" % (
        tspan("编辑串读", "Editor's Trails"),
        tspan("每个主题先给一条 5—7 篇的入门线；读完这条线，再向下进入完整主题与全部故事。",
              "Each theme starts with a five-to-seven story trail; follow it first, then continue below to the full theme and archive."),
        cards)


def theme_index_section(zh, en, note_zh, note_en, cards, grid_class=""):
    return """<section class="lib-section"><div class="lib-head"><h2>%s</h2><p>%s</p></div><div class="lib-grid theme-mosaic %s">%s</div></section>""" % (
        tspan(zh, en), tspan(note_zh, note_en), grid_class, cards)


def theme_library_body():
    photo_cards = "".join(photo_theme_card(s) for s in SERIES)
    trail_cards = "".join(trail_library_card(t) for t in TRAILS)
    movement_cards = "".join(movement_library_card(m) for m in MOVEMENTS)
    return """%s
<main class="theme-library">
<div class="lib-head"><h2>%s</h2><p>%s</p></div>
%s
%s
%s
%s
</main>""" % (
        LIBRARY_CSS,
        tspan("主题", "Themes"),
        tspan("先读五条编辑串读；再按摄影主题、绘画小径与绘画流派进入完整档案。",
              "Start with five editor's trails; then enter the full archive by photography theme, painting trail and movement."),
        story_trails_block(),
        theme_index_section(
            "摄影主题", "Photography Themes",
            "%d 个主题：太空探索、灾难与调查、工程与城市、铁路与工业、艺术与图像；点击进入摄影站主题搜索。" % len(SERIES),
            "%d themes: space, disaster, engineering, rail and art; each card opens the photography search." % len(SERIES),
            photo_cards, "index-photo"),
        theme_index_section(
            "绘画小径", "Painting Trails",
            "%d 条小径：从光、城市、身体到战争、日常与无名者。" % len(TRAILS),
            "%d trails: from light, city and body to war, daily life and the unnamed." % len(TRAILS),
            trail_cards),
        theme_index_section(
            "绘画流派", "Painting Movements",
            "%d 个 A 类流派，按风格与年代进入流派页。" % len(MOVEMENTS),
            "%d movements; enter each movement page by style and period." % len(MOVEMENTS),
            movement_cards),
    )


def axis_photo_card(s, era_start):
    theme_zh = s.get("theme") or ""
    theme_en = SERIES_EN.get(theme_zh, theme_zh)
    meta_zh = "%s · %s" % (s.get("year") or "", theme_zh)
    meta_en = "%s · %s" % (s.get("year") or "", theme_en)
    return """<a class="axis-card" data-axis-group="photo-%s" href="/story/%s.html">
<img src="%s" alt="%s" loading="lazy"><div class="ac"><h3>%s</h3><span>%s</span></div></a>""" % (
        esc(era_start), esc(s["id"]), esc(s["img"]), esc(s.get("title")), tspan(s.get("title"), s.get("title_en")),
        tspan(meta_zh, meta_en))


def axis_movement_card(m, era_start):
    covers = safe_cover_pool(
        [paint_img(x) for x in (m.get("works") or [])] + [paint_img(m.get("hero"))],
        SAFE_COVER_BY_MOVEMENT.get(m.get("zh")),
    )
    return """<a class="axis-card" data-axis-group="paint-%s" href="%s">
<img src="%s" alt="%s" loading="lazy"><div class="ac"><h3>%s</h3><span>%s</span></div></a>""" % (
        esc(era_start), esc(movement_link(m["slug"])), esc(covers[0] if covers else ""),
        esc(m["zh"]), tspan(m["zh"], m["en"]), tspan(m.get("years_zh"), m.get("years_en")))


def dual_axis_body():
    rows = []
    for start, end, pslugs, label, note, note_en in ERAS:
        movs = movements_for_era(start, end)
        paint_cards = "".join(axis_movement_card(m, start) for m in movs)
        photo = [s for s in PHOTO_STORIES if start <= photo_year(s) < end]
        photo.sort(key=lambda s: (photo_year(s), s.get("date") or ""))
        photo_cards = "".join(axis_photo_card(s, start) for s in photo[:14])
        rows.append("""<div class="axis-row">
<div class="axis-side paint">%s</div>
<div class="axis-year"><b>%s</b></div>
<div class="axis-side photo">%s</div>
</div>""" % (
            paint_cards if paint_cards else '<div class="axis-empty"></div>',
            esc(label),
            photo_cards if photo_cards else '<div class="axis-empty"></div>',
        ))
    shuffle = """<script>(function(){
var cards=[].slice.call(document.querySelectorAll('.axis-card[data-axis-group]'));
if(!cards.length)return;
function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t;}return a;}
function render(){
  cards.forEach(function(c){c.style.display='none';});
  var groups={};
  cards.forEach(function(c){var g=c.getAttribute('data-axis-group');(groups[g]=groups[g]||[]).push(c);});
  var used={};
  Object.keys(groups).sort().forEach(function(g){
    var want=g.indexOf('paint-')===0?1:2;
    var pool=shuffle(groups[g].slice());
    var shown=0;
    for(var i=0;i<pool.length&&shown<want;i++){
      var c=pool[i], img=c.querySelector('img');
      var src=(img&&img.getAttribute('src')||'').split('?')[0];
      if(!src||used[src])continue;
      used[src]=1;c.style.display='';shown++;
    }
  });
}
render();
var btn=document.querySelector('.axis-shuffle');
if(btn)btn.addEventListener('click',render);
})();</script>"""
    return """%s
<main class="dual-timeline" aria-label="%s">
<div class="axis-tools"><button class="axis-shuffle" type="button">%s</button></div>
<div class="axis-head"><span>%s</span><span>%s</span><span>%s</span></div>
<div class="dual-axis">%s</div>
</main>%s""" % (
        LIBRARY_CSS,
        "Timeline",
        tspan("换一批", "Shuffle"),
        tspan("绘画 · 流派", "Painting · Movements"), tspan("年代", "Years"), tspan("摄影", "Photography"),
        "".join(rows), shuffle,
    )


def shell_page(source_path, body):
    source = source_path.read_text(encoding="utf-8")
    header_end = source.index("</header>") + len("</header>")
    footer_start = source.index('<footer class="site-foot">')
    footer_end = source.index("</footer>", footer_start) + len("</footer>")
    script = re.search(r'<script src="../../assets/site\.js[^"]*"></script>', source)
    script_tag = script.group(0) if script else '<script src="../../assets/site.js"></script>'
    return source[:header_end] + "\n" + body + "\n" + source[footer_start:footer_end] + "\n</div>\n" + script_tag + "\n</body>\n</html>\n"


PHOTO_AXIS_CSS = """
<style>
.photo-axis{max-width:1240px;margin:0 auto;padding:28px 28px 50px}
.photo-axis h1{font-family:var(--serif);font-weight:400;font-size:clamp(30px,4vw,46px);line-height:1.1;letter-spacing:-.02em;margin:0 0 20px}
.p-axis{position:relative;padding-left:30px}
.p-axis:before{content:"";position:absolute;left:8px;top:8px;bottom:8px;width:1px;background:var(--rule-strong)}
.p-era{position:relative;padding:17px 0 25px;border-bottom:1px solid var(--rule)}
.p-era:last-child{border-bottom:0}
.p-era:before{content:"";position:absolute;left:-26px;top:24px;width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--paper)}
.p-era-head{display:flex;align-items:baseline;gap:13px;margin:0 0 12px}
.p-era-head b{font-family:var(--serif);font-weight:400;font-size:22px;line-height:1.2}
.p-era-head span{font-size:9px;letter-spacing:.1em;color:var(--muted)}
.p-grid{display:flex;flex-wrap:wrap;gap:1px;background:transparent;border:0}
.p-grid .lib-card{flex:1 1 270px;min-width:0;border:1px solid var(--rule)}
@media(max-width:620px){.photo-axis{padding:22px 20px 34px}.p-axis{padding-left:22px}.p-era:before{left:-18px}.p-era-head b{font-size:19px}}
</style>
"""


def photo_story_library_card(s):
    theme_zh = s.get("theme") or ""
    theme_en = SERIES_EN.get(theme_zh, theme_zh)
    sub_zh = "%s · %s" % (s.get("year") or "", theme_zh)
    sub_en = "%s · %s" % (s.get("year") or "", theme_en)
    return """<a class="lib-card" href="https://chenhua.net/story/%s.html">
<div class="lib-thumb"><img src="%s" alt="%s" loading="eager"></div>
<div class="lib-body"><div class="lib-meta">PHOTOGRAPHY · %s</div>
<h3>%s</h3><p>%s</p></div></a>""" % (
        esc(s["id"]), esc(s["img"]), esc(s.get("title")), esc(s.get("year") or ""),
        tspan(s.get("title"), s.get("title_en")), tspan(sub_zh, sub_en))


def photo_theme_library_body():
    cards = "".join(photo_theme_card(s) for s in SERIES)
    randomize = ""
    return """%s
<main class="theme-library">
<div class="lib-head"><h2>%s</h2></div>
<div class="lib-grid theme-mosaic">%s</div>
</main>%s""" % (
        LIBRARY_CSS, tspan("摄影主题", "Photography Themes"), cards, randomize)


def photo_axis_body():
    rows = []
    for start, end, pslugs, label, note, note_en in ERAS:
        photo = [s for s in PHOTO_STORIES if start <= photo_year(s) < end]
        photo.sort(key=lambda s: (photo_year(s), s.get("date") or ""))
        if not photo:
            continue
        cards = "".join(photo_story_library_card(s) for s in photo[:6])
        rows.append("""<section class="p-era"><div class="p-era-head"><b>%s</b></div>
<div class="p-grid">%s</div></section>""" % (
            esc(label), cards))
    return """%s%s
<main class="photo-axis" aria-label="Photography Timeline">
<div class="p-axis">%s</div>
</main>""" % (LIBRARY_CSS, PHOTO_AXIS_CSS, "".join(rows))


def photo_page(from_path, body, title_zh, title_en):
    page = shell_page(from_path, body)
    page = re.sub(r'data-title-zh="[^"]*"', 'data-title-zh="%s"' % esc(title_zh), page, count=1)
    page = re.sub(r'data-title-en="[^"]*"', 'data-title-en="%s"' % esc(title_en), page, count=1)
    page = re.sub(r"<title>.*?</title>", "<title>%s</title>" % esc(title_zh), page, count=1, flags=re.S)
    return page


def build_photo_pages():
    (PHOTO / "themes").mkdir(parents=True, exist_ok=True)
    (PHOTO / "timeline").mkdir(parents=True, exist_ok=True)
    (PHOTO / "themes" / "index.html").write_text(
        photo_page(MAIN / "themes" / "index.html", photo_theme_library_body(), "摄影主题 · 尘画", "Photography Themes · Frame & Grain"),
        encoding="utf-8", newline="\n")
    (PHOTO / "timeline" / "index.html").write_text(
        photo_page(MAIN / "timeline" / "index.html", photo_axis_body(), "摄影时间线 · 尘画", "Photography Timeline · Frame & Grain"),
        encoding="utf-8", newline="\n")
    print("photo pages: themes cards, timeline photo-only axis")


def build_theme_library():
    path = MAIN / "themes" / "index.html"
    path.write_text(shell_page(path, theme_library_body()), encoding="utf-8", newline="\n")
    print("themes library", path.stat().st_size, "photo", len(SERIES), "trails", len(TRAILS), "movements", len(MOVEMENTS))


def build_dual_timeline():
    path = MAIN / "timeline" / "index.html"
    path.write_text(shell_page(path, dual_axis_body()), encoding="utf-8", newline="\n")
    print("timeline axis", path.stat().st_size, "eras", len(ERAS))


def main():
    copy_photo_today()
    build_theme_library()
    build_dual_timeline()
    build_photo_pages()
    build_paint_themes()
    patch_today_heroes()
    relabel_calendar_pages()
    copy_today_css()
    import build_calendar_index as bci
    bci.main()
    print("sections: photo themes/timeline/today copied; main combined themes/timeline; paint/themes; illustrated calendars")


if __name__ == "__main__":
    main()
