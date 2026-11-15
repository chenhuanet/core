# -*- coding: utf-8 -*-
"""第二轮题名收尾：去掉尾随空格，补全三位年份截断，处理少数手工题名。"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
COLLECTIONS = ("photos", "paintings", "objects", "links")

MANUAL = {
    "auto-256d170f": "Edith White - Still Life with Grapes (c. 1900)",
    "auto-dd7aafa6": "Marius Bauer - A Street in Cairo (etching)",
    "auto-2df8ce6f": "Portrait of a Boy, by George Benjamin Luks",
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


def update_alt(body, title):
    return re.sub(r"^!\[[^\]]*\]\(", "![" + title.replace("]", "\\]") + "](", body, count=1)


def complete(title, desc):
    desc = str(desc or "").strip()
    if not desc:
        return None
    first = re.split(r"\s*\|\s*|\n", desc)[0].strip()
    if first.lower().startswith(title.lower()) and len(first) > len(title):
        return first[:140].rstrip()
    return None


def main():
    cleaned = completed = flagged = 0
    for c in COLLECTIONS:
        for p in (CONTENT / c).glob("*/*.md"):
            if p.name == "README.md":
                continue
            fm, body = read_md(p)
            title = str(fm.get("title") or "")
            desc = (fm.get("license_snapshot") or {}).get("description") or ""
            new = None
            note = None
            if fm.get("id") in MANUAL:
                new = MANUAL[fm["id"]]
                note = "题名按源站对象页清理"
            elif fm.get("title_truncated") or title.endswith("…"):
                base = title.rstrip("…").strip()
                cand = complete(base, desc)
                if cand:
                    new = cand
                    note = "按源站描述补全题名"
                    fm.pop("title_truncated", None)
                    completed += 1
            else:
                stripped = title.rstrip()
                if stripped != title:
                    new = stripped
                    note = "去除题名尾随空格"
                    cleaned += 1
                if re.search(r"\b(18|19|20)\d$", stripped) or (new and new != title):
                    cand = complete(stripped, desc)
                    if cand and len(cand) > len(stripped):
                        new = cand
                        note = "按源站描述补全题名"
                        completed += 1
                    elif re.search(r"\b(18|19|20)\d$", stripped):
                        new = stripped + "…"
                        note = "源站题名在采集时截断，未补全"
                        fm["title_truncated"] = True
                        flagged += 1
            if new and new != title:
                fm["title_original"] = title
                fm["title"] = new
                fm["title_note"] = note
                if not fm.get("title_truncated"):
                    fm.pop("title_truncated", None)
                body = update_alt(body, new)
                write_md(p, fm, body)
    print("题名第二轮：去空格 %d · 补全 %d · 标记截断 %d" % (cleaned, completed, flagged))


if __name__ == "__main__":
    main()
