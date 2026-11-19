# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
base = Path(r"C:\Users\chenhua\Desktop\chenhua\next")
shutil.copy2(base / "core" / "assets" / "app.js", base / "dist" / "assets" / "app.js")
for site in ("main", "photo"):
    root = base / "dist" / site
    count = 0
    for p in root.rglob("*.html"):
        s = p.read_text(encoding="utf-8")
        n = s.replace("/next/dist/%s/today/" % site, "/next/dist/%s/today/calendar.html" % site)
        if n != s:
            p.write_text(n, encoding="utf-8", newline="\n")
            count += 1
    print(site, count)
