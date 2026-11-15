# -*- coding: utf-8 -*-
"""Phase 1.5 内容整理：把已采内容迁移为干净的 Markdown 内容仓。

原则：
  - 不删除记录，不改许可、证据、审计字段。
  - 只做可证实的类型分流与文案清理；不确定的标记 needs_review。
  - 33 条人工精策展文案保留；自动批次改成中性档案体。
  - 照片 / 绘画与版画 / 器物与文书 / 仅外链 四个 collection。
"""
import hashlib
import json
import pathlib
import re
import shutil
import sys
from collections import Counter, defaultdict

import yaml
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
import usage  # noqa: E402  (next/tools/usage.py)

SRC = ROOT / "archive" / "legacy-content"
OUT = ROOT / "next" / "content"
PREVIEW = ROOT / "next" / "preview-images.json"
REPORT = ROOT / "next" / "CONTENT-CLEANUP.md"

PHOTO_PROCESSES = {"银版", "锡版", "盐纸", "蛋白印相"}
PAINT_RX = re.compile(
    r"oil on (canvas|panel|board)|watercolou?r|gouache|\btempera\b|\bpastel\b|\bfresco\b|\bmural\b",
    re.I)
PRINT_RX = re.compile(
    r"etching on (paper|wove paper)|\betching\b|\bengraving\b|\blithograph\b|"
    r"\bwoodcut\b|\bmezzotint\b|\baquatint\b|\bdrypoint\b", re.I)
POSTCARD_RX = re.compile(
    r"\bpostcard\b|\bpost card\b|photomechanical print \(postcard\)|"
    r"picture postcard|scanned postcard|postcard print|明信片", re.I)
PHOTOCHROM_RX = re.compile(r"photochrom", re.I)
PHOTOMECH_RX = re.compile(r"photomechanical print", re.I)
STILL_RX = re.compile(r"still life|still-life", re.I)
PORTRAIT_RX = re.compile(r"portrait|self-portrait|self portrait", re.I)

# 只收“源站描述/题名能直接支撑”的条目；其余保持照片，或标 needs_review。
OVERRIDES = {
    "auto-d49e9fd0": dict(collection="paintings", content_type="painting", medium="绘画",
                          topic="痕迹", review="clean",
                          evidence="题名 Still Life；作者 Raphaelle Peale 为画家；源站文件页"),
    "auto-27bcc7d5": dict(collection="paintings", content_type="painting", medium="绘画",
                          topic="痕迹", review="clean",
                          evidence="题名 Still Life；作者 Camille Pissarro 为画家；源站文件页"),
    "auto-256d170f": dict(collection="paintings", content_type="painting", medium="油画",
                          topic="痕迹", review="clean",
                          evidence="源站描述：oil on canvas"),
    "auto-d713ad77": dict(collection="paintings", content_type="painting", medium="油画",
                          topic="街巷", review="clean",
                          evidence="源站描述：Oil on canvas"),
    "auto-2df8ce6f": dict(collection="paintings", content_type="painting", medium="绘画",
                          topic="面孔", review="needs_review",
                          evidence="题名 Portrait of a Boy；作者 George Benjamin Luks 为画家；画种待核",
                          note="题名与作者指向绘画；源站未直接写出画种，标为待核。"),
    "auto-9afb2e56": dict(collection="paintings", content_type="print", medium="版画",
                          topic="面孔", review="clean",
                          evidence="源站描述：Etching on wove paper"),
    "auto-dd7aafa6": dict(collection="paintings", content_type="print", medium="版画",
                          topic="街巷", review="clean",
                          evidence="源站描述：Etching on paper"),
    "auto-c6739d13": dict(collection="paintings", content_type="painting", medium="水彩",
                          topic="劳作", review="clean",
                          evidence="源站描述：Watercolour"),
    "auto-06443e0e": dict(collection="objects", content_type="object", medium="器物",
                          topic="痕迹", review="clean",
                          evidence="题名与描述：pictorial Isfahan rug"),
    "auto-b21888a0": dict(collection="objects", content_type="object", medium="器物",
                          topic="痕迹", review="clean",
                          evidence="题名与描述：Kashan pictorial rug"),
    "auto-4993fdb8": dict(collection="objects", content_type="object", medium="器物",
                          topic="痕迹", review="clean",
                          evidence="题名：Ceylon telegraph stamp"),
    "auto-69cf0522": dict(collection="objects", content_type="object", medium="器物",
                          topic="痕迹", review="clean",
                          evidence="题名：10 cents - British Ceylon - Silver；按钱币/器物处理"),
    "auto-5aef6dca": dict(collection="objects", content_type="document", medium="文书",
                          topic="痕迹", review="needs_review",
                          evidence="题名：Photostat copy of letter signed Jas. B. Eads",
                          note="与 auto-dc10d302 题名相同，待核是否重复。"),
    "auto-768ea122": dict(collection="photos", content_type="photograph", medium="航天影像",
                          topic="远方", review="needs_review",
                          evidence="NASA/JPL 影像；画面为旅行者金唱片上的蚀刻细节",
                          note="画面主体是金唱片蚀刻细节，作为航天影像保留，类型待核。"),
    "cle-d745b7a4": dict(collection="photos", content_type="photograph", medium="纪实照片",
                         topic="劳作", review="clean",
                         evidence="原 medium 为航天影像，但年代 1886、作者 Peter Henry Emerson 为摄影家；改回纪实照片"),
    "cle-d278a949": dict(collection="photos", content_type="photograph", medium="纪实照片",
                         topic="风景", review="clean",
                         evidence="原 medium 为航天影像，但年代 1891、作者 Peter Henry Emerson 为摄影家；改回纪实照片"),
}


