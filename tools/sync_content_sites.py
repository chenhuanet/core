# -*- coding: utf-8 -*-
"""Mirror the v3.2 release for main/paint/photo into their site repos.

Removes obsolete pages (including old record detail pages) while preserving git
metadata, workflows and README files.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "workspace" / "release"
SITES = ("main", "paint", "photo")
KEEP = {".git", ".github", "README.md", ".gitignore", "_redirects"}

for site in SITES:
    src = RELEASE / site
    dst = ROOT / "repos" / site
    for item in list(dst.iterdir()):
        if item.name in KEEP:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    print(site, "files", sum(1 for _ in dst.rglob("*") if _.is_file()))
