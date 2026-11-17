# -*- coding: utf-8 -*-
"""Build a real-data three-axis dataset from the existing bundle."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\chenhua\Desktop\chenhua")
BUNDLE = ROOT / "next" / "dist" / "data" / "bundle.js"

SERIES = [
    {"key": "space", "name": "太空探索", "name_en": "Space Exploration", "color": "#234c5d", "glyph": "轨",
     "desc": "火箭、卫星与深空探测器。"},
    {"key": "disaster", "name": "灾难与调查", "name_en": "Disaster & Investigation", "color": "#a64227", "glyph": "灾",
     "desc": "火灾、空难、地震与事故调查。"},
    {"key": "war", "name": "战争与冲突", "name_en": "War & Conflict", "color": "#7a2f26", "glyph": "战",
     "desc": "战线、战后与战争影像。"},
    {"key": "politics", "name": "政治与制度", "name_en": "Politics & Institutions", "color": "#3f4a60", "glyph": "政",
     "desc": "总统、议会、法院与街头政治。"},
    {"key": "science", "name": "科学与技术", "name_en": "Science & Technology", "color": "#2f5f57", "glyph": "科",
     "desc": "实验室、计算机、飞机与发明。"},
    {"key": "city", "name": "工程与城市", "name_en": "Engineering & City", "color": "#6b5b3e", "glyph": "构",
     "desc": "桥梁、隧道、铁塔与城市天际线。"},
    {"key": "rail", "name": "铁路与工业", "name_en": "Rail & Industry", "color": "#4e4b47", "glyph": "轨",
     "desc": "蒸汽、钢轨与工厂。"},
    {"key": "art", "name": "艺术与图像", "name_en": "Art & Image", "color": "#7a4a5a", "glyph": "像",
     "desc": "摄影家、画家与美术馆。"},
    {"key": "world", "name": "社会与日常", "name_en": "Society & Everyday", "color": "#4b5964", "glyph": "世",
     "desc": "城市生活、教育、宗教、体育与普通人的日常。"},
]

# Explicit overrides for the 13 prototype stories; keep their curated series stable.
OVERRIDES = {
    "today-01-01-new-horizons-2": "space",
    "today-05-06-channel-tunnel-alt": "city",
    "today-10-31-moons-of-pluto": "space",
    "today-01-15-us-airways-flight-1549-2": "disaster",
    "today-03-25-triangle-shirtwaist-factory-fire-alt": "disaster",
    "today-11-16-skylab-4": "space",
    "today-08-12-japan-air-lines-flight-123": "disaster",
    "today-12-23-tokyo-tower": "city",
    "today-09-27-locomotion-no-1": "rail",
    "today-05-29-portland-oregon": "city",
    "today-02-10-roy-lichtenstein-2": "art",
    "today-11-01-ansel-adams": "art",
    "today-10-21-solomon-r-guggenheim-museum-alt": "art",
    # Seven no-date long reads: keep them on the editorial axis.
    "first-fifty-years": "art",
    "unnamed-faces": "art",
    "earth-to-moon": "space",
    "street-a-day": "art",
    "china-1850-1930": "art",
    "hands-at-work": "art",
    "arecibo-1974": "space",
}

RULES = {
    "space": [
        "太空", "航天", "火箭", "卫星", "衛星", "飞船", "飛船", "空间站", "太空站", "天空实验室",
        "阿波罗", "阿波羅", "旅行者", "哈勃", "哈伯", "望远镜", "望遠鏡", "天文", "天文台", "宇宙",
        "星云", "星雲", "彗星", "小行星", "行星", "月面", "月球", "登月", "探月", "探测器", "探測器",
        "探测车", "火星", "冥王星", "柯伊伯", "星尘", "星塵", "勇气号", "勇氣號", "机遇号", "矮行星",
        "事件视界", "事件視界", "先驱者", "先驅者", "维京", "維京", "朱诺", "朱諾", "隼鸟", "隼鳥",
        "阿提米丝", "阿提米絲", "水星计划", "水星計畫",
        "nasa", "space", "rocket", "satellite", "orbit", "lunar", "apollo",
        "hubble", "voyager", "pluto", "kuiper", "skylab", "astronaut", "spacecraft",
        "space shuttle", "challenger", "columbia", "sts-", "mars", "mercury program",
        "juno", "hayabusa", "new horizons", "perseverance", "artemis",
    ],
    "disaster": [
        "灾难", "災難", "事故", "火灾", "火災", "大火", "地震", "海啸", "海嘯", "飓风", "颶風",
        "台风", "颱風", "龙卷风", "龍捲風", "洪水", "爆炸", "坠毁", "墜毀", "坠机", "墜機",
        "沉没", "沉沒", "遇难", "遇難", "伤亡", "傷亡", "空难", "空難", "风暴", "風暴", "火山",
        "切尔诺贝利", "車諾比", "泰坦尼克", "铁达尼", "興登堡", "兴登堡", "协和号", "協和號",
        "埃博拉", "疫情", "瘟疫", "矿难", "礦難", "坍塌", "泄漏", "洩漏", "污染",
        "disaster", "accident", "fire", "earthquake", "tsunami", "hurricane", "typhoon",
        "flood", "crash", "explosion", "wreck", "sinking", "tornado", "volcano", "pandemic",
    ],
    "war": [
        "战争", "戰爭", "战役", "戰役", "内战", "內戰", "空战", "空戰", "海战", "海戰",
        "空袭", "空襲", "轰炸", "轟炸", "轰炸机", "轟炸機", "战斗机", "戰鬥機", "航空母舰", "航空母艦",
        "军事", "軍事", "国防", "國防", "革命", "政变", "政變", "入侵", "占领", "佔領",
        "围攻", "圍攻", "抵抗", "军队", "軍隊", "海军", "海軍", "空军", "空軍", "陆军", "陸軍",
        "战区", "戰區", "前线", "前線", "停战", "停戰", "投降", "纳粹", "納粹", "法西斯",
        "冷战", "冷戰", "恐怖袭击", "恐怖襲擊", "武装", "武裝", "民兵", "游击", "游擊",
        "war", "battle", "invasion", "revolution", "coup", "nazi", "fascist", "cold war",
    ],
    "politics": [
        "总统", "總統", "首相", "总理", "總理", "国王", "國王", "女王", "皇帝", "国会", "國會",
        "议会", "議會", "政府", "选举", "選舉", "政党", "政黨", "联合国", "聯合國", "欧盟", "歐盟",
        "宪法", "憲法", "独立", "獨立", "外交", "条约", "條約", "法院", "最高法院", "政治",
        "policy", "president", "prime minister", "parliament", "congress", "election",
        "constitution", "treaty", "united nations",
    ],
    "science": [
        "科学", "科學", "物理", "化学", "化學", "生物", "医学", "醫學", "数学", "數學",
        "计算机", "計算機", "互联网", "互聯網", "万维网", "萬維網", "人工智能", "电报", "電報",
        "电话", "電話", "无线电", "無線電", "发明", "發明", "实验", "實驗", "诺贝尔", "諾貝爾",
        "研究", "理工", "工学院", "工程師", "工程师", "计算机科学", "航空", "飞机", "飛機",
        "客机", "客機", "民航", "飞行", "飛行", "航空公司", "波音", "太空船",
        "computer", "science", "physics", "chemistry", "biology", "medicine", "internet",
        "world wide web", "telephone", "radio", "invention", "laboratory", "aviation",
        "aircraft", "airplane", "airline",
    ],
    "art": [
        "摄影", "攝影", "摄影师", "攝影師", "画家", "畫家", "绘画", "繪畫", "油画", "油畫",
        "版画", "版畫", "雕塑", "电影", "電影", "影片", "导演", "導演", "音乐", "音樂",
        "歌剧", "歌劇", "剧院", "劇院", "博物馆", "博物館", "美术馆", "美術館", "展览", "展覽",
        "动画", "動畫", "时尚", "時尚", "设计", "設計", "艺术", "藝術", "艺术家", "藝術家",
        "乐队", "樂隊", "唱片", "文学", "文學", "作家", "小说", "小說", "奥斯卡", "奧斯卡",
        "art", "artist", "painting", "photograph", "photography", "film",
        "movie", "music", "opera", "theatre", "museum", "gallery", "exhibition", "sculpture",
        "animation", "fashion", "design", "pop art", "broadway", "jazz", "rock",
    ],
    "rail": [
        "铁路", "鐵路", "火车", "火車", "列车", "列車", "机车", "機車", "蒸汽", "轨道", "軌道",
        "工业", "工業", "工厂", "工廠", "制造", "製造", "机器", "機器", "钢铁", "鋼鐵", "矿", "礦",
        "railway", "rail", "train", "locomotive", "steam", "industrial",
        "factory", "manufacturing", "machine", "steel",
    ],
    "city": [
        "桥", "橋", "大桥", "大橋", "铁塔", "鐵塔", "隧道", "运河", "運河", "水坝", "水壩",
        "大坝", "大壩", "建筑", "建築", "大厦", "大廈", "摩天", "城市", "地铁", "地鐵", "机场", "機場",
        "港口", "工程", "建设", "建設", "施工", "世博会", "博覽會", "博览会", "天际线", "天際線",
        "bridge", "tower", "tunnel", "canal", "dam", "building", "skyscraper", "city",
        "subway", "airport", "harbor", "construction", "exposition", "world's fair", "architecture",
    ],
}

CLASSIFY_ORDER = ("space", "disaster", "war", "politics", "art", "rail", "city", "science")


def text_match(text, word):
    if re.fullmatch(r"[a-z0-9' -]+", word):
        return re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) is not None
    return word in text


def load_bundle():
    t = BUNDLE.read_text(encoding="utf-8")
    i = t.find("{")
    data, _ = json.JSONDecoder().raw_decode(t[i:])
    return data


def classify(title, subtitle, themes):
    # Title plus a short slice of the standfirst; full encyclopedia summaries
    # create too many accidental keyword hits.
    text = (title + " " + str(subtitle or "")[:220] + " " + " ".join(themes or [])).lower()
    if "太空" in (themes or []):
        return "space"
    if "灾变" in (themes or []):
        return "disaster"
    # Flight numbers without a Chinese "空难" word still belong to accidents.
    if re.search(r"(?:flight|航空)\s*\d+", title, re.I) or "班机" in title or "班機" in title or "航班" in title:
        return "disaster"
    for key in CLASSIFY_ORDER:
        if any(text_match(text, w) for w in RULES[key]):
            return key
    return "world"


def build_data():
    data = load_bundle()
    records = {r["id"]: r for r in data["records"]}
    series_by_key = {s["key"]: s for s in SERIES}
    stories = []
    for s in data["stories"]:
        sid = s["id"]
        date = s.get("date") or ""
        mmdd = date[5:10] if date else ""
        year = int(date[:4]) if date else None
        decade = ("pre1900" if year < 1900 else f"{(year // 10) * 10}s") if year else ""
        series_key = OVERRIDES.get(sid) or classify(s.get("title", ""), s.get("subtitle", ""), s.get("themes") or [])
        cover = records.get(s.get("cover"))
        image = (cover or {}).get("image") or ""
        series = series_by_key[series_key]
        stories.append({
            "id": sid,
            "title": s.get("title") or sid,
            "subtitle": s.get("subtitle") or "",
            "summary": s.get("intro") or s.get("subtitle") or "",
            "date": mmdd,
            "year": year,
            "decade": decade,
            "theme": series["name"],
            "series_key": series_key,
            "place": s.get("place") or "档案",
            "themes": s.get("themes") or [],
            "img": image,
            "cover": s.get("cover") or "",
            "href": f"../story/{sid}.html",
            "day_href": f"../today/{mmdd}.html" if mmdd else "",
            "type": s.get("type") or "",
            "today_rank": s.get("today_rank") or 0,
        })
    stories.sort(key=lambda x: (x["date"] or "99-99", x["year"] or 0, x["id"]))
    return {
        "series": SERIES,
        "stories": stories,
        "decades": ["pre1900", "1820s", "1840s", "1850s", "1860s", "1870s", "1880s", "1890s",
                     "1900s", "1910s", "1920s", "1930s", "1940s", "1950s", "1960s", "1970s",
                     "1980s", "1990s", "2000s", "2010s", "2020s"],
        "date_count": len({s["date"] for s in stories if s["date"]}),
    }


def main():
    out = build_data()
    out_path = ROOT / "next" / "dist" / "data" / "atlas.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    stories = out["stories"]
    print("stories", len(stories), "dated", sum(1 for s in stories if s["date"]))
    print("series counts", Counter(s["theme"] for s in stories).most_common())
    for name in [s["name"] for s in out["series"]]:
        years = [s for s in stories if s["theme"] == name]
        print(name, len(years), sorted({s["decade"] for s in years if s["decade"]}))
        print("  ", " / ".join(s["title"] for s in years[:8]))


if __name__ == "__main__":
    main()
