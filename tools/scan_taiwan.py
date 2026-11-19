import os, re, json
root = r"C:\Users\chenhua\Desktop\chenhua\next\content"
files = []
for dp, _, fs in os.walk(root):
    for f in fs:
        if f.lower().endswith((".md", ".json")):
            files.append(os.path.join(dp, f))

url_re = re.compile(r"https?://\S+")
def clean(s):
    s = url_re.sub("[URL]", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

zh_hits = []
en_hits = []
for p in files:
    try:
        text = open(p, encoding="utf-8").read()
    except Exception:
        continue
    for m in re.finditer("台湾|臺灣", text):
        a = max(0, m.start() - 18); b = min(len(text), m.end() + 22)
        ctx = clean(text[a:b])
        before = text[max(0, m.start()-2):m.start()]
        if before.endswith("中国"):
            continue
        zh_hits.append((os.path.relpath(p, root), m.start(), ctx))
    for m in re.finditer("Taiwan", text, re.I):
        a = max(0, m.start() - 25); b = min(len(text), m.end() + 30)
        ctx = clean(text[a:b])
        before = text[max(0, m.start()-12):m.start()].lower()
        after = text[m.end():m.end()+10].lower()
        if "china" in before or after.startswith(", china") or after.startswith(" china"):
            continue
        en_hits.append((os.path.relpath(p, root), m.start(), ctx))

print("ZH suspicious", len(zh_hits))
for h in zh_hits[:80]:
    print(h[0], h[2][:110])
print("EN suspicious", len(en_hits))
for h in en_hits[:80]:
    print(h[0], h[2][:130])
