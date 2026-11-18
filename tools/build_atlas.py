# -*- coding: utf-8 -*-
"""Generate the real-content Atlas page from the existing bundle."""
import json
import sys
import time
from pathlib import Path

TOOLS = Path(r"C:\Users\chenhua\Desktop\chenhua\next\tools")
sys.path.insert(0, str(TOOLS))
import build_atlas_data as data_builder

ROOT = Path(r"C:\Users\chenhua\Desktop\chenhua")
SOURCE = ROOT / "三轴融合原型" / "三轴融合原型.html"
MAIN = ROOT / "next" / "dist" / "main"
OUT_DIR = MAIN / "themes"
OUT = OUT_DIR / "index.html"
TIMELINE_DIR = MAIN / "timeline"


def read_source():
    return SOURCE.read_text(encoding="utf-8")


def build_data():
    raw = data_builder.build_data()
    themes = [
        {
            "name": s["name"],
            "en": s["name_en"],
            "color": s["color"],
            "desc": s["desc"],
        }
        for s in raw["series"]
    ]
    return {
        "themes": themes,
        "decades": raw["decades"],
        "stories": raw["stories"],
        "date_count": raw["date_count"],
        "total": len(raw["stories"]),
        "dated": sum(1 for s in raw["stories"] if s["date"]),
    }


def seo_head(html, title, description, canonical):
    block = (
        f"<title>{title}</title>\n"
        f'<meta name="description" content="{description}">\n'
        f'<meta name="robots" content="index,follow">\n'
        f'<link rel="canonical" href="{canonical}">\n'
        f'<link rel="alternate" hreflang="zh-CN" href="{canonical}">\n'
        f'<link rel="alternate" hreflang="en" href="{canonical}?lang=en">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:title" content="{title}">\n'
        f'<meta property="og:description" content="{description}">\n'
        f'<meta property="og:url" content="{canonical}">\n'
        f'<meta property="og:locale" content="zh_CN">\n'
        f'<meta property="og:locale:alternate" content="en_US">'
    )
    old = "<title>主题 · 尘画</title>"
    if old in html:
        return html.replace(old, block, 1)
    return html.replace("</head>", block + "\n</head>", 1)


def set_selected(html, view):
    for name in ("theme", "timeline", "calendar"):
        html = html.replace(
            f'data-view="{name}" aria-selected="true"',
            f'data-view="{name}" aria-selected="false"',
        )
    return html.replace(
        f'data-view="{view}" aria-selected="false"',
        f'data-view="{view}" aria-selected="true"',
        1,
    )


