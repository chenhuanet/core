# -*- coding: utf-8 -*-
"""内容收尾：修正明显主题误分，处理采集时被截断的标题。

只改可证实的字段；不动许可、证据、图片 sha。
"""
import pathlib
import re
from collections import Counter, defaultdict

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
COLLECTIONS = ("photos", "paintings", "objects", "links")

THEME_OF_TOPIC = {
    "面孔": "人间", "街巷": "人间", "劳作": "人间",
    "战火": "世事", "灾变": "世事", "权利": "世事",
    "远方": "天地", "风景": "天地",
    "痕迹": "技艺", "馆藏": "技艺",
}

TOPIC_FIXES = {
    "auto-65798bdf": "面孔",  # Face detail, Ambrose Burnside
    "auto-fb7886e9": "面孔",  # Face detail, Ambrose Burnside cropped
    "cle-6912c556": "风景",  # Upper Himalayahs, Manga Valley
    "cle-717b1d1d": "风景",
    "cle-73b1a8f6": "风景",  # Landscape with Tree and Three Men
    "cle-d0b1c8a5": "面孔",  # Man on a Horse
    "cle-7f62a63c": "面孔",  # Man with Walking Stick
    "auto-3a9da375": "面孔",  # Portret van een jongeman
    "cle-3900f786": "风景",  # View of the Acropolis
}

TITLE_FIXES = {
    "auto-d49e9fd0": "Still life with orange and book",
    "auto-27bcc7d5": "Camille Pissarro, Still Life with a Coffeepot",
}

TRUNC_RE = re.compile(r"(,|，|;|；|\band|\bof|\bwith|\bthe|\bfrom|\bat|\bin)\s*$", re.I)


def read_md(path):
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end < 0:
        return {}, text
    return yaml.safe_load(text[4:end]) or {}, text[end + 5:]


def write_md(path, fm, body):
    out = "---\n" + yaml.safe_dump(
        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
    ) + "---\n" + body
    path.write_text(out, encoding="utf-8", newline="\n")


def complete_title(title, desc):
    desc = str(desc or "").strip()
    if not desc:
        return None
    first = re.split(r"\s*\|\s*|\n", desc)[0].strip()
    if first.lower().startswith(title.lower()) and len(first) > len(title) + 3:
        return first[:140].rstrip()
    return None


