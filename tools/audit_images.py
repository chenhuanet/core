# -*- coding: utf-8 -*-
"""Audit the four image repositories before split/deploy."""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "next" / "images"
BUILD_ID = "20261123c"
CENTURIES = ("pre19century", "19century", "20century", "21century")
EXPECTED_PRIMARY = {"pre19century": 300, "19century": 773, "20century": 1058, "21century": 67}
THEMES = ("faith", "landscape", "portrait", "city", "word", "material")
H1_RE = re.compile(r"<h1\b", re.I)
JS_RE = re.compile(r'gallery\.js\?v=([0-9A-Za-z._-]+)')


def main():
    errors = []
    stats = {}
    for century in CENTURIES:
        folder = IMAGES / century
        if not folder.is_dir():
            errors.append("%s: missing folder" % century)
            continue
        index = folder / "index.html"
        if not index.exists():
            errors.append("%s: missing index.html" % century)
            continue
        text = index.read_text(encoding="utf-8", errors="ignore")
        if len(H1_RE.findall(text)) != 1:
            errors.append("%s: index h1=%d" % (century, len(H1_RE.findall(text))))
        m = JS_RE.search(text)
        if not m or m.group(1) != BUILD_ID:
            errors.append("%s: gallery.js version %r" % (century, m.group(1) if m else None))
        if ('"century": "%s"' % century) not in text:
            errors.append("%s: GALLERY_CONFIG century mismatch" % century)

        manifest_path = folder / "manifests" / "paintings.json"
        photos_path = folder / "manifests" / "photos.json"
        objects_path = folder / "manifests" / "objects.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"images": []}
        photos = json.loads(photos_path.read_text(encoding="utf-8")) if photos_path.exists() else {"images": []}
        objects = json.loads(objects_path.read_text(encoding="utf-8")) if objects_path.exists() else {"images": []}
        rows = (manifest.get("images") or []) + (photos.get("images") or []) + (objects.get("images") or [])
        primary = [r for r in rows if r.get("primary") is True]
        if len(primary) != EXPECTED_PRIMARY[century]:
            errors.append("%s: primary %d != %d" % (century, len(primary), EXPECTED_PRIMARY[century]))
        if len({r.get("id") for r in rows}) != len(rows):
            errors.append("%s: duplicate manifest ids" % century)
        missing_images = []
        missing_thumbs = []
        for r in primary:
            path = folder / str(r.get("path") or "")
            thumb = folder / "thumbs" / str(r.get("path") or "")
            if not path.is_file():
                missing_images.append(str(path.relative_to(folder)))
            if not thumb.is_file():
                missing_thumbs.append(str(thumb.relative_to(folder)))
            expected = "https://%s.chenhua.net/%s" % (century, r.get("path"))
            if r.get("url") != expected:
                errors.append("%s: bad url for %s" % (century, r.get("id")))
        if missing_images:
            errors.append("%s: missing images %d (e.g. %s)" % (century, len(missing_images), missing_images[:3]))
        if missing_thumbs:
            errors.append("%s: missing thumbs %d (e.g. %s)" % (century, len(missing_thumbs), missing_thumbs[:3]))

        theme_count = 0
        if century == "pre19century":
            for slug in THEMES:
                theme = folder / "themes" / slug / "index.html"
                if not theme.exists():
                    errors.append("pre19century: missing theme %s" % slug)
                    continue
                ttext = theme.read_text(encoding="utf-8", errors="ignore")
                theme_count += 1
                if len(H1_RE.findall(ttext)) != 1:
                    errors.append("pre19century/theme %s: h1=%d" % (slug, len(H1_RE.findall(ttext))))
                tm = JS_RE.search(ttext)
                if not tm or tm.group(1) != BUILD_ID:
                    errors.append("pre19century/theme %s: gallery version %r" % (slug, tm.group(1) if tm else None))
                if '"manifestBase": "../../"' not in ttext:
                    errors.append("pre19century/theme %s: manifestBase missing" % slug)
                if '"preview": true' in ttext:
                    errors.append("pre19century/theme %s: preview still true" % slug)
            sitemap = folder / "sitemap.xml"
            if sitemap.exists():
                stext = sitemap.read_text(encoding="utf-8")
                for slug in THEMES:
                    if "themes/%s/" % slug not in stext:
                        errors.append("pre19century: sitemap missing theme %s" % slug)
            else:
                errors.append("pre19century: missing sitemap.xml")
        stats[century] = {"primary": len(primary), "rows": len(rows), "themes": theme_count,
                          "missing_images": len(missing_images), "missing_thumbs": len(missing_thumbs)}

    result = {"ok": not errors, "build_id": BUILD_ID, "stats": stats, "errors": errors[:30]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
