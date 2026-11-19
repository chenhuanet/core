import os, re

ROOT = os.path.join(os.path.dirname(__file__), "..", "dist")
PHRASES = ["故事只有一篇", "入口应该有三个", "75001", "同一个档案馆", "三种读法", "档案馆", "只有一篇", "三种方式", "三种入口", "读法", "不止一种", "一站式", "沉浸式", "叙事", "解构", "重新发现", "被看见", "时间切片", "打开方式"]

for base, dirs, files in os.walk(ROOT):
    for name in files:
        if not name.endswith((".html", ".js", ".json", ".css")):
            continue
        path = os.path.join(base, name)
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        hits = []
        for phrase in PHRASES:
            if phrase in text:
                hits.append(phrase)
        if hits:
            rel = os.path.relpath(path, ROOT)
            print(f"{rel}: {', '.join(hits)}")
