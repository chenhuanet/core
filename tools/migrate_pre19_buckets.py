# -*- coding: utf-8 -*-
"""Move the 60 pre-1800 paintings from 19century to pre19century.

Changes both the image files/manifests source map and the Markdown records.
Run with --dry-run first; --apply is idempotent.
"""
import argparse
import json
import pathlib
import re
import shutil

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
PAINTINGS = CONTENT / "paintings"
PREVIEW_PATH = ROOT / "next" / "preview-images.json"
IMAGES = ROOT / "next" / "images"
BACKUP = ROOT / ".tmp" / "migrate-pre19-backup"


def read(path):
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end < 0:
        raise ValueError("bad frontmatter")
    return yaml.safe_load(text[4:end]) or {}, text[end + 5:]


def write(path, fm, body):
    text = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False,
                                    default_flow_style=False, width=1000) + "---\n" + body
    path.write_text(text, encoding="utf-8", newline="\n")


def rights_status(license_text):
    s = str(license_text or "").lower()
    if "cc0" in s:
        return "CC0"
    if "public domain" in s or "公有领域" in s or "pd" in s.split():
        return "PD"
    if "cc by-sa" in s or "cc-by-sa" in s:
        return "CC-BY-SA"
    if "cc by" in s or "cc-by" in s:
        return "CC-BY"
    return "PD"


def curation_theme(fm):
    if fm.get("curation_theme"):
        return fm["curation_theme"]
    topic = str(fm.get("topic") or "")
    if topic in ("信仰", "神话"):
        return "信仰与图像"
    if topic in ("山水", "风景", "远方"):
        return "山水与自然"
    if topic in ("文字", "馆藏", "痕迹"):
        return "文字与观看"
    if topic in ("街巷", "劳作", "世事", "战火", "灾变", "权利"):
        return "城市与日常"
    if topic in ("面孔",):
        return "人物与自我"
    return "人物与自我"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    preview = json.loads(PREVIEW_PATH.read_text(encoding="utf-8"))
    records = []
    bad = []
    for path in sorted(PAINTINGS.glob("*/*.md")):
        try:
            fm, body = read(path)
        except Exception as exc:
            bad.append("%s: %s" % (path.name, exc))
            continue
        if fm.get("collection") == "paintings" and isinstance(fm.get("year"), int) \
                and fm["year"] < 1800:
            records.append((path, fm, body))
    print("records:", len(records), "bad:", bad[:5])
    moved = 0
    missing = []
    for path, fm, body in records:
        rid = fm["id"]
        info = preview.get(rid)
        if not info:
            missing.append(rid + " (no preview map)")
            continue
        old_target = info["target"]
        new_target = old_target.replace("next/images/19century/", "next/images/pre19century/")
        if not new_target.startswith("next/images/pre19century/"):
            missing.append(rid + " (target not 19century)")
            continue
        src = ROOT / old_target
        dst = ROOT / new_target
        if not dst.exists():
            if not src.exists():
                missing.append(rid + " (image missing)")
                continue
            if args.apply:
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    dst.hardlink_to(src)
                except Exception:
                    shutil.copy2(src, dst)
        if args.apply:
            BACKUP.mkdir(parents=True, exist_ok=True)
            if not (BACKUP / path.name).exists():
                shutil.copy2(path, BACKUP / path.name)
            info["century"] = "pre19century"
            info["target"] = new_target
            info["thumb_target"] = new_target.replace(
                "/pre19century/paintings/", "/pre19century/thumbs/paintings/")
            fm["image"] = str(fm.get("image") or "").replace(
                "https://19century.chenhua.net/", "https://pre19century.chenhua.net/")
            body = body.replace("https://19century.chenhua.net/",
                                "https://pre19century.chenhua.net/")
            fm["image_century"] = "pre19century"
            fm["image_width"] = info.get("width") or fm.get("image_width")
            fm["image_height"] = info.get("height") or fm.get("image_height")
            fm["image_sha256"] = info.get("sha256") or fm.get("image_sha256")
            fm.setdefault("image_alt_zh", fm.get("title"))
            fm.setdefault("image_alt_en", fm.get("title_en") or fm.get("title"))
            fm.setdefault("image_credit", (fm.get("credit_line") or "") + " / " + (fm.get("source_short") or ""))
            fm.setdefault("rights_status", rights_status(fm.get("license")))
            fm.setdefault("license_url", "https://creativecommons.org/publicdomain/mark/1.0/")
            fm.setdefault("year_basis", "original")
            fm.setdefault("object_year", None)
            fm.setdefault("curation_theme", curation_theme(fm))
            if not fm.get("period"):
                fm["period"] = "%ds" % (int(fm["year"]) // 10 * 10)
            if not fm.get("era"):
                fm["era"] = "%d世纪" % ((int(fm["year"]) - 1) // 100 + 1)
            if not fm.get("attribution_status"):
                fm["attribution_status"] = "confirmed" if fm.get("creator_status") == "named" else "uncertain"
            if not fm.get("version_status"):
                fm["version_status"] = "copy" if "摹" in str(fm.get("date_label") or "") else "original"
            if not fm.get("provenance_note"):
                fm["provenance_note"] = ""
            write(path, fm, body)
            moved += 1
        else:
            moved += 1
    if args.apply:
        PREVIEW_PATH.write_text(json.dumps(preview, ensure_ascii=False, indent=1) + "\n",
                                encoding="utf-8", newline="\n")
    print("moved:", moved, "missing:", missing[:10])
    if missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
