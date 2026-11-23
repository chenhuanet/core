# -*- coding: utf-8 -*-
"""生成世纪图片仓：主图硬链接/复制、480px 缩略图、按 collection 分 manifest。"""
import json
import os
import pathlib
import shutil
from collections import Counter, defaultdict

import yaml
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "next" / "preview-images.json"
CONTENT = ROOT / "next" / "content"
IMAGES = ROOT / "next" / "images"
THUMB_MAX = 480
THUMB_QUALITY = 70


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def make_thumb(target, thumb):
    if thumb.exists():
        return
    thumb.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(target) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
            im.save(thumb, "JPEG", quality=THUMB_QUALITY, optimize=True, progressive=True)
    except Exception as exc:
        print("  ! thumb failed %s: %s" % (target.name, exc))


def main():
    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    by_shard = defaultdict(list)
    linked = copied = thumbs = 0
    seen = set()

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
        if not target.exists():
            try:
                if src.resolve() != target.resolve():
                    os.link(src, target)
                    linked += 1
            except Exception:
                if src.resolve() != target.resolve():
                    shutil.copy2(src, target)
                    copied += 1
        name = target.name
        thumb_rel = pathlib.PurePosixPath("thumbs") / pathlib.PurePosixPath(str(target_rel))
        thumb = IMAGES / century / pathlib.Path(str(thumb_rel))
        make_thumb(target, thumb)
        if thumb.exists():
            thumbs += 1
        row = {
            "id": rid,
            "title": fm.get("title") or rid,
            "title_en": fm.get("title_en"),
            "year": fm.get("year"),
            "date_label": fm.get("date_label"),
            "collection": collection,
            "content_type": fm.get("content_type") or "photograph",
            "decade": decade,
            "path": "%s/%s/%s" % (collection, decade, name),
            "url": "https://%s.chenhua.net/%s/%s/%s" % (century, collection, decade, name),
            "preview_url": "/next/images/%s/%s/%s/%s" % (century, collection, decade, name),
            "thumb_url": "https://%s.chenhua.net/thumbs/%s/%s/%s" % (century, collection, decade, name),
            "thumb_preview_url": "/next/images/%s/thumbs/%s/%s/%s" % (century, collection, decade, name),
            "detail_collection": collection,
            "detail_slug": rid,
            "sha256": info.get("sha256"),
            "bytes": target.stat().st_size if target.exists() else info.get("bytes"),
            "width": info.get("width"),
            "height": info.get("height"),
            "region": fm.get("region"),
            "topic": fm.get("topic"),
            "curation_theme": fm.get("curation_theme"),
            "primary": True,
        }
        if rid not in seen:
            by_shard[(century, collection)].append(row)
            seen.add(rid)

        # Optional detail images: record paths point at the deployed image.
        for item in (fm.get("images") or []):
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "")
            marker = "https://%s.chenhua.net/" % century
            if not path.startswith(marker):
                continue
            rel = path[len(marker):]
            extra = IMAGES / century / pathlib.Path(rel)
            if not extra.exists() or rel.split("/")[-1] == name:
                continue
            extra_thumb_rel = pathlib.PurePosixPath("thumbs") / pathlib.PurePosixPath(rel)
            extra_thumb = IMAGES / century / pathlib.Path(str(extra_thumb_rel))
            make_thumb(extra, extra_thumb)
            by_shard[(century, collection)].append({
                "id": "%s-%s" % (rid, item.get("role") or "detail"),
                "title": fm.get("title") or rid,
                "title_en": fm.get("title_en"),
                "year": fm.get("year"),
                "date_label": fm.get("date_label"),
                "collection": collection,
                "content_type": fm.get("content_type") or "painting",
                "decade": decade,
                "path": rel,
                "url": path,
                "preview_url": "/next/images/%s/%s" % (century, rel),
                "thumb_url": "https://%s.chenhua.net/thumbs/%s" % (century, rel),
                "thumb_preview_url": "/next/images/%s/thumbs/%s" % (century, rel),
                "detail_collection": collection,
                "detail_slug": rid,
                "sha256": item.get("sha256"),
                "bytes": extra.stat().st_size,
                "width": item.get("width"),
                "height": item.get("height"),
                "region": fm.get("region"),
                "topic": fm.get("topic"),
                "curation_theme": fm.get("curation_theme"),
                "primary": False,
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
            "- 缩略图：`thumbs/...`（480px，画廊首屏用）\n"
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
    print("硬链接 %d · 复制 %d · 缩略图 %d" % (linked, copied, thumbs))


if __name__ == "__main__":
    main()
