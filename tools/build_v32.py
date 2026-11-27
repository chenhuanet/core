# -*- coding: utf-8 -*-
"""v3.2 static site builder.

Reads the three content repos, assigns records to century sites, renders
11 sites in Chinese and English, and writes workspace/release/<site>/.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402

ROOT = K.ROOT
RELEASE = ROOT / "workspace" / "release"
DATA = ROOT / "workspace" / "data"
PAINT = ROOT / "repos" / "painting-history-and-craft"
PHOTO = ROOT / "repos" / "photography-history-and-craft"
AI = ROOT / "repos" / "ai-image-generation-guide"
CORE = ROOT / "repos" / "core"

RECORD_SITES = ("pre19century", "19century", "20century", "21century", "aiera")
CONTENT_SITES = ("main", "paint", "painting", "photo", "photography", "ai")
SITE_TITLES = {
    "paint": ("绘画史", "Painting History"),
    "painting": ("学习绘画", "Learn Painting"),
    "photo": ("摄影史", "Photography History"),
    "photography": ("学习摄影", "Learn Photography"),
    "ai": ("AI 图像", "AI Images"),
}
TYPE_LABELS = {
    "chapters": ("章节", "Chapters"),
    "movements": ("流派", "Movements"),
    "artists": ("艺术家", "Artists"),
    "periods": ("时期", "Periods"),
    "regions": ("地域", "Regions"),
    "trails": ("路线", "Trails"),
    "techniques": ("技法", "Techniques"),
    "readings": ("阅读", "Readings"),
    "dialogues": ("对话", "Dialogues"),
    "eras": ("时代", "Eras"),
    "photographers": ("摄影家", "Photographers"),
    "exhibitions": ("展览", "Exhibitions"),
    "themes": ("主题", "Themes"),
    "processes": ("工艺", "Processes"),
}


def load_images():
    for rel in ("workspace/data/preview-images.json", "workspace/preview-images.json"):
        path = ROOT / rel
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


IMAGES = load_images()


def load_records():
    records = []
    for repo, sub, coll in (
        (PAINT, "paintings", "paintings"),
        (PHOTO, "photos", "photos"),
        (PHOTO, "objects", "objects"),
        (PHOTO, "links", "links"),
        (PHOTO, "stories", "stories"),
    ):
        base = repo / sub
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if p.name in ("README.md",):
                continue
            meta, body = K.read_md(p)
            if not meta.get("id"):
                continue
            records.append({"meta": meta, "body": body.strip(), "collection": coll, "path": p})
    return records


def year_of(meta):
    y = meta.get("year")
    if isinstance(y, int):
        return y
    if isinstance(y, str) and y.strip().isdigit():
        return int(y.strip())
    m = re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b", str(meta.get("date_label") or ""))
    return int(m.group(1)) if m else None


def century_of(meta):
    y = year_of(meta)
    if y is None:
        return "20century"
    if y < 1800:
        return "pre19century"
    if y < 1900:
        return "19century"
    if y < 2000:
        return "20century"
    return "21century"


def record_kind(collection):
    return {"paintings": "painting", "photos": "photo", "objects": "object", "links": "links", "stories": "story"}[collection]


def record_path(rec):
    kind = record_kind(rec["collection"])
    if kind == "links":
        return "/links/%s.html" % rec["meta"]["id"]
    return "/%s/%s.html" % (kind, rec["meta"]["id"])


def image_url(rec, century=None):
    rid = rec["meta"]["id"]
    hit = IMAGES.get(rid)
    if hit:
        cent = hit.get("century") or century
        target = hit["target"].replace("\\", "/")
        marker = "/images/%s/" % cent
        if marker in target:
            rel = target.split(marker, 1)[1]
            return "https://%s.chenhua.net/%s" % (cent, rel), "https://%s.chenhua.net/thumbs/%s" % (cent, rel)
    src = rec["meta"].get("image")
    if src:
        return str(src), ""
    return "", ""


def clean_title(text, limit=120):
    text = str(text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def card_html(rec, lang, site_key):
    meta = rec["meta"]
    title = clean_title(K.pick(meta, "title", lang, meta.get("id")))
    year = meta.get("date_label") or year_of(meta) or ""
    image, thumb = image_url(rec, century_of(meta))
    href = K.origin("photo" if rec["collection"] == "links" else century_of(meta)) + K.lang_path(record_path(rec), lang)
    if image:
        img = '<img src="%s" alt="%s" loading="lazy" decoding="async">' % (K.esc(thumb or image), K.esc(title))
    else:
        img = '<span class="card-noimg">%s</span>' % K.esc(title[:1])
    return ('<a class="s-card" href="%s">%s<div class="c"><b>%s</b><span>%s</span></div></a>'
            % (K.esc(href), img, K.esc(title), K.esc(year)))


def page_intro(lang, zh, en):
    return zh if lang == "zh" else en


def write_site(site_key, files):
    base = RELEASE / site_key
    if base.exists():
        import time
        for attempt in range(5):
            try:
                shutil.rmtree(base)
                break
            except PermissionError:
                time.sleep(1 + attempt)
        else:
            raise SystemExit("cannot clean release dir: %s" % base)
    for rel, text in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return len(files)


def build_assets(site_key):
    base = RELEASE / site_key / "assets"
    base.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CORE / "assets" / "app.css", base / "app.css")
    shutil.copy2(CORE / "assets" / "site.js", base / "site.js")
    shutil.copy2(CORE / "static" / "static.css", base / "static.css")
    shutil.copy2(CORE / "static" / "history.css", base / "history.css")
    leaf_src = CORE / "leaf"
    leaf_dst = base / "leaf"
    leaf_dst.mkdir(parents=True, exist_ok=True)
    for p in leaf_src.glob("*.svg"):
        shutil.copy2(p, leaf_dst / p.name)
    if (CORE / "assets" / "hero-venus.jpg").exists():
        shutil.copy2(CORE / "assets" / "hero-venus.jpg", base / "hero-venus.jpg")


def legal_body(lang):
    if lang == "en":
        return ("<h1 class='s-title'>Disclaimer</h1><section class='s-note'>"
                "<p>Frame &amp; Grain is a non-commercial index of historical images. "
                "Rights belong to the source institutions and rights holders. "
                "We do not sell images. Takedown requests are handled through the contact on chenhua.net.</p></section>")
    return ("<h1 class='s-title'>免责条款</h1><section class='s-note'>"
            "<p>尘画是非商业性的历史影像索引项目。影像权利归来源机构与权利人所有；"
            "本站不出售图片。下架与更正请求请通过 chenhua.net 公布的联系方式提出。</p></section>")


def build_legal(site_key, files):
    for lang in ("zh", "en"):
        path = "/legal/"
        title = "免责条款" if lang == "zh" else "Disclaimer"
        desc = "尘画免责条款与权利说明" if lang == "zh" else "Disclaimer and rights"
        body = "<main class='s-main'>" + legal_body(lang) + "</main>"
        files[K.lang_path(path, lang).lstrip("/") + "index.html"] = K.page(site_key, lang, path, title, desc, body)


def build_404(site_key, files):
    html = """<!doctype html><html lang="zh-CN" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>404 · 尘画</title>
