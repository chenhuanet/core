# -*- coding: utf-8 -*-
from pathlib import Path

pairs = [
    ('"staticPhotoBase": "https://photo.chenhua.net/photo/"', '"staticPhotoBase": ""'),
    ('"staticPaintBase": "https://paint.chenhua.net/painting/"', '"staticPaintBase": ""'),
]
n = 0
for site in ("main", "paint", "photo"):
    for p in (Path("workspace/release") / site).rglob("*.html"):
        text = p.read_text(encoding="utf-8")
        new = text
        for old, rep in pairs:
            new = new.replace(old, rep)
        if new != text:
            p.write_text(new, encoding="utf-8")
            n += 1
print("patched", n)
