import glob
import json
import pathlib
import re

SEL = {}
for f in glob.glob(r"C:\Users\chenhua\Desktop\chenhua\next\_today_selected_*.json"):
    SEL.update(json.loads(pathlib.Path(f).read_text(encoding="utf-8")))
META = json.loads(pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\_today_final_meta_all.json").read_text(encoding="utf-8"))

BAD = re.compile(r"China|Taiwan|Hong Kong|Tiananmen|Putin|Trump|Biden|Gaddafi|Hamas|Israel|Palestine|Gaza|Nazi|Holocaust|war|invasion|president|election|communist|terror|bomb|attack|assassination|massacre|genocide|riot|protest|military|army|siege|hostage|kidnap|shooting|gunman|militant|jihad|ISIS|al-Qaeda|Ukraine|Russia|Syria|Iraq|Afghanistan|Iran|refugee|migrant", re.I)
GOOD = re.compile(r"Flight|disaster|fire|ship|bridge|building|tower|museum|film|television|music|album|painting|photograph|camera|telescope|spacecraft|satellite|rover|expedition|stadium|theatre|library|university|company|railway|station|canal|dam|earthquake|volcano|cyclone|hurricane|tornado|flood|mining|factory|exhibition|fair|festival|opera|ballet|novel|newspaper|magazine|radio|airport|harbor|port|rail|metro|subway|tunnel|observatory|gallery|architecture|sculpture|portrait|record|speed|flight|train|hotel|park|zoo|market", re.I)

VDATES = sorted([pathlib.Path(f).name[6:11] for f in glob.glob(r"C:\Users\chenhua\Desktop\chenhua\next\content\stories\photos\today-*-visual-dossier.md")])
rows = []
for md in VDATES:
    primary = (META.get(md, {}).get("page") or {}).get("title") or ""
    picks = []
    for cand in SEL.get(md, []):
        t = (cand.get("title") or "")
        if not t or t == primary or BAD.search(t) or not GOOD.search(t) or t.count("_") < 2:
            continue
        picks.append(t)
        if len(picks) >= 3:
            break
    rows.append({"md": md, "primary": primary, "candidates": picks})

pathlib.Path(r"C:\Users\chenhua\Desktop\chenhua\next\_replacement_candidates.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("dates", len(rows), "with candidates", sum(1 for x in rows if x["candidates"]))
