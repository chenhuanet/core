# -*- coding: utf-8 -*-
"""Sync v3.2 record-site output into the four century repos.

Only HTML/assets/manifests metadata are touched; image files and workflows stay.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "workspace" / "release"
SITES = ("pre19century", "19century", "20century", "21century")
SKIP = {"photos", "paintings", "objects", "thumbs", "manifests", ".git", ".github", "README.md", ".gitignore", "_redirects"}

for site in SITES:
    src = RELEASE / site
    dst = ROOT / "repos" / site
    copied = 0
    for item in src.iterdir():
        if item.name in SKIP:
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
        copied += 1
    print(site, "synced", copied)
