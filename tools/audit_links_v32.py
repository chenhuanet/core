# -*- coding: utf-8 -*-
"""v3.2 local link and image audit for the release tree."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402

ROOT = K.ROOT
RELEASE = ROOT / "workspace" / "release"
IMAGES = ROOT / "workspace" / "images"
SITE_BY_DOMAIN = {v["domain"]: k for k, v in K.SITE_META.items()}

A_RE = re.compile(r'<a\s[^>]*href="([^"]+)"', re.I)
IMG_RE = re.compile(r'<img\s[^>]*src="([^"]+)"', re.I)


def resolve_local(site, path):
    site_dir = RELEASE / site
    clean = unquote(urlsplit(path).path)
    if not clean.startswith("/"):
        return None
    rel = clean.lstrip("/")
    target = site_dir / rel
    if target.is_dir():
        target = target / "index.html"
    return target


def main():
    report = {"broken_links": [], "broken_images": [], "asset_hash_mismatch": [], "pages": 0, "links": 0, "images": 0}
    hashes = {}
    for site in K.SITE_META:
        base = RELEASE / site
        if not base.exists():
            continue
        for rel in ("assets/app.css", "assets/site.js", "assets/static.css", "assets/history.css"):
            p = base / rel
            if p.exists():
                h = __import__("hashlib").sha256(p.read_bytes()).hexdigest()
                hashes.setdefault(rel, set()).add(h)
        for p in base.rglob("*.html"):
            report["pages"] += 1
            html = p.read_text(encoding="utf-8")
            for href in A_RE.findall(html):
                report["links"] += 1
                if href.startswith(("http://", "https://", "mailto:", "#", "javascript:", "tel:")):
                    continue
                target = resolve_local(site, href)
                if target is not None and not target.exists():
                    report["broken_links"].append({"site": site, "file": p.relative_to(base).as_posix(), "href": href})
            for src in IMG_RE.findall(html):
                if src.startswith("data:"):
                    continue
                report["images"] += 1
                if src.startswith("//"):
                    src = "https:" + src
                if src.startswith(("http://", "https://")):
                    parts = urlsplit(src)
                    if parts.netloc not in SITE_BY_DOMAIN:
                        continue
                    local = IMAGES / SITE_BY_DOMAIN[parts.netloc] / unquote(parts.path).lstrip("/")
                    if not local.exists():
                        report["broken_images"].append({"site": site, "file": p.relative_to(base).as_posix(), "src": src})
                else:
                    target = resolve_local(site, src)
                    if target is not None and not target.exists():
                        report["broken_images"].append({"site": site, "file": p.relative_to(base).as_posix(), "src": src})
    for rel, values in hashes.items():
        if len(values) > 1:
            report["asset_hash_mismatch"].append({"asset": rel, "hashes": sorted(values)})
    report["ok"] = not report["broken_links"] and not report["broken_images"] and not report["asset_hash_mismatch"]
    out = ROOT / "workspace" / "data" / "v32-links.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}, ensure_ascii=False, indent=1))
    for key in ("broken_links", "broken_images", "asset_hash_mismatch"):
        if report[key]:
            print("SAMPLE", key, json.dumps(report[key][:5], ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
