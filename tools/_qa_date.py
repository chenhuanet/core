import sys
sys.path.insert(0, r"C:\Users\chenhua\Desktop\chenhua\next\tools")
import build_preview as bp
for s in ["约 1843","约 1870–1880 年代","19–20 世纪","约 1870s","约 1872–1887","清宫旧藏","1969-07-20"]:
    print(repr(s), "->", bp.english_date(s))
for s in ["Public Domain (美国政府作品)","No known copyright restrictions（来源声明，非许可）","CC BY 4.0"]:
    print(repr(s), "->", bp.license_en(s))
