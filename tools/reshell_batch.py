# -*- coding: utf-8 -*-
"""Batch re-shell legacy main/paint/photo pages into the v3.2 release,
generate a new search page, and rebuild sitemaps.

New v3.2 pages already in the release win; legacy pages fill the sections the
new build does not generate (themes, today, timeline, story, records, gallery).
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402
import build_v32 as B  # noqa: E402
import reshell_legacy as R  # noqa: E402

ROOT = K.ROOT
RELEASE = ROOT / "workspace" / "release"
SECTIONS = {
    "main": ("themes", "timeline", "today", "story", "editorial", "stories", "gallery"),
    "paint": ("themes", "records", "stories", "gallery", "history"),
    "photo": ("themes", "today", "timeline", "records", "stories", "gallery", "history"),
}
ASSET_PREFIXES = ("/assets/", "/data/")


def copy_asset(url, repo, site):
    path = url.split("?")[0]
    if not path.startswith(ASSET_PREFIXES):
        return
    src = repo / path.lstrip("/")
    if not src.exists():
        return
    dst = RELEASE / site / path.lstrip("/")
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def collect_assets(html):
    urls = R.CSS_RE.findall(html) + R.JS_RE.findall(html)
    return [u for u in urls if u.split("?")[0].startswith(ASSET_PREFIXES)]


def reshell_site(site):
    repo = ROOT / "repos" / site
    out = RELEASE / site
    stats = {"written": 0, "skipped": 0, "nochrome": 0}
    seen = set()
    for section in SECTIONS[site]:
        base = repo / section
        if not base.exists():
            continue
        for src in sorted(base.rglob("*.html")):
            rel = src.relative_to(repo).as_posix()
            if rel.endswith("404.html"):
                continue
            for lang in ("zh", "en"):
                target = out / (("en/" if lang == "en" else "") + rel)
                if target.exists():
                    stats["skipped"] += 1
                    continue
                html = src.read_text(encoding="utf-8")
                page_path = "/" + rel
                if page_path.endswith("index.html"):
                    page_path = page_path[: -len("index.html")]
                rendered = R.reshell(html, site, lang, page_path, repo)
                if rendered is None:
                    stats["nochrome"] += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rendered, encoding="utf-8")
                stats["written"] += 1
                if rel not in seen:
                    for url in collect_assets(html):
                        copy_asset(url, repo, site)
                    seen.add(rel)
    return stats


def record_js_map(scope):
    data = {}
    for rid, (century, kind) in R.RECORD_MAP.items():
        if scope == "paint" and kind != "painting":
            continue
        if scope == "photo" and kind not in ("photo", "object", "links"):
            continue
        base = "https://%s.chenhua.net/%s/%s.html" % (century, kind, rid)
        data[rid] = [base, base.replace(".net/", ".net/en/", 1)]
    return data


def search_page(site):
    for lang in ("zh", "en"):
        title = "搜索" if lang == "zh" else "Search"
        desc = "搜索标题、作者、地点、主题与年代。" if lang == "zh" else "Search titles, creators, places, themes and years."
        mapping = json.dumps(record_js_map(site), ensure_ascii=False, separators=(",", ":"))
        inline = """<main class="s-main">
<h1 class="s-title">%s</h1>
<form class="s-search" onsubmit="return false"><input id="q" type="search" autocomplete="off" placeholder="%s"><button type="button" id="go">%s</button></form>
<p class="s-lede" id="hint"></p><div class="s-grid" id="results"></div>
</main>
<script>
document.addEventListener("DOMContentLoaded",function(){var q=document.getElementById("q"),r=document.getElementById("results"),h=document.getElementById("hint");
var en=document.documentElement.getAttribute("data-lang")==="en";var idx=(window.CHENHUA_SEARCH_INDEX||{}).records||{};
function run(){var v=q.value.trim().toLowerCase();r.innerHTML="";if(!v){h.textContent="";return}var n=0;
for(var id in idx){var row=idx[id]||[];var text=(row[0]||"")+" "+(row[1]||"")+" "+id;if(text.toLowerCase().indexOf(v)<0)continue;
var url=window.CHENHUA_RECORD_URL[id];if(!url)continue;var label=(en?row[1]:row[0])||id;label=String(label).slice(0,80);
var a=document.createElement("a");a.className="s-card";a.href=url[en?1:0];
a.innerHTML='<div class="c"><b>'+label.replace(/[<>&]/g,"")+'</b><span>'+id+'</span></div>';r.appendChild(a);n++;if(n>=60)break}
h.textContent=n?(en?n+" results":n+" 条结果"):(en?"No results":"没有结果")}
q.addEventListener("input",run);document.getElementById("go").addEventListener("click",run);run()});
</script>""" % (title, "搜索标题、作者、地点" if lang == "zh" else "Search titles, creators, places",
                "搜索" if lang == "zh" else "Search")
        map_file = RELEASE / site / "data" / "record-map.js"
        map_file.parent.mkdir(parents=True, exist_ok=True)
        map_file.write_text("window.CHENHUA_RECORD_URL=%s;" % mapping, encoding="utf-8")
        extra = ('<script src="/data/record-map.js" defer></script>'
                 '<script src="/data/search-index.js" defer></script>')
        page = K.page(site, lang, "/search/", title, desc, inline, extra)
        target = RELEASE / site / (("en/" if lang == "en" else "") + "search/index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")


def patch_app_js(site):
    p = RELEASE / site / "assets" / "app.js"
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    old = '''  function staticHref(r) {
    if (r.collection === "paintings") {
      if (CFG.staticPaintBase) return CFG.staticPaintBase + r.id + ".html";
      return siteUrl(CFG.site === "paint" ? "painting/" + r.id + ".html" : "../paint/painting/" + r.id + ".html");
    }
    if (CFG.staticPhotoBase) return CFG.staticPhotoBase + r.id + ".html";
    return siteUrl(CFG.site === "photo" ? "photo/" + r.id + ".html" : "../photo/photo/" + r.id + ".html");
  }'''
    new = '''  function staticHref(r) {
    var y = Number(r.year) || 0;
    var c = y && y < 1800 ? "pre19century" : y && y < 1900 ? "19century" : y && y < 2000 ? "20century" : "21century";
    var kind = r.collection === "paintings" ? "painting" : r.collection === "objects" ? "object" : r.collection === "links" ? "links" : "photo";
    return "https://" + c + ".chenhua.net/" + kind + "/" + r.id + ".html";
  }'''
    if old in text:
        p.write_text(text.replace(old, new), encoding="utf-8")


def rebuild_sitemap(site):
    base = RELEASE / site
    paths = []
    for p in base.rglob("*.html"):
        rel = p.relative_to(base).as_posix()
        if rel == "404.html" or rel.startswith("en/"):
            continue
        path = "/" + rel
        if path.endswith("index.html"):
            path = path[: -len("index.html")]
        paths.append(path)
    (base / "sitemap.xml").write_text(B.sitemap(site, sorted(set(paths))), encoding="utf-8")


def main():
    R.build_record_map()
    for site in ("main", "paint", "photo"):
        stats = reshell_site(site)
        search_page(site)
        src_index = ROOT / "repos" / "main" / "data" / "search-index.js"
        dst_index = RELEASE / site / "data" / "search-index.js"
        dst_index.parent.mkdir(parents=True, exist_ok=True)
        if src_index.exists():
            shutil.copy2(src_index, dst_index)
        patch_app_js(site)
        rebuild_sitemap(site)
        print(site, stats)


if __name__ == "__main__":
    main()
