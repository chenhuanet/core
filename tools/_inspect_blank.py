import re
from pathlib import Path

p = Path("workspace/release/pre19century/painting/a-charioteer-riding-through-a-rocky-landscape-with-an-entourag-1616.html")
text = p.read_text(encoding="utf-8")
for m in re.finditer(r"<a\b([^>]*)>", text):
    attrs = m.group(1)
    if 'target="_blank"' in attrs:
        href = re.search(r'href="([^"]*)"', attrs)
        print(href.group(1) if href else "NO-HREF")
