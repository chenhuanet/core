# -*- coding: utf-8 -*-
"""压缩世纪图片仓里的展示图，并回写内容 frontmatter。

规则：
  - 长边最大 1600px，JPEG quality 82，PNG optimize。
  - 原图留在 assets/img，不修改；只替换 next/images 下的硬链接/副本。
  - 原 sha256 保留为 image_original_sha256；新 sha256 写入 image_sha256。
"""
import hashlib
import json
import os
import pathlib
import sys
import time

import yaml
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[2]
NEXT = ROOT / "next"
PREVIEW = NEXT / "preview-images.json"
CONTENT = NEXT / "content"

MAX_EDGE = 1600
JPEG_QUALITY = 82
Image.MAX_IMAGE_PIXELS = None


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_md(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    return yaml.safe_load(text[4:end]) or {}, text


def write_md(path, fm, text):
    end = text.find("\n---\n", 4)
    body = text[end + 5:] if end >= 0 else "\n" + text
    out = "---\n" + yaml.safe_dump(
        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
    ) + "---\n" + body
    path.write_text(out, encoding="utf-8", newline="\n")


def compress_one(src, target, ext):
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        if max(w, h) > MAX_EDGE:
            scale = MAX_EDGE / float(max(w, h))
            im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                           Image.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        if ext in (".jpg", ".jpeg"):
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(tmp, format="JPEG", quality=JPEG_QUALITY, optimize=True,
                    progressive=True)
        elif ext == ".png":
            if im.mode == "P":
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")
            im.save(tmp, format="PNG", optimize=True, compress_level=9)
        else:
            raise ValueError("unsupported extension: %s" % ext)
        os.replace(tmp, target)
        return im.size


def main():
    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    before = sum((ROOT / v["source"]).stat().st_size for v in preview.values())
    after = 0
    done = skipped = failed = 0
    failures = []
    t0 = time.time()

    for i, (rid, info) in enumerate(preview.items(), 1):
        src = ROOT / info["source"]
        target = ROOT / info["target"]
        ext = pathlib.PurePosixPath(info["target"]).suffix.lower()
        if not src.exists():
            failed += 1
            failures.append((rid, "source missing"))
            continue
        try:
            old_sha = info.get("sha256") or sha256_file(src)
            new_size = compress_one(src, target, ext)
            new_sha = sha256_file(target)
            new_bytes = target.stat().st_size
            info.update({
                "sha256": new_sha,
                "bytes": new_bytes,
                "width": new_size[0],
                "height": new_size[1],
                "original_sha256": old_sha,
            })
            md = CONTENT / info["collection"] / info["decade"] / ("%s.md" % rid)
            if md.exists():
                fm, text = read_md(md)
                fm["image_original_sha256"] = old_sha
                fm["image_sha256"] = new_sha
                fm["image_bytes"] = new_bytes
                fm["image_width"] = new_size[0]
                fm["image_height"] = new_size[1]
                fm["image_processing"] = "long-edge-%d-q%d" % (MAX_EDGE, JPEG_QUALITY)
                write_md(md, fm, text)
            else:
                skipped += 1
            after += new_bytes
            done += 1
        except Exception as e:
            failed += 1
            failures.append((rid, str(e)))
        if i % 100 == 0:
            print("  %d / %d" % (i, len(preview)), flush=True)

    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=1),
                       encoding="utf-8", newline="\n")
    print("压缩完成：%d 张 · 跳过 %d · 失败 %d · %.1fs" % (
        done, skipped, failed, time.time() - t0))
    print("体积：%.1f MB → %.1f MB（%.0f%%）" % (
        before / 1048576, after / 1048576,
        100.0 * after / before if before else 0))
    if failures:
        print("失败样例：")
        for rid, err in failures[:10]:
            print(" ", rid, err)


if __name__ == "__main__":
    main()