def main():
    records = []
    for c in COLLECTIONS:
        for p in sorted((CONTENT / c).glob("*/*.md")):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if isinstance(fm, dict) and fm.get("id"):
                records.append((p, fm, body))

    topic_fixed = 0
    title_completed = 0
    title_flagged = 0

    for p, fm, body in records:
        rid = fm.get("id")
        changed = False
        if rid in TOPIC_FIXES:
            fm["topic"] = TOPIC_FIXES[rid]
            fm["theme"] = THEME_OF_TOPIC.get(fm["topic"], fm.get("theme"))
            changed = True
            topic_fixed += 1

        title = str(fm.get("title") or "")
        cleaned = re.sub(r"…{2,}", "…", title)
        if cleaned != title:
            fm["title"] = title = cleaned
            changed = True
        new_title = None
        note = None
        if fm.get("title_note") or fm.get("title_truncated") or title.endswith("…"):
            pass
        elif rid in TITLE_FIXES:
            new_title = TITLE_FIXES[rid]
            note = "题名按源站对象页清理"
        elif TRUNC_RE.search(title) or title.count("(") > title.count(")"):
            desc = (fm.get("license_snapshot") or {}).get("description") or ""
            new_title = complete_title(title, desc)
            if new_title:
                note = "按源站描述补全题名"
                title_completed += 1
            else:
                new_title = title.rstrip(" ,;，；") + "…"
                note = "源站题名在采集时截断，未补全"
                fm["title_truncated"] = True
                title_flagged += 1
        if new_title and new_title != title:
            fm["title_original"] = title
            fm["title"] = new_title
            fm["title_note"] = note
            body = re.sub(r"^!\[[^\]]*\]\(", "![" + new_title.replace("]", "\\]") + "](",
                          body, count=1)
            changed = True
        if changed:
            write_md(p, fm, body)

    # 重新生成 README（不重跑迁移，避免压缩 sha 回退）
    collections = Counter(f.get("collection") for _, f, _ in records)
    types = Counter(f.get("content_type") for _, f, _ in records)
    centuries = Counter(f.get("image_century") for _, f, _ in records if f.get("image_century"))
    story_count = len([p for p in (CONTENT / "stories" / "photos").glob("*.md")
                       if p.name != "README.md"])

    lines = [
        "# 尘画 · 内容仓", "",
        "> `historical-photography-and-painting` · 以图为史，记录人间的大事与小事。", "",
        "| collection | 数量 |", "| --- | --- |",
    ]
    for c in COLLECTIONS:
        lines.append("| %s | %d |" % (c, collections.get(c, 0)))
    lines += ["", "| 类型 | 数量 |", "| --- | --- |"]
    for k, v in types.most_common():
        lines.append("| %s | %d |" % (k, v))
    lines += ["", "## 目录", "",
              "- [photos/](photos/)：摄影影像",
              "- [paintings/](paintings/)：绘画与版画",
              "- [objects/](objects/)：器物与文书",
              "- [links/](links/)：仅外链卡",
              "- [stories/](stories/)：专题（已刊 %d 篇）" % story_count,
              "- [schema/](schema/)：字段规则", "",
              "## 整理说明", "",
              "- 33 条人工精策展文案保留；其余自动批次为中性档案体。",
              "- 类型分流只使用源站描述、题名与既有 medium 证据；不确定的标 `review_status: needs_review`。",
              "- 不删除记录、不改许可、不改证据与审计字段。",
              "- 完整移动/校正清单见 [`../CONTENT-CLEANUP.md`](../CONTENT-CLEANUP.md)。", ""]
    (CONTENT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    for c in COLLECTIONS:
        rows = [(p, f, b) for p, f, b in records if f.get("collection") == c]
        decades = Counter(f.get("period") for _, f, _ in rows if f.get("period"))
        tcount = Counter(f.get("content_type") for _, f, _ in rows)
        out = ["# %s" % {"photos": "照片", "paintings": "绘画与版画",
                          "objects": "器物与文书", "links": "仅外链"}[c], "",
               "共 **%d** 条。" % len(rows), "", "| 类型 | 数量 |", "| --- | --- |"]
        for k, v in tcount.most_common():
            out.append("| %s | %d |" % (k, v))
        out += ["", "| 年代 | 数量 | 目录 |", "| --- | --- | --- |"]
        for d in sorted(decades):
            out.append("| %s | %d | [%s/](%s/) |" % (d, decades[d], d, d))
        (CONTENT / c / "README.md").write_text("\n".join(out) + "\n",
                                               encoding="utf-8", newline="\n")
        for d in sorted(decades):
            drows = [(p, f, b) for p, f, b in rows if f.get("period") == d]
            drows.sort(key=lambda x: (x[1].get("year") or 0, x[1].get("title") or ""))
            out = ["# %s · %s · %d 条" % (c, d, len(drows)), "",
                   "| 年 | 标题 | 类型 | 主题 | 地域 | 来源 |",
                   "| --- | --- | --- | --- | --- | --- |"]
            for p, f, b in drows:
                out.append("| %s | [%s](%s.md) | %s | %s | %s | %s |" % (
                    f.get("year"), f.get("title"), f.get("id"), f.get("content_type"),
                    f.get("topic"), f.get("region"), f.get("source_short")))
            (CONTENT / c / d / "README.md").write_text(
                "\n".join(out) + "\n", encoding="utf-8", newline="\n")

    # schema 补充可选字段说明
    sp = CONTENT / "schema" / "photo.schema.json"
    schema = __import__("json").loads(sp.read_text(encoding="utf-8"))
    schema.setdefault("fields", {}).update({
        "title_original": "题名被清理/补全前的原始值",
        "title_note": "题名清理依据",
        "title_truncated": "源站题名在采集时截断，未补全",
    })
    sp.write_text(__import__("json").dumps(schema, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8", newline="\n")

    print("内容收尾：主题修正 %d · 标题补全 %d · 标题标记截断 %d" % (
        topic_fixed, title_completed, title_flagged))


if __name__ == "__main__":
    main()
