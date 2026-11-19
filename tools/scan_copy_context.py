import os

for rel in [r"dist\data\atlas.json", r"dist\data\bundle.js", r"dist\main\themes\index.html"]:
    path = os.path.join(os.path.dirname(__file__), "..", rel)
    text = open(path, encoding="utf-8", errors="ignore").read()
    for needle in ["75001", "同一个档案馆", "三种读法", "读法", "档案馆"]:
        start = 0
        found = 0
        while True:
            i = text.find(needle, start)
            if i < 0:
                break
            print(f"--- {rel} :: {needle} @{i}")
            print(text[max(0, i - 160):i + 220].replace("\n", " ⏎ "))
            start = i + len(needle)
            found += 1
            if found >= 4:
                break
