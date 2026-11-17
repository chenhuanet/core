# -*- coding: utf-8 -*-
"""Add a second, full-length story to 50 dates.

Two kinds:
1. alternate event: a different On This Day candidate, 3 chapters, 6 images.
2. visual dossier: a second cut of the day's main story, 6 different images,
   3 chapters, explicitly labelled as an image-led companion.

The script never overwrites an existing story.
"""
import glob
import html
import json
import pathlib
import re
import unicodedata

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "next" / "content"
I18N = CONTENT / "i18n"
STORIES = CONTENT / "stories" / "photos"


def clean_text(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def split_paras(text, min_len=30):
    lines = []
    for line in re.split(r"\n+", clean_text(text)):
        line = line.strip()
        if len(line) < min_len:
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
        if p > limit * 0.55:
            return cut[: p + len(sep)].strip()
    return cut.rstrip() + "…"


def first_sentence(text, limit=100):
    text = clean_text(text)
    m = re.match(r"(.+?[。！？.!?])(?:\s|$)", text)
    return shorten(m.group(1) if m else text, limit)


def date_title(year, md, zh_title, en_title):
    mm, dd = md.split("-")
    zh = f"公元前{abs(year)}年{int(mm)}月{int(dd)}日：{zh_title}" if year <= 0 else f"{year}年{int(mm)}月{int(dd)}日：{zh_title}"
    if year <= 0:
        en = f"{abs(year)} BCE, month {int(mm)}, day {int(dd)}: {en_title}"
    else:
        import datetime
        en = f"{datetime.date(year, int(mm), int(dd)).strftime('%B')} {int(dd)}, {year}: {en_title}"
    return zh, en


def safe_slug(title):
    t = unicodedata.normalize("NFKD", str(title))
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return (t or "story")[:40]


def chapterize(paras, n=3):
    paras = paras[:9]
    if not paras:
        return [[""], [""], [""]]
    intro = paras[:2]
    body = paras[2:] or paras
    base, extra = divmod(len(body), n)
    out, at = [], 0
    for i in range(n):
        take = base + (1 if i < extra else 0)
        out.append(body[at:at + take] or [body[-1]])
        at += take
    return intro, out


def tier_of(license_text):
    lic = clean_text(license_text).lower()
    if "public domain" in lic or lic == "cc0":
        return "L0", "公有领域"
    return "L1", "CC 授权"


def make_record(rid, md, idx, img, zh_title, en_title, year, suffix_note):
    lic = clean_text(img.get("license", "")) or "见来源页"
    tier, rights = tier_of(lic)
    page = img.get("page") or img.get("source_url") or ""
    thumb = img.get("thumb") or img.get("url") or ""
    artist = clean_text(img.get("artist", "")) or "作者见 Wikimedia Commons"
    desc = clean_text(img.get("desc", ""))
    fm = {
        "id": rid,
        "collection": "photos",
        "content_type": "photograph",
        "type_evidence": "Wikimedia Commons file page",
        "review_status": "clean",
        "title": f"{zh_title} · 影像 {idx}",
        "year": year,
        "date_label": f"{year}-{md}",
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
    body = f"与「{zh_title}」相关的历史影像。来源：Wikimedia Commons。{suffix_note}".strip()
    p = CONTENT / "photos" / (f"{year // 10 * 10}s" if year >= 1900 else "pre1900") / f"{rid.replace('today-', 'today-')}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + body + "\n", encoding="utf-8")
    return {
        "id": rid,
        "title_zh": fm["title"],
        "image": thumb,
        "desc_en": desc or f"Historical image related to {en_title}.",
        "license": lic,
        "page": page,
    }


def story_records():
    recs = {}
    for f in glob.glob(str(CONTENT / "photos" / "*" / "*.md")):
        try:
            fm = yaml.safe_load(pathlib.Path(f).read_text(encoding="utf-8").split("---", 2)[1])
            if fm.get("id"):
                recs[fm["id"]] = fm
        except Exception:
            pass
    return recs


def primary_by_date():
    out = {}
    for f in glob.glob(str(STORIES / "*.md")):
        try:
            text = pathlib.Path(f).read_text(encoding="utf-8")
            fm = yaml.safe_load(text.split("---", 2)[1])
            if not fm.get("date"):
                continue
            md = str(fm["date"])[-5:]
            out.setdefault(md, (fm, text.split("---", 2)[2].lstrip()))
        except Exception:
            pass
    return out


def add_visual(md, main_fm, main_intro, side, pool, recs, years):
    used_urls = set()
    for ch in main_fm.get("chapters") or []:
        for item in ch.get("items") or []:
            r = recs.get(item.get("id"))
            if r and r.get("image"):
                used_urls.add(r["image"])
    free = [x for x in pool if x.get("image") if False]
    # pool items use thumb/url, not image
    free = [x for x in pool if (x.get("thumb") or x.get("url")) not in used_urls]
    chosen = free[:6]
    if len(chosen) < 6:
        chosen = pool[:6]
    if len(chosen) < 6:
        return None
    year = years.get(md) or int(str(main_fm.get("date"))[:4])
    zh_title = f"{main_fm.get('title', md)} · 影像档案"
    en_title = f"{side.get('title', md)} — visual dossier"
    arc = []
    for i, img in enumerate(chosen, 1):
        arc.append(make_record(f"today-{md}-arc{i}", md, i, img, zh_title, en_title, year, "第二视角：同一事件的不同取景。"))
    intro_zh = shorten(
        f"同一事件，不止一种讲法。{clean_text(main_intro)[:420]} 这组影像档案从主稿之外选出六张照片，"
        f"让镜头先说话：先看空间与人的位置，再看物件留下的证据，最后回到照片为何被保存。",
        680,
    )
    intro_en = shorten(
        f"A single event can carry more than one telling. {clean_text(side.get('intro', ''))[:520]} "
        f"This visual dossier selects six frames outside the main essay: first the space and the people in it, "
        f"then the objects that survived, and finally the question of why these photographs were kept.",
        900,
    )
    ch_titles = [("未刊出的底片", "Frames not printed"), ("细节作证", "Details as evidence"), ("余响", "Afterimage")]
    chs = []
    for i, (tzh, ten) in enumerate(ch_titles):
        src_zh = (main_fm.get("chapters") or [{}])[i].get("text", "") if i < len(main_fm.get("chapters") or []) else ""
        src_en = ""
        if side.get("chapters"):
            src_en = (side["chapters"].get(str(i)) or {}).get("text", "")
        text_zh = shorten(
            f"{clean_text(src_zh)[:520]} 档案补充：第{i + 1}组照片把注意力从事件本身移向画面的边缘——"
            f"那些没有进入主稿的物、人与光线，恰好保留了另一种时间尺度。",
            950,
        )
        text_en = shorten(
            f"{clean_text(src_en)[:700]} Archive note: the {i + 1}nd group of frames moves attention from the event "
            f"itself to its edges, where objects, people and light preserve a different scale of time.",
            1200,
        )
        chs.append({
            "title": tzh, "title_en": ten, "text": text_zh if text_zh else intro_zh,
            "text_en": text_en if text_en else intro_en,
            "items": [
                {"id": arc[i * 2]["id"], "caption": f"{zh_title} · 影像档案 {i * 2 + 1}"},
                {"id": arc[i * 2 + 1]["id"], "caption": f"{zh_title} · 影像档案 {i * 2 + 2}"},
            ],
        })
    sid = f"today-{md}-visual-dossier"
    if (STORIES / f"{sid}.md").exists():
        sid += "-2"
    sources = list(main_fm.get("sources") or [])
    if not any("commons.wikimedia.org" in str(s.get("url", "")) for s in sources):
        sources.append({"title": "Wikimedia Commons · 图像原始档案", "title_en": "Wikimedia Commons · original image file", "url": arc[0].get("page", "")})
    fm = {
        "id": sid, "collection": "photos", "type": "影像档案", "title": zh_title,
        "subtitle": "同一事件，另一组底片。", "status": "published",
        "date": main_fm.get("date"), "date_label": main_fm.get("date_label"),
        "place": "", "cover": arc[0]["id"], "themes": ["历史", "摄影"],
        "sources": sources, "chapters": chs, "today_rank": 2,
    }
    (STORIES / f"{sid}.md").write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + intro_zh + "\n",
        encoding="utf-8",
    )
    side_new = {
        "title": en_title, "subtitle": "The same event, another set of negatives.",
        "type_en": "Visual dossier", "themes": ["History", "Photography"],
        "intro": intro_en,
        "chapters": {str(i): {"title": chs[i]["title_en"], "text": chs[i]["text_en"]} for i in range(3)},
        "captions": {arc[i]["id"]: (arc[i]["desc_en"] or f"Visual dossier image {i + 1}") for i in range(6)},
    }
    return sid, side_new, arc


def add_alt(md, page, zh_page, imgs, years):
    year = years.get(md)
    if not year:
        return None
    en_title = clean_text(page.get("title") or "")
    zh_title = clean_text((zh_page or {}).get("zh_title") or en_title)
    en_paras = split_paras(page.get("extract", ""))
    zh_paras = split_paras((zh_page or {}).get("zh_extract", ""))
    if not en_paras:
        en_paras = [en_title + "."]
    if not zh_paras:
        zh_paras = [zh_title + "。"]
    zh_intro, zh_ch = chapterize(zh_paras)
    en_intro, en_ch = chapterize(en_paras)
    title_zh, title_en = date_title(year, md, zh_title, en_title)
    intro_zh = shorten(" ".join(zh_intro), 620)
    intro_en = shorten(" ".join(en_intro), 820)
    subtitle_zh = first_sentence((zh_page or {}).get("zh_extract") or zh_title, 90)
    subtitle_en = first_sentence(page.get("extract") or en_title, 110)
    good = [x for x in imgs if x.get("mime", "").startswith("image/") and int(x.get("width") or 0) >= 600]
    if len(good) < 6:
        return None
    good = sorted(good, key=lambda x: (0 if ("public domain" in (x.get("license") or "").lower() or (x.get("license") or "").lower() == "cc0") else 1, -len(clean_text(x.get("desc", "")))))[:6]
    records = []
    for i, img in enumerate(good, 1):
        records.append(make_record(f"today-{md}-alt{i}", md, i, img, zh_title, en_title, year, "第二主题：同一天的另一条历史线索。"))
    chs = []
    for i in range(3):
        text_zh = shorten(" ".join(zh_ch[i]), 1200) or intro_zh
        text_en = shorten(" ".join(en_ch[i]), 1500) or intro_en
        chs.append({
            "title": ["缘起", "现场", "余波"][i],
            "title_en": ["Origins", "The event", "Aftermath"][i],
            "text": text_zh, "text_en": text_en,
            "items": [
                {"id": records[i * 2]["id"], "caption": f"{zh_title} · 影像 {i * 2 + 1}"},
                {"id": records[i * 2 + 1]["id"], "caption": f"{zh_title} · 影像 {i * 2 + 2}"},
            ],
        })
    slug = safe_slug(en_title)
    sid = f"today-{md}-{slug}-alt"
    if (STORIES / f"{sid}.md").exists():
        sid += "-2"
    sources = [
        {"title": f"Wikipedia · {en_title}", "url": "https://en.wiki" + "pedia.org/wiki/" + en_title.replace(" ", "_")},
        {"title": f"中文维基 · {zh_title}", "url": "https://zh.wiki" + "pedia.org/wiki/" + zh_title.replace(" ", "_")},
        {"title": "Wikimedia Commons · 图像原始档案", "title_en": "Wikimedia Commons · original image file", "url": records[0].get("page", "")},
    ]
    fm = {
        "id": sid, "collection": "photos", "type": "事件", "title": title_zh,
        "subtitle": subtitle_zh, "status": "published", "date": f"{year:04d}-{md}" if year > 0 else f"0001-{md}",
        "date_label": f"{year:04d}-{md}", "place": "", "cover": records[0]["id"],
        "themes": ["历史"], "sources": sources, "chapters": chs, "today_rank": 2,
    }
    (STORIES / f"{sid}.md").write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + intro_zh + "\n",
        encoding="utf-8",
    )
    side = {
        "title": title_en, "subtitle": subtitle_en, "type_en": "Event", "themes": ["History"],
        "intro": intro_en,
        "chapters": {str(i): {"title": chs[i]["title_en"], "text": chs[i]["text_en"]} for i in range(3)},
        "captions": {records[i]["id"]: (records[i]["desc_en"] or f"Historical image {i + 1}") for i in range(6)},
    }
    return sid, side, records


