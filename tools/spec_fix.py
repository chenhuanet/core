# -*- coding: utf-8 -*-
"""修正新规范校验发现的问题：evidence 类型、正文图片 alt、专题封面。"""
import json
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
ORIG = ROOT / "archive" / "legacy-content" / "photos"
COLLECTIONS = ("photos", "paintings", "objects", "links")

BAD_EVIDENCE = {
    "auto-768ea122",
    "auto-2df8ce6f",
    "auto-5aef6dca",
    "auto-dc10d302",
}


def read_md(path):
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end < 0:
        return {}, text
    return yaml.safe_load(text[4:end]) or {}, text[end + 5:]


def write_md(path, fm, body):
    path.write_text("---\n" + yaml.safe_dump(
        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
    ) + "---\n" + body, encoding="utf-8", newline="\n")


def alt_text(title):
    return str(title or "").replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def fix_body(body, image, title):
    if not image:
        return body
    marker = "](" + image + ")"
    idx = body.find(marker)
    if idx < 0:
        return "![%s](%s)\n\n" % (alt_text(title), image) + body.lstrip("\n")
    start = body.rfind("![", 0, idx)
    if start < 0:
        return body
    return body[:start] + "![" + alt_text(title) + marker + body[idx + len(marker):]


def main():
    fixed_evidence = fixed_body = 0
    for c in COLLECTIONS:
        for p in (CONTENT / c).glob("*/*.md"):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            rid = fm.get("id")
            changed = False
            if rid in BAD_EVIDENCE and not isinstance(fm.get("evidence"), dict):
                orig_path = ORIG / ("%s.json" % rid)
                if orig_path.exists():
                    orig = json.loads(orig_path.read_text(encoding="utf-8"))
                    if isinstance(orig.get("evidence"), dict):
                        fm["type_evidence"] = str(fm.get("evidence") or "")
                        fm["evidence"] = orig["evidence"]
                        fixed_evidence += 1
                        changed = True
            if c != "links":
                new_body = fix_body(body, fm.get("image"), fm.get("title"))
                if new_body != body:
                    body = new_body
                    fixed_body += 1
                    changed = True
            if changed:
                write_md(p, fm, body)
    print("规范修正：evidence %d · 正文图片 %d" % (fixed_evidence, fixed_body))


if __name__ == "__main__":
    main()
