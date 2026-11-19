import os, re
roots = [r"C:\Users\chenhua\Desktop\chenhua\next\dist\main", r"C:\Users\chenhua\Desktop\chenhua\next\dist\photo", r"C:\Users\chenhua\Desktop\chenhua\next\dist\paint"]
tag = re.compile(r"<[^>]+>")
url = re.compile(r"https?://\S+")
for root in roots:
    bad = []
    total = 0
    for dp, _, fs in os.walk(root):
        for f in fs:
            if not f.lower().endswith(".html"): continue
            total += 1
            p = os.path.join(dp, f)
            text = open(p, encoding="utf-8", errors="ignore").read()
            text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
            text = tag.sub(" ", text)
            text = url.sub(" ", text)
            text = re.sub(r"\s+", " ", text)
            for m in re.finditer("台湾|臺灣", text):
                before = text[max(0, m.start()-2):m.start()]
                if before.endswith("中国"): continue
                bad.append((os.path.relpath(p, root), text[max(0,m.start()-18):m.end()+22]))
    print(root, "pages", total, "standalone zh", len(bad))
    for b in bad[:12]: print(" ", b[0], "|", b[1])
