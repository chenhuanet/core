# -*- coding: utf-8 -*-
"""尘画内容仓重复审计。

输出：
  next/DUPLICATE-AUDIT.md        人读报告（分组明细）
  next/duplicate-audit.json      机读结果（供清理脚本使用）

检查维度：
  1. 同一展示图（image_sha256）
  2. 同一原图（image_original_sha256）
  3. 同一源文件 URL（source_image）
  4. 同一源对象页（page_url）
  5. 同题名 + 同年（不同图，仅提示）
  6. 磁盘上字节相同的图片文件（sha256）
  7. 未被任何记录引用的孤儿图片文件
  8. 缺图字段 / 缺文件
"""
import collections
import hashlib
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
NEXT = ROOT / "next"
CONTENT = NEXT / "content"
IMAGES = NEXT / "images"
OUT_MD = NEXT / "DUPLICATE-AUDIT.md"
OUT_JSON = NEXT / "duplicate-audit.json"

COLLECTIONS = ("photos", "paintings", "objects", "links")


def read_md(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text.strip()
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text.strip()
    return yaml.safe_load(text[4:end]) or {}, text[end + 5:].strip()


def load_records():
    rows = []
    for collection in COLLECTIONS:
        for p in sorted((CONTENT / collection).glob("*/*.md")):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if not fm.get("id"):
                continue
            fm["_path"] = str(p.relative_to(ROOT))
            fm["_collection"] = collection
            fm["_body"] = body
            rows.append(fm)
    return rows


def quality_key(r):
    """重复组里保留哪一条：证据/释文/权利更完整者优先。"""
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", r.get("_body") or "").strip()
    return (
        1 if (r.get("evidence") or {}).get("claim") else 0,
        len(body),
        1 if r.get("license_url") else 0,
        1 if r.get("page_url") else 0,
        1 if r.get("image_width") else 0,
        -len(str(r.get("title") or "")),
    )


def norm_url(u):
    if not u:
        return ""
    u = str(u).strip()
    u = re.sub(r"[?#].*$", "", u)
    return u.rstrip("/").lower()


def norm_title(t):
    t = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(t or "").lower())
    return t


def group_by(rows, keyfn):
    g = collections.defaultdict(list)
    for r in rows:
        k = keyfn(r)
        if k:
            g[k].append(r)
    return {k: v for k, v in g.items() if len(v) > 1}


