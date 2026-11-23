# -*- coding: utf-8 -*-
"""Post-build semantic patch: add missing H1s and normalize decorative image alt.

The release tree is a repo-shaped snapshot; this patch is applied after every
build so a clean rebuild cannot lose the fixes.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "next" / "release"
HIDDEN = ("position:absolute;width:1px;height:1px;padding:0;margin:-1px;"
          "overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0")

H1_TITLES = {
    ("main", "themes/index.html"): ("主题", "Themes"),
    ("main", "timeline/index.html"): ("时间线", "Timeline"),
    ("main", "today/calendar.html"): ("日历", "Calendar"),
    ("photo", "themes/index.html"): ("摄影主题", "Photography themes"),
    ("photo", "timeline/index.html"): ("摄影时间线", "Photography timeline"),
    ("photo", "today/calendar.html"): ("摄影日历", "Photography calendar"),
}


def hidden_h1(zh, en):
    return ('<h1 style="%s"><span data-l="zh">%s</span><span data-l="en">%s</span></h1>'
            % (HIDDEN, html.escape(zh, quote=False), html.escape(en, quote=False)))


def insert_after_main_or_body(text, block):
    if re.search(r"<h1\b", text, re.I):
        return text
    m = re.search(r"<main\b[^>]*>", text, re.I)
    if not m:
        m = re.search(r"<body\b[^>]*>", text, re.I)
    if not m:
        return text
    return text[:m.end()] + block + text[m.end():]


def page_title(text):
    m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if not m:
        return "尘画", "Frame & Grain"
    raw = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    title = raw.split(" · ")[0].strip() or raw
    return title, title


def patch_file(site, path):
    rel = path.relative_to(RELEASE / site).as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    changed = False

    if rel == "404.html" and '<div class="big">404</div>' in text:
        text = text.replace('<div class="big">404</div>', '<h1 class="big">404</h1>', 1)
        changed = True

    if rel == "stories/index.html" and "http-equiv=\"refresh\"" in text:
        # A tiny redirect page still needs a top-level heading for parsers,
        # even though the visible copy is only the redirect notice.
        if not re.search(r"<h1\b", text, re.I):
            text = insert_after_main_or_body(text, hidden_h1("主题", "Themes"))
            changed = True
        path.write_text(text, encoding="utf-8", newline="\n")
        return changed

    if (site, rel) in H1_TITLES:
        zh, en = H1_TITLES[(site, rel)]
        if not re.search(r"<h1\b", text, re.I):
            text = insert_after_main_or_body(text, hidden_h1(zh, en))
            changed = True

    if not re.search(r"<h1\b", text, re.I):
        zh, en = page_title(text)
        text = insert_after_main_or_body(text, hidden_h1(zh, en))
        changed = True

    # A hero image inside .day-hero-cover is already aria-hidden by its
    # container. Make the image itself explicit too, so empty alt is not
    # mistaken for a missing description by downstream audits.
    text = re.sub(
        r'(<div class="day-hero-cover"[^>]*aria-hidden="true"[^>]*><img\b[^>]*?)(\s*alt="")',
        lambda m: m.group(1) + ' aria-hidden="true"' + m.group(2),
        text,
        flags=re.I,
    )

    if changed or text != path.read_text(encoding="utf-8", errors="ignore"):
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def patch_tree(root=RELEASE):
    count = 0
    for site in ("main", "photo", "paint"):
        for p in (Path(root) / site).rglob("*.html"):
            if patch_file(site, p):
                count += 1
    print("[semantics] patched %d pages" % count)
    return count


if __name__ == "__main__":
    patch_tree()
