# -*- coding: utf-8 -*-
import json
import re
from collections import Counter
from pathlib import Path

DATA = Path(r"C:\Users\chenhua\Desktop\chenhua\next\dist\data\atlas.json")
d = json.loads(DATA.read_text(encoding="utf-8"))

RULES = {
    "space": ["太空","航天","火箭","卫星","衛星","飞船","飛船","空间站","太空站","天空实验室","阿波罗","阿波羅","旅行者","哈勃","哈伯","望远镜","望遠鏡","天文","天文台","宇宙","星云","星雲","彗星","小行星","行星","月面","月球","登月","探月","探测器","探測器","探测车","火星","冥王星","柯伊伯","星尘","星塵","勇气号","勇氣號","机遇号","矮行星","事件视界","事件視界","先驱者","先驅者","维京","維京","朱诺","朱諾","隼鸟","隼鳥","阿提米丝","阿提米絲","水星计划","水星計畫","nasa","space","rocket","satellite","orbit","lunar","apollo","hubble","voyager","pluto","kuiper","skylab","astronaut","spacecraft","space shuttle","challenger","columbia","sts-","mars","mercury program","juno","hayabusa","new horizons","perseverance","artemis"],
    "disaster": ["灾难","災難","事故","火灾","火災","大火","地震","海啸","海嘯","飓风","颶風","台风","颱風","龙卷风","龍捲風","洪水","爆炸","坠毁","墜毀","坠机","墜機","沉没","沉沒","遇难","遇難","伤亡","傷亡","空难","空難","风暴","風暴","火山","切尔诺贝利","車諾比","泰坦尼克","铁达尼","興登堡","兴登堡","协和号","協和號","埃博拉","疫情","瘟疫","矿难","礦難","坍塌","泄漏","洩漏","污染","disaster","accident","fire","earthquake","tsunami","hurricane","typhoon","flood","crash","explosion","wreck","sinking","tornado","volcano","pandemic"],
    "war": ["战争","戰爭","战役","戰役","内战","內戰","空战","空戰","海战","海戰","空袭","空襲","轰炸","轟炸","军事","軍事","国防","國防","革命","政变","政變","入侵","占领","佔領","围攻","圍攻","抵抗","军队","軍隊","海军","海軍","空军","空軍","陆军","陸軍","战区","戰區","前线","前線","停战","停戰","投降","纳粹","納粹","法西斯","冷战","冷戰","恐怖袭击","恐怖襲擊","武装","武裝","民兵","游击","游擊","war","battle","invasion","revolution","coup","nazi","fascist","cold war"],
    "politics": ["总统","總統","首相","总理","總理","国王","國王","女王","皇帝","国会","國會","议会","議會","政府","选举","選舉","政党","政黨","联合国","聯合國","欧盟","歐盟","宪法","憲法","独立","獨立","外交","条约","條約","法院","最高法院","政治","总统制","共和","民主","policy","president","prime minister","parliament","congress","election","constitution","treaty","united nations"," European Union".strip()],
    "science": ["科学","科學","物理","化学","化學","生物","医学","醫學","数学","數學","计算机","計算機","互联网","互聯網","万维网","萬維網","人工智能","电报","電報","电话","電話","无线电","無線電","发明","發明","实验","實驗","诺贝尔","諾貝爾","研究","理工","工学院","工程師","工程师","IBM","计算机科学","computer","science","physics","chemistry","biology","medicine","internet","world wide web","telephone","radio","invention","laboratory"],
    "art": ["摄影","攝影","摄影师","攝影師","画家","畫家","绘画","繪畫","油画","油畫","版画","版畫","雕塑","电影","電影","影片","导演","導演","音乐","音樂","歌剧","歌劇","剧院","劇院","博物馆","博物館","美术馆","美術館","展览","展覽","动画","動畫","时尚","時尚","设计","設計","艺术","藝術","艺术家","藝術家","歌","乐队","樂隊","唱片","文学","文學","作家","小说","小說","建筑?","art","artist","painting","photograph","photography","film","movie","music","opera","theatre","museum","gallery","exhibition","sculpture","animation","fashion","design","pop art","broadway","jazz","rock"],
    "rail": ["铁路","鐵路","火车","火車","列车","列車","机车","機車","蒸汽","轨道","軌道","工业","工業","工厂","工廠","制造","製造","机器","機器","钢铁","鋼鐵","矿","礦","railway","rail","train","locomotive","steam","industrial","factory","manufacturing","machine","steel"],
    "city": ["桥","橋","大桥","大橋","塔","铁塔","鐵塔","隧道","运河","運河","水坝","水壩","大坝","大壩","建筑","建築","大厦","大廈","摩天","城市","地铁","地鐵","机场","機場","港口","工程","建设","建設","施工","世博会","博覽會","博览会","天际线","天際線","bridge","tower","tunnel","canal","dam","building","skyscraper","city","subway","airport","harbor","construction","exposition","world's fair","architecture"],
}

ORDER = ["space","disaster","war","politics","science","rail","city","art"]


def match(text, w):
    if re.fullmatch(r"[a-z0-9' -]+", w):
        return re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) is not None
    return w in text


def classify(title, subtitle, themes):
    text = (title + " " + (subtitle or "") + " " + " ".join(themes or [])).lower()
    if "太空" in (themes or []):
        return "space"
    if "灾变" in (themes or []):
        return "disaster"
    for key in ORDER:
        if any(match(text, w) for w in RULES[key]):
            return key
    return "world"


counts = Counter()
samples = {}
for s in d["stories"]:
    k = classify(s["title"], s.get("subtitle", ""), s.get("themes", []))
    counts[k] += 1
    samples.setdefault(k, []).append(s["title"])

print(counts.most_common())
for k, _ in counts.most_common():
    print("\n==", k, len(samples[k]))
    for t in samples[k][:14]:
        print(" ", t)
