import glob
import json
import pathlib
import re

import yaml

BASE = pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\content\stories\photos")
BUILD = json.loads(pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\_today_build_data.json").read_text(encoding="utf-8"))
SIDE = json.loads(pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\content\i18n\stories.en.json").read_text(encoding="utf-8"))
BAD = re.compile(r"China|Taiwan|Hong Kong|Tiananmen|war|invasion|president|election|communist|nuclear|terror|bomb", re.I)


def han(s):
    return len(re.findall("[\u4e00-\u9fff]", s))


rows = []
for f in BASE.glob("today-*.md"):
    text = f.read_text(encoding="utf-8")
    try:
        fm = yaml.safe_load(text.split("---", 2)[1])
    except Exception:
        continue
    full = text.split("---", 2)[2] + "\n" + "\n".join((c.get("text") or "") for c in (fm.get("chapters") or []))
    if han(full) >= 800:
        continue
    md = f.name[6:11]
    sid = fm.get("id")
    if fm.get("today_rank") == 2 and sid in SIDE:
        s = SIDE[sid]
        e = (s.get("intro") or "") + "\n" + "\n".join((s.get("chapters", {}).get(str(i), {}) or {}).get("text", "") for i in range(3))
    else:
        e = (BUILD.get(md) or {}).get("extract", "")
    e = re.sub(r"<[^>]+>", " ", e or "")
    e = re.sub(r"\s+", " ", e).strip()
    if not e or BAD.search(e) or BAD.search(fm.get("title", "") or ""):
        continue
    rows.append({"file": f.name, "id": sid, "md": md, "text": e[:1800]})

pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\_today_short_translate_input.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("short with safe source", len(rows))
