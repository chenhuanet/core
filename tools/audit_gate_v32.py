# -*- coding: utf-8 -*-
"""v3.2 gate: reads release audits and the build manifest, fails on any blocking condition."""
import json
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402

DATA = K.ROOT / "workspace" / "data"
FAIL = []


def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main():
    audit = load("v32-audit.json")
    links = load("v32-links.json")
    manifest = load("build-manifest.json")
    for name, obj in (("v32-audit.json", audit), ("v32-links.json", links), ("build-manifest.json", manifest)):
        if obj is None:
            FAIL.append("missing " + name)
    if audit:
        for key in ("bad_counts", "nav_mismatch", "bad_h1", "bad_canonical", "bad_hreflang",
                    "missing_pair", "bad_version", "lang_query", "record_in_content_site", "link_in_record_site"):
            if audit.get(key):
                FAIL.append("audit.%s=%d" % (key, len(audit[key])))
        if not audit.get("ok"):
            FAIL.append("audit.ok=false")
    if links:
        for key in ("broken_links", "broken_images", "asset_hash_mismatch"):
            if links.get(key):
                FAIL.append("links.%s=%d" % (key, len(links[key])))
        if not links.get("ok"):
            FAIL.append("links.ok=false")
    if manifest:
        if manifest.get("build_id") != K.BUILD_ID:
            FAIL.append("build_id mismatch")
        if manifest.get("ui_manifest_hash") != __import__("hashlib").sha256((K.CORE / "ui-manifest.json").read_bytes()).hexdigest():
            FAIL.append("ui_manifest_hash mismatch")
        if manifest.get("active_repos") != 15:
            FAIL.append("active_repos != 15")
        if manifest.get("git_repos") != 15:
            FAIL.append("git_repos != 15 (%d)" % manifest.get("git_repos", 0))
        for site, info in manifest.get("sites", {}).items():
            if not info.get("exists"):
                FAIL.append("site missing: " + site)
    print("GATE", "PASS" if not FAIL else "FAIL")
    for f in FAIL:
        print(" -", f)
    out = DATA / "v32-gate.json"
    out.write_text(json.dumps({"ok": not FAIL, "failures": FAIL}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
