# -*- coding: utf-8 -*-
"""v3.2 build manifest: 11 sites, 15 active repos, asset and UI hashes."""
import hashlib
import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402

ROOT = K.ROOT
RELEASE = ROOT / "workspace" / "release"
DATA = ROOT / "workspace" / "data"
REPOS = [
    "painting-history-and-craft", "photography-history-and-craft", "ai-image-generation-guide",
    "core", "main", "paint", "painting", "photo", "photography", "ai",
    "pre19century", "19century", "20century", "21century", "aiera",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_state(name):
    path = ROOT / "repos" / name
    if not (path / ".git").exists():
        return {"repo": name, "git": False, "head": None, "branch": None, "dirty": None}
    def git(*args):
        return subprocess.run(["git", "-C", str(path)] + list(args), capture_output=True, text=True).stdout.strip()
    return {
        "repo": name, "git": True,
        "head": git("rev-parse", "HEAD") or None,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD") or None,
        "dirty": bool(git("status", "--porcelain")),
    }


def main():
    sites = {}
    for site in K.SITE_META:
        base = RELEASE / site
        if not base.exists():
            sites[site] = {"exists": False}
            continue
        html = list(base.rglob("*.html"))
        en = [p for p in html if p.relative_to(base).as_posix().startswith("en/")]
        record_pages = [p for p in html if "/photo/" in p.as_posix() or "/painting/" in p.as_posix() or "/object/" in p.as_posix()]
        assets = {}
        for rel in ("assets/app.css", "assets/site.js", "assets/static.css", "assets/history.css"):
            p = base / rel
            if p.exists():
                assets[rel] = sha(p)
        sites[site] = {
            "exists": True,
            "domain": K.site_meta(site)["domain"],
            "html": len(html),
            "zh_html": len(html) - len(en),
            "en_html": len(en),
            "record_pages": len(record_pages) if site in ("pre19century", "19century", "20century", "21century", "aiera") else 0,
            "files": sum(1 for _ in base.rglob("*") if _.is_file()),
            "assets": assets,
        }
    manifest = {
        "version": "v3.2",
        "build_id": K.BUILD_ID,
        "ui_manifest_hash": sha(K.CORE / "ui-manifest.json"),
        "sites": sites,
        "total_html": sum(s.get("html", 0) for s in sites.values()),
        "repos": [repo_state(n) for n in REPOS],
    }
    manifest["active_repos"] = len(manifest["repos"])
    manifest["git_repos"] = sum(1 for r in manifest["repos"] if r["git"])
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "build-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"build_id": manifest["build_id"], "total_html": manifest["total_html"],
                      "git_repos": manifest["git_repos"], "active_repos": manifest["active_repos"]}, ensure_ascii=False))
    print(json.dumps({k: v.get("html") for k, v in sites.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
