# -*- coding: utf-8 -*-
"""Pad very short meta/og descriptions in the current release (future builds do it in sitekit)."""
import re
from pathlib import Path

RELEASE = Path("workspace/release")
DESC = re.compile(r'(<meta name="description" content=")([^"]*)(")', re.I)
OG = re.compile(r'(<meta property="og:description" content=")([^"]*)(")', re.I)
ZH = "尘画历史影像与视觉资料索引"
EN = "An index of historical images and visual culture"


def pad(text, tail):
    text = text.strip()
    if len(text) >= 20:
        return text
    return (text + " · " if text else "") + tail


count = 0
for p in RELEASE.rglob("*.html"):
    html = p.read_text(encoding="utf-8")
    en = p.relative_to(RELEASE).as_posix().split("/", 1)[1].startswith("en/") if "/" in p.relative_to(RELEASE).as_posix() else False
    tail = EN if en else ZH
    new = DESC.sub(lambda m: m.group(1) + pad(m.group(2), tail) + m.group(3), html)
    new = OG.sub(lambda m: m.group(1) + pad(m.group(2), tail) + m.group(3), new)
    if new != html:
        p.write_text(new, encoding="utf-8")
        count += 1
print("padded", count)
