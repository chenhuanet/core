# -*- coding: utf-8 -*-
"""重复清理（可回滚）。

做四件事：
  1. 删除未被任何故事引用的 today-*-arc* 记录（死条目）
  2. 删除同页面的低分辨率重复：auto-1925e020（Challenger 960px 版）
  3. 删除单个故事页内重复出现的同一张图（保留第一次出现）
  4. 从 preview-images.json 移除被删条目，并把图片移到备份目录

所有被删文件先移动到 archive/cleanup-20261118/，不直接消失。
用法：python cleanup_duplicates.py [--apply]
"""
import argparse
import collections
import json
import pathlib
import re
import shutil

import yaml

ROOT = pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua")
CONTENT = ROOT / "next" / "content"
PREVIEW = ROOT / "next" / "preview-images.json"
BACKUP = ROOT / "archive" / "cleanup-20261118"
LOG = ROOT / "next" / "DEDUPE-LOG.md"


def read_md(p):
    t = p.read_text(encoding="utf-8")
    if not t.startswith("---\n"):
        return {}, t
    e = t.find("\n---\n", 4)
    return yaml.safe_load(t[4:e]) or {}, t[e + 5:]


def load_records():
    rows = {}
    for c in ("photos", "paintings", "objects", "links"):
        for p in sorted((CONTENT / c).glob("*/*.md")):
            if p.name == "README.md":
                continue
            fm, _ = read_md(p)
            if fm.get("id"):
                fm["_p"] = p
                fm["_c"] = c
                rows[fm["id"]] = fm
    return rows


def load_story_refs():
    refs = collections.defaultdict(set)
    stories = {}
    for p in sorted((CONTENT / "stories" / "photos").glob("*.md")):
        if p.name == "README.md":
            continue
        fm, _ = read_md(p)
        if not fm.get("id"):
            continue
        ids = []
        for ch in fm.get("chapters") or []:
            for it in ch.get("items") or []:
                rid = it.get("id") if isinstance(it, dict) else str(it)
                if rid:
                    ids.append(rid)
            ids.extend(ch.get("photo_ids") or [])
        if fm.get("cover"):
            refs[fm["cover"]].add(fm["id"])
        stories[fm["id"]] = {"path": p, "ids": ids, "fm": fm}
    return refs, stories


def move(src, sub):
    dst = BACKUP / sub / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


def remove_item_block(text, rid):
    lines = text.splitlines(keepends=True)
    pat = re.compile(r"^\s*- id:\s*" + re.escape(rid) + r"\s*$")
    for i, line in enumerate(lines):
        if pat.match(line):
            j = i + 1
            while j < len(lines) and lines[j].startswith("    ") and lines[j].strip():
                j += 1
            removed = "".join(lines[i:j])
            del lines[i:j]
            return "".join(lines), removed
    return text, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    records = load_records()
    refs, stories = load_story_refs()

    # 1. 未被引用的 arc 记录
    arc_dead = sorted(rid for rid in records
                      if rid.startswith("today-") and "-arc" in rid and not refs.get(rid))

    # 2. Challenger 低分辨率重复
    dup_records = []
    if "auto-1925e020" in records and "auto-097ceddb" in records:
        a, b = records["auto-1925e020"], records["auto-097ceddb"]
        if a.get("page_url") == b.get("page_url"):
            dup_records.append("auto-1925e020")

    # 3. 单页内同图重复：保留第一次出现
    story_fixes = []
    for sid, s in stories.items():
        urls = {}
        for rid in s["ids"]:
            r = records.get(rid)
            if not r or not r.get("image"):
                continue
            urls.setdefault(r["image"], []).append(rid)
        for u, ids in urls.items():
            if len(ids) > 1:
                # 保留有有效图片引用的第一个，其余删除
                for extra in ids[1:]:
                    story_fixes.append((s["path"], extra, sid, u))

    print("待删 arc 记录:", len(arc_dead))
    print("待删重复记录:", dup_records)
    print("待修故事条目:", len(story_fixes), [x[1] for x in story_fixes])
    if not args.apply:
        print("（dry-run，未改动）")
        return

    moved = move_log = []
    for rid in arc_dead:
        p = records[rid]["_p"]
        dst = move(p, "records/%s" % records[rid]["_c"])
        moved.append((str(p.relative_to(ROOT)), str(dst.relative_to(ROOT)), "unreferenced arc"))

    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    for rid in dup_records:
        p = records[rid]["_p"]
        dst = move(p, "records/%s" % records[rid]["_c"])
        moved.append((str(p.relative_to(ROOT)), str(dst.relative_to(ROOT)), "duplicate lower-res"))
        info = preview.pop(rid, None)
        if info and info.get("target"):
            img = ROOT / info["target"]
            if img.exists():
                dst_img = move(img, "images/%s" % info["century"])
                moved.append((str(img.relative_to(ROOT)), str(dst_img.relative_to(ROOT)), "duplicate image"))

    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    story_changed = 0
    backed_up = set()
    for path, rid, sid, u in story_fixes:
        text = path.read_text(encoding="utf-8")
        new, removed = remove_item_block(text, rid)
        if not removed:
            print("WARN 未找到条目", sid, rid)
            continue
        if path not in backed_up:
            move(path, "stories")
            backed_up.add(path)
        path.write_text(new, encoding="utf-8", newline="\n")
        story_changed += 1

    lines = ["# 重复清理记录", "", "日期：2026-11-18", "",
             "| 类型 | 数量 |", "| --- | --- |",
             "| 未引用 arc 记录 | %d |" % len(arc_dead),
             "| 同源低分辨率重复记录 | %d |" % len(dup_records),
             "| 单页内重复图条目 | %d |" % story_changed, "",
             "被删文件已移至 `archive/cleanup-20261118/`，可原样恢复。", ""]
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("完成：arc=%d dup=%d story=%d，备份 %s" % (len(arc_dead), len(dup_records), story_changed, BACKUP))
    for a, b, why in moved[:5]:
        print("  ", a, "->", b, why)


if __name__ == "__main__":
    main()
