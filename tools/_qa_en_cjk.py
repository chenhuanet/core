import pathlib, re, sys

root = pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\dist")
cjk = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")
# find any element carrying data-l="en" whose immediate text contains CJK
pat = re.compile(r'<([a-zA-Z][\w-]*)([^>]*\bdata-l="en"[^>]*)>(.*?)</\1>', re.S)
bad = []
count = 0
for p in root.rglob("*.html"):
    t = p.read_text(encoding="utf-8")
    for m in pat.finditer(t):
        count += 1
        body = re.sub(r"<[^>]+>", "", m.group(3))
        if cjk.search(body):
            bad.append((str(p.relative_to(root)), body.strip()[:90]))
print("en blocks", count, "cjk", len(bad))
for x in bad[:30]:
    print(x)
