import sys
sys.path.insert(0, r"C:\Users\chenhua\Desktop\chenhua\next\tools")
import build_preview as bp
stories=bp.load_story_files(bp.load_records())
for s in stories:
    print(s["id"], "|", s.get("rights_summary"))
