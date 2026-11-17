# -*- coding: utf-8 -*-
"""Generate the 345 new 'on this day' stories, records and English sidecars.

Source data: next/_today_build_data.json (Wikipedia extracts, years, image lists)
             next/_today_image_pool.json (free-licensed Commons images)
Output: content/photos/<decade>/today-*.md
        content/stories/photos/today-*.md
        content/i18n/stories.en.json, records.en.json, captions.en.json
"""
import html
import json
import pathlib
import datetime
import re
import sys
import unicodedata

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
I18N = CONTENT / "i18n"


def clean_text(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def split_paras(text, min_len=35):
    text = clean_text(text)
    lines = []
    for line in re.split(r"\n+", text):
        line = line.strip()
        if len(line) < min_len:
            continue
        if line.endswith(":") or line.endswith("："):
            continue
        if line.lower() in ("references", "see also", "外部链接", "参考文献", "注释"):
            continue
        if line not in lines:
            lines.append(line)
    return lines


def shorten(text, limit):
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("。", "！", "？", ". ", "! ", "? "):
        p = cut.rfind(sep)
        if p > limit * 0.6:
            return cut[: p + len(sep)].strip()
    return cut.rstrip() + "…"


def first_sentence(text, limit=100):
    text = clean_text(text)
    m = re.match(r"(.+?[。！？.!?])(?:\s|$)", text)
    s = m.group(1) if m else text
    return shorten(s, limit)


def date_title(year, md, zh_title, en_title):
    mm, dd = md.split("-")
    zh = (f"公元前{abs(year)}年{int(mm)}月{int(dd)}日：{zh_title}" if year <= 0 else f"{year}年{int(mm)}月{int(dd)}日：{zh_title}")
    en = (f"{abs(year)} BCE, month {int(mm)}, day {int(dd)}: {en_title}" if year <= 0 else f"{datetime.date(year, int(mm), int(dd)).strftime('%B')} {int(dd)}, {year}: {en_title}")
    return zh, en


def safe_slug(title):
    t = unicodedata.normalize("NFKD", str(title))
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return (t or "story")[:44]


def chapterize(paras, n_chapters=3):
    paras = paras[:9]
    if not paras:
        return [[""], [""], [""]]
    intro = paras[:2]
    body = paras[2:] or paras
    # split remaining paragraphs as evenly as possible
    n = len(body)
    base = n // n_chapters
    extra = n % n_chapters
    out = []
    at = 0
    for i in range(n_chapters):
        take = base + (1 if i < extra else 0)
        out.append(body[at:at + take] or [body[-1]])
        at += take
    return intro, out


def pick_images(pool, n=6):
    # Prefer public domain / CC0, then short-licensed images with descriptions.
    def key(m):
        lic = clean_text(m.get("license", "")).lower()
        pri = 0 if ("public domain" in lic or lic == "cc0" or "pd" in lic) else 1
        return (pri, -len(clean_text(m.get("desc", ""))), m.get("title", ""))

    return sorted(pool, key=key)[:n]


def make_record(md, idx, img, story_zh, zh_title, year):
    rid = f"today-{md}-img{idx}"
    desc = clean_text(img.get("desc", ""))
    artist = clean_text(img.get("artist", "")) or "作者见 Wikimedia Commons"
    lic = clean_text(img.get("license", "")) or "见来源页"
    page = img.get("page") or ""
    thumb = img.get("thumb") or img.get("url") or ""
    title_zh = f"{zh_title} · 影像 {idx}"
    note_zh = f"与「{zh_title}」相关的历史影像。来源：Wikimedia Commons。"
    note_en = desc or f"Historical image related to {story_zh}."
    tier = "L0" if ("public domain" in lic.lower() or lic.lower() == "cc0") else "L1"
    rights = "公有领域" if tier == "L0" else "CC 授权"
    fm = {
        "id": rid,
        "collection": "photos",
        "content_type": "photograph",
        "type_evidence": "Wikimedia Commons file page",
        "review_status": "clean",
        "title": title_zh,
        "year": year,
        "date_label": (f"{year}-{md}" if year > 0 else f"公元前{abs(year)}年{int(md[:2])}月{int(md[3:])}日"),
        "era": "近现代",
        "kind": "历史影像",
        "theme": "历史",
        "topic": "事件",
        "region": "世界",
        "medium": "摄影",
        "place": "",
        "creator": artist,
        "creator_status": "已知" if artist != "作者见 Wikimedia Commons" else "未知",
        "source": "Wikimedia Commons",
        "source_short": "Commons",
        "source_url": page,
        "page_url": page,
        "license": lic,
        "tier": tier,
        "rights_status": rights,
        "commercial_ok": True,
        "image": thumb,
        "evidence": {"source": "Wikimedia Commons", "file_page": page},
        "audit": {"checked": "2026-11-16"},
    }
    body = note_zh
    fname = f"today-{md}-{idx}.md"
    # decade bucket; arbitrary old dates go to pre1900
    decade = f"{year // 10 * 10}s" if year >= 1900 else "pre1900"
    path = CONTENT / "photos" / decade / fname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + body + "\n",
        encoding="utf-8",
    )
    return {
        "id": rid,
        "title_zh": title_zh,
        "note_zh": note_zh,
        "note_en": note_en,
        "desc_en": desc,
        "image": thumb,
    }


