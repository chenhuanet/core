# -*- coding: utf-8 -*-
"""用 Cleveland Open Access API 补全被截断的克利夫兰题名。"""
import json
import pathlib
import re
import time
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
COLLECTIONS = ("photos", "paintings", "objects", "links")


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


def update_alt(body, title):
    return re.sub(r"^!\[[^\]]*\]\(", "![" + title.replace("]", "\\]") + "](", body, count=1)


def fetch(accession):
    url = "https://openaccess-api.clevelandart.org/api/artworks/%s" % accession
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ChenhuaContent/0.2"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            data = d.get("data") or {}
            title = data.get("title") or ""
            if not title:
                tomb = data.get("tombstone") or ""
                title = tomb.split(". ", 1)[0]
            return title.strip()
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5)


def main():
    fixed = missed = 0
    for c in COLLECTIONS:
        for p in (CONTENT / c).glob("*/*.md"):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            if not fm.get("title_truncated"):
                continue
            if fm.get("source_short") != "克利夫兰艺术博物馆":
                continue
            page = str(fm.get("page_url") or "")
            accession = page.rstrip("/").split("/")[-1]
            title = fetch(accession)
            if not title:
                missed += 1
                continue
            fm["title_original"] = fm.get("title")
            fm["title"] = title
            fm["title_note"] = "按 Cleveland 对象页补全"
            fm.pop("title_truncated", None)
            body = update_alt(body, title)
            write_md(p, fm, body)
            fixed += 1
            time.sleep(0.5)
    print("Cleveland 题名补全：%d · 仍未取到：%d" % (fixed, missed))


if __name__ == "__main__":
    main()
