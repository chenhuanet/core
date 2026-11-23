# -*- coding: utf-8 -*-
"""Patch the deployed painting detail pages in place: only the Chinese body."""
import json
import pathlib
import re
from html import escape

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAINT = ROOT / "repos-git" / "paint"
bundle = (PAINT / "data" / "bundle.js").read_text(encoding="utf-8")
data, _ = json.JSONDecoder().raw_decode(bundle.split("=", 1)[1].lstrip())
rows = [r for r in data["records"] if r.get("collection") == "paintings"
        and r.get("content_type") == "painting"]

REPLACEMENTS = [
    ("《女史箴图》", ""),
]

changed = 0
missing = []
for r in rows:
    path = PAINT / "painting" / (r["id"] + ".html")
    if not path.exists():
        missing.append(r["id"])
        continue
    text = path.read_text(encoding="utf-8")
    note = r.get("note", "").strip()
    if not note:
        continue
    start = text.find("<p>《女史箴图》")
    if start < 0:
        # Already-correct page or another layout.
        continue
    # The English body begins at the first English paragraph after the bad block.
    m = re.search(r"<p>(?:[A-Z][^<]{20,}|The [^<]{20,})</p>", text[start:])
    if not m:
        missing.append(r["id"] + ":end")
        continue
    end = start + m.start()
    paras = "".join("<p>%s</p>" % escape(p.strip()) for p in note.split("\n\n") if p.strip())
    text = text[:start] + paras + text[end:]
    title = r.get("title", "").strip("《》")
    text = text.replace('alt="《女史箴图》"', 'alt="%s"' % title)
    text = text.replace('data-alt-zh="《女史箴图》"', 'data-alt-zh="%s"' % title)
    text = re.sub(r"site\.js\?v=[0-9A-Za-z]+", "site.js?v=20261123c", text)
    path.write_text(text, encoding="utf-8", newline="\n")
    changed += 1

print("patched", changed, "missing", missing[:10], "count", len(missing))
