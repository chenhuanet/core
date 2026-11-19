import os, re, json
root = r"C:\Users\chenhua\Desktop\chenhua\next\content"
terms = re.compile(r"地图|地圖|舆图|輿圖|疆域|map\b|Map\b|atlas\b", re.I)
rows = []
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.lower().endswith(".md"):
            continue
        p = os.path.join(dp, f)
        txt = open(p, encoding="utf-8").read()
        title = ""
        m = re.search(r"^title:\s*(.+)$", txt, re.M)
        if m: title = m.group(1).strip()
        if terms.search(title):
            rows.append((os.path.relpath(p, root), title))
print("map-like titles", len(rows))
for r in rows[:80]: print(r[0], "|", r[1])
