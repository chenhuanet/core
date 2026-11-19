import os, re
root = r"C:\Users\chenhua\Desktop\chenhua\next\content"
pat = re.compile(r"(?:File:|image:|source_image:).*(?:map|Map|MAP|地图|地圖|舆图|輿圖)", re.I)
url = re.compile(r"https?://\S+")
rows = []
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.lower().endswith(".md"): continue
        p = os.path.join(dp, f)
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            if pat.search(line):
                rows.append((os.path.relpath(p, root), i, url.sub("[URL]", line.strip())[:160]))
print("map-like file refs", len(rows))
for r in rows[:60]: print(r[0], r[1], r[2])