<link rel="stylesheet" href="/assets/app.css?v=%s"><link rel="stylesheet" href="/assets/static.css?v=%s">
</head><body class="static-body"><main class="s-main" style="padding:12vh 24px;text-align:center">
<p style="letter-spacing:.2em;color:var(--dim)">404</p>
<h1 class="s-title" id="t">页面不存在</h1><p id="p">站点已重建，请从图片库或搜索进入。</p>
<p><a class="s-btn" href="https://chenhua.net/images/">图片库</a> <a class="s-btn" href="https://chenhua.net/">主站</a></p>
<script>if(location.pathname.indexOf("/en/")===0){document.documentElement.lang="en";document.getElementById("t").textContent="Page not found";document.getElementById("p").textContent="This site has been rebuilt. Please enter through the image library or search."}</script>
</main></body></html>""" % (K.BUILD_ID, K.BUILD_ID)
    files["404.html"] = html


def sitemap(site_key, paths):
    entries = []
    for path in paths:
        for lang in ("zh", "en"):
            loc = K.page_url(site_key, path, lang)
            alt_zh = K.page_url(site_key, path, "zh")
            alt_en = K.page_url(site_key, path, "en")
            entries.append(
                "<url><loc>%s</loc><xhtml:link rel='alternate' hreflang='zh-CN' href='%s'/>"
                "<xhtml:link rel='alternate' hreflang='en' href='%s'/>"
                "<xhtml:link rel='alternate' hreflang='x-default' href='%s'/></url>"
                % (K.esc(loc), K.esc(alt_zh), K.esc(alt_en), K.esc(alt_zh))
            )
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">%s</urlset>' % "".join(entries))


def finish_site(site_key, files, paths):
    if "/legal/" not in paths:
        paths = list(paths) + ["/legal/"]
    files["robots.txt"] = "User-agent: *\nAllow: /\nSitemap: https://%s/sitemap.xml\n" % K.site_meta(site_key)["domain"]
    files["sitemap.xml"] = sitemap(site_key, paths)
    files[".nojekyll"] = ""
    files["CNAME"] = K.site_meta(site_key)["domain"] + "\n"
    build_legal(site_key, files)
    build_404(site_key, files)
    count = write_site(site_key, files)
    build_assets(site_key)
    return count


def record_meta_rows(rec, lang):
    m = rec["meta"]
    rows = []
    def add(label_zh, label_en, value):
        if value in (None, "", []):
            return
        rows.append((label_zh, label_en, value))
    add("作者", "Creator", K.pick(m, "creator", lang))
    add("流派", "Movement", K.pick(m, "movement", lang))
    add("馆藏", "Collection", K.pick(m, "holding", lang))
    add("尺寸", "Dimensions", K.pick(m, "dimensions", lang))
    add("材质", "Medium", K.pick(m, "medium", lang))
    add("来源", "Source", K.pick(m, "source_short", lang) or m.get("source"))
    add("年代", "Date", K.pick(m, "date_label", lang) or year_of(m))
    add("地域", "Region", K.pick(m, "region", lang))
    add("许可", "Licence", m.get("license"))
    add("权利状态", "Rights", m.get("rights_status"))
    return rows


def record_page(rec, lang, all_records):
    meta = rec["meta"]
    century = century_of(meta)
    site_key = "photo" if rec["collection"] == "links" else century
    path = record_path(rec)
    title = clean_title(K.pick(meta, "title", lang, meta["id"]))
    title_en = clean_title(meta.get("title_en") or title)
    desc = K.pick(meta, "date_label", lang) + " · " + K.pick(meta, "creator", lang)
    image, thumb = image_url(rec, century)
    body_text = re.sub(r"!\[[^\]]*\]\([^)]+\)\s*", "", rec["body"]).strip()
    note = body_text if lang == "zh" else ""
    if lang == "en":
        tr = EN_RECORDS.get(meta["id"], {})
        note = tr.get("note") or ""
        if tr.get("title"):
            title = clean_title(tr["title"])
    if note:
        note_html = K.md_to_html(note)
    elif lang == "en":
        note_html = "<p>%s</p>" % K.esc("An English note for this record has not been published yet. The object metadata below is authoritative.")
    else:
        note_html = ""
    fig = ""
    if image:
        fig = ('<figure class="s-figure"><a href="%s" target="_blank" rel="noopener">'
               '<img src="%s" alt="%s" fetchpriority="high" decoding="async"></a>'
               '<figcaption>%s</figcaption></figure>'
               % (K.esc(image), K.esc(thumb or image), K.esc(title),
                  K.esc(" · ".join(str(x) for x in [K.pick(meta, "creator", lang), K.pick(meta, "source_short", lang), meta.get("license")] if x))))
    rows = "".join("<div><b>%s</b>%s</div>" % (K.esc(z if lang == "zh" else e), K.esc(v)) for z, e, v in record_meta_rows(rec, lang))
    actions = []
    if meta.get("page_url"):
        actions.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">%s</a>' % (
            K.esc(meta["page_url"]), "Object page ↗" if lang == "en" else "对象页 ↗"))
    if meta.get("license_url"):
        actions.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">%s</a>' % (
            K.esc(meta["license_url"]), "Licence deed ↗" if lang == "en" else "许可原文 ↗"))
    if meta.get("source_url"):
        actions.append('<a class="s-btn" href="%s" target="_blank" rel="noopener">%s</a>' % (
            K.esc(meta["source_url"]), "Source ↗" if lang == "en" else "来源 ↗"))
    actions.append('<a class="s-btn gold" href="%s">%s</a>' % (
        K.esc(K.origin(site_key) + K.lang_path("/records/" if rec["collection"] != "links" else "/", lang)),
        "Back to the century" if lang == "en" else "返回本世纪"))
    related = [r for r in all_records if r is not rec and r["collection"] == rec["collection"] and century_of(r["meta"]) == century][:4]
    related_html = ""
    if related:
        related_html = ('<section class="s-related"><h2>%s</h2><div class="s-grid">%s</div></section>'
                        % ("同世纪记录" if lang == "zh" else "More from this century",
                           "".join(card_html(r, lang, site_key) for r in related)))
    ld = {
        "@context": "https://schema.org",
        "@type": "VisualArtwork" if rec["collection"] == "paintings" else ("Photograph" if rec["collection"] == "photos" else "CreativeWork"),
        "name": title_en if lang == "en" else title,
        "alternateName": title if lang == "en" else title_en,
        "datePublished": str(meta.get("date_label") or year_of(meta) or ""),
        "creator": K.pick(meta, "creator", "en"),
        "creditText": " · ".join(str(x) for x in [K.pick(meta, "creator", "en"), K.pick(meta, "source_short", "en"), meta.get("license")] if x),
        "license": meta.get("license_url") or meta.get("license"),
        "isPartOf": K.origin(site_key) + "/",
        "inLanguage": ["zh-CN", "en"],
    }
    if image:
        ld["contentUrl"] = image
        ld["thumbnailUrl"] = thumb or image
    extra = '<script type="application/ld+json">%s</script>\n' % json.dumps(ld, ensure_ascii=False)
    kicker = {"paintings": ("绘画记录", "Painting record"), "photos": ("照片记录", "Photograph record"),
              "objects": ("器物记录", "Object record"), "links": ("外链卡", "External link card")}[rec["collection"]]
    body = ('<main class="s-main"><div class="s-kicker">%s · %s</div>'
            '<h1 class="s-title">%s</h1>'
            '<div class="s-sub"><span>%s</span></div>%s'
            '<div class="s-note">%s</div>'
            '<div class="s-meta">%s</div>'
            '<div class="s-actions">%s</div>%s</main>'
            % (kicker[0] if lang == "zh" else kicker[1], K.esc(meta.get("date_label") or year_of(meta) or ""),
               K.esc(title),
               K.esc(" · ".join(str(x) for x in [K.pick(meta, "place", lang), K.pick(meta, "medium", lang)] if x)),
               fig, note_html, rows, "".join(actions), related_html))
    return K.page(site_key, lang, path, title, desc, body, extra, "article", image)


def build_records(records):
    global EN_RECORDS
    EN_RECORDS = {}
    for p in (PAINT / "i18n" / "records.en.json", PHOTO / "i18n" / "records.en.json"):
        if p.exists():
            EN_RECORDS.update(json.loads(p.read_text(encoding="utf-8")))
    counts = {}
    by_site = {s: [] for s in RECORD_SITES}
    for rec in records:
        if rec["collection"] in ("links", "stories"):
            continue
        rec["_century"] = century_of(rec["meta"])
        if rec["_century"] in by_site:
            by_site[rec["_century"]].append(rec)
    for site_key, items in by_site.items():
        files = {}
        paths = ["/", "/records/"]
        items.sort(key=lambda r: (year_of(r["meta"]) or 0, r["meta"]["id"]))
        for lang in ("zh", "en"):
            title = SITE_TITLES.get(site_key, (K.site_meta(site_key)["zh"], K.site_meta(site_key)["en"]))[0 if lang == "zh" else 1]
            desc = ("%s 世纪的绘画、照片与器物记录" if lang == "zh" else "Painting, photograph and object records of the %s century") % site_key.replace("century", "")
            cards = "".join(card_html(r, lang, site_key) for r in items)
            body = ('<main class="s-main"><div class="s-kicker">%s</div>'
                    '<h1 class="s-title">%s</h1><p class="s-lede">%s</p>'
                    '<div class="s-grid">%s</div></main>'
                    % ("记录层" if lang == "zh" else "Record layer", K.esc(title),
                       K.esc("%d 条记录" % len(items) if lang == "zh" else "%d records" % len(items)), cards))
            files[K.lang_path("/", lang).lstrip("/") + "index.html"] = K.page(site_key, lang, "/", title, desc, body)
            # catalog
            groups = {}
            for r in items:
                groups.setdefault(record_kind(r["collection"]), []).append(r)
            parts = []
            for kind in ("painting", "photo", "object"):
                group = groups.get(kind)
                if not group:
                    continue
                parts.append("<h2>%s</h2><div class='s-grid'>%s</div>" % (
                    {"painting": "绘画" if lang == "zh" else "Painting",
                     "photo": "照片" if lang == "zh" else "Photograph",
                     "object": "器物" if lang == "zh" else "Object"}[kind],
                    "".join(card_html(r, lang, site_key) for r in group)))
            body = ('<main class="s-main"><div class="s-kicker">%s</div><h1 class="s-title">%s</h1>%s</main>'
                    % ("完整目录" if lang == "zh" else "Full catalogue",
                       K.esc(title + ("目录" if lang == "zh" else " catalogue")), "".join(parts)))
            files[K.lang_path("/records/", lang).lstrip("/") + "index.html"] = K.page(site_key, lang, "/records/", title, desc, body)
        for r in items:
            for lang in ("zh", "en"):
                path = record_path(r)
                files[K.lang_path(path, lang).lstrip("/")] = record_page(r, lang, items)
                if path not in paths:
                    paths.append(path)
        counts[site_key] = finish_site(site_key, files, paths)
    return counts, by_site


def collection_pages(repo, site_key, section, types, lang_title):
    """Build index + article pages for history/ or craft/ collections."""
    out = []
    for type_key in types:
        d = repo / section / type_key
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            meta, body = K.read_md(p)
            meta.setdefault("id", p.stem)
            out.append({"type": type_key, "meta": meta, "body": body, "path": p})
    return out


def first_para(body, lang):
    text = K.lang_section(body, lang)
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("**") and s != "---":
            return s
    return ""


def item_title(meta, lang):
    for key in ("title_" + lang, "name_" + lang, "zh" if lang == "zh" else "en", "title", "name"):
        if meta.get(key):
            return str(meta[key])
    return meta.get("id", "")


def item_years(meta, lang):
    return meta.get("years_" + lang) or meta.get("years") or meta.get("date_label") or meta.get("date") or ""


EN_LABELS = {
    "问题": "Question", "论点": "Thesis", "观看": "Look", "说明": "Note",
    "摘要": "Summary", "特征": "Traits", "小传": "Biography", "导言": "Introduction",
    "结语": "Closing", "背景": "Context", "为什么": "Why", "解读": "Reading",
    "关键词": "Keywords", "主题": "Themes", "步骤": "Steps", "副题": "Subtitle",
    "路线": "Route", "名称": "Name",
}


def article_page(site_key, lang, section, type_key, item, all_items):
    meta = item["meta"]
    title = item_title(meta, lang)
    body_text = K.lang_section(item["body"], lang)
    if lang == "en":
        for zh, en in EN_LABELS.items():
            body_text = body_text.replace("**" + zh + "**", "**" + en + "**")
    html_body = K.md_to_html(body_text)
    if not html_body and lang == "en":
        html_body = "<p>This page is being translated. The Chinese original is available at the Chinese URL.</p>"
    path = "/%s/%s/%s.html" % (section, type_key, meta.get("id"))
    years = item_years(meta, lang)
    type_label = TYPE_LABELS.get(type_key, (type_key, type_key))[0 if lang == "zh" else 1]
    section_label = ("历史" if lang == "zh" else "History") if section == "history" else ("技艺" if lang == "zh" else "Craft")
    body = ('<main class="s-main"><div class="s-kicker">%s · %s</div><h1 class="s-title">%s</h1>'
            '<div class="s-sub">%s</div><div class="s-note">%s</div></main>'
            % (section_label, K.esc(type_label), K.esc(title), K.esc(years), html_body))
    return K.page(site_key, lang, path, title, first_para(item["body"], lang) or title, body)


def century_cards(lang):
    out = []
    for key in ("pre19century", "19century", "20century", "21century", "aiera"):
        meta = K.site_meta(key)
        out.append('<a class="s-card" href="%s"><div class="c"><b>%s</b><span>%s</span></div></a>'
                   % (K.esc(K.page_url(key, "/", lang)), K.esc(meta["zh"] if lang == "zh" else meta["en"]),
                      K.esc(meta["tagline_zh"] if lang == "zh" else meta["tagline_en"])))
    return ('<h2>%s</h2><div class="s-grid">%s</div>'
            % ("作品记录" if lang == "zh" else "Image records", "".join(out)))


def build_content_site(site_key, repo, section, types, label_zh, label_en):
    items = collection_pages(repo, site_key, section, types, None)
    files = {}
    paths = ["/", "/%s/" % section]
    label = label_zh if True else label_en
    by_type = {}
    for it in items:
        by_type.setdefault(it["type"], []).append(it)
    for lang in ("zh", "en"):
        title = SITE_TITLES[site_key][0 if lang == "zh" else 1]
        cards = []
        for type_key, group in by_type.items():
            links = []
            for it in group:
                years = K.esc(item_years(it["meta"], lang))
                year_html = "<span>%s</span>" % years if years else ""
                links.append(
                    '<a class="s-card" href="%s"><div class="c"><b>%s</b>%s</div></a>'
                    % (K.esc(K.lang_path("/%s/%s/%s.html" % (section, type_key, it["meta"].get("id")), lang)),
                       K.esc(item_title(it["meta"], lang)), year_html))
            cards.append("<h2>%s</h2><div class='s-grid'>%s</div>" % (
                K.esc(TYPE_LABELS.get(type_key, (type_key, type_key))[0 if lang == "zh" else 1]), "".join(links)))
        body = ('<main class="s-main"><div class="s-kicker">%s</div><h1 class="s-title">%s</h1>'
                '<p class="s-lede">%s</p>%s%s</main>'
                % (K.esc(label_zh if lang == "zh" else label_en), K.esc(title),
                   K.esc("%d 篇" % len(items) if lang == "zh" else "%d articles" % len(items)),
                   "".join(cards), century_cards(lang)))
        files[K.lang_path("/", lang).lstrip("/") + "index.html"] = K.page(site_key, lang, "/", title, first_para("", lang) or title, body)
        files[K.lang_path("/%s/" % section, lang).lstrip("/") + "index.html"] = K.page(site_key, lang, "/%s/" % section, title, title, body)
    for it in items:
        path = "/%s/%s/%s.html" % (section, it["type"], it["meta"].get("id"))
        paths.append(path)
        for lang in ("zh", "en"):
            files[K.lang_path(path, lang).lstrip("/")] = article_page(site_key, lang, section, it["type"], it, items)
    return finish_site(site_key, files, paths)


def build_photo_links(records):
    files = {}
    paths = ["/", "/links/"]
    links = [r for r in records if r["collection"] == "links"]
    for lang in ("zh", "en"):
        title = SITE_TITLES["photo"][0 if lang == "zh" else 1]
        cards = "".join(card_html(r, lang, "photo") for r in links)
        body = ('<main class="s-main"><h1 class="s-title">%s</h1><div class="s-grid">%s</div></main>'
                % (K.esc("外链卡" if lang == "zh" else "External link cards"), cards))
        files[K.lang_path("/links/", lang).lstrip("/") + "index.html"] = K.page("photo", lang, "/links/", title, title, body)
    for r in links:
        path = record_path(r)
        paths.append(path)
        for lang in ("zh", "en"):
            files[K.lang_path(path, lang).lstrip("/")] = record_page(r, lang, links)
    return files, paths


def load_story_en():
    p = PHOTO / "i18n" / "stories.en.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


STORY_EN = {}


def story_image(item_id, records_by_id):
    rec = records_by_id.get(item_id)
    if rec:
        return image_url(rec)
    hit = IMAGES.get(item_id)
    if hit:
        cent = hit["century"]
        rel = hit["target"].replace("\\", "/").split("/images/%s/" % cent, 1)[-1]
        return "https://%s.chenhua.net/%s" % (cent, rel), "https://%s.chenhua.net/thumbs/%s" % (cent, rel)
    return "", ""


def story_page(story, lang, records_by_id):
    meta = story["meta"]
    sid = meta["id"]
    tr = STORY_EN.get(sid, {})
    title = clean_title(tr.get("title") or meta.get("title") or sid)
    subtitle = tr.get("subtitle") or meta.get("subtitle") or ""
    date_label = meta.get("date_label") or meta.get("date") or ""
    place = meta.get("place") or ""
    chapters = meta.get("chapters") or []
    if lang == "en" and tr.get("chapters"):
        en_ch = tr["chapters"]
        if isinstance(en_ch, dict):
            chapters = [
                {"title": en_ch.get(str(i), {}).get("title", ch.get("title", "")),
                 "text": en_ch.get(str(i), {}).get("text", ""),
                 "items": ch.get("items") or []}
                for i, ch in enumerate(chapters)
            ]
    image, thumb = story_image(meta.get("cover"), records_by_id)
    fig = ""
    if image:
        fig = ('<figure class="s-figure"><img src="%s" alt="%s" fetchpriority="high" decoding="async">'
               '<figcaption>%s</figcaption></figure>' % (K.esc(thumb or image), K.esc(title), K.esc(date_label)))
    parts = []
    for ch in chapters:
        items = []
        for item in ch.get("items") or []:
            iid = item.get("id")
            img, th = story_image(iid, records_by_id)
            cap = item.get("caption") or iid
            rec = records_by_id.get(iid)
            href = ""
            if rec and rec["collection"] in ("photos", "paintings", "objects"):
                href = K.origin(century_of(rec["meta"])) + K.lang_path(record_path(rec), lang)
            inner = ('<img src="%s" alt="%s" loading="lazy" decoding="async"><div class="c"><b>%s</b></div>'
                     % (K.esc(th or img), K.esc(cap), K.esc(cap))) if img else ('<div class="c"><b>%s</b></div>' % K.esc(cap))
            items.append('<a class="s-card" href="%s">%s</a>' % (K.esc(href), inner) if href else '<div class="s-card">%s</div>' % inner)
        parts.append('<section class="s-note"><h2>%s</h2><p>%s</p><div class="s-grid">%s</div></section>'
                     % (K.esc(ch.get("title", "")), K.esc(ch.get("text", "")), "".join(items)))
    path = "/stories/%s.html" % sid
    body = ('<main class="s-main"><div class="s-kicker">%s · %s</div><h1 class="s-title">%s</h1>'
            '<div class="s-sub">%s%s</div>%s%s</main>'
            % ("影像档案" if lang == "zh" else "Visual dossier", K.esc(date_label), K.esc(title),
               K.esc(subtitle), (" · " + K.esc(place)) if place else "", fig, "".join(parts)))
    desc = subtitle if len(subtitle) >= 20 else title
    return K.page("photo", lang, path, title, desc, body, og_type="article", image=image)


def build_stories(records):
    global STORY_EN
    STORY_EN = load_story_en()
    stories = [r for r in records if r["collection"] == "stories"]
    by_id = {r["meta"]["id"]: r for r in records}
    files = {}
    paths = ["/stories/"]
    for lang in ("zh", "en"):
        cards = []
        for s in sorted(stories, key=lambda r: str(r["meta"].get("date") or ""), reverse=True):
            meta = s["meta"]
            tr = STORY_EN.get(meta["id"], {})
            title = clean_title(tr.get("title") or meta.get("title") or meta["id"])
            img, th = story_image(meta.get("cover"), by_id)
            pic = ('<img src="%s" alt="%s" loading="lazy" decoding="async">' % (K.esc(th or img), K.esc(title))) if img else ""
            cards.append('<a class="s-card" href="%s">%s<div class="c"><b>%s</b><span>%s</span></div></a>'
                         % (K.esc(K.lang_path("/stories/%s.html" % meta["id"], lang)), pic,
                            K.esc(title), K.esc(meta.get("date_label") or meta.get("date") or "")))
        body = ('<main class="s-main"><h1 class="s-title">%s</h1><div class="s-grid">%s</div></main>'
                % ("影像档案" if lang == "zh" else "Visual dossiers", "".join(cards)))
        files[K.lang_path("/stories/", lang).lstrip("/") + "index.html"] = K.page(
            "photo", lang, "/stories/", "影像档案" if lang == "zh" else "Visual dossiers",
            "摄影故事" if lang == "zh" else "Photography stories", body)
    for s in stories:
        path = "/stories/%s.html" % s["meta"]["id"]
        paths.append(path)
        for lang in ("zh", "en"):
            files[K.lang_path(path, lang).lstrip("/")] = story_page(s, lang, by_id)
    return files, paths


def main():
    records = load_records()
    counts, by_site = build_records(records)
    print("record sites", counts)

    paint_files = build_content_site("paint", PAINT, "history",
                                     ("chapters", "movements", "artists", "periods", "regions", "trails"),
                                     "绘画史", "Painting history")
    painting_files = build_content_site("painting", PAINT, "craft",
                                        ("techniques", "readings", "dialogues"),
                                        "学习绘画", "Learn painting")
    photo_files = build_content_site("photo", PHOTO, "history",
                                     ("eras", "chapters", "movements", "photographers", "exhibitions", "regions", "trails", "themes"),
                                     "摄影史", "Photography history")
    photography_files = build_content_site("photography", PHOTO, "craft",
                                           ("processes", "readings"),
                                           "学习摄影", "Learn photography")
    print("content sites", paint_files, painting_files, photo_files, photography_files)

    # photo links and stories are merged into the photo site output
    link_files, link_paths = build_photo_links(records)
    story_files, story_paths = build_stories(records)
    base = RELEASE / "photo"
    for rel, text in list(link_files.items()) + list(story_files.items()):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    # ai guide placeholder
    files = {}
    for lang in ("zh", "en"):
        title = SITE_TITLES["ai"][0 if lang == "zh" else 1]
        body = ('<main class="s-main"><h1 class="s-title">%s</h1><p class="s-lede">%s</p>'
                '<div class="s-grid"><a class="s-card" href="https://aiera.chenhua.net/%s"><div class="c"><b>%s</b><span>%s</span></div></a></div></main>'
                % (K.esc(title),
                   K.esc("AI 生成图像的方法、配方与声明。首批内容整理中。" if lang == "zh"
                         else "Methods, recipes and disclosure for AI-generated images. The first batch is in preparation."),
                   "en/" if lang == "en" else "",
                   K.esc("AI 影像库" if lang == "zh" else "AI image archive"),
                   K.esc("记录与配方" if lang == "zh" else "Records and recipes")))
        files[K.lang_path("/", lang).lstrip("/") + "index.html"] = K.page("ai", lang, "/", title, title, body)
    finish_site("ai", files, ["/"])

    # main portal
    files = {}
    cards = [
        ("paint", "绘画史", "Painting History", "章节、流派、艺术家与作品目录"),
        ("painting", "学习绘画", "Learn Painting", "材料、技法、修复与观看"),
        ("photo", "摄影史", "Photography History", "时代、摄影家、展览与作品目录"),
        ("photography", "学习摄影", "Learn Photography", "工艺、曝光、冲洗与数字工作流"),
        ("ai", "AI 图像", "AI Images", "生成方法、配方与声明"),
    ]
    for lang in ("zh", "en"):
        grid = "".join(
            '<a class="s-card" href="%s"><div class="c"><b>%s</b><span>%s</span></div></a>'
            % (K.esc(K.page_url(key, "/", lang)), K.esc(z if lang == "zh" else e), K.esc(d))
            for key, z, e, d in cards)
        body = ('<main class="s-main"><div class="s-kicker">%s</div><h1 class="s-title">%s</h1>'
                '<p class="s-lede">%s</p><div class="s-grid">%s</div></main>'
                % ("尘画" if lang == "zh" else "Frame & Grain",
                   K.esc("尘归尘，画归画" if lang == "zh" else "Image as history"),
                   K.esc("历史影像的索引、叙事与学习方法。" if lang == "zh" else "An index, narrative and learning resource for historical images."),
                   grid))
        files[K.lang_path("/", lang).lstrip("/") + "index.html"] = K.page("main", lang, "/", "尘画" if lang == "zh" else "Frame & Grain",
                                                                          "历史影像索引" if lang == "zh" else "Historical image index", body)
        # images portal
        lib = "".join(
            '<a class="s-card" href="%s"><div class="c"><b>%s</b><span>%s</span></div></a>'
            % (K.esc(K.page_url(k, "/", lang)), K.esc(K.site_meta(k)["zh"] if lang == "zh" else K.site_meta(k)["en"]),
               K.esc("%d 条" % len(by_site[k]) if lang == "zh" else "%d records" % len(by_site[k])))
            for k in RECORD_SITES)
        body = ('<main class="s-main"><h1 class="s-title">%s</h1><div class="s-grid">%s</div></main>'
                % ("图片库" if lang == "zh" else "Image Library", lib))
        files[K.lang_path("/images/", lang).lstrip("/") + "index.html"] = K.page("main", lang, "/images/", "图片库" if lang == "zh" else "Image Library",
                                                                                "按世纪进入记录站" if lang == "zh" else "Enter the record sites by century", body)
    finish_site("main", files, ["/", "/images/"])

    # merge photo links paths into photo sitemap by regenerating
    photo_paths = ["/"] + ["/history/"]
    for it in collection_pages(PHOTO, "photo", "history", ("eras", "chapters", "movements", "photographers", "exhibitions", "regions", "trails", "themes"), None):
        photo_paths.append("/history/%s/%s.html" % (it["type"], it["meta"].get("id")))
    photo_paths += ["/links/"] + [record_path(r) for r in records if r["collection"] == "links"]
    photo_paths += story_paths
    photo_paths.append("/legal/")
    (RELEASE / "photo" / "sitemap.xml").write_text(sitemap("photo", photo_paths), encoding="utf-8")

    report = {"record_sites": counts, "records": len(records)}
    (DATA / "v32-build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
