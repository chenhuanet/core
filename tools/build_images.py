# -*- coding: utf-8 -*-
"""生成世纪图片仓预览：硬链接图片 + 按 collection 分 manifest。"""
import json
import os
import pathlib
import shutil
from collections import Counter, defaultdict

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "next" / "preview-images.json"
CONTENT = ROOT / "next" / "content"
IMAGES = ROOT / "next" / "images"


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def main():
    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    by_shard = defaultdict(list)
    linked = copied = 0

    for rid, info in preview.items():
        century = info["century"]
        collection = info.get("collection", "photos")
        decade = info["decade"]
        fm = read_frontmatter(CONTENT / collection / decade / ("%s.md" % rid))
        src = ROOT / info["source"]
        target_rel = pathlib.PurePosixPath(info["target"]).relative_to(
            pathlib.PurePosixPath("next/images/%s" % century))
        target = IMAGES / century / pathlib.Path(str(target_rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            pass
        else:
            try:
                os.link(src, target)
                linked += 1
            except Exception:
                shutil.copy2(src, target)
                copied += 1
        name = target.name
        by_shard[(century, collection)].append({
            "id": rid,
            "title": fm.get("title") or rid,
            "year": fm.get("year"),
            "date_label": fm.get("date_label"),
            "collection": collection,
            "content_type": fm.get("content_type") or "photograph",
            "decade": decade,
            "path": "%s/%s/%s" % (collection, decade, name),
            "url": "https://%s.chenhua.net/%s/%s/%s" % (century, collection, decade, name),
            "preview_url": "/next/images/%s/%s/%s/%s" % (century, collection, decade, name),
            "detail_collection": collection,
            "detail_slug": rid,
            "sha256": info.get("sha256"),
            "bytes": info.get("bytes"),
            "width": info.get("width"),
            "height": info.get("height"),
        })

    for century in sorted({c for c, _ in by_shard}):
        folder = IMAGES / century
        (folder / "manifests").mkdir(parents=True, exist_ok=True)
        counts = Counter()
        for collection in ("photos", "paintings", "objects"):
            rows = sorted(by_shard.get((century, collection), []),
                          key=lambda r: (r["year"] or 0, r["title"]))
            counts[collection] = len(rows)
            payload = {
                "century": century,
                "collection": collection,
                "base_url": "https://%s.chenhua.net" % century,
                "count": len(rows),
                "images": rows,
            }
            (folder / "manifests" / ("%s.json" % collection)).write_text(
                json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8", newline="\n")
        (folder / "README.md").write_text(
            "# %s · 图片仓\n\n"
            "- 照片：`photos/<decade>/<id>-<sha8>.<ext>`\n"
            "- 绘画与版画：`paintings/<decade>/...`\n"
            "- 器物与文书：`objects/<decade>/...`\n"
            "- 清单：`manifests/photos.json`、`paintings.json`、`objects.json`\n"
            "- 根目录 `index.html` 是最简瀑布索引页，不是裸文件目录。\n\n"
            "当前：照片 **%d** · 绘画/版画 **%d** · 器物/文书 **%d**。\n"
            % (century, counts["photos"], counts["paintings"], counts["objects"]),
            encoding="utf-8", newline="\n")
        (folder / ".nojekyll").write_text("", encoding="utf-8")

    print("世纪图片仓：")
    for century in sorted({c for c, _ in by_shard}):
        print("  %s · 照片 %d · 绘画/版画 %d · 器物/文书 %d" % (
            century,
            len(by_shard.get((century, "photos"), [])),
            len(by_shard.get((century, "paintings"), [])),
            len(by_shard.get((century, "objects"), [])),
        ))
    print("硬链接 %d · 复制 %d" % (linked, copied))


if __name__ == "__main__":
    main()
