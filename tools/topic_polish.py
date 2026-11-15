# -*- coding: utf-8 -*-
"""街巷主题复审：只改题名/画面能直接支撑的条目。"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"

THEME = {"面孔": "人间", "街巷": "人间", "劳作": "人间",
         "战火": "世事", "灾变": "世事", "权利": "世事",
         "远方": "天地", "风景": "天地", "痕迹": "技艺"}

FIX = {}
for rid in [
    "auto-9d51e82c", "auto-0f5644ba", "auto-2386b6db", "auto-5313e057",
    "auto-b22c9ba0", "auto-f2137056", "auto-843ff6a2", "auto-a1a66c3b",
    "auto-f96631dc", "auto-505fc4ea",
]:
    FIX[rid] = "面孔"
for rid in ["auto-842331b8", "auto-c0e6b4bd"]:
    FIX[rid] = "远方"
for rid in [
    "auto-8c080ab0", "auto-9f21e83e", "auto-8365b881", "auto-cd92d782",
    "auto-4c287d82", "auto-6789e3ba", "auto-19a586ae", "auto-d415edb0",
    "auto-67f9ec22", "auto-663eeeac", "auto-7f45ffe9", "auto-028ad92f",
    "auto-11c15b50", "auto-12121563", "auto-2e7c6547", "auto-8df6958a",
    "auto-a9cd905e", "auto-b4c97918", "auto-c9bb727b", "auto-1dc35f40",
    "auto-543128bb", "auto-8440bef5", "auto-9a76eac6", "auto-ccac2df7",
    "auto-fe19ea31",
]:
    FIX[rid] = "战火"
for rid in ["auto-0fd59fdf", "auto-571a4b0f", "auto-2efbc131", "auto-5d500d59", "auto-8c4b10dc"]:
    FIX[rid] = "灾变"
for rid in ["cle-35395512", "cle-2e4f1ddc", "cle-b667de05", "cle-117ea105", "auto-db5ba509"]:
    FIX[rid] = "风景"
for rid in ["auto-edf40d26", "auto-dd42e382", "auto-770ff3fb", "auto-7e278f92", "auto-972653ca"]:
    FIX[rid] = "劳作"


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


def main():
    changed = 0
    for p in (CONTENT / "photos").glob("*/*.md"):
        if p.name == "README.md":
            continue
        fm, body = read_md(p)
        rid = fm.get("id")
        if rid not in FIX or fm.get("topic") != "街巷":
            continue
        fm["topic"] = FIX[rid]
        fm["theme"] = THEME.get(fm["topic"], fm.get("theme"))
        fm["topic_note"] = "人工按题名/画面复核校正"
        write_md(p, fm, body)
        changed += 1
    print("街巷主题复审：修正 %d 条" % changed)


if __name__ == "__main__":
    main()
