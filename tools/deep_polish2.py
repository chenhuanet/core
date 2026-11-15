# -*- coding: utf-8 -*-
"""补扫：把最后几件明显绘画/书页复制品移入 paintings/objects。"""
import json
import os
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
PREVIEW = ROOT / "next" / "preview-images.json"

THEME = {"面孔": "人间", "街巷": "人间", "风景": "天地", "痕迹": "技艺"}

MOVES = {
    "auto-505fc4ea": dict(collection="paintings", content_type="painting", medium="油画",
                          topic="面孔", title="Ivan Žabota - Portret starca",
                          evidence="画面为油画；题名/作者"),
    "auto-91d0ab3b": dict(collection="paintings", content_type="painting", medium="油画",
                          topic="风景", title="Vilhelm Arnesen - Under Ceylon - 1900",
                          evidence="画面为油画；题名/作者"),
    "auto-58575fef": dict(collection="paintings", content_type="painting", medium="油画",
                          topic="风景",
                          title="Vilhelm Arnesen - Dampskibet Annam på Mekongfloden ved Saigon - 1900",
                          evidence="画面为油画；题名/作者"),
    "auto-892adcb7": dict(collection="objects", content_type="object", medium="纸品实物",
                          topic="街巷", title="Glaspalast München 1900 027",
                          evidence="书页上的绘画复制品，带图注/页码"),
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


def update_alt(body, title):
    return re.sub(r"^!\[[^\]]*\]\(", "![" + title.replace("]", "\\]") + "](", body, count=1)


def find_record(rid):
    for c in ("photos", "paintings", "objects", "links"):
        for p in (CONTENT / c).glob("*/*.md"):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if fm.get("id") == rid:
                return p, fm, body
    return None, None, None


def main():
    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    count = 0
    for rid, spec in MOVES.items():
        p, fm, body = find_record(rid)
        if not p:
            continue
        period = fm.get("period") or "undated"
        century = fm.get("image_century")
        info = preview.get(rid)
        if info:
            old_target = info["target"]
            new_target = old_target.replace("/photos/", "/%s/" % spec["collection"], 1)
            src = ROOT / old_target
            dst = ROOT / new_target
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                os.replace(src, dst)
            info["collection"] = spec["collection"]
            info["target"] = new_target
            filename = pathlib.PurePosixPath(new_target).name
            new_url = "https://%s.chenhua.net/%s/%s/%s" % (
                century, spec["collection"], period, filename)
            old_url = fm.get("image")
            fm["image"] = new_url
            body = body.replace(old_url, new_url) if old_url else body
        old_title = fm.get("title")
        fm["collection"] = spec["collection"]
        fm["content_type"] = spec["content_type"]
        fm["medium"] = spec["medium"]
        fm["topic"] = spec["topic"]
        fm["theme"] = THEME.get(spec["topic"], fm.get("theme"))
        fm["type_evidence"] = spec["evidence"]
        fm["review_status"] = "clean"
        fm.pop("review_note", None)
        if old_title != spec["title"]:
            fm["title_original"] = old_title
            fm["title"] = spec["title"]
            fm["title_note"] = "按源站文件名/题名补全"
            body = update_alt(body, spec["title"])
        target = CONTENT / spec["collection"] / period / ("%s.md" % rid)
        write_md(target, fm, body)
        if p != target:
            p.unlink()
        count += 1
    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=1),
                       encoding="utf-8", newline="\n")
    print("补扫移入：%d 件" % count)


if __name__ == "__main__":
    main()
