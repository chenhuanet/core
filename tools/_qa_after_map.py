import sys, re
sys.path.insert(0, r"C:\Users\chenhua\Desktop\chenhua\next\tools")
import build_preview as bp
rows=bp.load_records()
cjk=re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")
bad=[(r["id"],r.get("title_en"),r.get("note_en"),r.get("creator"),r.get("credit_line_en")) for r in rows if cjk.search(" ".join(str(r.get(k) or "") for k in ("title_en","note_en","credit_line_en")))]
print("cjk",len(bad))
for x in bad[:10]: print(x)
