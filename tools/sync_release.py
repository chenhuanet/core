# -*- coding: utf-8 -*-
"""Sync next/release into the four publishing repos, preserving repo metadata.

Usage:
  python next/tools/sync_release.py --dry-run
  python next/tools/sync_release.py --apply
"""
import argparse
import filecmp
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "next" / "release"
REPOS = ROOT / "repos-git"
SITES = ("main", "photo", "paint")
PROTECTED = {".git", ".github", ".gitignore", "CNAME", "README.md", "CONTENT-CLEANUP.md"}


def sync_site(site, apply=False):
    src = RELEASE / site
    dst = REPOS / site
    copied = 0
    skipped = 0
    changed = []
    for p in src.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(src)
        if rel.parts and rel.parts[0] in PROTECTED:
            skipped += 1
            continue
        target = dst / rel
        if target.exists() and filecmp.cmp(p, target, shallow=False):
            continue
        changed.append(str(rel).replace("\\", "/"))
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
        copied += 1
    return {"changed": copied, "skipped": skipped, "sample": changed[:12]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.apply and not args.dry_run:
        raise SystemExit("choose --apply or --dry-run")
    report = {}
    for site in SITES:
        report[site] = sync_site(site, apply=args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    (ROOT / ".tmp" / "sync_release_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