def main():
    html = read_source()
    data = build_data()
    total = data["total"]
    dated = data["dated"]
    decades = len(data["decades"])

    # Replace the hard-coded prototype data block with live data.
    start = html.index("const THEMES = [")
    end = html.index("const state = {", start)
    html = html[:start] + "const THEMES = ATLAS_DATA.themes;\nconst DECADES = ATLAS_DATA.decades;\nconst STORIES = ATLAS_DATA.stories;\n" + html[end:]

    # Stable initial focus: a known story with a valid cover and date.
    html = html.replace(
        'const state = {view:"theme", theme:"太空探索", decade:null, date:null, focus:"new-horizons"};',
        'const state = {view:"theme", theme:null, decade:null, date:null, focus:"today-01-01-new-horizons-2"};',
        1,
    )

    # Insert the generated dataset before the main script.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(
        "<script>\nconst THEMES = ATLAS_DATA.themes;",
        f"<script>\nconst ATLAS_DATA = {payload};\nconst THEMES = ATLAS_DATA.themes;",
        1,
    )

    # Canonical site paths: theme at /themes/, timeline at /timeline/, dates at /today/.
    html = html.replace("../next/dist/main/index.html", "/")
    html = html.replace("../next/dist/main/themes/index.html", "/themes/")
    html = html.replace("../next/dist/main/timeline/", "/timeline/")
    html = html.replace("../next/dist/main/today/index.html", "/today/")
    html = html.replace("../next/dist/main/", "/")
    html = html.replace("../next/dist/photo/", "https://photo.chenhua.net/")
    html = html.replace("../next/dist/paint/", "https://paint.chenhua.net/")
    html = html.replace("../next/dist/assets/", "/assets/")
    html = html.replace("../../assets/", "/assets/")
    html = html.replace("三轴档案 · 尘画", "图录总览 · 尘画")
    html = html.replace("Archive Atlas / 三轴档案", "Archive Atlas / 全站图录")
    html = html.replace("全站图录 · 13 篇抽样", f"全站图录 · {total} 篇")
    html = html.replace("Full Atlas · 13 sampled entries", f"Full Atlas · {total} entries")
    html = html.replace("本页载入 13 篇真实故事", f"全站 {total} 篇故事已接入；其中 {dated} 篇有日期。")
    html = html.replace("This page loads 13 real stories", f"All {total} stories are connected; {dated} carry a date.")
    html = html.replace("原型说明：", "全站说明：")
    html = html.replace("三轴", "图录")
    html = html.replace("全站总览", "全站图录")
    html = html.replace(
        "本页只载入 13 篇真实故事，用于验证三轴联动；完整 376 篇在站点日页。",
        f"全站 {total} 篇故事已接入；其中 {dated} 篇有日期。",
    )

    # JS strings that still assume the 13-story sample.
    html = html.replace(
        "未锁定筛选 · 全馆 13 篇抽样",
        f"未锁定筛选 · 全馆 {total} 篇",
    )
    html = html.replace(
        "完整站点里，这一天也许有故事；原型只抽了 13 篇。",
        "这一天暂无故事；全站日期索引仍可从日页查看。",
    )
    html = html.replace(
        "左边是主题目录，右边的横条是该主题在十个年代里的分布。点横条上的年代分布，也能直接切到时间线。",
        f"按主题浏览；年代分布横条显示该主题在 {decades} 个年代里的篇数。",
    )
    html = html.replace("无抽样故事", "无故事")

    # Undated long-form stories must not pretend to have a calendar coordinate.
    html = html.replace(
        '<button class="coord" data-axis="date" type="button"><span class="coord-k">日历</span><span class="coord-v">${s.date}</span><span class="coord-a">↗</span></button>',
        '${s.date?`<button class="coord" data-axis="date" type="button"><span class="coord-k">日历</span><span class="coord-v">${s.date}</span><span class="coord-a">↗</span></button>`:`<button class="coord is-disabled" type="button" disabled><span class="coord-k">日历</span><span class="coord-v">无日期</span></button>`}',
        1,
    )
    html = html.replace(
        '<button type="button" data-go="date"><span class="k">日历</span><span class="v">${s.date}</span><span class="go">↗</span></button>',
        '${s.date?`<button type="button" data-go="date"><span class="k">日历</span><span class="v">${s.date}</span><span class="go">↗</span></button>`:`<button type="button" disabled><span class="k">日历</span><span class="v">无日期</span></button>`}',
        1,
    )

    # Counts are data-driven, not hard-coded.

    # Matrix columns depend on the real decade list.
    html = html.replace(
        '$("#matrix").innerHTML = head + rows;',
        'const matrix = $("#matrix");\n  matrix.style.gridTemplateColumns = `126px repeat(${DECADES.length}, minmax(56px, 1fr))`;\n  matrix.style.minWidth = `${126 + DECADES.length * 56}px`;\n  matrix.innerHTML = head + rows;',
        1,
    )

    # Scroll the decade ruler to the focused story's decade first, otherwise
    # to the first decade that has a story in the active theme.
    html = html.replace(
        "const idx=state.decade?DECADES.indexOf(state.decade):Math.max(0,DECADES.findIndex(d=>STORIES.some(s=>s.decade===d && themeMatch(s))));",
        "const focus=storyOf(state.focus); const idx=state.decade?DECADES.indexOf(state.decade):(focus&&focus.decade?DECADES.indexOf(focus.decade):Math.max(0,DECADES.findIndex(d=>STORIES.some(s=>s.decade===d && themeMatch(s)))));",
        1,
    )
    html = html.replace(
        "sc.scrollLeft=Math.max(0,idx*190-8);",
        "const idxSafe=Number.isFinite(idx)?idx:0; const rg=$('.ruler-grid'); const sync=()=>{if(rg) rg.style.transform=`translateX(${-sc.scrollLeft}px)`;}; const jump=()=>{sc.scrollLeft=Math.max(0,idxSafe*190-8); sync();}; jump(); sc.onscroll=sync; setTimeout(jump,150); setTimeout(jump,650); requestAnimationFrame(()=>requestAnimationFrame(jump));",
        1,
    )

    # View state is selected by the static route, not by query parameters.

    # Keep the decade ruler aligned with the horizontally scrolling track.
    html = html.replace(
        "sc.scrollLeft=Math.max(0,idx*190-8);",
        "sc.scrollLeft=Math.max(0,idx*190-8);\n    const rg=$('.ruler-grid');\n    const sync=()=>{if(rg) rg.style.transform=`translateX(${-sc.scrollLeft}px)`;};\n    sc.onscroll=sync; sync(); setTimeout(()=>{sc.scrollLeft=Math.max(0,idx*190-8); sync();},150);",
        1,
    )

    # The prototype was drawn for 10 decades; the real archive has 21.
    html = html.replace(
        ".ruler-grid{display:grid;grid-template-columns:repeat(10,minmax(180px,1fr));min-width:1800px;position:relative;top:-1px}",
        ".ruler-grid{display:grid;grid-template-columns:repeat(21,minmax(180px,1fr));min-width:3780px;position:relative;top:-1px}",
        1,
    )
    html = html.replace(
        ".decade-track{display:grid;grid-template-columns:repeat(10,minmax(180px,1fr));min-width:1800px;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);background:var(--rule);gap:1px}",
        ".decade-track{display:grid;grid-template-columns:repeat(21,minmax(180px,1fr));min-width:3780px;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);background:var(--rule);gap:1px}",
        1,
    )

    # A six-column matrix on a narrow screen still scrolls horizontally.
    html = html.replace(
        ".spark{display:grid;grid-template-columns:repeat(10,1fr);gap:2px;align-items:end;height:22px}",
        ".spark{display:grid;grid-template-columns:repeat(21,1fr);gap:2px;align-items:end;height:22px}",
        1,
    )
    html = html.replace(
        ".matrix{grid-template-columns:104px repeat(10,minmax(52px,1fr))}",
        ".matrix{grid-template-columns:104px repeat(21,minmax(52px,1fr))}",
        1,
    )
    html = html.replace(
        ".matrix{display:grid;grid-template-columns:126px repeat(10,minmax(56px,1fr));min-width:860px;border-top:1px solid var(--rule);border-left:1px solid var(--rule)}",
        ".matrix{display:grid;grid-template-columns:126px repeat(21,minmax(56px,1fr));min-width:1300px;border-top:1px solid var(--rule);border-left:1px solid var(--rule)}",
        1,
    )

    # Make the large theme panel scroll instead of making the whole page enormous.
    html = html.replace(
        ".theme-panel{border:1px solid var(--rule);background:var(--panel);padding:18px}",
        ".theme-panel{border:1px solid var(--rule);background:var(--panel);padding:18px}\n.theme-panel .story-stack{max-height:560px;overflow:auto;padding-right:6px}\n.theme-row .count{white-space:nowrap}",
        1,
    )

    base_state = 'const state = {view:"theme", theme:null, decade:null, date:null, focus:"today-01-01-new-horizons-2"};'
    routes = [
        (
            OUT_DIR / "index.html",
            "theme",
            "主题 · 尘画",
            "按主题浏览尘画的历史摄影与绘画故事。",
            "https://www.chenhua.net/themes/",
        ),
        (
            TIMELINE_DIR / "index.html",
            "timeline",
            "时间线 · 尘画",
            "按年代浏览尘画的历史摄影与绘画故事。",
            "https://www.chenhua.net/timeline/",
        ),
    ]
    for path, view, title, description, canonical in routes:
        page = html
        if view == "timeline":
            page = page.replace(base_state, base_state.replace('view:"theme"', 'view:"timeline"'), 1)
        page = set_selected(page, view)
        page = seo_head(page, title, description, canonical)
        heading = "主题" if view == "theme" else "时间线"
        page = page.replace("<h1>图录</h1>", f"<h1>{heading}</h1>", 1)
        page = page.replace('aria-label="图录视图"', f'aria-label="{heading}视图"', 1)
        # Local preview lives under next/dist/main/<route>; dist/assets is two levels up.
        # split_repos.py rewrites this to ../assets for the published repo root.
        page = page.replace('href="/assets/', 'href="../../assets/').replace('src="/assets/', 'src="../../assets/')
        page = page.replace('href="/', 'href="../').replace('src="/', 'src="../')
        page = page.replace('src="../../assets/site.js"', 'src="../../assets/site.js?v=%s"' % int(time.time()))
        active_href = "../themes/" if view == "theme" else "../timeline/"
        page = page.replace('<a href="%s">' % active_href, '<a href="%s" aria-current="page">' % active_href, 1)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding="utf-8")
        print("wrote", path, "bytes", path.stat().st_size, "stories", total, "dates", data["date_count"])


if __name__ == "__main__":
    main()
