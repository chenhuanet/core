# -*- coding: utf-8 -*-
"""深度内容收尾：把明显绘画/版画/素描移入 paintings，解决 3 条待核，
补齐外链卡许可快照，并用 Commons 文件名补全可补的题名。
"""
import json
import os
import pathlib
import re
import urllib.parse

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
PREVIEW = ROOT / "next" / "preview-images.json"
COLLECTIONS = ("photos", "paintings", "objects", "links")

THEME_OF_TOPIC = {
    "面孔": "人间", "街巷": "人间", "劳作": "人间",
    "战火": "世事", "灾变": "世事", "权利": "世事",
    "远方": "天地", "风景": "天地",
    "痕迹": "技艺", "馆藏": "技艺",
}

# 画面已人工核对：油画 / 水彩 / 版画 / 素描
MOVES = {
    "auto-78b2a883": dict(title="The School Room", content_type="drawing", medium="素描",
                          topic="街巷", evidence="题名与画面：铅笔/炭笔素描"),
    "auto-0d3092e4": dict(title="Anders Zorn - Grandmother III (1884)", content_type="print",
                          medium="版画", topic="面孔", evidence="画面有版画压痕与签名；Zorn 蚀刻"),
    "auto-723f2014": dict(title="Nicola Facchinetti - Lagoa Rodrigo de Freitas, Rio de Janeiro, ca. 1884",
                          content_type="painting", medium="油画", topic="风景",
                          evidence="画面为油画；题名/作者"),
    "auto-ba3dba36": dict(title="Giovanni Battista Castagneto - Porto do Rio de Janeiro (2)",
                          content_type="painting", medium="油画", topic="风景",
                          evidence="画面为油画；题名/作者"),
    "auto-e13d5cd2": dict(title="Giovanni Battista Castagneto - Porto do Rio de Janeiro, 1884",
                          content_type="painting", medium="油画", topic="风景",
                          evidence="画面为油画；题名/作者"),
    "auto-ad61b00e": dict(title="Victor Meirelles - Estudo para Panorama do Rio de Janeiro - Ilha das Cobras e Morro de Santo Antônio, c. 1885",
                          content_type="painting", medium="油画", topic="风景",
                          evidence="画面为油画；题名/作者"),
    "auto-aed4a918": dict(title="Ivan Konstantinovich Aivazovsky - Shipwreck off the Black Sea Coast",
                          content_type="painting", medium="油画", topic="灾变",
                          evidence="画面为油画；题名/作者"),
    "auto-e80436fe": dict(title="Ivan Konstantinovich Aivazovsky - Shipwreck on a Stormy Morning, 1895",
                          content_type="painting", medium="油画", topic="灾变",
                          evidence="画面为油画；题名/作者"),
    "auto-9fd3fc18": dict(title="Anders Zorn - Billy Mason (1900)", content_type="print",
                          medium="版画", topic="面孔", evidence="画面有蚀刻线条与签名；Zorn 版画"),
    "auto-f2dad429": dict(title="Lesser Ury - Nächtliche Strassenszene, Berlin (1920)",
                          content_type="painting", medium="油画", topic="街巷",
                          evidence="画面为油画；题名/作者"),
    "auto-62ae36e0": dict(title="Heinrich Hermann - Cape Town from the Top of Kloof Street",
                          content_type="painting", medium="水彩", topic="风景",
                          evidence="画面为水彩；题名/作者"),
    "auto-580fb4aa": dict(title="Leo Tolstoy by I.S. Kazakov (1900, Odessa)",
                          content_type="painting", medium="绘画", topic="面孔",
                          evidence="画面为肖像绘画；题名/作者"),
}

FLAG_FIXES = {
    "auto-2df8ce6f": dict(content_type="painting", medium="油画", topic="面孔",
                          evidence="画面为厚涂油画；题名/作者 George Benjamin Luks",
                          review="clean", remove_review_note=True),
    "auto-5aef6dca": dict(review="clean", remove_review_note=True,
                          evidence="文书照片；1875-09-05 信，与 auto-dc10d302 非重复"),
    "auto-dc10d302": dict(review="clean", remove_review_note=True,
                          evidence="文书；1875-08-10 信，与 auto-5aef6dca 非重复"),
    "auto-768ea122": dict(title="Inspection of the Center Engraving on the Nickel Plated Mother Record",
                          title_note="按 NASA 说明补全",
                          evidence="画面为工作人员检查金唱片母版中心刻纹的纪实照片",
                          review="clean", remove_review_note=True,
                          content_type="photograph", medium="航天影像", topic="远方"),
}


def read_md(path):
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end < 0:
        return {}, text
    return yaml.safe_load(text[4:end]) or {}, text[end + 5:]


