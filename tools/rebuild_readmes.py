# -*- coding: utf-8 -*-
"""按当前记录重建各 collection/decade 的 README 索引，保持原有表格格式。"""
import collections
import pathlib

import yaml

ROOT = pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\content")


def fm(p):
    t = p.read_text(encoding="utf-8")
    e = t.find("\n---\n", 4)
    return yaml.safe_load(t[4:e]) or {}


def main():
    for c in ("photos", "paintings", "objects", "links"):
        base = ROOT / c
        if not base.exists():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            rows = []
            for p in d.glob("*.md"):
                if p.name == "README.md":
                    continue
                x = fm(p)
                if x.get("id"):
                    rows.append(x)
            if not rows:
                continue
            rows.sort(key=lambda x: (x.get("year") or 0, str(x.get("title") or "")))
            lines = ["# %s · %s · %d 条" % (c, d.name, len(rows)), "",
                     "| 年 | 标题 | 类型 | 主题 | 地域 | 来源 |",
                     "| --- | --- | --- | --- | --- | --- |"]
            for x in rows:
                title = str(x.get("title") or x["id"]).replace("|", "\\|")
                lines.append("| %s | [%s](%s.md) | %s | %s | %s | %s |" % (
                    x.get("year") or "", title, x["id"],
                    x.get("content_type") or "", x.get("topic") or "",
                    x.get("region") or "", x.get("source_short") or x.get("source") or ""))
            (d / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            print(c, d.name, len(rows))


if __name__ == "__main__":
    main()
