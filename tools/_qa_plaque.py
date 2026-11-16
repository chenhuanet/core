import pathlib, re
p=pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\dist\photo\photo\1969-plaque.html")
t=p.read_text(encoding="utf-8")
for key in ["creditText","Public Domain","Statement:","Basis:","Licence","figcaption"]:
    print("\n###",key)
    for m in re.finditer(re.escape(key),t):
        print(t[max(0,m.start()-100):m.start()+240].replace("\n"," "))
