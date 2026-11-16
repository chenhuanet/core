import sys, collections
sys.path.insert(0, r"C:\Users\chenhua\Desktop\chenhua\next\tools")
import build_preview as bp
rows=bp.load_records()
c=collections.Counter(str((r.get("evidence") or {}).get("status") or "") for r in rows)
print(c)
b=collections.Counter(str((r.get("evidence") or {}).get("basis") or "") for r in rows)
print("bases",len(b))
for k,v in b.most_common(15): print(v,k)
