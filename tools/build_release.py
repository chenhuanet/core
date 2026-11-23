# -*- coding: utf-8 -*-
"""Reproducible release build for chenhua.net.

Pipeline:
  1. clean next/dist
  2. run the content/static/section builders in dependency order
  3. rewrite next/dist into a repo-shaped release tree under next/release
  4. audit the release tree

The release tree is what should be synced to repos-git. It is deliberately
separate from next/dist so preview URLs never leak into production.
"""
import argparse
import html
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urljoin

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "next" / "tools"
DIST = ROOT / "next" / "dist"
RELEASE = ROOT / "next" / "release"
CORE = ROOT / "next" / "core"
BUILD_ID = "20261123c"

SITES = {
    "main": {"origin": "https://chenhua.net", "domain": "chenhua.net"},
    "photo": {"origin": "https://photo.chenhua.net", "domain": "photo.chenhua.net"},
    "paint": {"origin": "https://paint.chenhua.net", "domain": "paint.chenhua.net"},
}
HOST_TO_SITE = {v["domain"]: k for k, v in SITES.items()} | {"www.chenhua.net": "main"}
CENTURIES = ("pre19century", "19century", "20century", "21century")

STEPS = [
    ("build_images.py", "图片仓与缩略图"),
    ("build_preview.py", "预览构建"),
    ("build_static.py", "静态详情页"),
    ("build_today_pages.py", "历史今天"),
    ("build_paint_history.py", "绘画史"),
    ("build_atlas.py", "主题/时间线底稿"),
    ("build_sections.py", "专题页与日历"),
]