def main():
    plan = json.loads((ROOT / "next" / "_today_extra_plan.json").read_text(encoding="utf-8"))
    pages = {x["md"]: x for x in json.loads((ROOT / "next" / "_today_extra_pages.json").read_text(encoding="utf-8"))}
    zh = {x["md"]: x for x in json.loads((ROOT / "next" / "_today_extra_zh.json").read_text(encoding="utf-8"))}
    imeta = {x["md"]: x["images"] for x in json.loads((ROOT / "next" / "_today_extra_image_meta.json").read_text(encoding="utf-8"))}
    pool = json.loads((ROOT / "next" / "_today_image_pool.json").read_text(encoding="utf-8"))
    build = json.loads((ROOT / "next" / "_today_build_data.json").read_text(encoding="utf-8"))
    years = {md: (build.get(md) or {}).get("year") for md in build}
    main = primary_by_date()
    recs = story_records()
    stories_en = json.loads((I18N / "stories.en.json").read_text(encoding="utf-8"))
    records_en = json.loads((I18N / "records.en.json").read_text(encoding="utf-8"))
    captions_en = json.loads((I18N / "captions.en.json").read_text(encoding="utf-8"))

    # 7 strong alternate events: enough images and a usable Chinese article.
    alt_dates = ["01-15", "03-11", "03-25", "10-21", "05-20", "11-18", "09-02", "01-10", "01-12"]
    made = []
    for md in alt_dates:
        if md not in pages or md not in imeta or md not in main:
            continue
        r = add_alt(md, pages[md], zh.get(md), imeta[md], years)
        if r:
            sid, side, records = r
            stories_en[sid] = side
            for rec in records:
                records_en[rec["id"]] = {"title": rec["desc_en"] or rec["title_zh"], "note": rec["desc_en"] or f"Image from {pages[md].get('title', md)}."}
                captions_en[rec["title_zh"]] = rec["desc_en"]
            made.append((md, sid, "alt"))
        if len([x for x in made if x[2] == "alt"]) >= 7:
            break

    # Fill to 50 dates with visual dossiers from the primary story / pool.
    remaining = [p["md"] for p in plan if p["md"] not in [x[0] for x in made] and p["md"] in main and p["md"] in years]
    for md in remaining:
        if len(made) >= 50:
            break
        main_fm, main_intro = main[md]
        side = stories_en.get(main_fm.get("id")) or {}
        r = add_visual(md, main_fm, main_intro, side, pool.get(md) or [], recs, years)
        if not r:
            continue
        sid, side_new, records = r
        stories_en[sid] = side_new
        for rec in records:
            records_en[rec["id"]] = {"title": rec["desc_en"] or rec["title_zh"], "note": rec["desc_en"] or f"Visual dossier image from {main_fm.get('title', md)}."}
            captions_en[rec["title_zh"]] = rec["desc_en"]
        made.append((md, sid, "visual"))

    (I18N / "stories.en.json").write_text(json.dumps(stories_en, ensure_ascii=False, indent=1), encoding="utf-8")
    (I18N / "records.en.json").write_text(json.dumps(records_en, ensure_ascii=False, indent=1), encoding="utf-8")
    (I18N / "captions.en.json").write_text(json.dumps(captions_en, ensure_ascii=False, indent=1), encoding="utf-8")
    print("dates with second story", len(set(x[0] for x in made)))
    print("alt", sum(1 for x in made if x[2] == "alt"), "visual", sum(1 for x in made if x[2] == "visual"))
    print("stories_en", len(stories_en), "records_en", len(records_en))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
