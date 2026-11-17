# -*- coding: utf-8 -*-
"""Phase 1 预览构建：Markdown 内容 + 世纪图片清单 → 三个站点 + 图片站瀑布页。"""
import json
import pathlib
import re
import shutil
import sys
import time
from collections import Counter
from html import escape as html_escape

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
import usage  # noqa: E402  (next/tools/usage.py)

NEXT = ROOT / "next"
CONTENT = NEXT / "content"
CORE = NEXT / "core"
DIST = NEXT / "dist"
IMAGES = NEXT / "images"
PREVIEW_MAP = json.loads((NEXT / "preview-images.json").read_text(encoding="utf-8"))

I18N_DIR = CONTENT / "i18n"


def load_i18n(name, default):
    p = I18N_DIR / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        print("i18n load failed: %s (%s)" % (p, exc))
        return default


TAXONOMY = load_i18n("taxonomy.en.json", {})
RECORD_I18N = load_i18n("records.en.json", {})
STORY_I18N = load_i18n("stories.en.json", {})
CAPTIONS_I18N = load_i18n("captions.en.json", {})
UI_I18N = load_i18n("ui.json", {"zh": {}, "en": {}})
USAGE_EN = TAXONOMY.get("usage", {})
STORY_TYPE_EN = {"长文": "Long read", "事件": "Event", "专题": "Story",
                 "摄影": "Photography", "绘画": "Painting"} 


def tx(kind, value):
    if not value:
        return ""
    return (TAXONOMY.get(kind) or {}).get(value, value)


CREATOR_EN = {
    "富山県内務部第四課": "Toyama Prefectural Government, Fourth Section",
    "小川一真": "Ogawa Kazumasa",
    "望月小太郎": "Mochizuki Kotarō",
    "大東京写真帖": "Dai Tokyo Shashinchō (Great Tokyo Photograph Album)",
    "毎日新聞社「日本の肖像」・「毎日グラフ」1950年6月10日号":
        "Mainichi Shimbun, “Portraits of Japan” / Mainichi Graphic, 10 June 1950 issue",
    "大英博物馆": "The British Museum",
    "故宫博物院": "The Palace Museum",
    "美国国会图书馆": "Library of Congress",
    "史密森尼 美国艺术博物馆": "Smithsonian American Art Museum",
    "史密森尼 非裔美国人历史文化馆": "Smithsonian National Museum of African American History and Culture",
    "史密森尼 国家邮政博物馆": "Smithsonian National Postal Museum",
    "史密森尼 美国国家历史博物馆": "Smithsonian National Museum of American History",
}


def creator_en(value):
    v = (value or "").strip()
    if not v:
        return "Unknown"
    if v in CREATOR_EN:
        return CREATOR_EN[v]
    if any(k in v for k in ("不详", "佚名", "未知", "未著录")):
        return "Unknown (not recorded by source)" if "源" in v else "Unknown"
    if v == "投稿者がスキャン":
        return "Contributor scan"
    if "Unknown author" in v:
        return "Unknown author"
    return v


def _ordinal(n):
    n = str(n)
    if n.endswith("11") or n.endswith("12") or n.endswith("13"):
        return n + "th"
    return n + {"1": "st", "2": "nd", "3": "rd"}.get(n[-1], "th")


def english_date(value):
    s = str(value or "").strip()
    if not s:
        return ""
    special = {"清宫旧藏": "Qing palace collection"}
    if s in special:
        return special[s]
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return "%s %d, %d" % (months[int(m.group(2)) - 1], int(m.group(3)), int(m.group(1)))
    m = re.fullmatch(r"公元前(\d+)年(\d+)月(\d+)日", s)
    if m:
        return "%s %d, %s BCE" % (months[int(m.group(2)) - 1], int(m.group(3)), m.group(1))
    s = s.replace("约 ", "ca. ").replace("约", "ca.")
    s = re.sub(r"(\d{1,2})\s*[–-]\s*(\d{1,2})\s*世纪",
               lambda m: _ordinal(m.group(1)) + "–" + _ordinal(m.group(2)) + " century", s)
    s = re.sub(r"(\d{1,2})\s*世纪",
               lambda m: _ordinal(m.group(1)) + " century", s)
    s = re.sub(r"(\d{4})\s*[–-]\s*(\d{4})\s*年代", r"\1–\2s", s)
    s = re.sub(r"(\d{4})\s*年代", r"\1s", s)
    s = s.replace("年代", "s").replace("年", "")
    s = re.sub(r"\s+s\b", "s", s)
    return s.strip()