def run_steps():
    env = os.environ.copy()
    env["CHENHUA_REMOTE"] = "1"
    env["CHENHUA_PUBLISH"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    started = time.time()
    for name, label in STEPS:
        print("\n[build] %s (%s)" % (name, label))
        proc = subprocess.run([sys.executable, str(TOOLS / name)], cwd=str(ROOT), env=env,
                              text=True, encoding="utf-8", errors="replace")
        if proc.returncode:
            raise SystemExit("build step failed: %s (exit %d)" % (name, proc.returncode))
    print("[build] all steps finished in %.1fs" % (time.time() - started))


def canonical_page_path(rel: str) -> str:
    rel = rel.replace("\\", "/").lstrip("/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[:-len("index.html")]
    return "/" + rel


def unique_urls(paths):
    seen = set()
    out = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def map_production_path(path: str, page_site: str):
    """Map a dist-internal absolute path to a production URL or root-relative asset."""
    if path.startswith("/next/dist/assets/"):
        return "/" + path[len("/next/dist/"):]
    if path.startswith("/next/dist/data/"):
        return "/" + path[len("/next/dist/"):]
    if path.startswith("/next/images/"):
        rest = path[len("/next/images/"):]
        century = rest.split("/", 1)[0]
        if century in CENTURIES:
            return "https://%s.chenhua.net/%s" % (century, rest[len(century) + 1:])
        return None
    if path == "/next/dist" or path == "/next/dist/":
        return SITES[page_site]["origin"] + "/"
    if path.startswith("/next/dist/"):
        rest = path[len("/next/dist/"):]
        for site in SITES:
            if rest == site or rest.startswith(site + "/"):
                rel = "" if rest == site else rest[len(site) + 1:]
                if rel.endswith("/index.html"):
                    rel = rel[:-len("index.html")]
                return SITES[site]["origin"] + "/" + rel
        return None
    if path.startswith("/assets/") or path.startswith("/data/"):
        return path
    return None


def rewrite_value(raw: str, page_url: str, page_site: str):
    raw = html.unescape(raw.strip())
    if not raw:
        return raw
    low = raw.lower()
    if low.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return raw
    if raw.startswith("//"):
        return raw
    joined = urljoin(page_url, raw)
    parts = urlsplit(joined)
    path = parts.path
    mapped = map_production_path(path, page_site)
    if mapped is None:
        if parts.scheme in ("http", "https") and parts.netloc:
            # External absolute URLs are left alone, except legacy www host.
            if parts.netloc.lower() == "www.chenhua.net":
                mapped = "https://chenhua.net" + path
                parts = parts._replace(netloc="chenhua.net")
            else:
                return raw
        else:
            return raw
    if mapped.startswith("/"):
        out = mapped
    else:
        out = mapped
    # Preserve query and fragment from the original joined URL.
    if parts.query:
        out += "?" + parts.query
    if parts.fragment:
        out += "#" + parts.fragment
    return out


ATTR_RE = re.compile(r'(?P<pre>\b(?:href|src|poster|data-src)\s*=\s*")(?P<url>[^"]*)(?P<post>")', re.I)
SRCSET_RE = re.compile(r'(?P<pre>\bsrcset\s*=\s*")(?P<val>[^"]*)(?P<post>")', re.I)


def rewrite_html(text: str, rel: str, site: str):
    page_url = "%s/next/dist/%s/%s" % (SITES[site]["origin"], site, rel.replace("\\", "/"))
    def attr_sub(m):
        return m.group("pre") + rewrite_value(m.group("url"), page_url, site) + m.group("post")
    text = ATTR_RE.sub(attr_sub, text)
    def srcset_sub(m):
        items = []
        for item in m.group("val").split(","):
            bits = item.strip().split(None, 1)
            if not bits:
                continue
            url = rewrite_value(bits[0], page_url, site)
            items.append(url + ((" " + bits[1]) if len(bits) > 1 else ""))
        return m.group("pre") + ", ".join(items) + m.group("post")
    text = SRCSET_RE.sub(srcset_sub, text)
    # Inline JS / JSON that still contains dist paths.
    for prefix in ("../../next/dist/", "../next/dist/", "./next/dist/"):
        text = text.replace(prefix, "/next/dist/")
    for site_name, meta in SITES.items():
        text = text.replace("/next/dist/%s/" % site_name, meta["origin"] + "/")
    text = text.replace("/next/dist/assets/", "/assets/")
    text = text.replace("/next/dist/data/", "/data/")
    text = text.replace("/next/dist/", SITES[site]["origin"] + "/")
    for century in CENTURIES:
        text = text.replace("/next/images/%s/" % century, "https://%s.chenhua.net/" % century)
        text = text.replace("../images/%s/" % century, "https://%s.chenhua.net/" % century)
        text = text.replace("../../images/%s/" % century, "https://%s.chenhua.net/" % century)
        text = text.replace("../../../images/%s/" % century, "https://%s.chenhua.net/" % century)
    # Relative asset/data prefixes left in inline config or CSS.
    text = re.sub(r"(?:\.\./)+assets/", "/assets/", text)
    text = re.sub(r"(?:\.\./)+data/", "/data/", text)
    text = text.replace("www.chenhua.net", "chenhua.net")
    return text


def copy_site(site: str):
    src = DIST / site
    dst = RELEASE / site
    if not src.exists():
        raise SystemExit("missing dist site: %s" % src)
    dst.mkdir(parents=True, exist_ok=True)
    html_count = 0
    for p in src.rglob("*"):
        if p.is_dir():
            continue
        out = dst / p.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".html":
            text = p.read_text(encoding="utf-8", errors="ignore")
            text = rewrite_html(text, str(p.relative_to(src)), site)
            out.write_text(text, encoding="utf-8", newline="\n")
            html_count += 1
        else:
            shutil.copy2(p, out)
    # Assets and data are repeated in each repo root.
    assets = RELEASE / site / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for p in (DIST / "assets").rglob("*"):
        if p.is_file():
            target = assets / p.relative_to(DIST / "assets")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    for name in ("gallery.css", "gallery.js"):
        s = CORE / "gallery" / name
        if s.exists():
            shutil.copy2(s, assets / name)
    data = RELEASE / site / "data"
    data.mkdir(parents=True, exist_ok=True)
    for p in (DIST / "data").glob("*"):
        if p.is_file() and p.name not in ("bundle.js", "bundle.meta.json"):
            shutil.copy2(p, data / p.name)
    (RELEASE / site / ".nojekyll").write_text("", encoding="utf-8")
    return html_count


def audit_release():
    sys.path.insert(0, str(TOOLS))
    import audit_release as ar
    return ar.audit(RELEASE)


def write_manifest(counts):
    files = []
    for p in sorted(RELEASE.rglob("*")):
        if p.is_file():
            files.append({"path": str(p.relative_to(RELEASE)).replace("\\", "/"),
                          "bytes": p.stat().st_size})
    manifest = {
        "build_id": BUILD_ID,
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "html": counts,
        "files": len(files),
        "entries": files,
    }
    (RELEASE / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true", help="reuse current next/dist")
    ap.add_argument("--skip-audit", action="store_true")
    args = ap.parse_args()

    if not args.skip_build:
        if DIST.exists():
            shutil.rmtree(DIST)
        run_steps()
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True, exist_ok=True)
    counts = {}
    for site in SITES:
        counts[site] = copy_site(site)
    from patch_semantics import patch_tree
    patch_tree(RELEASE)
    write_manifest(counts)
    print("\n[release] html:", json.dumps(counts), "files:", sum(1 for p in RELEASE.rglob('*') if p.is_file()))
    if args.skip_audit:
        return
    result = audit_release()
    print("[audit]", json.dumps(result, ensure_ascii=False))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
