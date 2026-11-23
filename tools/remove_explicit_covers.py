# -*- coding: utf-8 -*-
"""Keep explicit nudity out of theme/timeline cover pools.

This is a curation rule, not a content removal: the work pages and records stay
intact. Only cover selection for cards is filtered.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "repos-git" / "main" / "data" / "bundle.js"

UNSAFE_IDS = {
    "giotto-lamentation-1305",
    "weyden-descent-from-cross-1435",
    "rubens-descent-from-cross-1614",
    "masaccio-expulsion-1427",
    "botticelli-primavera-1480",
    "botticelli-birth-of-venus-1485",
    "bosch-garden-earthly-delights-1500",
    "michelangelo-creation-of-adam-1511",
    "ingres-grande-odalisque-1814",
    "goya-saturn-1820",
    "delacroix-liberty-1830",
    "courbet-painters-studio-1855",
    "manet-olympia-1863",
    "manet-dejeuner-sur-herbe-1863",
    "gauguin-where-do-we-come-from-1898",
    "schiele-self-portrait-1912",
    "moreau-jupiter-semele-1895",
}

# A safe representative per movement, used when a cover is replaced.
SAFE_BY_MOVEMENT = {
    "早期文艺复兴": "duccio-maesta-1308",
    "盛期文艺复兴": "leonardo-mona-lisa-1503",
    "北方文艺复兴": "van-eyck-arnolfini-1434",
    "矫饰主义": "parmigianino-madonna-long-neck-1535",
    "巴洛克": "rembrandt-night-watch-1642",
    "洛可可": "watteau-pilgrimage-cythera-1717",
    "新古典主义": "david-oath-of-horatii-1784",
    "浪漫主义": "friedrich-wanderer-1818",
    "现实主义": "millet-the-gleaners-1857",
    "印象主义": "monet-impression-sunrise-1872",
    "后印象主义": "van-gogh-starry-night-1889",
    "象征主义": "boecklin-isle-of-the-dead-1883",
    "元代文人山水": "huang-gongwang-fuchun-1350",
    "浮世绘": "hokusai-great-wave-1831",
    "表现主义": "kirchner-street-berlin-1913",
}
FALLBACK_ID = "klimt-the-kiss-1908"

raw = BUNDLE.read_text(encoding="utf-8")
data, _ = json.JSONDecoder().raw_decode(raw.split("=", 1)[1].lstrip())
rows = [r for r in data["records"] if r.get("collection") == "paintings"
        and r.get("content_type") == "painting"]
by_id = {r["id"]: r for r in rows}

def base(url):
    return (url or "").split("?")[0].rstrip()

def image_of(rid):
    r = by_id.get(rid) or {}
    return base(r.get("image") or r.get("preview_image") or "")

unsafe_url_to_id = {}
for rid in UNSAFE_IDS:
    r = by_id.get(rid) or {}
    for key in ("image", "preview_image"):
        u = base(r.get(key))
        if u:
            unsafe_url_to_id[u] = rid
unsafe_set = set(unsafe_url_to_id)
safe_fallback = image_of(FALLBACK_ID)

def safe_by_movement_for(rid):
    r = by_id.get(rid) or {}
    fallback_id = SAFE_BY_MOVEMENT.get(r.get("movement") or "", FALLBACK_ID)
    return image_of(fallback_id) or safe_fallback

def replace_lib_img(match):
    tag = match.group(0)
    src_m = re.search(r'src="([^"]*)"', tag)
    pool_m = re.search(r'data-covers="([^"]*)"', tag)
    if not src_m:
        return tag
    src = src_m.group(1)
    if pool_m:
        pool = [x for x in pool_m.group(1).split("|") if x and base(x) not in unsafe_set]
        if not pool:
            fallback = safe_by_movement_for(unsafe_url_to_id.get(base(src), "")) or safe_fallback
            pool = [fallback]
        if base(src) in unsafe_set or not src:
            src = pool[0]
        tag = re.sub(r'src="[^"]*"', 'src="%s"' % src.replace("&", "&amp;"), tag, count=1)
        tag = re.sub(r'data-covers="[^"]*"', 'data-covers="%s"' % "|".join(pool).replace("&", "&amp;"), tag, count=1)
    else:
        if base(src) in unsafe_set:
            new = safe_by_movement_for(unsafe_url_to_id[base(src)])
            tag = re.sub(r'src="[^"]*"', 'src="%s"' % new.replace("&", "&amp;"), tag, count=1)
    return tag

pages = [
    ROOT / "repos-git" / "main" / "themes" / "index.html",
    ROOT / "repos-git" / "paint" / "themes" / "index.html",
    ROOT / "repos-git" / "main" / "timeline" / "index.html",
]
for path in pages:
    text = path.read_text(encoding="utf-8")
    text, n = re.subn(r"<img\b[^>]*>", replace_lib_img, text)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(path.name, "img tags", n, "remaining unsafe", sum(u in text for u in unsafe_set))

print("unsafe ids", len(UNSAFE_IDS), "unsafe urls", len(unsafe_set))
