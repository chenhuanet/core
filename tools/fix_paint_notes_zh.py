# -*- coding: utf-8 -*-
"""Repair the Chinese painting notes: body image + translated Chinese text."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAINT = ROOT / "repos-git" / "paint"
NOTES = ROOT / "next" / "_paint_notes_zh.json"
CONTENT = ROOT / "next" / "content" / "paintings"

with NOTES.open(encoding="utf-8") as fh:
    zh = json.load(fh)

# Keep proper names and work titles aligned with the rest of the site.
REPLACEMENTS = [
    ("克林姆特", "克里姆特"),
    ("《星夜》", "《星月夜》"),
    ("《接吻》", "《吻》"),
    ("吉奥托", "乔托"),
    ("布鲁盖尔", "老彼得·勃鲁盖尔"),
    ("《犹迪特斩霍洛费尔尼》", "《朱迪斯斩首荷罗孚尼》"),
    ("犹迪特", "朱迪斯"),
    ("霍洛费尔尼", "荷罗孚尼"),
    ("《西特拉朝圣》", "《舟发西苔岛》"),
    ("《拾穗》", "《拾穗者》"),
    ("《当代三美人》", "《三位美人》"),
    ("《我们从哪里来？我们是谁？我们往哪里去？》", "《我们从何处来？我们是谁？我们向何处去？》"),
    ("维也纳分裂派", "维也纳分离派"),
    ("张泽东", "张择端"),
    ("王希民", "王希孟"),
    ("顾启志", "顾恺之"),
    ("博瑟", "义和团"),
    ("潘夫人", "班姬"),
    ("冯夫人", "冯媛"),
    ("这些数字", "这些人物"),
    ("数字几乎", "人物几乎"),
    ("数字之间", "人物之间"),
    ("中风", "笔触"),
    ("恶疮", "矿绿"),
    ("小鹰", "小贩"),
    ("（tronie）", "（类型画）"),
    ("ōkubi-e", "大头画"),
]

for key, value in list(zh.items()):
    for old, new in REPLACEMENTS:
        value = value.replace(old, new)
    value = re.sub(r"[ \t]+\n", "\n", value).strip()
    value = value.replace("\n\n\n", "\n\n")
    zh[key] = value

# Some automatically harvested records only carry file-page provenance.
# Give them a clean, factual archival caption instead of leaking File: names.
AUTO_REGION = {
    "auto-d49e9fd0": "美国",
    "auto-d713ad77": "英国",
    "auto-e13d5cd2": "巴西",
    "auto-ba3dba36": "巴西",
    "auto-723f2014": "巴西",
    "auto-ad61b00e": "巴西",
    "auto-aed4a918": "黑海",
    "auto-e80436fe": "黑海",
    "auto-62ae36e0": "开普敦",
    "auto-580fb4aa": "俄国",
    "auto-27bcc7d5": "法国",
    "auto-58575fef": "越南",
    "auto-2df8ce6f": "美国",
    "auto-256d170f": "美国",
    "auto-91d0ab3b": "锡兰",
    "auto-f2dad429": "柏林",
    "auto-505fc4ea": "斯拉夫",
    "auto-c6739d13": "苏格兰",
}

bundle_text = (PAINT / "data" / "bundle.js").read_text(encoding="utf-8")
prefix, payload = bundle_text.split("=", 1)
data, _ = json.JSONDecoder().raw_decode(payload.lstrip())
records = data["records"]
paint_rows = [r for r in records if r.get("collection") == "paintings"
              and r.get("content_type") == "painting"]

for r in paint_rows:
    rid = r["id"]
    if rid.startswith("auto-"):
        title = r.get("title", "").strip("《》")
        creator = r.get("creator") or "佚名"
        year = r.get("year") or ""
        movement = r.get("movement") or "绘画"
        region = AUTO_REGION.get(rid, "所在地")
        medium = r.get("medium") or "绘画"
        if creator == "佚名":
            creator = "佚名画家"
        zh[rid] = ("《%s》是%s约%s年的%s作品，现藏信息待考。画面以“%s”为题，"
                   "属于%s的%s传统，可作为同时代绘画的参照。"
                   % (title, creator, year, movement, title, region, medium))
    r["note"] = zh[rid]
    r["note_html"] = zh[rid]
    old = r.get("search_text") or ""
    # Drop the old boilerplate before appending the corrected note.
    if "《女史箴图》" in old:
        old = old.split("《女史箴图》", 1)[0].rstrip()
    r["search_text"] = (old + " " + zh[rid]).strip()

# Write a compact bundle; the page loader accepts both compact and spaced JSON.
(PAINT / "data" / "bundle.js").write_text(
    prefix + "= " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
    encoding="utf-8", newline="\n")

# Replace the poisoned Markdown body while leaving the verified front matter intact.
count = 0
for path in sorted(CONTENT.rglob("*.md")):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        continue
    end = text.find("\n---\n", 4)
    if end < 0:
        continue
    front = text[4:end]
    body = text[end + 5:]
    rid_match = re.search(r"^id:\s*([^\n]+)", front, re.M)
    image_match = re.search(r"^image:\s*([^\n]+)", front, re.M)
    title_match = re.search(r"^title:\s*([^\n]+)", front, re.M)
    if not (rid_match and image_match and title_match):
        continue
    rid = rid_match.group(1).strip()
    if rid not in zh:
        continue
    image = image_match.group(1).strip()
    title = title_match.group(1).strip()
    new_body = "![%s](%s)\n\n%s\n" % (title, image, zh[rid])
    path.write_text(text[:end + 5] + "\n" + new_body, encoding="utf-8", newline="\n")
    count += 1

print("updated bundle records:", len(paint_rows), "markdown files:", count)
print("missing notes:", [r["id"] for r in paint_rows if not zh.get(r["id"])])