LICENSE_EN = {
    "No known copyright restrictions（来源声明，非许可）":
        "No known copyright restrictions (source statement, not a licence)",
    "Public Domain (美国政府作品)": "Public Domain (U.S. government work)",
    "权利保留 · 禁止批量采集": "All rights reserved · bulk harvesting prohibited",
}


def license_en(value):
    v = str(value or "").strip()
    if not v:
        return ""
    return LICENSE_EN.get(v, v)


def note_en_for(r, manual=None):
    if manual:
        return manual
    date = english_date(r.get("date_label") or r.get("year"))
    region = r.get("region_en") or tx("region", r.get("region"))
    creator = creator_en(r.get("creator"))
    source = r.get("source_short_en") or tx("source_short", r.get("source_short"))
    catalog = (r.get("evidence") or {}).get("catalog_id") or ""
    ctype = (r.get("content_type_en") or tx("content_type", r.get("content_type")) or "image").lower()
    medium = (r.get("medium_en") or tx("medium", r.get("medium")) or "").lower()
    first = ", ".join(x for x in (date, region) if x)
    if first:
        first += "."
    second = creator
    if source:
        second += "; source: " + source
    if catalog:
        second += ", catalog no. " + str(catalog)
    if second:
        second += "."
    if ctype in ("link",):
        third = ""
    elif medium and medium != ctype:
        article = "an" if ctype[0] in "aeiou" else "a"
        third = "This is %s %s (%s)." % (article, ctype, medium)
    else:
        article = "an" if ctype[0] in "aeiou" else "a"
        third = "This is %s %s." % (article, ctype)
    return " ".join(x for x in (first, second, third) if x)



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
                "credit_line": " · ".join(
                    p for i, p in enumerate((fm.get("creator") or "作者见源站著录",
                                             fm.get("source_short") or "",
                                             fm.get("license") or ""))
                    if p and (i == 0 or p != (fm.get("creator") or "作者见源站著录",
                                               fm.get("source_short") or "",
                                               fm.get("license") or "")[i - 1])),
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
            tr = RECORD_I18N.get(rid, {}) or {}
            ue = USAGE_EN.get(u["code"], {})
            rec["title_en"] = tr.get("title") or (fm.get("title") if not re.search(r"[\u4e00-\u9fff]", str(fm.get("title") or "")) else rec["title"])
            rec["place_en"] = tr.get("place") or tx("place", fm.get("place"))
            rec["theme_en"] = tx("theme", fm.get("theme"))
            rec["topic_en"] = tx("topic", fm.get("topic"))
            rec["region_en"] = tx("region", fm.get("region"))
            rec["medium_en"] = tx("medium", fm.get("medium"))
            rec["kind_en"] = tx("kind", fm.get("kind"))
            rec["era_en"] = tx("era", fm.get("era"))
            rec["content_type_en"] = tx("content_type", rec["content_type"])
            rec["source_short_en"] = tx("source_short", fm.get("source_short"))
            rec["usage_label_en"] = ue.get("label") or u["label"]
            rec["usage_short_en"] = ue.get("short") or u["short"]
            rec["usage_desc_en"] = ue.get("desc") or u["desc"]
            rec["usage_obligation_en"] = ue.get("obligation") or u["obligation"]
            rec["usage_credit_en"] = ue.get("credit") or u["credit"]
            rec["note_en"] = tr.get("note") or note_en_for(rec, None)
            credit_parts = [creator_en(fm.get("creator")), rec["source_short_en"],
                            license_en(fm.get("license"))]
            credit_parts = [p for i, p in enumerate(credit_parts)
                            if p and (i == 0 or p != credit_parts[i - 1])]
            rec["credit_line_en"] = " · ".join(credit_parts)
            rec["date_label_en"] = english_date(fm.get("date_label") or fm.get("year"))
            rec["search_text_en"] = " ".join(str(x) for x in [
                rec["title_en"], fm.get("year"), fm.get("date_label"), rec["place_en"],
                fm.get("creator"), rec["topic_en"], rec["theme_en"], rec["region_en"],
                rec["medium_en"], rec["source_short_en"], rec["note_en"]] if x).lower()
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
            "date": str(fm.get("date") or ""),
            "date_label": str(fm.get("date_label") or ""),
            "today_rank": int(fm.get("today_rank") or 1),
            "place": fm.get("place") or "",
            "sources": fm.get("sources") or [],
            "intro": body.strip(),
            "status": fm.get("status") or "draft",
            "cover": cover,
            "photo_ids": ids,
            "themes": fm.get("themes") or [],
            "chapters": chapters,
            "count": len(ids),
            "rights_summary": " · ".join("%s %d" % (k, v) for k, v in sorted(usages.items())),
        })
        s = stories[-1]
        s["date_label_en"] = english_date(s["date_label"] or s["date"])
        s["rights_summary_en"] = " · ".join(
            "%s · %d %s" % (k, v, "image" if v == 1 else "images")
            for k, v in sorted(usages.items()))
        tr = STORY_I18N.get(s["id"], {}) or {}
        s["title_en"] = tr.get("title") or (s["title"] if not re.search(r"[\u4e00-\u9fff]", s["title"]) else s["title"])
        s["subtitle_en"] = tr.get("subtitle") or s["subtitle"]
        s["intro_en"] = tr.get("intro") or s["intro"]
        s["type_en"] = tr.get("type_en") or STORY_TYPE_EN.get(s["type"], "Story")
        s["themes_en"] = tr.get("themes") or [tx("theme", x) for x in s["themes"]]
        s["place_en"] = tx("place", s["place"])
        chapter_tr = tr.get("chapters") or {}
        for idx, ch in enumerate(s["chapters"]):
            ctr = chapter_tr.get(str(idx)) or {}
            ch["title_en"] = ctr.get("title") or ch["title"]
            ch["text_en"] = ctr.get("text") or ch["text"]
        item_tr = tr.get("captions") or {}
        for ch in s["chapters"]:
            for it in ch["items"]:
                it["caption_en"] = (item_tr.get(it["id"])
                                    or CAPTIONS_I18N.get(it["caption"])
                                    or it["caption"])
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
            "date": "",
            "date_label": "",
            "place": "",
            "sources": [],
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
    "today": ("%s", "历史上的今天：每天至少一个故事。"),
    "gallery": ("影像 · %s", "按年代与主题浏览摄影与绘画。"),
    "stories": ("主题 · %s", "事件、人物、地方与技艺。"),
    "timeline": ("时间线 · %s", "主题按年代排列。"),
    "search": ("搜索 · %s", "搜标题、地点、作者、主题与年代。"),
    "about": ("关于 · %s", "尘画的来源、许可与整理方式。"),
    "rights": ("授权 · %s", "图片许可、署名与商用说明。"),
}
ROUTE_META_EN = {
    "gallery": ("Archive · %s", "Browse photography and painting by era and theme."),
    "stories": ("Stories · %s", "Events, people, places and craft."),
    "timeline": ("Timeline · %s", "Stories arranged by year."),
    "search": ("Search · %s", "Search titles, places, creators, themes and years."),
    "about": ("About · %s", "Sources, licences and how Chenhua organises its images."),
    "rights": ("Rights · %s", "Image licences, credit and commercial use."),
}


