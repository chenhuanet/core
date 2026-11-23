# -*- coding: utf-8 -*-
"""Phase 1 预览构建：Markdown 内容 + 世纪图片清单 → 三个站点 + 图片站瀑布页。"""
import json
import os
import pathlib
import re
import shutil
import sys
import time
import hashlib
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
PUBLISH = os.environ.get("CHENHUA_PUBLISH") == "1"

I18N_DIR = CONTENT / "i18n"


def preview_url(target):
    """预览图在图片仓，不在站点仓；把 next/images/<century>/... 转为图片站 URL。"""
    target = str(target or "").replace("\\", "/").lstrip("/")
    if target.startswith("next/images/"):
        parts = target.split("/", 3)
        if len(parts) == 4 and parts[2]:
            return "https://%s.chenhua.net/%s" % (parts[2], parts[3])
    return "/" + target


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
CURATION_THEME_EN = {
    "信仰与图像": "Faith and Image",
    "山水与自然": "Landscape and Nature",
    "人物与自我": "Portrait and Self",
    "城市与日常": "City and Everyday Life",
    "文字与观看": "Word and Looking",
    "材料与技法": "Material and Technique",
}
STORY_AXES_PATH = CONTENT / "story-axes.json"
STORY_AXES = (json.loads(STORY_AXES_PATH.read_text(encoding="utf-8")).get("stories") or {}
               if STORY_AXES_PATH.exists() else {})
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
                "title": fm.get("title_zh") or fm.get("title") or rid,
                "year": fm.get("year"),
                "date_label": fm.get("date_label"),
                "era": fm.get("era"),
                "kind": fm.get("kind"),
                "theme": fm.get("theme"),
                "topic": fm.get("topic"),
                "curation_theme": fm.get("curation_theme"),
                "region": fm.get("region"),
                "medium": fm.get("medium"),
                "medium_detail": fm.get("medium_detail"),
                "period": fm.get("period"),
                "place": fm.get("place"),
                "china": fm.get("china"),
                "creator": fm.get("creator_zh") or fm.get("creator"),
                "creator_status": fm.get("creator_status"),
                "attribution_status": fm.get("attribution_status"),
                "version_status": fm.get("version_status"),
                "object_year": fm.get("object_year"),
                "year_basis": fm.get("year_basis"),
                "provenance_note": fm.get("provenance_note"),
                "image_credit": fm.get("image_credit"),
                "images": fm.get("images") or [],
                "movement": fm.get("movement") or "",
                "movement_en_raw": fm.get("movement_en") or "",
                "dimensions": fm.get("dimensions") or "",
                "dimensions_en_raw": fm.get("dimensions_en") or "",
                "holding": fm.get("holding") or "",
                "holding_en_raw": fm.get("holding_en") or "",
                "source": fm.get("source"),
                "source_short": fm.get("source_short"),
                "source_url": fm.get("source_url"),
                "page_url": fm.get("page_url"),
                "page_url_basis": fm.get("page_url_basis"),
                "fetched_at": fm.get("fetched_at"),
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
                "image_original_sha256": fm.get("image_original_sha256"),
                "image_width": fm.get("image_width"),
                "image_height": fm.get("image_height"),
                "image_alt_zh": fm.get("image_alt_zh"),
                "image_alt_en": fm.get("image_alt_en"),
                "image_credit_en": fm.get("image_credit_en"),
                "image_century": fm.get("image_century"),
                "preview_image": preview_url(preview["target"]) if preview else None,
                "preview_thumb_image": (
                    preview_url(preview.get("thumb_target"))
                    if preview and preview.get("thumb_target")
                    else (
                        preview_url(str(preview["target"]).replace(
                            "/images/%s/" % preview.get("century"), "/images/%s/thumbs/" % preview.get("century"), 1))
                        if preview and preview.get("target") else None
                    )
                ),
                "decade": preview["decade"] if preview else (
                    fm.get("period") if re.fullmatch(r"\d{4}s", str(fm.get("period") or "")) else ""),
                "search_text": " ".join(str(x) for x in [
                    fm.get("title_zh"), fm.get("title"), fm.get("title_en"), fm.get("year"), fm.get("date_label"), fm.get("place"),
                    fm.get("creator"), fm.get("movement"), fm.get("topic"), fm.get("theme"), fm.get("region"),
                    fm.get("medium"), fm.get("source_short"), note] if x).lower(),
            }
            tr = RECORD_I18N.get(rid, {}) or {}
            ue = USAGE_EN.get(u["code"], {})
            rec["title_en"] = tr.get("title") or fm.get("title_en") or (fm.get("title") if not re.search(r"[\u4e00-\u9fff]", str(fm.get("title") or "")) else rec["title"])
            rec["creator_en"] = tr.get("creator") or fm.get("creator_en") or creator_en(fm.get("creator"))
            rec["movement_en"] = tr.get("movement") or rec.get("movement_en_raw") or ""
            rec["dimensions_en"] = tr.get("dimensions") or rec.get("dimensions_en_raw") or rec.get("dimensions") or ""
            rec["holding_en"] = tr.get("holding") or rec.get("holding_en_raw") or ""
            rec["medium_en"] = tr.get("medium") or tx("medium", fm.get("medium"))
            rec["place_en"] = tr.get("place") or (TAXONOMY.get("place") or {}).get(fm.get("place")) or tx("region", fm.get("place"))
            rec["theme_en"] = tx("theme", fm.get("theme"))
            rec["curation_theme_en"] = CURATION_THEME_EN.get(fm.get("curation_theme"), fm.get("curation_theme") or "")
            rec["topic_en"] = tx("topic", fm.get("topic"))
            rec["region_en"] = tx("region", fm.get("region"))
            rec["kind_en"] = tx("kind", fm.get("kind"))
            rec["era_en"] = tx("era", fm.get("era"))
            rec["content_type_en"] = tx("content_type", rec["content_type"])
            rec["source_short_en"] = tx("source_short", fm.get("source_short"))
            rec["usage_label_en"] = ue.get("label") or u["label"]
            rec["usage_short_en"] = ue.get("short") or u["short"]
            rec["usage_desc_en"] = ue.get("desc") or u["desc"]
            rec["usage_obligation_en"] = ue.get("obligation") or u["obligation"]
            rec["usage_credit_en"] = ue.get("credit") or u["credit"]
            rec["note_en"] = fm.get("note_en") or tr.get("note") or note_en_for(rec, None)
            credit_parts = [rec["creator_en"], rec["source_short_en"],
                            license_en(fm.get("license"))]
            credit_parts = [p for i, p in enumerate(credit_parts)
                            if p and (i == 0 or p != credit_parts[i - 1])]
            rec["credit_line_en"] = " · ".join(credit_parts)
            rec["date_label_en"] = english_date(fm.get("date_label") or fm.get("year"))
            rec["search_text_en"] = " ".join(str(x) for x in [
                rec["title_en"], fm.get("year"), fm.get("date_label"), rec["place_en"],
                fm.get("creator"), rec["movement_en"], rec["topic_en"], rec["theme_en"], rec["region_en"],
                rec["medium_en"], rec["source_short_en"], rec["note_en"]] if x).lower()
            rows.append(rec)
    rows.sort(key=lambda r: (r["year"] or 0, r["title"]))
    dedup_path = CONTENT / "record-dedup.json"
    if dedup_path.exists():
        mapping = json.loads(dedup_path.read_text(encoding="utf-8")).get("duplicates") or {}
        by_id = {r["id"]: r for r in rows}
        for rid, cid in mapping.items():
            rec = by_id.get(rid)
            if rec and cid in by_id:
                rec["duplicate_of"] = cid
                rec["canonical_record"] = cid
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
            "themes": [x for x in (fm.get("themes") or []) if x != "历史"],
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
        ax = STORY_AXES.get(s["id"]) or {}
        if ax:
            s["series_key"] = ax.get("series_key") or ""
            s["series"] = ax.get("series") or ""
            s["series_en"] = ax.get("series_en") or s["series"]
            s["series_rank"] = int(ax.get("series_rank") or 0)
            s["axis_decade"] = ax.get("axis_decade") or ""
            s["axis_mmdd"] = ax.get("axis_mmdd") or ""
            s["axis_visibility"] = ax.get("axis_visibility") or {
                "calendar": bool(s["date"]), "timeline": bool(s["axis_decade"]), "theme": True}
            if not s["themes"]:
                s["themes"] = [s["series"]]
                s["themes_en"] = [s["series_en"]]
        else:
            s["series_key"] = ""
            s["series"] = ""
            s["series_en"] = ""
            s["series_rank"] = 0
            s["axis_decade"] = ""
            s["axis_mmdd"] = ""
            s["axis_visibility"] = {"calendar": False, "timeline": False, "theme": False}
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
    # Keep story covers as a curated set: reuse the same image only when the
    # story has no other usable frame.  This removes the "same cover on a dozen
    # date pages" effect without deleting any story.
    used_cover_images = set()
    for s in sorted(stories, key=lambda x: (x.get("date") or "9999-99-99", x["id"])):
        current = (by_id.get(s["cover"]) or {}).get("image") or ""
        if current and current in used_cover_images:
            for pid in s["photo_ids"]:
                img = (by_id.get(pid) or {}).get("image") or ""
                if img and img not in used_cover_images:
                    s["cover"] = pid
                    current = img
                    break
        if current:
            used_cover_images.add(current)
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
    path = DIST / "data" / "bundle.js"
    path.write_text(
        "window.CHENHUA_BUNDLE = %s;\n" % payload,
        encoding="utf-8", newline="\n")
    meta = {
        "file": "bundle.js",
        "records": len(records),
        "stories": len(stories),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    (DIST / "data" / "bundle.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")


# Fields the client shell actually reads.  Everything else (evidence, audit,
# image hashes, coordinates, rights internals) belongs to the build, not the
# browser.  Notes and search text are split into route-specific files below.
CLIENT_RECORD_FIELDS = {
    "id", "collection", "content_type", "isLink",
    "title", "title_en", "year", "date_label",
    "topic", "region", "place", "place_en",
    "creator", "movement", "movement_en",
    "source_short", "usage_code", "usage_short",
    "usage_short_en", "commercial_ok",
    "image", "preview_image", "themes", "themes_en",
}
CLIENT_STORY_FIELDS = {
    "id", "title", "title_en", "subtitle", "subtitle_en", "intro", "intro_en",
    "cover", "photo_ids", "date", "date_label", "status", "themes", "themes_en",
    "type", "type_en", "count",
}


def _write_js(path, name, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "window.%s = %s;\n" % (name, json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")),
        encoding="utf-8", newline="\n")


def write_client_bundle(site, cfg, records, stories, stats):
    """Write the lean per-site bundle plus route-specific note/search payloads.

    The canonical ``dist/data/bundle.js`` stays complete for the static builders;
    browsers get only the fields rendered by app.js.
    """
    collections = set(cfg.get("collections") or [])
    site_records = [r for r in records
                    if r.get("collection") in collections and not r.get("duplicate_of")]
    site_ids = {r["id"] for r in site_records}
    site_stories = [
        s for s in stories
        if any(i in site_ids for i in (s.get("photo_ids") or []))
    ]
    lean_records = [
        {k: v for k, v in r.items() if k in CLIENT_RECORD_FIELDS}
        for r in site_records
    ]
    lean_stories = [
        {k: v for k, v in s.items() if k in CLIENT_STORY_FIELDS}
        for s in site_stories
    ]
    lean = {"records": lean_records, "stories": lean_stories, "stats": stats}
    data_dir = DIST / site / "data"
    _write_js(data_dir / "client-bundle.js", "CHENHUA_BUNDLE", lean)

    notes = {}
    for r in site_records:
        note = {k: r.get(k) for k in ("note", "note_en", "note_html") if r.get(k)}
        if note:
            notes[r["id"]] = note
    _write_js(data_dir / "today-notes.js", "CHENHUA_TODAY_NOTES", notes)

    record_index = {}
    for r in site_records:
        record_index[r["id"]] = [r.get("search_text") or "", r.get("search_text_en") or ""]
    story_index = {}
    for s in site_stories:
        zh = [s.get("title") or "", s.get("subtitle") or "", s.get("intro") or ""]
        en = [s.get("title_en") or "", s.get("subtitle_en") or "", s.get("intro_en") or ""]
        for ch in (s.get("chapters") or []):
            zh += [ch.get("title") or "", ch.get("text") or ""]
            en += [ch.get("title_en") or "", ch.get("text_en") or ""]
        zh += list(s.get("themes") or [])
        en += list(s.get("themes_en") or [])
        story_index[s["id"]] = [" ".join(zh), " ".join(en)]
    _write_js(data_dir / "search-index.js", "CHENHUA_SEARCH_INDEX",
              {"records": record_index, "stories": story_index})
    client = data_dir / "client-bundle.js"
    meta = {
        "site": site,
        "file": "client-bundle.js",
        "records": len(lean_records),
        "stories": len(lean_stories),
        "notes": len(notes),
        "search_records": len(record_index),
        "search_stories": len(story_index),
        "bytes": client.stat().st_size,
        "sha256": hashlib.sha256(client.read_bytes()).hexdigest(),
    }
    (data_dir / "client-bundle.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")


DOMAINS = {
    "main": "https://chenhua.net",
    "photo": "https://photo.chenhua.net",
    "paint": "https://paint.chenhua.net",
}
ROUTE_META = {
    "today": ("%s", "历史上的今天：按日期浏览尘画收录的历史故事与影像。"),
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
    "about": ("About · %s", "Sources, licences and how Frame & Grain organises its images."),
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


def _nav_label(item, lang):
    return '<span data-l="%s">%s</span>' % (lang, html_escape(item[1 if lang == "zh" else 2]))


STATIC_HEAD_NAV = [
    ("https://chenhua.net/themes/", "主题", "Themes"),
    ("https://chenhua.net/timeline/", "时间线", "Timeline"),
    ("https://chenhua.net/today/calendar.html", "日历", "Calendar"),
    ("https://photo.chenhua.net/", "摄影", "Photography"),
    ("https://paint.chenhua.net/", "绘画", "Painting"),
    ("https://netcn.org/", "导航", "Directory"),
]
STATIC_FOOT_NAV = [
    ("https://chenhua.net/", "出尘入画", "Frame & Grain"),
    ("https://chenhua.net/images/", "图片库", "Image Library"),
    ("https://chenhua.net/themes/", "主题", "Themes"),
    ("https://chenhua.net/timeline/", "时间线", "Timeline"),
    ("https://chenhua.net/today/calendar.html", "日历", "Calendar"),
    ("https://photo.chenhua.net/", "摄影", "Photography"),
    ("https://paint.chenhua.net/", "绘画", "Painting"),
    ("https://netcn.org/", "导航", "Directory"),
]


def _static_nav(items):
    return "".join(
        '<a href="%s">%s%s</a>' % (
            html_escape(item[0]),
            _nav_label(item, "zh"), _nav_label(item, "en"),
        )
        for item in items
    )


def static_shell(cfg):
    """No-JS shell navigation; audit requires exactly one desknav and one sf-nav."""
    home = cfg.get("home") or "/"
    header = (
        '<header class="appbar static-appbar">'
        '<a class="brand" href="%s"><img class="leaf-mark brand-mark" '
        'src="/assets/leaf/surprised.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async">'
        '<span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span>'
        '<span class="wm-lite">入</span><span class="wm-strong">画</span></span>'
        '<span class="sub"><span data-l="zh">尘归尘，画归画</span>'
        '<span data-l="en">Image as history</span></span></a>'
        '<nav class="desknav" aria-label="站内导航">%s</nav>'
        '<div class="right"><button class="langbtn" type="button" data-lang-toggle '
        'aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button>'
        '<button class="iconbtn themebtn" type="button" data-themebtn aria-label="切换明暗">'
        '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
        'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
        '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg>'
        '</button></div></header>'
    ) % (html_escape(home), _static_nav(STATIC_HEAD_NAV))
    foot = (
        '<footer class="site-foot"><div class="sf-left"><span data-l="zh">尘归尘，画归画</span>'
        '<span data-l="en">Image as history</span></div>'
        '<nav class="sf-nav" aria-label="站内导航">%s</nav>'
        '<div class="sf-right"><a href="https://chenhua.net/legal/">'
        '<span data-l="zh">免责条款</span><span data-l="en">Disclaimer</span></a></div></footer>'
    ) % _static_nav(STATIC_FOOT_NAV)
    return (
        '<div class="static-splash">%s'
        '<main class="static-splash-main"><span data-l="zh">正在打开尘画</span>'
        '<span data-l="en">Opening Frame &amp; Grain</span></main>%s</div>'
    ) % (header, foot)


def write_site(site, cfg, records, stories, stats, build_id):
    out = DIST / site
    out.mkdir(parents=True, exist_ok=True)
    write_client_bundle(site, cfg, records, stories, stats)
    brand = cfg.get("brand") or "尘画"
    domain = DOMAINS[site]
    routes = ["today", "gallery", "stories", "search"]
    if site == "main":
        routes.insert(3, "timeline")
    for stale in ("about", "rights"):
        stale_dir = out / stale
        if stale_dir.exists():
            shutil.rmtree(stale_dir)
    site_ids = {r["id"] for r in records
                if r["collection"] in cfg["collections"] and not r.get("duplicate_of")}
    has_stories = any(site_ids.intersection(s.get("photo_ids") or []) for s in stories)
    def prefix_leaf(route):
        return ("../" if route == "today" else "../../") + "assets/leaf/"
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    for route in routes:
        root = route == "today"
        page_cfg = dict(cfg)
        page_cfg["leafBase"] = "/assets/leaf/" if PUBLISH else prefix_leaf(route)
        cfg_json = json.dumps(page_cfg, ensure_ascii=False).replace("</", "<\\/")
        title_tpl, desc_tpl = ROUTE_META[route]
        title = cfg["title"] if root else (title_tpl % brand)
        desc = cfg.get("desc") if root else desc_tpl
        title_en_tpl, desc_en_tpl = ROUTE_META_EN.get(route, ("%s", ""))
        brand_en = cfg.get("brand_en") or "Frame & Grain"
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
<body data-title-zh="搜索 · 尘画" data-title-en="Search · Frame & Grain">
<p><span data-l="zh">正在前往尘画统一搜索：<a href="%s">继续</a></span><span data-l="en">Redirecting to Frame & Grain search: <a href="%s">continue</a></span></p>
<script src="../../assets/site.js"></script>
</body>
</html>
""" % (canonical_target, target, target, target)
            folder = out / "search"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "index.html").write_text(redirect, encoding="utf-8", newline="\n")
            continue
        if site == "main" and route == "timeline":
            # The real timeline page is generated by build_atlas.py at /timeline/.
            continue
        if site == "main" and route == "stories":
            target = "../themes/index.html"
            canonical_target = domain + "/themes/"
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
<p><span data-l="zh">正在前往主题：<a href="%s">继续</a></span><span data-l="en">Redirecting to themes: <a href="%s">continue</a></span></p>
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
                 "timeline": "时间线", "about": "关于", "rights": "授权"}[r])
            for r in routes if r != "search")
        navlinks += ('<a href="%s">摄影</a><a href="%s">绘画</a>'
                     '<a href="https://netcn.org/">导航</a>') % (
                         cfg.get("photoBase") or "", cfg.get("paintBase") or "")
        noscript = ('<div class="seo-fallback"><h1>%s</h1><p>%s</p><nav>%s</nav></div>'
                    % (title, desc, navlinks))
        static_html = static_shell(cfg)
        extra_scripts = ""
        if route == "today":
            extra_scripts = ('<script src="%sdata/today-notes.js?v=%s"></script>'
                             % (prefix, build_id))
        elif route == "search":
            extra_scripts = ('<script src="%sdata/search-index.js?v=%s"></script>'
                             % (prefix, build_id))
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
<link rel="dns-prefetch" href="//pre19century.chenhua.net">
<link rel="dns-prefetch" href="//19century.chenhua.net">
<link rel="dns-prefetch" href="//20century.chenhua.net">
<link rel="dns-prefetch" href="//21century.chenhua.net">
<script>(function(){try{function ck(n){var m=document.cookie.match(new RegExp("(?:^|; )"+n+"=([^;]*)"));return m?decodeURIComponent(m[1]):""}var q=new URLSearchParams(location.search).get("lang");var l=q||ck("chenhua-lang")||localStorage.getItem("chenhua-lang")||"zh";if(l==="en"){document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en"}else{document.documentElement.setAttribute("data-lang","zh");document.documentElement.lang="zh-CN"}var t=ck("chenhua-theme")||localStorage.getItem("chenhua-theme");if(t!=="light"&&t!=="dark")t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}catch(e){}})();</script>
%s<link rel="stylesheet" href="%sassets/app.css?v=%s">
</head>
<body data-title-zh="%s" data-title-en="%s" data-desc-zh="%s" data-desc-en="%s">
<div id="app" aria-live="polite">%s</div>
<noscript>%s</noscript>
<script>window.SITE_CONFIG = %s;</script>
<script src="%sassets/i18n.js?v=%s"></script>
<script src="%sdata/client-bundle.js?v=%s"></script>
%s
<script src="%sassets/app.js?v=%s"></script>
<script src="%sassets/site.js?v=%s"></script>
</body>
</html>
""" % (html_escape(title, quote=True), html_escape(desc, quote=True), robots, canonical,
       canonical, canonical, canonical,
       prefix,
       html_escape(title, quote=True), html_escape(desc, quote=True), canonical, ld,
       prefix, build_id,
       html_escape(title, quote=True), html_escape(title_en or title, quote=True),
       html_escape(desc, quote=True), html_escape(desc_en or desc, quote=True),
       static_html, noscript, cfg_json,
       prefix, build_id, prefix, build_id, extra_scripts,
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
    labels = {
        "pre19century": ("19世纪前", "Pre-19th Century",
                         "1800 年以前的绘画、版画与素描。",
                         "Paintings, prints and drawings made before 1800."),
        "19century": ("19世纪", "19th Century",
                      "1800—1899 年的摄影、绘画与器物。",
                      "Photography, painting and objects, 1800–1899."),
        "20century": ("20世纪", "20th Century",
                      "1900—1999 年的摄影、绘画与器物。",
                      "Photography, painting and objects, 1900–1999."),
        "21century": ("21世纪", "21st Century",
                      "2000—2026 年的摄影与图像。",
                      "Photography and images, 2000–2026."),
    }
    for century in ("pre19century", "19century", "20century", "21century"):
        folder = IMAGES / century
        if not folder.exists():
            continue
        shutil.copy2(CORE / "gallery" / "gallery.css", folder / "gallery.css")
        shutil.copy2(CORE / "gallery" / "gallery.js", folder / "gallery.js")
        title, title_en, desc_zh, desc_en = labels[century]
        title_zh = "%s · 尘画图片索引" % title
        title_en = "%s · Frame & Grain Image Index" % title_en
        g_home = (
            '<a href="../../dist/main/"><span data-l="zh">出尘入画</span><span data-l="en"><span class="sf-brand-long">Frame &amp; Grain</span><span class="sf-brand-short">Frame</span></span></a>'
        )
        g_top_nav = (
            '<a href="../../dist/main/themes/"><span data-l="zh">主题</span><span data-l="en">Themes</span></a>'
            '<a href="../../dist/main/timeline/"><span data-l="zh">时间线</span><span data-l="en">Timeline</span></a>'
            '<a href="../../dist/main/today/calendar.html"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
            '<a href="../../dist/photo/"><span data-l="zh">摄影</span><span data-l="en">Photography</span></a>'
            '<a href="../../dist/paint/"><span data-l="zh">绘画</span><span data-l="en">Painting</span></a>'
            '<a href="https://netcn.org/"><span data-l="zh">导航</span><span data-l="en">Directory</span></a>'
        )
        g_foot_nav = (
            g_home +
            '<a href="../../dist/main/images/"><span data-l="zh">图片库</span><span data-l="en">Image Library</span></a>'
            '<a href="../../dist/main/themes/"><span data-l="zh">主题</span><span data-l="en">Themes</span></a>'
            '<a href="../../dist/main/timeline/"><span data-l="zh">时间线</span><span data-l="en">Timeline</span></a>'
            '<a href="../../dist/main/today/calendar.html"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
            '<a href="../../dist/photo/"><span data-l="zh">摄影</span><span data-l="en">Photography</span></a>'
            '<a href="../../dist/paint/"><span data-l="zh">绘画</span><span data-l="en">Painting</span></a>'
            '<a href="https://netcn.org/"><span data-l="zh">导航</span><span data-l="en">Directory</span></a>'
        )
        g_left = (
            '<div class="sf-left"><span data-l="zh">© 2026 尘画 · <a href="https://chenhua.net">chenhua.net</a></span>'
            '<span data-l="en">© 2026 <span class="sf-brand-long">Frame &amp; Grain</span><span class="sf-brand-short">Frame</span> · <a href="https://chenhua.net">chenhua.net</a></span></div>'
        )
        g_right = ('<div class="sf-right"><a href="../../dist/main/legal/">'
                   '<span data-l="zh">免责条款</span><span data-l="en">Disclaimer</span></a></div>')
        early_links = ""
        if century == "pre19century":
            items = [
                ("early-landscape-self", "山水与自我", "Landscape and the Self"),
                ("early-europe-faith", "信仰与图像", "Faith and Image"),
                ("early-other-tradition", "另一条传统", "Another Tradition"),
                ("early-word-scroll", "文字、长卷与观看", "Text, Scroll, and Looking"),
                ("early-material", "材料与技法", "Material and Method"),
                ("early-city-daily", "城市与日常", "City and Everyday Life"),
            ]
            early_links = '<div class="g-early"><p><span data-l="zh">六个展览 · 从作品进入 1800 年前的绘画</span><span data-l="en">Six exhibitions · enter painting before 1800 through works</span></p><div>%s</div></div>' % "".join(
                '<a href="https://paint.chenhua.net/history/exhibition-%s.html"><span data-l="zh">%s</span><span data-l="en">%s</span></a>' % (slug, zh, en)
                for slug, zh, en in items)
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
<link rel="icon" type="image/svg+xml" href="https://chenhua.net/assets/leaf/favicon.svg">
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
  <a class="g-brand" href="../../dist/main/"><img class="g-mark" src="https://chenhua.net/assets/leaf/curious.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="g-en"><span data-l="zh">尘归尘，画归画</span><span data-l="en">Image as history</span></span></a>
  <nav class="g-nav">
    {g_top_nav}
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
  {early_links}
  <div class="g-chips" id="gChips"></div>
  <div class="g-count" id="gCount">—</div>
  <div class="g-masonry" id="gMasonry"></div>
  <div class="g-more"><button id="gMore" type="button"><span data-l="zh">加载更多</span><span data-l="en">Load more</span></button></div>
</main>
<footer class="site-foot">
  {g_left}
  <nav class="sf-nav" aria-label="站内导航">{g_foot_nav}</nav>
  {g_right}
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
<script src="gallery.js?v={build_id}"></script>
</body>
</html>
"""
        (folder / "index.html").write_text(html, encoding="utf-8", newline="\n")
        theme_urls = ""
        if century == "pre19century":
            write_theme_pages(folder, build_id)
            theme_urls = "".join(
                '<url><loc>https://%s.chenhua.net/themes/%s/</loc></url>\n' % (century, slug)
                for slug, _, _, _, _ in THEME_PAGES)
        (folder / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '<url><loc>https://%s.chenhua.net/</loc></url>\n'
            '%s</urlset>\n' % (century, theme_urls),
            encoding="utf-8", newline="\n")
        (folder / "robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: https://%s.chenhua.net/sitemap.xml\n" % century,
            encoding="utf-8", newline="\n")


THEME_PAGES = [
    ("faith", "信仰与图像", "Faith and Image",
     "宗教图像、仪式空间与神圣叙事。", "Religious images, ritual space and sacred narrative."),
    ("landscape", "山水与自然", "Landscape and Nature",
     "山水、园林、地景与自然。", "Mountains, gardens, land and nature."),
    ("portrait", "人物与自我", "Portrait and Self",
     "肖像、供养人、身份与自我。", "Portraits, donors, identity and self."),
    ("city", "城市与日常", "City and Everyday Life",
     "市集、街巷、劳动、节庆与宫廷生活。", "Markets, streets, labour, festivals and court life."),
    ("word", "文字与观看", "Word and Looking",
     "长卷、题跋、手抄本与版画文字。", "Scrolls, inscriptions, manuscripts and printed words."),
    ("material", "材料与技法", "Material and Technique",
     "金箔、矿物颜料、壁画、绢本与版画线。", "Gold, mineral pigments, fresco, silk and print lines."),
]


def write_theme_pages(folder, build_id):
    for slug, zh, en, desc_zh, desc_en in THEME_PAGES:
        theme_dir = folder / "themes" / slug
        theme_dir.mkdir(parents=True, exist_ok=True)
        canonical = "https://%s.chenhua.net/themes/%s/" % (folder.name, slug)
        title_zh = "%s · 尘画图片索引" % zh
        title_en = "%s · Frame & Grain Image Index" % en
        top = (
            '<a href="https://chenhua.net/themes/"><span data-l="zh">主题</span><span data-l="en">Themes</span></a>'
            '<a href="https://chenhua.net/timeline/"><span data-l="zh">时间线</span><span data-l="en">Timeline</span></a>'
            '<a href="https://chenhua.net/today/calendar.html"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
            '<a href="https://photo.chenhua.net/"><span data-l="zh">摄影</span><span data-l="en">Photography</span></a>'
            '<a href="https://paint.chenhua.net/"><span data-l="zh">绘画</span><span data-l="en">Painting</span></a>'
            '<a href="https://netcn.org/"><span data-l="zh">导航</span><span data-l="en">Directory</span></a>'
        )
        foot = (
            '<a href="https://chenhua.net/"><span data-l="zh">出尘入画</span><span data-l="en">Frame &amp; Grain</span></a>'
            '<a href="https://chenhua.net/images/"><span data-l="zh">图片库</span><span data-l="en">Image Library</span></a>'
            '<a href="https://chenhua.net/themes/"><span data-l="zh">主题</span><span data-l="en">Themes</span></a>'
            '<a href="https://chenhua.net/timeline/"><span data-l="zh">时间线</span><span data-l="en">Timeline</span></a>'
            '<a href="https://chenhua.net/today/calendar.html"><span data-l="zh">日历</span><span data-l="en">Calendar</span></a>'
            '<a href="https://photo.chenhua.net/"><span data-l="zh">摄影</span><span data-l="en">Photography</span></a>'
            '<a href="https://paint.chenhua.net/"><span data-l="zh">绘画</span><span data-l="en">Painting</span></a>'
        )
        cfg = {
            "century": folder.name,
            "photoBase": "https://photo.chenhua.net/",
            "paintBase": "https://paint.chenhua.net/",
            "photoStaticBase": "https://photo.chenhua.net/photo/",
            "paintStaticBase": "https://paint.chenhua.net/painting/",
            "mainBase": "https://chenhua.net/",
            "preview": False,
            "manifestBase": "../../",
            "filters": {"theme": zh},
        }
        html = f"""<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<meta name="description" content="{html_escape(desc_zh, quote=True)}">
<title>{html_escape(title_zh)}</title>
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="zh-CN" href="{canonical}">
<link rel="alternate" hreflang="en" href="{canonical}?lang=en">
<link rel="icon" type="image/svg+xml" href="https://chenhua.net/assets/leaf/favicon.svg">
<link rel="stylesheet" href="../../gallery.css?v={build_id}">
<script>
(function(){{try{{var q=new URLSearchParams(location.search).get("lang");var l=q||localStorage.getItem("chenhua-lang");if(l==="en"){{document.documentElement.setAttribute("data-lang","en");
document.documentElement.setAttribute("lang","en");}}
var t=localStorage.getItem("chenhua-theme");if(!t&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)t="light";if(t==="light"){{document.documentElement.setAttribute("data-theme","light");}}}}catch(e){{}}}})();
</script>
</head>
<body data-title-zh="{html_escape(title_zh, quote=True)}" data-title-en="{html_escape(title_en, quote=True)}">
<header class="g-head">
  <a class="g-brand" href="https://chenhua.net/"><img class="g-mark" src="https://chenhua.net/assets/leaf/curious.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="g-en"><span data-l="zh">尘归尘，画归画</span><span data-l="en">Image as history</span></span></a>
  <nav class="g-nav">{top}</nav>
  <div class="g-tools">
    <button class="g-tool g-lang" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button>
    <button class="g-tool" type="button" data-themebtn aria-label="切换到浅色"><span class="icon-sun">☀</span><span class="icon-moon">☾</span></button>
  </div>
</header>
<main class="g-wrap">
  <div class="g-intro"><h1>{html_escape(zh)}</h1>
    <p><span data-l="zh">{html_escape(desc_zh)}</span><span data-l="en">{html_escape(desc_en)}</span></p>
  </div>
  <div class="g-chips" id="gChips"></div>
  <div class="g-count" id="gCount">—</div>
  <div class="g-masonry" id="gMasonry"></div>
  <div class="g-more"><button id="gMore" type="button"><span data-l="zh">加载更多</span><span data-l="en">Load more</span></button></div>
</main>
<footer class="site-foot">
  <div class="sf-left"><span data-l="zh">© 2026 尘画 · <a href="https://chenhua.net">chenhua.net</a></span><span data-l="en">© 2026 Frame &amp; Grain · <a href="https://chenhua.net">chenhua.net</a></span></div>
  <nav class="sf-nav" aria-label="站内导航">{foot}</nav>
  <div class="sf-right"><a href="https://chenhua.net/legal/"><span data-l="zh">免责条款</span><span data-l="en">Disclaimer</span></a></div>
</footer>
<script>window.GALLERY_CONFIG = {json.dumps(cfg, ensure_ascii=False)};</script>
<script src="../../gallery.js?v={build_id}"></script>
</body>
</html>
"""
        (theme_dir / "index.html").write_text(html, encoding="utf-8", newline="\n")


def write_404(build_id):
    out = DIST / "main" / "404.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    nav_links = "".join('<a href="%s"><span data-l="zh">%s</span><span data-l="en">%s</span></a>' % (h, z, e)
                       for z, e, h in [
                           ("尘画", "Frame & Grain", "/"),
                           ("主题", "Themes", "/themes/"),
                           ("时间线", "Timeline", "/timeline/"),
                           ("日历", "Calendar", "/today/calendar.html"),
                           ("摄影", "Photography", "https://photo.chenhua.net/"),
                           ("绘画", "Painting", "https://paint.chenhua.net/"),
                           ("导航", "Directory", "https://netcn.org/"),
                       ])
    foot_nav_links = nav_links.replace(
        '<span data-l="zh">尘画</span><span data-l="en">Frame & Grain</span>',
        '<span data-l="zh">出尘入画</span><span data-l="en"><span class="sf-brand-long">Frame &amp; Grain</span><span class="sf-brand-short">Frame</span></span>'
    ).replace(
        '<span data-l="zh">历史上的今天</span>',
        '<span data-l="zh">日历</span>'
    ).replace(
        '<span data-l="en">On This Day</span>',
        '<span data-l="en">Calendar</span>'
    )
    foot_left = (
        '<div class="sf-left"><span data-l="zh">© 2026 尘画 · <a href="https://chenhua.net">chenhua.net</a></span>'
        '<span data-l="en">© 2026 <span class="sf-brand-long">Frame &amp; Grain</span><span class="sf-brand-short">Frame</span> · <a href="https://chenhua.net">chenhua.net</a></span></div>'
    )
    html = """<!doctype html>
<html lang="zh-CN" data-theme="dark" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0c0b">
<title>页面不存在 · 尘画</title>
<meta name="robots" content="noindex,follow">
<link rel="icon" type="image/svg+xml" href="/assets/leaf/favicon.svg">
<link rel="stylesheet" href="/assets/app.css?v=%s">
<link rel="stylesheet" href="/assets/static.css?v=%s">
<script>(function(){try{function ck(n){var m=document.cookie.match(new RegExp("(?:^|; )"+n+"=([^;]*)"));return m?decodeURIComponent(m[1]):""}var q=new URLSearchParams(location.search).get("lang");var l=q||ck("chenhua-lang")||localStorage.getItem("chenhua-lang")||"zh";if(l==="en"){document.documentElement.setAttribute("data-lang","en");document.documentElement.lang="en"}else{document.documentElement.setAttribute("data-lang","zh");document.documentElement.lang="zh-CN"}var t=ck("chenhua-theme")||localStorage.getItem("chenhua-theme");if(t!=="light"&&t!=="dark")t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}catch(e){}})();</script>
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
<body class="static-body" data-title-zh="页面不存在 · 尘画" data-title-en="Page not found · Frame & Grain">
<div class="s-shell">
<header class="appbar s-appbar">
<a class="brand" href="/"><img class="leaf-mark brand-mark" src="/assets/leaf/surprised.svg" width="30" height="30" alt="" aria-hidden="true" decoding="async"><span class="wm"><span class="wm-lite">出</span><span class="wm-strong">尘</span><span class="wm-lite">入</span><span class="wm-strong">画</span></span><span class="sub"><span data-l="zh">尘归尘，画归画</span><span data-l="en">Image as history</span></span></a>
<nav class="desknav">%s</nav>
<div class="right"><button class="langbtn" type="button" data-lang-toggle aria-label="切换到英文"><span data-l="zh">EN</span><span data-l="en">中文</span></button><button class="iconbtn themebtn" type="button" data-themebtn aria-label="切换明暗"><svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg></button></div>
</header>
<main class="notfound">
<div class="big">404</div>
<div class="empty empty-leaf"><img class="leaf-mark empty-mark" src="/assets/leaf/surprised.svg" width="120" height="120" alt="" aria-hidden="true" decoding="async"><b><span data-l="zh">页面不存在</span><span data-l="en">Page not found</span></b><p><span data-l="zh">地址可能已变更，或页面尚未收录。</span><span data-l="en">The address may have changed, or the page is not here.</span></p></div>
<div><a class="btn gold" href="/"><span data-l="zh">返回首页</span><span data-l="en">Back home</span></a><a class="btn" href="/themes/"><span data-l="zh">浏览主题</span><span data-l="en">Browse themes</span></a></div>
</main>
</div>
<footer class="site-foot">
%s
<nav class="sf-nav" aria-label="站内导航">%s</nav>
<div class="sf-right"><a href="/legal/"><span data-l="zh">免责条款</span><span data-l="en">Disclaimer</span></a></div>
</footer>
<script src="/assets/site.js?v=%s"></script>
</body></html>
""" % (build_id, build_id, nav_links, foot_left, foot_nav_links, build_id)
    out.write_text(html, encoding="utf-8", newline="\n")


def main():
    build_id = "20261123c"
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

    if PUBLISH:
        base = {
            "main": "https://chenhua.net/", "photo": "https://photo.chenhua.net/",
            "paint": "https://paint.chenhua.net/",
        }
        leaf_base = "/assets/leaf/"
    else:
        base = {
            "main": "/next/dist/main/", "photo": "/next/dist/photo/",
            "paint": "/next/dist/paint/",
        }
        leaf_base = "/next/dist/assets/leaf/"

    def site_nav(site):
        themes = base["main"] + "themes/"
        timeline = base["main"] + "timeline/"
        calendar = base["main"] + "today/calendar.html"
        return [
            {"label": "尘画", "label_en": "Frame & Grain", "href": base["main"], "icon": "home", "site": "main"},
            {"label": "主题", "label_en": "Themes", "href": themes, "icon": "stories", "site": "main"},
            {"label": "时间线", "label_en": "Timeline", "href": timeline, "icon": "timeline", "site": "main"},
            {"label": "日历", "label_en": "Calendar", "href": calendar, "icon": "timeline", "site": "main"},
            {"label": "摄影", "label_en": "Photography", "href": base["photo"], "icon": "photo", "site": "photo"},
            {"label": "绘画", "label_en": "Painting", "href": base["paint"], "icon": "paint", "site": "paint"},
            {"label": "导航", "label_en": "Directory", "href": "https://netcn.org/", "icon": "compass", "site": "netcn"},
        ]
    common = {"home": base["main"], "photoBase": base["photo"],
              "paintBase": base["paint"], "taxonomy": TAXONOMY,
              "leafBase": leaf_base}
    static_base = {}
    if PUBLISH:
        static_base = {
            "base": "/",
            "staticPhotoBase": "https://photo.chenhua.net/photo/",
            "staticPaintBase": "https://paint.chenhua.net/painting/",
            "staticStoryBase": "https://chenhua.net/story/",
        }
    main_cfg = {
        "site": "main", "title": "尘画 · 出尘入画", "brand": "尘画", "brand_en": "Frame & Grain",
        "title_en": "Frame & Grain · Out of dust, into the image",
        "sub": "尘归尘，画归画", "sub_en": "Image as history",
        "desc": "尘画：历史摄影与绘画图录。",
        "desc_en": "Frame & Grain: an archive of historical photography and painting.",
        "collections": ["photos", "paintings", "links"],
        "base": base["main"], "nav": site_nav("main"), **common, **static_base,
    }
    photo_cfg = {
        "site": "photo", "title": "尘画 · 摄影", "brand": "尘画", "brand_en": "Frame & Grain",
        "title_en": "Frame & Grain · Photography",
        "sub": "尘归尘，画归画", "sub_en": "Image as history",
        "desc": "尘画摄影：历史摄影图录。",
        "desc_en": "Frame & Grain Photography: an archive of historical photographs.",
        "collections": ["photos", "links"],
        "base": base["photo"], "nav": site_nav("photo"), **common, **static_base,
    }
    paint_cfg = {
        "site": "paint", "title": "尘画 · 绘画", "brand": "尘画", "brand_en": "Frame & Grain",
        "title_en": "Frame & Grain · Painting",
        "sub": "尘归尘，画归画", "sub_en": "Image as history",
        "desc": "尘画绘画：绘画与版画图录。",
        "desc_en": "Frame & Grain Painting: an archive of paintings and prints.",
        "collections": ["paintings"],
        "base": base["paint"], "nav": site_nav("paint"), **common, **static_base,
    }
    write_i18n_assets()
    write_bundle(records, stories, stats)
    write_site("main", main_cfg, records, stories, stats, build_id)
    write_site("photo", photo_cfg, records, stories, stats, build_id)
    write_site("paint", paint_cfg, records, stories, stats, build_id)
    write_404(build_id)
    write_galleries(build_id)

    print("预览构建完成：records %d · stories %d · 站点 main/photo/paint · 图片站 pre19/19/20/21century"
          % (len(records), len(stories)))
    print("统计：" + json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