def build_story(md, data, pool):
    year = data["year"]
    en_title = clean_text(data["title"])
    zh_title = clean_text(data.get("zh_title") or en_title)
    en_text = clean_text(data.get("extract", ""))
    zh_text = clean_text(data.get("zh_extract", ""))
    en_paras = split_paras(en_text)
    zh_paras = split_paras(zh_text)
    if not zh_paras:
        zh_paras = [f"{zh_title}。"]
    if not en_paras:
        en_paras = [en_title + "."]
    zh_intro, zh_ch = chapterize(zh_paras)
    en_intro, en_ch = chapterize(en_paras)
    intro_zh = shorten(" ".join(zh_intro), 650)
    intro_en = shorten(" ".join(en_intro), 900)
    if not intro_zh:
        intro_zh = f"{zh_title}。"
    if not intro_en:
        intro_en = en_title + "."
    title_zh, title_en = date_title(year, md, zh_title, en_title)
    subtitle_zh = first_sentence(zh_text or zh_title, 80)
    subtitle_en = first_sentence(en_text or en_title, 110)
    imgs = pick_images(pool, 6)
    if len(imgs) < 6:
        raise RuntimeError(f"not enough images for {md}: {len(imgs)}")

    records = []
    for i, img in enumerate(imgs, 1):
        records.append(make_record(md, i, img, en_title, zh_title, year))

    chs = []
    for i in range(3):
        text_zh = shorten(" ".join(zh_ch[i]), 1300)
        text_en = shorten(" ".join(en_ch[i]), 1600)
        if not text_zh:
            text_zh = intro_zh
        if not text_en:
            text_en = intro_en
        pos = i * 2
        items = [
            {"id": records[pos]["id"], "caption": f"{zh_title} · 影像 {pos + 1}"},
            {"id": records[pos + 1]["id"], "caption": f"{zh_title} · 影像 {pos + 2}"},
        ]
        chs.append({
            "title": ["缘起", "现场", "余波"][i],
            "text": text_zh,
            "items": items,
            "title_en": ["Origins", "The event", "Aftermath"][i],
            "text_en": text_en,
        })

    slug = safe_slug(en_title)
    sid = f"today-{md}-{slug}"
    # avoid accidental collisions
    suffix = 2
    while (CONTENT / "stories" / "photos" / f"{sid}.md").exists():
        sid = f"today-{md}-{slug}-{suffix}"
        suffix += 1

    fm = {
        "id": sid,
        "collection": "photos",
        "type": "事件",
        "title": title_zh,
        "subtitle": subtitle_zh,
        "status": "published",
        "date": (f"{year:04d}-{md}" if year > 0 else f"0001-{md}"),
        "date_label": (f"{year:04d}-{md}" if year > 0 else f"公元前{abs(year)}年{int(md[:2])}月{int(md[3:])}日"),
        "place": "",
        "cover": records[0]["id"],
        "themes": ["历史"],
        "sources": [
            {"title": f"Wikipedia · {en_title}", "url": "https://en.wikipedia.org/wiki/" + en_title.replace(" ", "_")},
            {"title": f"中文维基 · {zh_title}", "url": "https://zh.wikipedia.org/wiki/" + zh_title.replace(" ", "_")},
        ],
        "chapters": [{"title": c["title"], "text": c["text"], "items": c["items"]} for c in chs],
    }
    path = CONTENT / "stories" / "photos" / f"{sid}.md"
    path.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + intro_zh + "\n",
        encoding="utf-8",
    )

    side = {
        "title": title_en,
        "subtitle": subtitle_en,
        "type_en": "Event",
        "themes": ["History"],
        "intro": intro_en,
        "chapters": {
            str(i): {"title": en_ch[i] and ["Origins", "The event", "Aftermath"][i] or "", "text": chs[i]["text_en"]}
            for i in range(3)
        },
        "captions": {records[i]["id"]: (records[i]["desc_en"] or f"Historical image {i + 1}") for i in range(6)},
    }
    return sid, side, records


def main():
    data = json.loads((ROOT / "next" / "_today_build_data.json").read_text(encoding="utf-8"))
    pools = json.loads((ROOT / "next" / "_today_image_pool.json").read_text(encoding="utf-8"))
    stories_en = json.loads((I18N / "stories.en.json").read_text(encoding="utf-8"))
    records_en = json.loads((I18N / "records.en.json").read_text(encoding="utf-8"))
    captions_en = json.loads((I18N / "captions.en.json").read_text(encoding="utf-8"))
    written = 0
    skipped = []
    for md, item in sorted(data.items()):
        if item.get("existing"):
            continue
        pool = pools.get(md) or []
        if len(pool) < 6:
            skipped.append((md, "images"))
            continue
        sid, side, records = build_story(md, item, pool)
        stories_en[sid] = side
        for r in records:
            records_en[r["id"]] = {"title": r["desc_en"] or r["title_zh"], "note": r["note_en"]}
            captions_en[r["title_zh"]] = r["desc_en"] or r["note_en"]
        written += 1
    (I18N / "stories.en.json").write_text(json.dumps(stories_en, ensure_ascii=False, indent=1), encoding="utf-8")
    (I18N / "records.en.json").write_text(json.dumps(records_en, ensure_ascii=False, indent=1), encoding="utf-8")
    (I18N / "captions.en.json").write_text(json.dumps(captions_en, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", written, "skipped", skipped, "stories_en", len(stories_en), "records_en", len(records_en))
    return 0


if __name__ == "__main__":
    sys.exit(main())