def write_md(path, fm, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(
        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
    ) + "---\n" + body, encoding="utf-8", newline="\n")


def find_record(rid):
    for c in COLLECTIONS:
        for p in (CONTENT / c).glob("*/*.md"):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if fm.get("id") == rid:
                return p, c, fm, body
    return None, None, None, None


def update_alt(body, title):
    return re.sub(r"^!\[[^\]]*\]\(", "![" + title.replace("]", "\\]") + "](", body, count=1)


def main():
    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    moved = flags = commons_titles = 0

    for rid, spec in MOVES.items():
        p, c, fm, body = find_record(rid)
        if not p:
            continue
        period = fm.get("period") or "undated"
        century = fm.get("image_century")
        info = preview.get(rid)
        if info:
            old_target = info["target"]
            new_target = old_target.replace("/photos/", "/paintings/", 1)
            src = ROOT / old_target
            dst = ROOT / new_target
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                os.replace(src, dst)
            info["collection"] = "paintings"
            info["target"] = new_target
            filename = pathlib.PurePosixPath(new_target).name
            new_url = "https://%s.chenhua.net/paintings/%s/%s" % (century, period, filename)
            old_url = fm.get("image")
            fm["image"] = new_url
            body = body.replace(old_url, new_url) if old_url else body
        fm["collection"] = "paintings"
        fm["content_type"] = spec["content_type"]
        fm["medium"] = spec["medium"]
        fm["topic"] = spec["topic"]
        fm["theme"] = THEME_OF_TOPIC.get(spec["topic"], fm.get("theme"))
        fm["type_evidence"] = spec["evidence"]
        fm["review_status"] = "clean"
        fm.pop("review_note", None)
        if fm.get("title") != spec["title"]:
            fm["title_original"] = fm.get("title")
            fm["title"] = spec["title"]
            fm["title_note"] = "按源站文件名/题名补全"
            body = update_alt(body, spec["title"])
        fm.pop("title_truncated", None)
        write_md(CONTENT / "paintings" / period / ("%s.md" % rid), fm, body)
        if p != CONTENT / "paintings" / period / ("%s.md" % rid):
            p.unlink()
        moved += 1

    for rid, spec in FLAG_FIXES.items():
        p, c, fm, body = find_record(rid)
        if not p:
            continue
        old_title = fm.get("title")
        for k, v in spec.items():
            if k in ("remove_review_note",):
                if v:
                    fm.pop("review_note", None)
            elif k == "review":
                fm["review_status"] = v
            else:
                fm[k] = v
        if spec.get("topic"):
            fm["theme"] = THEME_OF_TOPIC.get(spec["topic"], fm.get("theme"))
        if spec.get("title") and old_title != spec["title"]:
            fm["title_original"] = old_title
            body = update_alt(body, spec["title"])
        write_md(p, fm, body)
        flags += 1

    # 外链卡：补最小许可快照
    for p in (CONTENT / "links").glob("*/*.md"):
        if p.name == "README.md":
            continue
        fm, body = read_md(p)
        if not fm.get("license_snapshot"):
            fm["license_snapshot"] = {
                "captured_at": fm.get("fetched_at"),
                "license": fm.get("license"),
                "license_url": fm.get("license_url"),
                "page_url": fm.get("page_url"),
                "note": "原外链卡未保存许可快照；按现有字段重建",
            }
            write_md(p, fm, body)

    # Commons 截断题名：用文件名补全；Cleveland 保持标记
    for c in COLLECTIONS:
        for p in (CONTENT / c).glob("*/*.md"):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if not fm.get("title_truncated"):
                continue
            if fm.get("source_short") != "维基共享资源":
                continue
            page = str(fm.get("page_url") or "")
            if "File:" not in page:
                continue
            name = urllib.parse.unquote(page.split("File:", 1)[1])
            name = name.split("?")[0]
            name = re.sub(r"\.(jpg|jpeg|png)$", "", name, flags=re.I)
            name = name.replace("_", " ").strip()
            name = re.sub(r"\s*\(\d{6,}\)\s*$", "", name)
            current = str(fm.get("title") or "").rstrip("…").strip()
            if len(name) <= len(current):
                continue
            fm["title_original"] = fm.get("title")
            fm["title"] = name[:140]
            fm["title_note"] = "按 Commons 文件名补全"
            fm.pop("title_truncated", None)
            body = update_alt(body, fm["title"])
            write_md(p, fm, body)
            commons_titles += 1

    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=1),
                       encoding="utf-8", newline="\n")
    print("深度收尾：移入绘画 %d · 待核解决 %d · Commons 题名补全 %d" % (
        moved, flags, commons_titles))


if __name__ == "__main__":
    main()
