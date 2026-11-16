# -*- coding: utf-8 -*-
"""Phase 1 预览构建：Markdown 内容 + 世纪图片清单 → 三个站点 + 图片站瀑布页。"""
import json
import pathlib
import re
import shutil
import sys
import time
from collections import Counter

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
import usage  # noqa: E402  (next/tools/usage.py)

NEXT = ROOT / "next"
CONTENT = NEXT / "content"
CORE = NEXT / "core"
DIST = NEXT / "dist"
IMAGES = NEXT / "images"
PREVIEW_MAP = json.loads((NEXT / "preview-images.json").read_text(encoding="utf-8"))


def read_md(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text.strip()
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text.strip()
    fm = yaml.safe_load(text[4:end]) or {}
    body = text[end + 5:].strip()
    return fm, body


def md_inline(s):
    s = (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def note_text(body):
    return re.sub(r"^!\[[^\]]*\]\([^)]*\)\s*", "", body or "").strip()


def load_records():
    rows = []
    for collection in ("photos", "paintings", "objects", "links"):
        for p in sorted((CONTENT / collection).glob("*/*.md")):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if not fm.get("id"):
                continue
            u = usage.describe(fm.get("tier"), fm.get("rights_status"))
            note = note_text(body)
            rid = fm["id"]
            preview = PREVIEW_MAP.get(rid)
            rec = {
                "id": rid,
                "collection": collection,
                "content_type": fm.get("content_type") or ("link" if collection == "links" else "photograph"),
                "type_evidence": fm.get("type_evidence") or "",
                "review_status": fm.get("review_status") or "clean",
                "review_note": fm.get("review_note") or "",
                "isLink": collection == "links",
                "title": fm.get("title") or rid,
                "year": fm.get("year"),
                "date_label": fm.get("date_label"),
                "era": fm.get("era"),
                "kind": fm.get("kind"),
                "theme": fm.get("theme"),
                "topic": fm.get("topic"),
                "region": fm.get("region"),
                "medium": fm.get("medium"),
                "period": fm.get("period"),
                "place": fm.get("place"),
                "china": fm.get("china"),
                "creator": fm.get("creator"),
                "creator_status": fm.get("creator_status"),
                "source": fm.get("source"),
                "source_short": fm.get("source_short"),
                "source_url": fm.get("source_url"),
                "page_url": fm.get("page_url"),
                "page_url_basis": fm.get("page_url_basis"),
                "license": fm.get("license"),
                "license_url": fm.get("license_url"),
                "tier": fm.get("tier"),
                "rights_status": fm.get("rights_status"),
                "commercial_ok": fm.get("commercial_ok"),
                "usage_code": u["code"],
                "usage_label": u["label"],
                "usage_short": u["short"],
                "usage_obligation": u["obligation"],
                "usage_credit": u["credit"],
                "usage_color": u["color"],
                "credit_line": "%s · %s · %s" % (
                    fm.get("creator") or "作者见源站著录",
                    fm.get("source_short") or "",
                    fm.get("license") or ""),
                "note": note,
                "note_html": md_inline(note),
                "evidence": fm.get("evidence") if isinstance(fm.get("evidence"), dict) else {},
                "audit": fm.get("audit") if isinstance(fm.get("audit"), dict) else {},
                "image": fm.get("image"),
                "image_sha256": fm.get("image_sha256"),
                "image_century": fm.get("image_century"),
                "preview_image": ("/" + preview["target"]) if preview else None,
                "decade": preview["decade"] if preview else (
                    fm.get("period") if re.fullmatch(r"\d{4}s", str(fm.get("period") or "")) else ""),
                "search_text": " ".join(str(x) for x in [
                    fm.get("title"), fm.get("year"), fm.get("date_label"), fm.get("place"),
                    fm.get("creator"), fm.get("topic"), fm.get("theme"), fm.get("region"),
                    fm.get("medium"), fm.get("source_short"), note] if x).lower(),
            }
            rows.append(rec)
    rows.sort(key=lambda r: (r["year"] or 0, r["title"]))
    return rows


def pick(rows, pred, n):
    out = [r for r in rows if pred(r) and r.get("preview_image")]
    out.sort(key=lambda r: (r["year"] or 0, r["title"]))
    return out[:n]


def load_story_files(records):
    by_id = {r["id"]: r for r in records}
    stories = []
    for p in sorted((CONTENT / "stories" / "photos").glob("*.md")):
        fm, body = read_md(p)
        if not fm.get("id"):
            continue
        chapters, ids = [], []
        for ch in fm.get("chapters") or []:
            items = []
            for it in ch.get("items") or []:
                if isinstance(it, dict):
                    rid, cap = it.get("id"), it.get("caption") or ""
                else:
                    rid, cap = str(it), ""
                if rid in by_id:
                    items.append({"id": rid, "caption": cap})
                    ids.append(rid)
            if not items:
                for rid in ch.get("photo_ids") or []:
                    if rid in by_id:
                        items.append({"id": rid, "caption": ""})
                        ids.append(rid)
            if items:
                chapters.append({
                    "title": ch.get("title") or "",
                    "text": ch.get("text") or "",
                    "items": items,
                })
        if not chapters:
            continue
        cover = fm.get("cover") if fm.get("cover") in ids else ids[0]
        usages = Counter(by_id[i]["usage_code"] for i in ids)
        stories.append({
            "id": fm["id"],
            "title": fm.get("title") or fm["id"],
            "subtitle": fm.get("subtitle") or "",
            "type": fm.get("type") or "长文",
            "intro": body.strip(),
            "status": fm.get("status") or "draft",
            "cover": cover,
            "photo_ids": ids,
            "themes": fm.get("themes") or [],
            "chapters": chapters,
            "count": len(ids),
            "rights_summary": " · ".join("%s %d" % (k, v) for k, v in sorted(usages.items())),
        })
    return stories


def build_stories(rows):
    early = pick(rows, lambda r: r["medium"] in ("银版", "锡版", "盐纸", "蛋白印相"), 10)
    faces = pick(rows, lambda r: r["topic"] == "面孔" and r["creator_status"] == "unknown", 10)
    if len(faces) < 6:
        faces = pick(rows, lambda r: r["topic"] == "面孔", 10)
    space = pick(rows, lambda r: r["region"] == "太空", 10)
    specs = [
        ("first-fifty-years", "摄影术的前五十年",
         "从银版到蛋白印相，光如何学会留下细节",
         "专题样板 · 待策展。这里先用现有早期工艺影像搭出专题页的阅读节奏，正式文案在下一阶段撰写。",
         early, ["技艺"]),
        ("unnamed-faces", "没有留下名字的人",
         "肖像里的普通人，和没有写下的那一半",
         "专题样板 · 待策展。选取面孔类中作者不详的影像，先验证“不替无名者编故事”的写法。",
         faces, ["人间"]),
        ("earth-to-moon", "从地球到月面",
         "离开地表之后，我们第一次回头看",
         "专题样板 · 待策展。太空与航天影像权利干净、叙事线完整，适合作为第一个正式专题。",
         space, ["天地"]),
    ]
    stories = []
    for sid, title, sub, intro, items, themes in specs:
        if not items:
            continue
        stories.append({
            "id": sid,
            "title": title,
            "subtitle": sub,
            "intro": intro,
            "type": "长文",
            "themes": themes,
            "status": "筹备中",
            "cover": items[0]["id"],
            "photo_ids": [r["id"] for r in items],
            "count": len(items),
        })
    return stories


def write_bundle(records, stories, stats):
    (DIST / "data").mkdir(parents=True, exist_ok=True)
    data = {"records": records, "stories": stories, "stats": stats}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (DIST / "data" / "bundle.js").write_text(
        "window.CHENHUA_BUNDLE = %s;\n" % payload,
        encoding="utf-8", newline="\n")


DOMAINS = {
    "main": "https://www.chenhua.net",
    "photo": "https://photo.chenhua.net",
    "paint": "https://paint.chenhua.net",
}
ROUTE_META = {
    "today": ("%s", "以图为史，记录人间的大事与小事。"),  # root uses cfg.title / cfg.desc
    "gallery": ("影像 · %s", "出尘入画。按年代与主题浏览尘画已收录的影像档案。"),
    "stories": ("主题 · %s", "出尘入画。事件、人物、地方、技艺与长文。"),
    "timeline": ("时间线 · %s", "出尘入画。主题按年代排列。"),
    "search": ("搜索 · %s", "搜标题、地点、作者、主题与年代。"),
    "about": ("关于 · %s", "尘画，出尘入画，尘归尘，画归画。采集、复核与策展方式。"),
    "rights": ("授权 · %s", "U1–U5 使用性质、署名与商用边界。"),
}


def write_site(site, cfg, records, stories, stats, build_id):
    out = DIST / site
    out.mkdir(parents=True, exist_ok=True)
    brand = cfg.get("brand") or "尘画"
    domain = DOMAINS[site]
    routes = ["today", "gallery", "stories", "search", "about", "rights"]
    if site == "main":
        routes.insert(3, "timeline")
    site_ids = {r["id"] for r in records if r["collection"] in cfg["collections"]}
    has_stories = any(site_ids.intersection(s.get("photo_ids") or []) for s in stories)
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    for route in routes:
        root = route == "today"
        title_tpl, desc_tpl = ROUTE_META[route]
        title = cfg["title"] if root else (title_tpl % brand)
        desc = cfg.get("desc") if root else desc_tpl
        canonical = domain + "/" + ("" if root else route + "/")
        prefix = "../" if root else "../../"
        robots = "noindex,follow" if (route == "search" or (route == "stories" and not has_stories)) else "index,follow"
        navlinks = "".join(
            '<a href="%s">%s</a>' % (
                (cfg.get("base") or "/") + ("" if r == "today" else r + "/"),
                {"today": "今日", "gallery": "影像", "stories": "主题",
                 "timeline": "时间线", "search": "搜索",
                 "about": "关于", "rights": "授权"}[r])
            for r in routes)
        navlinks += ('<a href="%s">摄影</a><a href="%s">绘画</a>'
                     '<a href="https://netcn.org/">导航</a>') % (
                         cfg.get("photoBase") or "", cfg.get("paintBase") or "")
        noscript = ('<div class="seo-fallback"><h1>%s</h1><p>%s</p><nav>%s</nav></div>'
                    % (title, desc, navlinks))
        ld = ""
        if site == "main" and root:
            ld_data = {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "尘画",
                "alternateName": ["出尘入画", "尘归尘，画归画"],
                "url": DOMAINS["main"] + "/",
                "inLanguage": "zh-CN",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": DOMAINS["main"] + "/search/?q={search_term_string}",
                    "query-input": "required name=search_term_string",
                },
            }
            ld = '<script type="application/ld+json">%s</script>\n' % json.dumps(
                ld_data, ensure_ascii=False).replace("</", "<\\/")
        html = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>%s</title>
<meta name="description" content="%s">
<meta name="robots" content="%s">
<link rel="canonical" href="%s">
<meta property="og:type" content="website">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<link rel="dns-prefetch" href="//19century.chenhua.net">
<link rel="dns-prefetch" href="//20century.chenhua.net">
<link rel="dns-prefetch" href="//21century.chenhua.net">
%s<link rel="stylesheet" href="%sassets/app.css?v=%s">
</head>
<body>
<div id="app" aria-live="polite"></div>
<noscript>%s</noscript>
<script>window.SITE_CONFIG = %s;</script>
<script src="%sdata/bundle.js?v=%s"></script>
<script src="%sassets/app.js?v=%s"></script>
</body>
</html>
""" % (title, desc, robots, canonical, title, desc, canonical, ld,
       prefix, build_id, noscript, cfg_json,
       prefix, build_id, prefix, build_id)
        folder = out if root else out / route
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(html, encoding="utf-8", newline="\n")


def write_gallery_assets():
    src = CORE / "gallery"
    dst = DIST / "assets"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("gallery.css", "gallery.js"):
        shutil.copy2(src / name, dst / name)


def write_galleries(build_id):
    for century in ("19century", "20century", "21century"):
        folder = IMAGES / century
        if not folder.exists():
            continue
        shutil.copy2(CORE / "gallery" / "gallery.css", folder / "gallery.css")
        shutil.copy2(CORE / "gallery" / "gallery.js", folder / "gallery.js")
        title = {"19century": "19th Century", "20century": "20th Century",
                 "21century": "21st Century"}[century]
        html = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>%s · 尘画图片索引</title>
<link rel="stylesheet" href="gallery.css?v=%s">
</head>
<body>
<header class="g-head">
  <div class="g-brand"><span class="g-cn">尘画</span><span class="g-en">出尘入画 · %s</span></div>
  <nav class="g-nav">
    <a href="../../dist/main/">尘画</a>
    <a href="../../dist/main/stories/">主题</a>
    <a href="../../dist/main/timeline/">时间线</a>
    <a href="../../dist/photo/">摄影</a>
    <a href="../../dist/paint/">绘画</a>
    <a href="../../dist/main/search/">搜索</a>
    <a href="https://netcn.org/">导航</a>
  </nav>
</header>
<main class="g-wrap">
  <div class="g-intro">
    <h1>%s</h1>
    <p>这是尘画的图片索引页。完整档案、许可与来源见摄影 / 绘画站；本页只做浏览入口。</p>
  </div>
  <div class="g-chips" id="gChips"></div>
  <div class="g-count" id="gCount">—</div>
  <div class="g-masonry" id="gMasonry"></div>
  <div class="g-more"><button id="gMore" type="button">加载更多</button></div>
</main>
<footer class="g-foot">
  <nav>
    <a href="../../dist/main/">尘画</a>
    <a href="../../dist/main/stories/">主题</a>
    <a href="../../dist/main/timeline/">时间线</a>
    <a href="../../dist/photo/">摄影</a>
    <a href="../../dist/paint/">绘画</a>
    <a href="../../dist/main/search/">搜索</a>
    <a href="https://netcn.org/">导航</a>
  </nav>
  <p>尘画 · 出尘入画 · 尘归尘，画归画</p>
  <p><a href="../../dist/main/legal/">法律声明</a> · 影像版权归原作者与收藏机构</p>
</footer>
<script>window.GALLERY_CONFIG = %s;</script>
<script src="gallery.js?v=%s"></script>
</body>
</html>
""" % (title, build_id, title, title, json.dumps({
            "century": century,
            "photoBase": "../../dist/photo/",
            "paintBase": "../../dist/paint/",
            "photoStaticBase": "../../dist/photo/photo/",
            "paintStaticBase": "../../dist/paint/painting/",
            "mainBase": "../../dist/main/",
            "preview": True,
        }, ensure_ascii=False), build_id)
        (folder / "index.html").write_text(html, encoding="utf-8", newline="\n")


def main():
    build_id = str(int(time.time()))
    records = load_records()
    real_stories = load_story_files(records)
    samples = build_stories(records)
    real_ids = {s["id"] for s in real_stories}
    stories = real_stories + [s for s in samples if s["id"] not in real_ids]
    stats = {
        "total": len(records),
        "photos": sum(1 for r in records if r["collection"] == "photos"),
        "paintings": sum(1 for r in records if r["collection"] == "paintings"),
        "objects": sum(1 for r in records if r["collection"] == "objects"),
        "links": sum(1 for r in records if r["collection"] == "links"),
        "content_types": dict(Counter(r["content_type"] for r in records).most_common()),
        "centuries": dict(Counter(r["image_century"] for r in records if r["image_century"])),
        "topics": dict(Counter(r["topic"] for r in records if r["topic"]).most_common()),
        "regions": dict(Counter(r["region"] for r in records if r["region"]).most_common()),
        "usage": dict(Counter(r["usage_code"] for r in records if r["usage_code"]).most_common()),
        "sources": dict(Counter(r["source_short"] for r in records if r["source_short"]).most_common()),
    }
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    for name in ("app.css", "app.js"):
        shutil.copy2(CORE / "assets" / name, DIST / "assets" / name)

    base = {
        "main": "/next/dist/main/", "photo": "/next/dist/photo/",
        "paint": "/next/dist/paint/",
    }
    nav = [
        {"label": "尘画", "href": base["main"], "icon": "home", "site": "main"},
        {"label": "主题", "themes": True, "icon": "stories"},
        {"label": "时间线", "timeline": True, "icon": "timeline", "wideOnly": True},
        {"label": "摄影", "href": base["photo"], "icon": "photo", "site": "photo"},
        {"label": "绘画", "href": base["paint"], "icon": "paint", "site": "paint"},
        {"label": "搜索", "route": "search", "icon": "search"},
        {"label": "导航", "href": "https://netcn.org/", "icon": "compass", "site": "netcn"},
    ]
    common = {"home": base["main"], "photoBase": base["photo"],
              "paintBase": base["paint"], "nav": nav}
    main_cfg = {
        "site": "main", "title": "尘画 · 出尘入画", "brand": "尘画",
        "sub": "出尘入画 · 以图为史",
        "desc": "尘画，出尘入画，尘归尘，画归画。以图为史，记录人间的大事与小事。",
        "collections": ["photos", "paintings", "links"],
        "base": base["main"], **common,
    }
    photo_cfg = {
        "site": "photo", "title": "尘画 · 摄影", "brand": "尘画",
        "sub": "出尘入画 · 摄影",
        "desc": "尘画摄影，出尘入画，尘归尘，画归画。摄影影像开放档案。",
        "collections": ["photos", "links"],
        "base": base["photo"], **common,
    }
    paint_cfg = {
        "site": "paint", "title": "尘画 · 绘画", "brand": "尘画",
        "sub": "出尘入画 · 绘画",
        "desc": "尘画绘画，出尘入画，尘归尘，画归画。绘画与版画开放档案。",
        "collections": ["paintings"],
        "base": base["paint"], **common,
    }
    write_bundle(records, stories, stats)
    write_site("main", main_cfg, records, stories, stats, build_id)
    write_site("photo", photo_cfg, records, stories, stats, build_id)
    write_site("paint", paint_cfg, records, stories, stats, build_id)
    write_galleries(build_id)

    print("预览构建完成：records %d · stories %d · 站点 main/photo/paint · 图片站 19/20/21century"
          % (len(records), len(stories)))
    print("统计：" + json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
