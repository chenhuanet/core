# -*- coding: utf-8 -*-
"""Read-only live audit for chenhua.net, photo, paint and four century image sites.

Reads live sitemaps, fetches every page, and checks:
  - HTTP status 200
  - exactly one <h1>
  - site.js (content sites) or gallery.js (image sites) version is BUILD_ID
  - canonical presence and, for known intentional mismatches, the expected URL
  - optional: first few image URLs per page return 200

The script only reads the network. It never writes to the site repos.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

BUILD_ID = "20261123c"
SITEMAPS = {
    "main": "https://chenhua.net/sitemap.xml",
    "photo": "https://photo.chenhua.net/sitemap.xml",
    "paint": "https://paint.chenhua.net/sitemap.xml",
    "pre19century": "https://pre19century.chenhua.net/sitemap.xml",
    "19century": "https://19century.chenhua.net/sitemap.xml",
    "20century": "https://20century.chenhua.net/sitemap.xml",
    "21century": "https://21century.chenhua.net/sitemap.xml",
}
SITE_ORIGINS = {
    "main": "https://chenhua.net",
    "photo": "https://photo.chenhua.net",
    "paint": "https://paint.chenhua.net",
    "pre19century": "https://pre19century.chenhua.net",
    "19century": "https://19century.chenhua.net",
    "20century": "https://20century.chenhua.net",
    "21century": "https://21century.chenhua.net",
}
UA = "chenhua-live-audit/1.0 (+https://chenhua.net/)"
CANONICAL_EXCEPTIONS = {
    "https://chenhua.net/stories/": "https://chenhua.net/themes/",
    "https://chenhua.net/stories/index.html": "https://chenhua.net/themes/",
    "https://photo.chenhua.net/search/": "https://chenhua.net/search/?scope=photos",
    "https://photo.chenhua.net/search/index.html": "https://chenhua.net/search/?scope=photos",
    "https://photo.chenhua.net/themes/": "https://chenhua.net/themes/",
    "https://photo.chenhua.net/timeline/": "https://chenhua.net/timeline/",
    "https://paint.chenhua.net/search/": "https://chenhua.net/search/?scope=paintings",
    "https://paint.chenhua.net/search/index.html": "https://chenhua.net/search/?scope=paintings",
}
IMAGE_RE = re.compile(r"https?://[^\s\"'<>]+?\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s\"'<>]*)?", re.I)
H1_RE = re.compile(r"<h1\b", re.I)
CANON_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', re.I)
JS_RE = re.compile(r'(?:site|gallery)\.js\?v=([0-9A-Za-z._-]+)')
H1_OPTIONAL_RE = re.compile(r'(?:/search/|/timeline/|/themes/|/stories/|/404\.html|/today/calendar\.html)$')
REDIRECT_RE = re.compile(r'<meta[^>]+http-equiv=["\']refresh["\']', re.I)
SITE_IMAGE_SUFFIX = ".chenhua.net"


def get(url, method="GET", timeout=25, retries=2):
    last = None
    for attempt in range(retries + 1):
        req = Request(url, headers={"User-Agent": UA}, method=method)
        try:
            with urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "ignore")
        except Exception as exc:
            last = exc
            if attempt < retries:
                time.sleep(1.0 + attempt)
    raise last


def load_sitemap(url):
    status, text = get(url)
    if status != 200:
        raise RuntimeError("sitemap %s -> %s" % (url, status))
    root = ET.fromstring(text)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [node.text.strip() for node in root.findall(".//s:url/s:loc", ns) if node.text]


def release_urls(root, image_root=None):
    """Enumerate every HTML file in a release tree, not only sitemap entries.

    Sitemap intentionally omits duplicate detail pages and a few redirect pages,
    while the release audit covers all of them. Image repositories live
    separately; pass image_root to include them.
    """
    urls = {}
    for site, origin in SITE_ORIGINS.items():
        site_root = (Path(image_root) / site) if image_root and site.endswith("century") else (root / site)
        if not site_root.exists():
            continue
        items = []
        for p in sorted(site_root.rglob("*.html")):
            rel = p.relative_to(site_root).as_posix()
            if rel == "index.html":
                url = origin + "/"
            elif rel.endswith("/index.html"):
                url = origin + "/" + rel[:-len("index.html")]
            else:
                url = origin + "/" + rel
            items.append(url)
        urls[site] = items
    return urls


def expected_from_release(root, image_root=None):
    """Use the local release HTML as the canonical expectation per URL."""
    expected = {}
    for site, origin in SITE_ORIGINS.items():
        site_root = (Path(image_root) / site) if image_root and site.endswith("century") else (root / site)
        if not site_root.exists():
            continue
        for p in sorted(site_root.rglob("*.html")):
            rel = p.relative_to(site_root).as_posix()
            if rel == "index.html":
                url = origin + "/"
            elif rel.endswith("/index.html"):
                url = origin + "/" + rel[:-len("index.html")]
            else:
                url = origin + "/" + rel
            try:
                html = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            expected[url] = {
                "canonical": canonical_for(url, html),
                "redirect": bool(REDIRECT_RE.search(html)),
            }
    return expected


def canonical_for(url, html):
    m = CANON_RE.search(html)
    if not m:
        return None
    return urljoin(url, m.group(1)).strip()


def audit_page(url, check_images=False, expected=None):
    result = {"url": url, "status": None, "h1": 0, "js": None, "canonical": None,
              "canonical_ok": True, "redirect": False, "images": [], "error": None}
    try:
        status, html = get(url)
        result["status"] = status
        if status != 200:
            result["error"] = "status %s" % status
            return result
        result["h1"] = len(H1_RE.findall(html))
        m = JS_RE.search(html)
        result["js"] = m.group(1) if m else None
        exp = (expected or {}).get(url) or {}
        result["redirect"] = bool(exp.get("redirect") or REDIRECT_RE.search(html))
        can = canonical_for(url, html)
        result["canonical"] = can
        if url.rstrip("/").endswith("/404.html") and can is None:
            result["canonical_ok"] = True
        elif exp.get("canonical"):
            result["canonical_ok"] = (can or "").rstrip("/") == exp["canonical"].rstrip("/")
        elif can is None:
            result["canonical_ok"] = False
        else:
            expected_canon = CANONICAL_EXCEPTIONS.get(url)
            if expected_canon is not None:
                result["canonical_ok"] = (can == expected_canon)
            else:
                result["canonical_ok"] = (can.rstrip("/") == url.rstrip("/"))
        if check_images:
            imgs = []
            for raw in IMAGE_RE.findall(html):
                full = urljoin(url, raw)
                host = (urlsplit(full).hostname or "").lower()
                if not (host == SITE_IMAGE_SUFFIX.lstrip(".") or host.endswith(SITE_IMAGE_SUFFIX)):
                    continue
                if full not in imgs:
                    imgs.append(full)
                if len(imgs) >= 3:
                    break
            result["images"] = imgs
    except Exception as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    return result


def check_image(url):
    try:
        status, _ = get(url, method="HEAD", timeout=20)
        return {"url": url, "status": status, "error": None}
    except Exception as exc:
        return {"url": url, "status": None, "error": "%s: %s" % (type(exc).__name__, exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".tmp/live-audit.json")
    ap.add_argument("--limit", type=int, default=0, help="only audit first N URLs per site")
    ap.add_argument("--images", action="store_true", help="also check up to 3 unique chenhua.net-hosted images per page")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--release-root", default="next/release",
                    help="local release tree used by --full to enumerate all pages")
    ap.add_argument("--image-root", default="repos",
                    help="four image repositories used by --full; pass an empty string to skip")
    ap.add_argument("--full", action="store_true",
                    help="audit every release HTML, not only sitemap URLs")
    ap.add_argument("--skip-sites", default="",
                    help="comma-separated sites to skip (useful when a custom domain is still pending)")
    args = ap.parse_args()
    skip = {s.strip() for s in args.skip_sites.split(",") if s.strip()}

    started = time.time()
    expected = {}
    if args.full:
        rel_root = Path(args.release_root)
        if not rel_root.exists():
            print("[fatal] release root not found: %s" % rel_root, file=sys.stderr)
            raise SystemExit(2)
        urls = release_urls(rel_root, args.image_root or None)
        expected = expected_from_release(rel_root, args.image_root or None)
        urls = {k: v for k, v in urls.items() if k not in skip}
        expected = {k: v for k, v in expected.items() if k not in skip}
        for site, xs in urls.items():
            print("[release] %s %s" % (site, len(xs)))
    else:
        urls = {}
        for site, sm in SITEMAPS.items():
            if site in skip:
                continue
            try:
                urls[site] = load_sitemap(sm)
            except Exception as exc:
                print("[fatal] %s: %s" % (site, exc), file=sys.stderr)
                raise SystemExit(2)
            if args.limit:
                urls[site] = urls[site][:args.limit]
            print("[sitemap] %s %s" % (site, len(urls[site])))

    all_urls = [(site, u) for site, xs in urls.items() for u in xs]
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(audit_page, u, args.images, expected): (site, u) for site, u in all_urls}
        for i, fut in enumerate(as_completed(futures), 1):
            site, u = futures[fut]
            try:
                r = fut.result()
            except Exception as exc:
                r = {"url": u, "status": None, "h1": 0, "js": None, "canonical": None,
                     "canonical_ok": True, "images": [], "error": str(exc)}
            r["site"] = site
            results.append(r)
            if i % 500 == 0:
                print("[pages] %d/%d" % (i, len(all_urls)))

    bad_status = [r for r in results if r["status"] != 200]
    bad_h1 = [r for r in results if r["status"] == 200 and r["h1"] != 1
              and not H1_OPTIONAL_RE.search(urlparse(r["url"]).path)]
    bad_js = [r for r in results if r["status"] == 200 and not r.get("redirect") and r["js"] != BUILD_ID
              and not H1_OPTIONAL_RE.search(urlparse(r["url"]).path)]
    bad_canon = [r for r in results if r["status"] == 200 and not r["canonical_ok"]]

    image_urls = sorted({img for r in results for img in r.get("images", [])})
    image_results = []
    if args.images and image_urls:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(check_image, u) for u in image_urls]
            for i, fut in enumerate(as_completed(futures), 1):
                image_results.append(fut.result())
                if i % 500 == 0:
                    print("[images] %d/%d" % (i, len(image_urls)))
    bad_images = [r for r in image_results if r["status"] != 200]

    counts = Counter(r["site"] for r in results)
    out = {
        "ok": not bad_status and not bad_h1 and not bad_js and not bad_canon and not bad_images,
        "build_id": BUILD_ID,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_seconds": round(time.time() - started, 1),
        "pages": len(results),
        "by_site": dict(counts),
        "status_bad": len(bad_status),
        "h1_bad": len(bad_h1),
        "js_bad": len(bad_js),
        "canonical_bad": len(bad_canon),
        "images_checked": len(image_results),
        "images_bad": len(bad_images),
        "samples": {
            "status_bad": bad_status[:10],
            "h1_bad": bad_h1[:10],
            "js_bad": bad_js[:10],
            "canonical_bad": bad_canon[:10],
            "images_bad": bad_images[:10],
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "samples"}, ensure_ascii=False, indent=2))
    if not out["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
