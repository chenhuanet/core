# -*- coding: utf-8 -*-
"""离线英译：记录说明与主题正文。

使用 NLLB-200-distilled-600M，分句翻译并做术语预映射，结果写入
next/content/i18n/records.en.json 与 stories.en.json。
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "next" / "tools"))
import build_preview as bp  # noqa: E402

I18N = ROOT / "next" / "content" / "i18n"
CACHE_PATH = I18N / ".mt_cache.json"
RECORDS_PATH = I18N / "records.en.json"
STORIES_PATH = I18N / "stories.en.json"
CAPTIONS_PATH = I18N / "captions.en.json"

CJK = re.compile(r"[\u4e00-\u9fff]")

PRE_MAP = {
    "达盖尔": "Daguerre",
    "银版法": "daguerreotype process",
    "银版照相": "daguerreotype",
    "银版": "daguerreotype",
    "蛋白印相": "albumen print",
    "蛋白照片": "albumen print",
    "锡版照": "tintype",
    "锡版": "tintype",
    "盐纸印相": "salt print",
    "盐纸": "salt print",
    "橱柜卡片照": "cabinet card",
    "橱柜卡片": "cabinet card",
    "名片照": "carte-de-visite",
    "珂罗版": "collotype",
    "伍兹金属版": "Woodburytype",
    "蓝晒": "cyanotype",
    "明信片": "postcard",
    "立体照片": "stereograph",
    " stereograph": "stereograph",
    "巴黎公社": "Paris Commune",
    "普法战争": "Franco-Prussian War",
    "美国内战": "American Civil War",
    "第一次世界大战": "First World War",
    "第二次世界大战": "Second World War",
    "大萧条": "Great Depression",
    "泰坦尼克号": "Titanic",
    "埃菲尔铁塔": "Eiffel Tower",
    "大沽炮台": "Taku Forts",
    "故宫博物院": "Palace Museum",
    "大英博物馆": "British Museum",
    "美国国会图书馆": "Library of Congress",
    "史密森尼": "Smithsonian",
    "维基共享资源": "Wikimedia Commons",
    "克利夫兰艺术博物馆": "Cleveland Museum of Art",
    "阿波罗": "Apollo",
    "国际空间站": "International Space Station",
    "猎户座": "Orion",
    "阿尔忒弥斯": "Artemis",
}

POST_MAP = [
    (r"\bDagher\b", "Daguerre"),
    (r"\bDager\b", "Daguerre"),
    (r"\bDaguerreotype process process\b", "daguerreotype process"),
    (r"\bsilver version\b", "daguerreotype"),
    (r"\bsilver plate process\b", "daguerreotype process"),
    (r"\bknitting machine\b", "loom"),
    (r"\bCotton Stadium\b", "cotton mill"),
    (r"\bthe photograph photo\b", "the photograph"),
    (r"\bphoto photograph\b", "photograph"),
    (r"\bthe cabinet card photo\b", "the cabinet card"),
    (r"\bDust to dust, image to image\b", "Dust to dust, image to image"),
]

TITLE_MAP = {
    "lnk-dpm": "The Palace Museum · Digital Cultural Relics",
    "1843-daguerreotype": "A man photographed himself into the studio",
    "1840s-priest": "A priest in daguerreotype",
    "lnk-bm": "The British Museum · Collection images",
    "1852-bridge": "The bridge at Paralda",
    "1860-taku": "The Taku Forts: the corner the French stormed",
    "1863-soldier": "The soldier lying down",
    "1860s-tintype": "Andy Wilson's tintype",
    "1871-paris-barricade": "The barricade on Rue de Castiglione",
    "1875-market": "Market day outside the city wall",
    "1888-eiffel-construction": "When the tower was half built",
    "commons-1900-beijing": "Beijing in 1900",
    "1900-women": "Two women who left no names",
    "1900-mailcar": "Boston's mail streetcar",
    "lnk-loc": "Library of Congress · Unassessed images",
    "1908-boy": "The boy at the loom",
    "commons-1912-titanic": "Titanic leaving Southampton",
    "1915-suffrage": "A women's suffrage postcard",
    "1918-influenza-ward": "1918: an influenza ward",
    "1918-redcross-station": "A demonstration at a Red Cross first-aid station",
    "commons-1930-shanghai": "Nanjing Road in the 1930s",
    "commons-1936-migrant": "Migrant Mother",
    "commons-1944-dday": "'Into the Jaws of Death'",
    "1945-vmail": "A V-Mail letter",
    "commons-1945-hiroshima": "Hiroshima, after the bomb",
    "commons-1945-iwojima": "The flag on Iwo Jima",
    "1968-earthrise-first": "Seeing Earthrise for the first time",
    "commons-1969-bootprint": "One footprint",
    "1969-saturn": "Saturn V",
    "1969-plaque": "The plaque left on the Moon",
    "commons-1969-aldrin": "The photographer reflected in the visor",
    "1981-sts1": "STS-1 lifts off",
    "commons-1989-berlin": "Juggling on the Berlin Wall",
    "2012-earth": "Looking down from the International Space Station",
    "2022-artemis": "Artemis I flight readiness review",
    "2026-earthset": "Earthset from Orion",
}


def load_cache():
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    tmp.replace(CACHE_PATH)


def split_sentences(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    parts = re.split(r"(?<=[。！？!?])", text)
    out = []
    for p in parts:
        p = p.strip()
        while len(p) > 420:
            cut = max(p.rfind("，", 0, 420), p.rfind("；", 0, 420), p.rfind("、", 0, 420))
            if cut < 120:
                cut = 420
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    return out


def pre_map(text):
    for zh, en in PRE_MAP.items():
        text = text.replace(zh, en)
    return text


def post_map(text):
    for pat, rep in POST_MAP:
        text = re.sub(pat, rep, text)
    text = text.replace("  ", " ").strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


class Translator:
    def __init__(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        self.torch = torch
        self.mid = "facebook/nllb-200-distilled-600M"
        self.tok = AutoTokenizer.from_pretrained(self.mid, src_lang="zho_Hans", tgt_lang="eng_Latn")
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.mid)
        self.model.eval()
        torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
        self.bos = self.tok.convert_tokens_to_ids("eng_Latn")

    def generate(self, texts):
        import torch
        enc = self.tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            ids = self.model.generate(**enc, forced_bos_token_id=self.bos, max_new_tokens=256)
        return [self.tok.decode(row, skip_special_tokens=True).strip() for row in ids]

    def translate(self, text, cache):
        key = hashlib.sha1(("v2|" + text).encode("utf-8")).hexdigest()
        if key in cache:
            return cache[key]
        sentences = split_sentences(pre_map(text))
        out = []
        batch = []
        for s in sentences:
            batch.append(s)
            if len(batch) >= 8:
                out.extend(self.generate(batch))
                batch = []
        if batch:
            out.extend(self.generate(batch))
        result = post_map(" ".join(x for x in out if x))
        if CJK.search(result):
            result = re.sub(r"[\u4e00-\u9fff]+", "", result).strip()
        cache[key] = result
        return result


def translate_record_notes(limit=0, save_every=25):
    rows = bp.load_records()
    existing = {}
    if RECORDS_PATH.exists():
        existing = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    cache = load_cache()
    translator = Translator()
    todo = [r for r in rows if CJK.search(r.get("note") or "")]
    if limit:
        todo = todo[:limit]
    print("records to translate:", len(todo))
    pending = {r["id"]: (existing.get(r["id"], {}) or {}) for r in todo}
    done = 0
    t0 = time.time()
    for r in todo:
        rid = r["id"]
        entry = pending.setdefault(rid, {})
        if not entry.get("note"):
            entry["note"] = translator.translate(r.get("note") or "", cache)
        if CJK.search(r.get("title") or ""):
            entry["title"] = TITLE_MAP.get(rid) or translator.translate(r.get("title") or "", cache)
        done += 1
        if done % save_every == 0:
            existing.update(pending)
            RECORDS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=1, sort_keys=True),
                                    encoding="utf-8", newline="\n")
            save_cache(cache)
            rate = done / max(1e-6, time.time() - t0)
            print("  %d/%d  %.2f/s" % (done, len(todo), rate), flush=True)
    existing.update(pending)
    RECORDS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=1, sort_keys=True),
                            encoding="utf-8", newline="\n")
    save_cache(cache)
    print("records i18n written:", len(existing))


def translate_captions():
    rows = bp.load_records()
    stories = bp.load_story_files(rows)
    caps = sorted({it.get("caption") for s in stories
                   for ch in s.get("chapters") or []
                   for it in ch.get("items") or [] if it.get("caption")})
    existing = {}
    if CAPTIONS_PATH.exists():
        existing = json.loads(CAPTIONS_PATH.read_text(encoding="utf-8"))
    todo = [c for c in caps if c not in existing]
    print("captions total", len(caps), "todo", len(todo))
    translator = Translator()
    cache = load_cache()
    for i, c in enumerate(todo, 1):
        existing[c] = translator.translate(c, cache)
        if i % 10 == 0:
            CAPTIONS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=1),
                                     encoding="utf-8", newline="\n")
            save_cache(cache)
            print("  %d/%d" % (i, len(todo)), flush=True)
    CAPTIONS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=1),
                             encoding="utf-8", newline="\n")
    save_cache(cache)
    print("captions written:", len(existing))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--captions", action="store_true")
    args = ap.parse_args()
    if args.captions:
        translate_captions()
    else:
        translate_record_notes(limit=args.limit)


if __name__ == "__main__":
    main()
