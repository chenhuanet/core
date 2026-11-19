# -*- coding: utf-8 -*-
from pathlib import Path
R=Path(r"C:\Users\chenhua\Desktop\chenhua\repos")
for p in [R/"main/index.html",R/"main/themes/index.html",R/"main/timeline/index.html",R/"main/today/01-01.html",R/"photo/themes/index.html",R/"photo/timeline/index.html",R/"photo/today/01-01.html",R/"paint/themes/index.html",R/"paint/history/calendar.html"]:
    s=p.read_text(encoding="utf-8")
    print("\n==",p.relative_to(R),"bytes",len(s))
    print("home-index",s.count("homeIndexBlock"),"combined",s.count("<!-- combined-sections -->"),"paint",s.count("paint-part"),"lead",s.count("photo-lead"),"hero",s.count("day-hero has-cover"),"paintblock",s.count("paint-today"))
    for key in ("/next/images","https://19century.chenhua.net","https://paint.chenhua.net/history","/today/"):
        print(key,s.count(key),end="; ")
    print()
    print("title",__import__('re').findall(r"<title>(.*?)</title>",s,__import__('re').S)[:1])