def century_of(year):
    if year is None:
        return "undated"
    if year < 1900:
        return "19century"
    if year < 2000:
        return "20century"
    return "21century"


def decade_of(rec):
    p = str(rec.get("period") or "")
    if re.fullmatch(r"\d{4}s", p):
        return p
    y = rec.get("year")
    if isinstance(y, int):
        return "%ds" % (y // 10 * 10)
    return "undated"


def archive_rel(rel):
    rel = str(rel or "").replace("\\", "/")
    if rel.startswith("content/"):
        return ROOT / "archive" / "legacy-content" / rel[len("content/"):]
    if rel.startswith("assets/"):
        return ROOT / "archive" / "originals" / rel
    return ROOT / rel


def note_of(rec):
    p = archive_rel(rec.get("note_file"))
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def image_info(rec):
    local = rec.get("local_image")
    p = archive_rel(local) if local else None
    if not p or not p.exists():
        return None
    ext = p.suffix.lower()
    sha = rec.get("image_sha256")
    if not sha:
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        with Image.open(p) as im:
            w, h = im.size
    except Exception:
        w = h = None
    return {
        "path": p, "ext": ext, "sha256": sha, "sha8": sha[:8],
        "bytes": p.stat().st_size, "width": w, "height": h,
    }


def evidence_text(rec):
    return " ".join(str(x) for x in [
        rec.get("title"), (rec.get("license_snapshot") or {}).get("description"),
        rec.get("creator"), rec.get("source_short"), rec.get("source")] if x)


def classify(rec):
    """返回 collection / content_type / medium / topic / evidence / review / note。"""
    rid = rec.get("id")
    text = evidence_text(rec)
    medium = rec.get("medium")
    topic = rec.get("topic")
    collection, content_type = "photos", "photograph"
    evidence = "原分类为摄影影像"
    review, note = "clean", ""

    # 33 条人工精策展是站点骨架：保留在 photos，不因 medium 是纸品/官方档案就移走。
    if "curation" not in rec:
        content_type = "photograph"
        evidence = "人工精策展；保留照片 collection"
        if POSTCARD_RX.search(text):
            content_type, medium = "postcard", "明信片"
            evidence = "人工精策展；题名/描述为明信片"
        elif re.search(r"v-?mail|信纸|letters?", text, re.I):
            content_type = "document"
            evidence = "人工精策展；题名/描述为信纸或文书"
        return "photos", content_type, medium, topic, evidence, "clean", ""

    if rid in OVERRIDES:
        o = OVERRIDES[rid]
        collection = o["collection"]
        content_type = o["content_type"]
        medium = o["medium"]
        topic = o["topic"]
        review = o["review"]
        evidence = o["evidence"]
        note = o.get("note", "")
        return collection, content_type, medium, topic, evidence, review, note

    if medium == "纸品实物":
        collection, content_type, medium, topic = "objects", "object", "纸品实物", "痕迹"
        evidence = "原分类 medium: 纸品实物"
        if POSTCARD_RX.search(text):
            content_type, medium = "postcard", "明信片"
            evidence = "原分类为纸品实物；源站描述为明信片"
            review = "clean"
    elif medium == "官方档案":
        # 「官方档案」是影像来源，不是文书实体；保留在 photos。
        content_type, medium = "photograph", "官方档案"
        evidence = "原分类 medium: 官方档案（机构/军方/任务档案影像）"
    elif medium == "航天影像" and (rec.get("year") or 0) < 1900:
        content_type, medium = "photograph", "纪实照片"
        evidence = "原分类为航天影像，但年代早于航天时代；按摄影影像处理"
        review = "needs_review"
    elif PAINT_RX.search(text):
        collection, content_type = "paintings", "painting"
        if re.search(r"oil on", text, re.I):
            medium = "油画"
        elif re.search(r"watercolou?r", text, re.I):
            medium = "水彩"
        else:
            medium = "绘画"
        topic = "痕迹" if STILL_RX.search(text) else ("面孔" if PORTRAIT_RX.search(text) else topic)
        evidence = "源站描述含绘画工艺词：" + (PAINT_RX.search(text).group(0) if PAINT_RX.search(text) else "")
    elif PRINT_RX.search(text):
        collection, content_type, medium = "paintings", "print", "版画"
        topic = "面孔" if PORTRAIT_RX.search(text) else topic
        evidence = "源站描述含版画工艺词：" + (PRINT_RX.search(text).group(0) if PRINT_RX.search(text) else "")
    elif POSTCARD_RX.search(text):
        content_type, medium = "postcard", "明信片"
        evidence = "源站描述/题名：明信片或照相印刷"
    elif PHOTOCHROM_RX.search(text):
        content_type, medium = "print", "彩色印刷"
        evidence = "来源/描述：Photochrom 彩色印刷"
    elif PHOTOMECH_RX.search(text):
        content_type, medium = "print", "印刷品"
        evidence = "源站描述：Photomechanical print"

    if collection in ("paintings", "objects") and STILL_RX.search(text):
        topic = "痕迹"
    return collection, content_type, medium, topic, evidence, review, note


def type_sentence(content_type, medium):
    m = str(medium or "")
    if content_type == "photograph":
        if m in PHOTO_PROCESSES:
            return "这是一张%s照片。" % m
        if m == "航天影像":
            return "这是一张航天影像。"
        return "这是一张摄影影像。"
    if content_type == "painting":
        return "这是一幅%s作品。" % (m or "绘画")
    if content_type == "print":
        return "这是一幅%s。" % (m or "印刷品")
    if content_type == "postcard":
        return "这是一张明信片。"
    if content_type == "object":
        return "这是一件%s。" % (m or "器物")
    if content_type == "document":
        return "这是一份文书。"
    return ""


def generated_note(rec, content_type, medium, review_note=""):
    date = rec.get("date_label") or rec.get("year") or "年代不详"
    place = rec.get("place") or rec.get("region") or "跨地域"
    creator = rec.get("creator") or "作者不详（源站未著录）"
    source = rec.get("source_short") or rec.get("source") or "来源不详"
    catalog = (rec.get("evidence") or {}).get("catalog_id") or ""
    catalog_s = "，馆藏编号 %s" % catalog if catalog else ""
    s = "%s，%s。%s；来源：%s%s。%s" % (
        date, place, creator, source, catalog_s, type_sentence(content_type, medium))
    if review_note:
        s += "（%s）" % review_note
    return s


THEME_OF_TOPIC = {
    "面孔": "人间", "街巷": "人间", "劳作": "人间",
    "战火": "世事", "灾变": "世事", "权利": "世事",
    "远方": "天地", "风景": "天地",
    "痕迹": "技艺", "馆藏": "技艺",
}


def build_record(rec, original_collection):
    if original_collection == "links":
        collection, content_type, medium, topic = "links", "link", "无图外链", "馆藏"
        evidence, review, review_note = "仅外链卡", "clean", ""
    else:
        collection, content_type, medium, topic, evidence, review, review_note = classify(rec)
    info = image_info(rec)
    decade = decade_of(rec)
    century = century_of(rec.get("year"))
    u = usage.describe(rec.get("tier"), rec.get("rights_status"))
    d = {
        "id": rec.get("id"),
        "collection": collection,
        "content_type": content_type,
        "type_evidence": evidence,
        "review_status": review,
        "title": rec.get("title"),
        "year": rec.get("year"),
        "date_label": rec.get("date_label"),
        "era": rec.get("era"),
        "kind": rec.get("kind"),
        "theme": THEME_OF_TOPIC.get(topic, rec.get("theme")),
        "topic": topic,
        "region": rec.get("region"),
        "medium": medium,
        "period": rec.get("period"),
        "place": rec.get("place"),
        "china": rec.get("china"),
        "creator": rec.get("creator"),
        "creator_status": rec.get("creator_status"),
        "source": rec.get("source"),
        "source_short": rec.get("source_short"),
        "source_url": rec.get("source_url"),
        "page_url": rec.get("page_url"),
        "page_url_basis": rec.get("page_url_basis"),
        "license": rec.get("license"),
        "license_raw": rec.get("license_raw"),
        "license_url": rec.get("license_url"),
        "tier": rec.get("tier"),
        "rights_status": rec.get("rights_status"),
        "commercial_ok": rec.get("commercial_ok"),
        "usage_code": u["code"],
        "fetched_at": rec.get("fetched_at"),
        "upstream": rec.get("upstream"),
        "classification": rec.get("classification"),
        "license_snapshot": rec.get("license_snapshot"),
        "evidence": rec.get("evidence"),
        "audit": rec.get("audit"),
    }
    if review_note:
        d["review_note"] = review_note
    if original_collection == "links":
        d["isLink"] = True
    elif info:
        d.update({
            "image": "https://%s.chenhua.net/%s/%s/%s-%s%s" % (
                century, collection, decade, d["id"], info["sha8"], info["ext"]),
            "source_image": rec.get("image"),
            "image_sha256": info["sha256"],
            "image_width": info["width"],
            "image_height": info["height"],
            "image_bytes": info["bytes"],
            "image_century": century,
            "image_repo": century,
        })
    else:
        d.update({
            "image": None,
            "source_image": rec.get("image"),
            "image_sha256": rec.get("image_sha256"),
            "image_century": century,
            "image_repo": century,
        })
    # 文案：33 条人工精策展 + 外链保留原文；自动批次改成中性档案体
    curated = "curation" not in rec
    if curated or original_collection == "links":
        body_note = note_of(rec)
    else:
        body_note = generated_note(rec, content_type, medium, review_note)
    return d, info, decade, century, u, body_note, curated


def yaml_frontmatter(d):
    return "---\n" + yaml.safe_dump(
        d, allow_unicode=True, sort_keys=False, default_flow_style=False
    ) + "---\n"


def write_readme(collection, rows, preview, decade_counts):
    names = {
        "photos": "照片", "paintings": "绘画与版画",
        "objects": "器物与文书", "links": "仅外链",
    }
    types = Counter(r["content_type"] for r in rows)
    title = "# %s\n\n" % names[collection]
    lines = [title.strip(), "",
             "共 **%d** 条。" % len(rows), "",
             "| 类型 | 数量 |", "| --- | --- |"]
    for k, v in types.most_common():
        lines.append("| %s | %d |" % (k, v))
    lines += ["", "## 按年代", "", "| 年代 | 数量 | 目录 |", "| --- | --- | --- |"]
    for dec in sorted(decade_counts):
        lines.append("| %s | %d | [%s/](%s/) |" % (dec, decade_counts[dec], dec, dec))
    lines += ["", "> 类型与文案清理规则见 [`../CONTENT-CLEANUP.md`](../CONTENT-CLEANUP.md)。", ""]
    (OUT / collection / "README.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n")


def main():
    photos = [json.loads(p.read_text(encoding="utf-8"))
              for p in sorted((SRC / "photos").glob("*.json"))]
    links = [json.loads(p.read_text(encoding="utf-8"))
             for p in sorted((SRC / "links").glob("*.json"))]

    # 清空生成的 collection 目录，保留 stories/schema/README
    for c in ("photos", "paintings", "objects", "links"):
        p = OUT / c
        if p.exists():
            shutil.rmtree(p)

    preview = {}
    all_rows = []
    missing = []
    moves = []
    flags = []
    type_counts = Counter()
    collection_counts = Counter()
    century_counts = Counter()
    decade_counts = defaultdict(Counter)

    for original_collection, records in (("photos", photos), ("links", links)):
        for rec in records:
            d, info, decade, century, u, body_note, curated = build_record(rec, original_collection)
            collection = d["collection"]
            folder = OUT / collection / decade
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / ("%s.md" % d["id"])
            body_parts = []
            if collection != "links" and d.get("image"):
                body_parts.append("![%s](%s)" % (d["title"], d["image"]))
            if body_note:
                body_parts.append(body_note)
            target.write_text(yaml_frontmatter(d) + "\n" + "\n\n".join(body_parts).strip() + "\n",
                              encoding="utf-8", newline="\n")
            if collection != "links" and info:
                preview[d["id"]] = {
                    "collection": collection,
                    "century": century,
                    "decade": decade,
                    "source": str(info["path"].relative_to(ROOT)).replace("\\", "/"),
                    "target": "next/images/%s/%s/%s/%s-%s%s" % (
                        century, collection, decade, d["id"], info["sha8"], info["ext"]),
                    "sha256": info["sha256"],
                    "bytes": info["bytes"],
                    "width": info["width"],
                    "height": info["height"],
                }
            elif collection != "links":
                missing.append(d["id"])
            all_rows.append(d)
            type_counts[d["content_type"]] += 1
            collection_counts[collection] += 1
            century_counts[century] += 1
            decade_counts[collection][decade] += 1
            if collection != original_collection:
                moves.append((d["id"], d["title"], original_collection, collection,
                              d["content_type"], d["type_evidence"]))
            if d["review_status"] != "clean":
                flags.append((d["id"], d["title"], d["content_type"], d["review_status"],
                              d.get("review_note", "")))

    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=1),
                       encoding="utf-8", newline="\n")

    # 根 README
    lines = [
        "# 尘画 · 内容仓",
        "",
        "> `historical-photography-and-painting` · 以图为史，记录人间的大事与小事。",
        "",
        "本仓是尘画的唯一事实源。站点与世纪图片仓都从这里的 Markdown 派生。",
        "",
        "## 当前内容",
        "",
        "| collection | 数量 | 说明 |",
        "| --- | --- | --- |",
        "| photos | %d | 摄影影像，含照片印相与以摄影为载体的明信片 |" % collection_counts["photos"],
        "| paintings | %d | 绘画与艺术版画 |" % collection_counts["paintings"],
        "| objects | %d | 器物、文书等非影像载体 |" % collection_counts["objects"],
        "| links | %d | 仅外链卡 |" % collection_counts["links"],
        "",
        "| 类型 | 数量 |",
        "| --- | --- |",
    ]
    for k, v in type_counts.most_common():
        lines.append("| %s | %d |" % (k, v))
    lines += [
        "",
        "| 世纪 | 数量 |",
        "| --- | --- |",
    ]
    for k in ("19century", "20century", "21century", "undated"):
        if century_counts.get(k):
            lines.append("| %s | %d |" % (k, century_counts[k]))
    lines += [
        "",
        "## 目录",
        "",
        "- [photos/](photos/)：摄影影像",
        "- [paintings/](paintings/)：绘画与版画",
        "- [objects/](objects/)：器物与文书",
        "- [links/](links/)：仅外链卡",
        "- [stories/](stories/)：专题（已刊 %d 篇）" % len([
            p for p in (OUT / "stories" / "photos").glob("*.md") if p.name != "README.md"]),
        "- [schema/](schema/)：字段规则",
        "",
        "## 整理说明",
        "",
        "- 33 条人工精策展文案保留；其余自动批次改为中性档案体，只写可核实字段。",
        "- 类型分流只使用源站描述、题名与既有 medium 证据；不确定的标 `review_status: needs_review`。",
        "- 不删除记录、不改许可、不改证据与审计字段。",
        "- 完整的移动/校正清单见 [`../CONTENT-CLEANUP.md`](../CONTENT-CLEANUP.md)。",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    for c in ("photos", "paintings", "objects", "links"):
        rows = [r for r in all_rows if r["collection"] == c]
        if not rows and c != "links":
            (OUT / c).mkdir(parents=True, exist_ok=True)
        if not rows and c == "links":
            (OUT / c).mkdir(parents=True, exist_ok=True)
        write_readme(c, rows, preview, decade_counts[c])
        for dec in sorted(decade_counts[c]):
            drows = [r for r in rows if r["period"] == dec or r.get("period") == dec]
            # period 可能为空，用目录实际记录
            drows = []
            for p in sorted((OUT / c / dec).glob("*.md")):
                if p.name == "README.md":
                    continue
                text = p.read_text(encoding="utf-8")
                end = text.find("\n---\n", 4)
                fm = yaml.safe_load(text[4:end]) if end > 0 else {}
                if isinstance(fm, dict):
                    drows.append(fm)
            drows.sort(key=lambda r: (r.get("year") or 0, r.get("title") or ""))
            out = ["# %s · %s · %d 条" % (c, dec, len(drows)), "",
                   "| 年 | 标题 | 类型 | 主题 | 地域 | 来源 |",
                   "| --- | --- | --- | --- | --- | --- |"]
            for r in drows:
                out.append("| %s | [%s](%s.md) | %s | %s | %s | %s |" % (
                    r.get("year"), r.get("title"), r.get("id"), r.get("content_type"),
                    r.get("topic"), r.get("region"), r.get("source_short")))
            (OUT / c / dec / "README.md").write_text(
                "\n".join(out) + "\n", encoding="utf-8", newline="\n")

    # 清理报告
    lines = [
        "# 内容整理报告",
        "",
        "> 本轮只做可证实的类型分流与文案清理；不删除记录、不改许可与证据。",
        "",
        "## 汇总",
        "",
        "| 项 | 数量 |",
        "| --- | --- |",
        "| 总记录 | %d |" % len(all_rows),
        "| photos | %d |" % collection_counts["photos"],
        "| paintings | %d |" % collection_counts["paintings"],
        "| objects | %d |" % collection_counts["objects"],
        "| links | %d |" % collection_counts["links"],
        "| 待核 | %d |" % len(flags),
        "",
        "### 类型分布",
        "",
        "| 类型 | photos | paintings | objects | links |",
        "| --- | --- | --- | --- | --- |",
    ]
    type_matrix = defaultdict(Counter)
    for r in all_rows:
        type_matrix[r["content_type"]][r["collection"]] += 1
    for t in sorted(type_matrix, key=lambda x: (-sum(type_matrix[x].values()), x)):
        c = type_matrix[t]
        lines.append("| %s | %d | %d | %d | %d |" % (
            t, c["photos"], c["paintings"], c["objects"], c["links"]))
    lines += [
        "",
        "## 移出照片的条目",
        "",
        "| id | 标题 | 原 collection | 新 collection | 类型 | 依据 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in moves:
        lines.append("| %s | %s | %s | %s | %s | %s |" % tuple(
            str(x).replace("|", "\\|") for x in m))
    lines += [
        "",
        "## 待核条目",
        "",
        "| id | 标题 | 类型 | 状态 | 说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for f in flags:
        lines.append("| %s | %s | %s | %s | %s |" % tuple(
            str(x).replace("|", "\\|") for x in f))
    lines += [
        "",
        "## 文案清理",
        "",
        "- 33 条无 `curation` 字段的人工精策展文案保留原文。",
        "- 其余自动批次改为：年代 / 地点 / 作者 / 来源 / 馆藏编号 / 类型句。",
        "- 不再沿用按 topic 生成的“短评”，避免静物、绘画、器物被写成街巷或劳作。",
        "",
        "## 未做的事",
        "",
        "- 没有按题名关键词批量移动；没有删除任何记录。",
        "- 没有把明信片全部移出 photos：它们仍是以摄影为载体的影像，但 `content_type` 标为 `postcard`、`medium` 标为 `明信片`。",
        "- 绘画/版画的画种只在源站有明确工艺词时写明；不明确的写 `绘画` 或标待核。",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    # schema / taxonomy
    old = json.loads((ROOT / "schema" / "photo.schema.json").read_text(encoding="utf-8"))
    new = dict(old)
    new["title"] = "尘画 · 内容条目 (Markdown frontmatter)"
    new["required"] = [
        "id", "collection", "content_type", "type_evidence", "review_status",
        "year", "date_label", "era", "kind", "topic", "place", "title",
        "source_short", "source_url", "license", "license_url", "tier",
        "image", "fetched_at", "upstream", "license_snapshot", "theme", "region",
        "medium", "period", "evidence", "audit", "page_url", "page_url_basis",
        "rights_status", "commercial_ok", "creator_status",
    ]
    new["allowed_collections"] = ["photos", "paintings", "objects", "links"]
    new["allowed_content_types"] = ["photograph", "painting", "print", "drawing", "postcard", "object", "document", "link"]
    new["allowed_review_status"] = ["clean", "needs_review"]
    new["allowed_mediums"] = sorted(set(old.get("allowed_mediums", [])) | {
        "油画", "水彩", "绘画", "版画", "素描", "明信片", "彩色印刷", "印刷品", "器物", "文书"})
    new["fields"] = dict(old.get("fields", {}))
    new["fields"].pop("local_image", None)
    new["fields"].pop("note_file", None)
    new["fields"]["collection"] = "photos / paintings / objects / links"
    new["fields"]["content_type"] = "photograph / painting / print / postcard / object / document / link"
    new["fields"]["type_evidence"] = "类型判定的源站依据；不确定时配合 review_status: needs_review"
    new["fields"]["review_status"] = "clean / needs_review"
    new["fields"]["image"] = "世纪图片站上的展示图 URL；二进制不进内容仓"
    new["fields"]["image_original_sha256"] = "压缩前原图 sha256，用于溯源"
    new["fields"]["image_processing"] = "展示图处理规则，如 long-edge-1600-q82"
    new["fields"]["source_image"] = "原始上游图片 URL，保留用于重新抓取与审计"
    (OUT / "schema" / "photo.schema.json").write_text(
        json.dumps(new, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    painting = {
        "title": "尘画 · 绘画与版画",
        "type": "object",
        "required": ["id", "collection", "content_type", "type_evidence", "title", "year", "medium", "topic", "license", "image", "evidence", "audit"],
        "allowed_collections": ["paintings"],
        "allowed_content_types": ["painting", "print"],
        "allowed_mediums": ["油画", "水彩", "绘画", "版画"],
    }
    (OUT / "schema" / "painting.schema.json").write_text(
        json.dumps(painting, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    obj = {
        "title": "尘画 · 器物与文书",
        "type": "object",
        "required": ["id", "collection", "content_type", "type_evidence", "title", "year", "medium", "topic", "image", "evidence", "audit"],
        "allowed_collections": ["objects"],
        "allowed_content_types": ["object", "document", "postcard"],
        "allowed_mediums": ["纸品实物", "器物", "文书", "明信片"],
    }
    (OUT / "schema" / "object.schema.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    tax = json.loads((ROOT / "schema" / "taxonomy.json").read_text(encoding="utf-8"))
    tax.setdefault("medium", {}).update({
        "油画": "布面/板面油画",
        "水彩": "水彩画",
        "绘画": "画种未在源站明确的绘画",
        "版画": "蚀刻、铜版、石版、木刻等艺术版画",
        "明信片": "以摄影或印刷图像为主的明信片",
        "彩色印刷": "Photochrom 等彩色照相印刷",
        "印刷品": "照相印刷、机械印刷图像",
        "器物": "地毯、邮票、钱币、器物等",
        "文书": "信件、公文、档案等",
    })
    tax["content_type"] = {
        "photograph": "照片或摄影工艺影像",
        "painting": "绘画",
        "print": "艺术版画或印刷图像",
        "postcard": "明信片",
        "object": "器物",
        "document": "文书",
        "link": "仅外链卡",
    }
    tax["collection_note"] = (
        "photos 收摄影影像，以及以摄影为载体的明信片/印刷品；"
        "paintings 收绘画与艺术版画；objects 收器物与文书；links 仅外链。")
    (OUT / "schema" / "taxonomy.json").write_text(
        json.dumps(tax, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("内容整理完成：总计 %d · photos %d · paintings %d · objects %d · links %d"
          % (len(all_rows), collection_counts["photos"], collection_counts["paintings"],
             collection_counts["objects"], collection_counts["links"]))
    print("类型：" + " · ".join("%s %d" % (k, v) for k, v in type_counts.most_common()))
    print("移出照片：%d · 待核：%d · 缺图：%d" % (len(moves), len(flags), len(missing)))
    print("报告：%s" % REPORT.relative_to(ROOT))


if __name__ == "__main__":
    main()