def write_i18n_assets():
    assets = DIST / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(UI_I18N, ensure_ascii=False).replace("</", "<\\/")
    (assets / "i18n.js").write_text("window.CHENHUA_I18N = %s;\n" % payload,
                                    encoding="utf-8", newline="\n")
    site_js = CORE / "assets" / "site.js"
    if site_js.exists():
        shutil.copy2(site_js, assets / "site.js")
    leaf_src = CORE / "leaf"
    leaf_dst = assets / "leaf"
    leaf_dst.mkdir(parents=True, exist_ok=True)
    for name in ("calm.svg", "joy.svg", "curious.svg", "think.svg",
                 "sleepy.svg", "surprised.svg", "shy.svg", "proud.svg", "favicon.svg"):
        if (leaf_src / name).exists():
            shutil.copy2(leaf_src / name, leaf_dst / name)


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
    def prefix_leaf(route):
        return ("../" if route == "today" else "../../") + "assets/leaf/"
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    for route in routes:
        root = route == "today"
        page_cfg = dict(cfg)
        page_cfg["leafBase"] = prefix_leaf(route)
        cfg_json = json.dumps(page_cfg, ensure_ascii=False).replace("</", "<\\/")
        title_tpl, desc_tpl = ROUTE_META[route]
        title = cfg["title"] if root else (title_tpl % brand)
        desc = cfg.get("desc") if root else desc_tpl
        title_en_tpl, desc_en_tpl = ROUTE_META_EN.get(route, ("%s", ""))
        brand_en = cfg.get("brand_en") or "Chenhua"
        title_en = cfg.get("title_en") if root else (title_en_tpl % brand_en)
        desc_en = cfg.get("desc_en") if root else desc_en_tpl
        canonical = domain + "/" + ("" if root else route + "/")
        prefix = "../" if root else "../../"
        robots = "noindex,follow" if (route == "search" or (route == "stories" and not has_stories)) else "index,follow"
        if site != "main" and route == "search":
            scope = "photos" if site == "photo" else "paintings"
            target = "../../main/search/?scope=" + scope
            canonical_target = DOMAINS["main"] + "/search/?scope=" + scope
            redirect = """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,follow">
<meta name="theme-color" content="#0d0c0b">
<title>搜索 · 尘画</title>
<link rel="canonical" href="%s">
<link rel="icon" type="image/svg+xml" href="../../assets/leaf/favicon.svg">
<meta http-equiv="refresh" content="0;url=%s">
<style>
html[data-lang="en"] [data-l="zh"]{display:none}
html[data-lang="zh"] [data-l="en"]{display:none}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0d0c0b;color:#ebe5da;font:14px/1.8 "PingFang SC","Microsoft YaHei",sans-serif}
html[data-theme="light"] body{background:#f6f2ea;color:#231f19}
a{color:#c8a24a}
html[data-theme="light"] a{color:#8b6520}
</style>
<script>
(function(){try{var t=localStorage.getItem("chenhua-theme");if(t)document.documentElement.setAttribute("data-theme",t);
var l=localStorage.getItem("chenhua-lang");if(l){document.documentElement.setAttribute("data-lang",l);
document.documentElement.setAttribute("lang",l==="en"?"en":"zh-CN");}}catch(e){}})();
</script>
</head>
<body data-title-zh="搜索 · 尘画" data-title-en="Search · Chenhua">
<p><span data-l="zh">正在前往尘画统一搜索：<a href="%s">继续</a></span><span data-l="en">Redirecting to Chenhua search: <a href="%s">continue</a></span></p>
<script src="../../assets/site.js"></script>
</body>
</html>
""" % (canonical_target, target, target, target)
            folder = out / "search"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "index.html").write_text(redirect, encoding="utf-8", newline="\n")
            continue
        if site == "main" and route in ("stories", "timeline"):
            target = "../atlas/index.html" + ("?view=timeline" if route == "timeline" else "")
            canonical_target = domain + "/atlas/" + ("?view=timeline" if route == "timeline" else "")
            redirect = """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,follow">
<meta name="theme-color" content="#0d0c0b">
<title>%s</title>
<link rel="canonical" href="%s">
<link rel="icon" type="image/svg+xml" href="../../assets/leaf/favicon.svg">
<meta http-equiv="refresh" content="0;url=%s">
<style>
html[data-lang="en"] [data-l="zh"]{display:none}
html[data-lang="zh"] [data-l="en"]{display:none}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0d0c0b;color:#ebe5da;font:14px/1.8 "PingFang SC","Microsoft YaHei",sans-serif}
html[data-theme="light"] body{background:#f6f2ea;color:#231f19}
a{color:#c8a24a}
html[data-theme="light"] a{color:#8b6520}
</style>
<script>
(function(){try{var t=localStorage.getItem("chenhua-theme");if(t)document.documentElement.setAttribute("data-theme",t);
var l=localStorage.getItem("chenhua-lang");if(l){document.documentElement.setAttribute("data-lang",l);
document.documentElement.setAttribute("lang",l==="en"?"en":"zh-CN");}}catch(e){}})();
</script>
</head>
<body data-title-zh="%s" data-title-en="%s">
<p><span data-l="zh">正在前往全站图录：<a href="%s">继续</a></span><span data-l="en">Redirecting to the Atlas: <a href="%s">continue</a></span></p>
</body>
</html>
""" % (title, canonical_target, target, title, title_en, target, target)
            folder = out / route
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "index.html").write_text(redirect, encoding="utf-8", newline="\n")
            continue

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
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>%s</title>
<meta name="description" content="%s">
<meta name="robots" content="%s">
<link rel="canonical" href="%s">
<link rel="alternate" hreflang="zh-CN" href="%s">
<link rel="alternate" hreflang="en" href="%s?lang=en">
<link rel="alternate" hreflang="x-default" href="%s">
<link rel="icon" type="image/svg+xml" href="%sassets/leaf/favicon.svg">
<meta property="og:type" content="website">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<link rel="dns-prefetch" href="//19century.chenhua.net">
<link rel="dns-prefetch" href="//20century.chenhua.net">
<link rel="dns-prefetch" href="//21century.chenhua.net">
<script>(function(){try{var q=new URLSearchParams(location.search).get("lang");var l=q||localStorage.getItem("chenhua-lang");if(l==="en"){document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en";}var t=localStorage.getItem("chenhua-theme");if(!t&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)t="light";if(t==="light"){document.documentElement.setAttribute("data-theme","light");}}catch(e){}})();</script>
%s<link rel="stylesheet" href="%sassets/app.css?v=%s">
</head>
<body data-title-zh="%s" data-title-en="%s" data-desc-zh="%s" data-desc-en="%s">
<div id="app" aria-live="polite"></div>
<noscript>%s</noscript>
<script>window.SITE_CONFIG = %s;</script>
<script src="%sassets/i18n.js?v=%s"></script>
<script src="%sdata/bundle.js?v=%s"></script>
<script src="%sassets/app.js?v=%s"></script>
</body>
</html>
""" % (html_escape(title, quote=True), html_escape(desc, quote=True), robots, canonical,
       canonical, canonical, canonical,
       prefix,
       html_escape(title, quote=True), html_escape(desc, quote=True), canonical, ld,
       prefix, build_id,
       html_escape(title, quote=True), html_escape(title_en or title, quote=True),
       html_escape(desc, quote=True), html_escape(desc_en or desc, quote=True),
       noscript, cfg_json,
       prefix, build_id, prefix, build_id, prefix, build_id)
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
        title_zh = "%s · 尘画图片索引" % title
        title_en = "%s · Chenhua Image Index" % title
        desc_zh = "按世纪浏览尘画影像。完整记录见摄影 / 绘画站。"
        desc_en = "Browse Chenhua images by century. Full records are on the Photography and Painting sites."
        g_nav = (
            '<a href="../../dist/main/"><span data-l="zh">尘画</span><span data-l="en">Chenhua</span></a>'
            '<a href="../../dist/main/atlas/"><span data-l="zh">图录</span><span data-l="en">Atlas</span></a>'
            '<a href="../../dist/main/atlas/?view=timeline"><span data-l="zh">时间线</span><span data-l="en">Timeline</span></a>'
            '<a href="../../dist/main/today/"><span data-l="zh">历史上的今天</span><span data-l="en">On This Day</span></a>'
            '<a href="../../dist/photo/"><span data-l="zh">摄影</span><span data-l="en">Photography</span></a>'
            '<a href="../../dist/paint/"><span data-l="zh">绘画</span><span data-l="en">Painting</span></a>'
            '<a href="../../dist/main/search/"><span data-l="zh">搜索</span><span data-l="en">Search</span></a>'
            '<a href="https://netcn.org/"><span data-l="zh">导航</span><span data-l="en">Directory</span></a>'
        )
        g_utility = (
            '<a href="../../dist/main/about/"><span data-l="zh">关于</span><span data-l="en">About</span></a>'
            '<a href="../../dist/main/rights/"><span data-l="zh">授权</span><span data-l="en">Rights</span></a>'
            '<a href="../../dist/main/legal/"><span data-l="zh">法律</span><span data-l="en">Legal</span></a>'
        )
        html = f"""<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<meta name="description" content="{desc_zh}">
<title>{title_zh}</title>
<link rel="alternate" hreflang="zh-CN" href="https://{century}.chenhua.net/">
<link rel="alternate" hreflang="en" href="https://{century}.chenhua.net/?lang=en">
<link rel="icon" type="image/svg+xml" href="../../dist/assets/leaf/favicon.svg">
<link rel="stylesheet" href="gallery.css?v={build_id}">
<script>
(function(){{try{{var q=new URLSearchParams(location.search).get("lang");var l=q||localStorage.getItem("chenhua-lang");if(l==="en"){{document.documentElement.setAttribute("data-lang","en");
document.documentElement.setAttribute("lang","en");}}
var t=localStorage.getItem("chenhua-theme");if(!t&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)t="light";if(t==="light"){{document.documentElement.setAttribute("data-theme","light");}}}}catch(e){{}}}})();
</script>
</head>
<body data-title-zh="{title_zh}" data-title-en="{title_en}"
      data-desc-zh="{desc_zh}" data-desc-en="{desc_en}">
<header class="g-head">
  <a class="g-brand" href="../../dist/main/"><img class="g-mark" src="../../dist/assets/leaf/curious.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="g-en"><span data-l="zh">尘归尘，画归画</span><span data-l="en">Image as history</span></span></a>
  <nav class="g-nav">
    {g_nav}
  </nav>
  <div class="g-tools">
    <button class="g-tool g-lang" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button>
    <button class="g-tool" type="button" data-themebtn aria-label="切换到浅色">
      <span class="icon-sun"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.4v2.2M12 19.4v2.2M2.4 12h2.2M19.4 12h2.2M5.2 5.2l1.6 1.6M17.2 17.2l1.6 1.6M18.8 5.2l-1.6 1.6M6.8 17.2l-1.6 1.6"/></svg></span>
      <span class="icon-moon"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M20 14.6A8.4 8.4 0 1 1 9.4 4a6.8 6.8 0 0 0 10.6 10.6z"/></svg></span>
    </button>
  </div>
</header>
<main class="g-wrap">
  <div class="g-intro">
    <h1>{title}</h1>
    <p><span data-l="zh">{desc_zh}</span><span data-l="en">{desc_en}</span></p>
  </div>
  <div class="g-chips" id="gChips"></div>
  <div class="g-count" id="gCount">—</div>
  <div class="g-masonry" id="gMasonry"></div>
  <div class="g-more"><button id="gMore" type="button"><span data-l="zh">加载更多</span><span data-l="en">Load more</span></button></div>
</main>
<footer class="site-foot">
  <a class="sf-brand" href="../../dist/main/"><span data-l="zh">出尘入画</span><span data-l="en">Chenhua</span></a>
  <nav class="sf-nav">{g_nav}</nav>
  <nav class="sf-utility">{g_utility}</nav>
</footer>
<script>window.GALLERY_CONFIG = {json.dumps({
            "century": century,
            "photoBase": "../../dist/photo/",
            "paintBase": "../../dist/paint/",
            "photoStaticBase": "../../dist/photo/photo/",
            "paintStaticBase": "../../dist/paint/painting/",
            "mainBase": "../../dist/main/",
            "preview": True,
        }, ensure_ascii=False)};</script>
<script src="../../dist/assets/site.js"></script>
<script src="gallery.js?v={build_id}"></script>
</body>
</html>
"""
        (folder / "index.html").write_text(html, encoding="utf-8", newline="\n")


def write_404(build_id):
    out = DIST / "main" / "404.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    nav_links = "".join('<a href="%s"><span data-l="zh">%s</span><span data-l="en">%s</span></a>' % (h, z, e)
                       for z, e, h in [
                           ("尘画", "Chenhua", "index.html"),
                           ("图录", "Atlas", "atlas/"),
                           ("时间线", "Timeline", "atlas/?view=timeline"),
                           ("历史上的今天", "On This Day", "today/"),
                           ("摄影", "Photography", "../../photo/"),
                           ("绘画", "Painting", "../../paint/"),
                           ("搜索", "Search", "search/"),
                           ("导航", "Directory", "https://netcn.org/"),
                       ])
    utility = "".join('<a href="%s"><span data-l="zh">%s</span><span data-l="en">%s</span></a>' % (h, z, e)
                      for z, e, h in [
                          ("关于", "About", "about/"),
                          ("授权", "Rights", "rights/"),
                          ("法律", "Legal", "legal/"),
                      ])
    html = """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>页面不存在 · 尘画</title>
<meta name="robots" content="noindex,follow">
<link rel="icon" type="image/svg+xml" href="../assets/leaf/favicon.svg">
<link rel="stylesheet" href="../assets/app.css?v=%s">
<link rel="stylesheet" href="../assets/static.css?v=%s">
<script>(function(){try{var q=new URLSearchParams(location.search).get("lang");var l=q||localStorage.getItem("chenhua-lang");if(l==="en"){document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en";}var t=localStorage.getItem("chenhua-theme");if(!t&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)t="light";if(t==="light"){document.documentElement.setAttribute("data-theme","light");}}catch(e){}})();</script>
<style>
.static-body{min-height:100vh}
.notfound{max-width:760px;margin:0 auto;padding:46px 20px 80px;text-align:center}
.notfound .empty-mark{width:120px;height:120px;margin:0 auto 12px}
.notfound h1{font-family:var(--serif);font-weight:400;font-size:clamp(30px,5vw,48px);letter-spacing:.08em;margin:0 0 8px}
.notfound p{font-size:13px;color:var(--muted);line-height:1.9;margin:0 auto 18px;max-width:34em}
.notfound .big{font-family:var(--serif);font-size:76px;line-height:1;color:var(--accent);letter-spacing:.04em;margin:0 0 8px}
.notfound .btn{margin:4px 4px 0}
</style>
</head>
<body class="static-body" data-title-zh="页面不存在 · 尘画" data-title-en="Page not found · Chenhua">
<div class="s-shell">
<header class="appbar s-appbar">
<a class="brand" href="index.html"><img class="leaf-mark brand-mark" src="../assets/leaf/surprised.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="sub"><span data-l="zh">尘归尘，画归画</span><span data-l="en">Image as history</span></span></a>
<nav class="desknav">%s</nav>
<div class="right"><button class="langbtn" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button><button class="iconbtn themebtn" type="button" data-themebtn aria-label="切换明暗"><svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg></button></div>
</header>
<main class="notfound">
<div class="big">404</div>
<div class="empty empty-leaf"><img class="leaf-mark empty-mark" src="../assets/leaf/surprised.svg" width="120" height="120" alt="" aria-hidden="true" decoding="async"><b><span data-l="zh">页面不存在</span><span data-l="en">Page not found</span></b><p><span data-l="zh">地址可能已变更，或页面尚未收录。</span><span data-l="en">The address may have changed, or the page is not here.</span></p></div>
<div><a class="btn gold" href="index.html"><span data-l="zh">返回首页</span><span data-l="en">Back home</span></a><a class="btn" href="atlas/"><span data-l="zh">浏览图录</span><span data-l="en">Browse the Atlas</span></a></div>
</main>
<footer class="site-foot"><a class="sf-brand" href="index.html"><span data-l="zh">出尘入画</span><span data-l="en">Chenhua</span></a><nav class="sf-nav">%s</nav><nav class="sf-utility">%s</nav></footer>
</div>
<script src="../assets/site.js?v=%s"></script>
</body></html>
""" % (build_id, build_id, nav_links, nav_links, utility, build_id)
    out.write_text(html, encoding="utf-8", newline="\n")


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
        {"label": "尘画", "label_en": "Chenhua", "href": base["main"], "icon": "home", "site": "main"},
        {"label": "图录", "label_en": "Atlas", "href": base["main"] + "atlas/", "icon": "stories"},
        {"label": "时间线", "label_en": "Timeline", "href": base["main"] + "atlas/?view=timeline", "icon": "timeline", "wideOnly": True},
        {"label": "历史上的今天", "label_en": "On This Day", "href": base["main"] + "today/", "icon": "timeline", "wideOnly": True},
        {"label": "摄影", "label_en": "Photography", "href": base["photo"], "icon": "photo", "site": "photo"},
        {"label": "绘画", "label_en": "Painting", "href": base["paint"], "icon": "paint", "site": "paint"},
        {"label": "搜索", "label_en": "Search", "search": True, "icon": "search"},
        {"label": "导航", "label_en": "Directory", "href": "https://netcn.org/", "icon": "compass", "site": "netcn"},
    ]
    common = {"home": base["main"], "photoBase": base["photo"],
              "paintBase": base["paint"], "nav": nav, "taxonomy": TAXONOMY,
              "leafBase": "/next/dist/assets/leaf/"}
    main_cfg = {
        "site": "main", "title": "尘画 · 出尘入画", "brand": "尘画", "brand_en": "Chenhua",
        "title_en": "Chenhua · Out of dust, into the image",
        "sub": "尘归尘，画归画", "sub_en": "Image as history",
        "desc": "尘画：历史摄影与绘画图录。",
        "desc_en": "Chenhua: an archive of historical photography and painting.",
        "collections": ["photos", "paintings", "links"],
        "base": base["main"], **common,
    }
    photo_cfg = {
        "site": "photo", "title": "尘画 · 摄影", "brand": "尘画", "brand_en": "Chenhua",
        "title_en": "Chenhua · Photography",
        "sub": "尘归尘，画归画", "sub_en": "Image as history",
        "desc": "尘画摄影：历史摄影图录。",
        "desc_en": "Chenhua Photography: an archive of historical photographs.",
        "collections": ["photos", "links"],
        "base": base["photo"], **common,
    }
    paint_cfg = {
        "site": "paint", "title": "尘画 · 绘画", "brand": "尘画", "brand_en": "Chenhua",
        "title_en": "Chenhua · Painting",
        "sub": "尘归尘，画归画", "sub_en": "Image as history",
        "desc": "尘画绘画：绘画与版画图录。",
        "desc_en": "Chenhua Painting: an archive of paintings and prints.",
        "collections": ["paintings"],
        "base": base["paint"], **common,
    }
    write_i18n_assets()
    write_bundle(records, stories, stats)
    write_site("main", main_cfg, records, stories, stats, build_id)
    write_site("photo", photo_cfg, records, stories, stats, build_id)
    write_site("paint", paint_cfg, records, stories, stats, build_id)
    write_404(build_id)
    write_galleries(build_id)

    print("预览构建完成：records %d · stories %d · 站点 main/photo/paint · 图片站 19/20/21century"
          % (len(records), len(stories)))
    print("统计：" + json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