def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows = load_records()
    stats = collections.Counter()
    stats["total"] = len(rows)
    for c in COLLECTIONS:
        stats[c] = sum(1 for r in rows if r["_collection"] == c)

    ids = collections.Counter(str(r["id"]) for r in rows)
    dup_ids = {k: v for k, v in ids.items() if v > 1}

    groups = {
        "display_hash": group_by(rows, lambda r: r.get("image_sha256")),
        "original_hash": group_by(rows, lambda r: r.get("image_original_sha256")),
        "source_image": group_by(rows, lambda r: norm_url(r.get("source_image"))),
        "page_url": group_by(rows, lambda r: norm_url(r.get("page_url"))),
        "title_year": group_by(rows, lambda r: (
            norm_title(r.get("title")), str(r.get("year") or "")) if r.get("year") else ""),
    }

    # 图片文件
    files = []
    for p in sorted(IMAGES.rglob("*")):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        if p.is_file():
            files.append((p, p.stat().st_size, file_sha(p)))

    by_hash = collections.defaultdict(list)
    for p, size, sha in files:
        by_hash[sha].append((p, size))

    referenced = set()
    missing = []
    for r in rows:
        img = r.get("image") or ""
        if img:
            referenced.add(pathlib.PurePosixPath(img).name)
            # 本地是否存在同名文件
            if not any(f[0].name == pathlib.PurePosixPath(img).name for f in files):
                missing.append(r)
    orphans = [p for p, size, sha in files if p.name not in referenced]

    groups_payload = {}
    for dim, dim_groups in groups.items():
        payload = {}
        for name, grp in sorted(dim_groups.items(), key=lambda kv: str(kv[0])):
            if isinstance(name, tuple):
                name = " / ".join(str(x) for x in name)
            members = []
            for r in sorted(grp, key=quality_key, reverse=True):
                members.append({
                    "id": r["id"],
                    "collection": r["_collection"],
                    "title": r.get("title"),
                    "year": r.get("year"),
                    "image": r.get("image"),
                    "source_image": r.get("source_image"),
                    "page_url": r.get("page_url"),
                    "tier": r.get("tier"),
                    "note_len": len((r.get("_body") or "")),
                    "path": r["_path"],
                })
            payload[str(name)] = {"key": str(name), "members": members}
        groups_payload[dim] = payload

    report = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "stats": dict(stats),
        "duplicate_ids": dup_ids,
        "groups": groups_payload,
        "disk_duplicate_groups": [
            {"sha256": sha, "files": [str(p.relative_to(ROOT)) for p, s in items]}
            for sha, items in sorted(by_hash.items()) if len(items) > 1
        ],
        "orphan_images": [str(p.relative_to(ROOT)) for p in orphans],
        "missing_image_files": [r["id"] for r in missing],
        "images": {"files": len(files), "referenced_names": len(referenced)},
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    def members_table(items):
        out = ["| id | 集合 | 题名 | 年 | tier | 释文字数 |", "| --- | --- | --- | --- | --- | --- |"]
        for m in items:
            out.append("| `%s` | %s | %s | %s | %s | %s |" % (
                m["id"], m["collection"], str(m["title"] or "").replace("|", "\\|"),
                m["year"] or "", m["tier"] or "", m["note_len"]))
        return "\n".join(out)

    lines = []
    lines.append("# 重复内容审计")
    lines.append("")
    lines.append("> 生成时间：%s；数据源 `next/content`。" % report["generated_at"])
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 项 | 数量 |")
    lines.append("| --- | --- |")
    for k in ("total", "photos", "paintings", "objects", "links"):
        lines.append("| %s | %d |" % (k, stats[k]))
    lines.append("| 重复 id | %d |" % len(dup_ids))
    for label, key in (("同展示图组", "display_hash"), ("同原图组", "original_hash"),
                       ("同源文件 URL 组", "source_image"), ("同对象页组", "page_url"),
                       ("同题名+同年组", "title_year")):
        n = len(groups[key])
        extra = sum(len(v) - 1 for v in groups[key].values())
        lines.append("| %s | %d 组（可减 %d 条） |" % (label, n, extra))
    lines.append("| 磁盘同哈希图片组 | %d |" % len(report["disk_duplicate_groups"]))
    lines.append("| 孤儿图片文件 | %d |" % len(orphans))
    lines.append("| 记录引用但本地缺图 | %d |" % len(missing))
    lines.append("")

    for title, key in (("同一展示图（image_sha256）", "display_hash"),
                       ("同一原图（image_original_sha256）", "original_hash"),
                       ("同一源文件 URL", "source_image"),
                       ("同一源对象页", "page_url"),
                       ("同题名 + 同年（不同图，仅供人工判断）", "title_year")):
        lines.append("## " + title)
        lines.append("")
        if not groups[key]:
            lines.append("无。")
            lines.append("")
            continue
        for key_value, items in sorted(groups[key].items()):
            lines.append("### %s 条 · %s" % (len(items), key_value if isinstance(key_value, str) else key_value))
            lines.append("")
            lines.append(members_table([
                {
                    "id": r["id"], "collection": r["_collection"], "title": r.get("title"),
                    "year": r.get("year"), "tier": r.get("tier"),
                    "note_len": len(r.get("_body") or ""),
                } for r in sorted(items, key=quality_key, reverse=True)
            ]))
            lines.append("")
    lines.append("## 磁盘上字节相同的图片")
    lines.append("")
    if report["disk_duplicate_groups"]:
        for g in report["disk_duplicate_groups"]:
            lines.append("- `%s`：%s" % (g["sha256"][:12], "、".join(g["files"])))
    else:
        lines.append("无。")
    lines.append("")
    lines.append("## 孤儿图片（未被任何记录引用）")
    lines.append("")
    if orphans:
        for p in orphans[:200]:
            lines.append("- `%s`" % p.relative_to(ROOT))
        if len(orphans) > 200:
            lines.append("- … 另有 %d 个" % (len(orphans) - 200))
    else:
        lines.append("无。")
    lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("records=%d photos=%d paintings=%d objects=%d links=%d" % (
        stats["total"], stats["photos"], stats["paintings"], stats["objects"], stats["links"]))
    print("dup ids=%d" % len(dup_ids))
    for label, key in (("display", "display_hash"), ("original", "original_hash"),
                       ("source_image", "source_image"), ("page_url", "page_url"),
                       ("title_year", "title_year")):
        print("%-14s groups=%3d extra=%3d" % (label, len(groups[key]),
              sum(len(v) - 1 for v in groups[key].values())))
    print("disk dup groups=%d orphans=%d missing=%d images=%d" % (
        len(report["disk_duplicate_groups"]), len(orphans), len(missing), len(files)))
    print("report:", OUT_MD)


if __name__ == "__main__":
    main()
