# -*- coding: utf-8 -*-
"""Validate 19th-century-and-earlier painting records before build.

This is intentionally stricter than painting.schema.json: the old catalog
predates the early-art fields, so only records with ``year < 1800`` are checked.
"""
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
PAINTINGS = CONTENT / "paintings"
SCHEMA = json.loads((CONTENT / "schema" / "early_painting.schema.json").read_text(encoding="utf-8"))
TAX = json.loads((CONTENT / "schema" / "taxonomy.json").read_text(encoding="utf-8"))

REQUIRED = SCHEMA["required"]
ALLOWED = {
    "content_type": set(SCHEMA["allowed_content_types"]),
    "medium": set(SCHEMA["allowed_mediums"]),
    "topic": set(SCHEMA["allowed_topics"]),
    "curation_theme": set(SCHEMA["allowed_curation_themes"]),
    "attribution_status": set(SCHEMA["allowed_attribution_status"]),
    "version_status": set(SCHEMA["allowed_version_status"]),
    "rights_status": set(SCHEMA["allowed_rights_status"]),
}
REGIONS = set(TAX["region"])


def read(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated frontmatter")
    return yaml.safe_load(text[4:end]) or {}, text[end + 5:]


def main():
    errors = []
    checked = 0
    for path in sorted(PAINTINGS.glob("*/*.md")):
        if path.name == "README.md":
            continue
        try:
            fm, body = read(path)
        except Exception as exc:
            errors.append((path.name, "frontmatter: %s" % exc))
            continue
        if not isinstance(fm, dict) or fm.get("collection") != "paintings":
            continue
        year = fm.get("year")
        if not isinstance(year, int) or year >= 1800 or year < 300:
            continue
        checked += 1
        for key in REQUIRED:
            if fm.get(key) in (None, ""):
                errors.append((path.name, "missing required field: %s" % key))
        for key, allowed in ALLOWED.items():
            value = fm.get(key)
            if value is not None and value not in allowed:
                errors.append((path.name, "invalid %s: %r" % (key, value)))
        if fm.get("region") not in REGIONS:
            errors.append((path.name, "invalid region: %r" % fm.get("region")))
        if not isinstance(fm.get("year"), int):
            errors.append((path.name, "year is not an integer"))
        if fm.get("period") and not re.fullmatch(r"\d{3,4}s", str(fm["period"])):
            errors.append((path.name, "period not YYYYs: %r" % fm.get("period")))
        image = str(fm.get("image") or "")
        if not image.startswith("https://pre19century.chenhua.net/"):
            errors.append((path.name, "image not on pre19century: %s" % image[:90]))
        if str(fm.get("image_century")) != "pre19century":
            errors.append((path.name, "image_century != pre19century"))
        if not fm.get("image_sha256") or not re.fullmatch(r"[0-9a-f]{64}", str(fm.get("image_sha256"))):
            errors.append((path.name, "invalid image_sha256"))
        if not fm.get("image_width") or not fm.get("image_height"):
            errors.append((path.name, "missing image dimensions"))
        if image and image not in body:
            errors.append((path.name, "body does not reference the image URL"))
        imgs = fm.get("images") or []
        if not isinstance(imgs, list):
            errors.append((path.name, "images must be a list"))
        else:
            roles = set(SCHEMA["allowed_image_roles"])
            for item in imgs:
                if not isinstance(item, dict):
                    errors.append((path.name, "images item is not an object"))
                    continue
                if item.get("role") not in roles:
                    errors.append((path.name, "invalid image role: %r" % item.get("role")))
                for key in ("path", "alt_zh", "alt_en"):
                    if not item.get(key):
                        errors.append((path.name, "images missing %s" % key))
    if errors:
        print("EARLY VALIDATION FAILED: %d errors / %d records" % (len(errors), checked))
        for name, msg in errors[:40]:
            print("  %s: %s" % (name, msg))
        return 1
    print("EARLY VALIDATION OK: %d records" % checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
