import sys, re, collections
sys.path.insert(0, r"C:\Users\chenhua\Desktop\chenhua\next\tools")
import build_preview as bp
rows=bp.load_records()
cjk=re.compile(r"[\u4e00-\u9fff]")
dates=collections.Counter()
lics=collections.Counter()
for r in rows:
    d=str(r.get("date_label") or r.get("year") or "")
    if cjk.search(d): dates[d]+=1
    l=str(r.get("license") or "")
    if cjk.search(l): lics[l]+=1
print("CJK dates",len(dates),dates.most_common(15))
print("CJK licenses",len(lics),lics)
print("claims",len({str((r.get('evidence') or {}).get('claim') or '') for r in rows}))
for r in rows[:5]+[x for x in rows if x.get("id") in ("1969-plaque","lnk-dpm")]:
    print("---",r["id"],r.get("title"))
    print(r.get("evidence"))
