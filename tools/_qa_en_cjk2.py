import pathlib, re, collections

root = pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\dist")
cjk = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")
pat = re.compile(r'<([a-zA-Z][\w-]*)([^>]*\bdata-l="en"[^>]*)>(.*?)</\1>', re.S)
bad = collections.Counter()
samples = {}
for p in root.rglob("*.html"):
    t = p.read_text(encoding="utf-8")
    for m in pat.finditer(t):
        body = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if not body or body == "中文":
            continue
        if cjk.search(body):
            bad[body] += 1
            samples.setdefault(body, str(p.relative_to(root)))
print("unique bad", len(bad), "occurrences", sum(bad.values()))
for text, n in bad.most_common(40):
    print(n, "|", samples[text], "|", text[:130])
