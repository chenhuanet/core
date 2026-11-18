# -*- coding: utf-8 -*-
"""Build the selected ginkgo leaf-spirit SVG assets.

The mark is deliberately transparent and has no cream halo: on a dark
background the warm gold leaf carries the shape; on a light background the
ink outline does. Eight expressions share one leaf body.
"""
from pathlib import Path

ROOT = Path(r"C:\Users\chenhua\Desktop\chenhua")
CORE_OUT = ROOT / "next" / "core" / "leaf"
DIST_OUT = ROOT / "next" / "dist" / "assets" / "leaf"
SAMPLES = ROOT / "站点标志" / "叶精灵"

INK = "#2b2118"
CREAM = "#fff8e8"
BLUSH = "#d98c74"

DEFS = """<defs>
<radialGradient id="gLeaf" cx=".34" cy=".25" r=".88">
  <stop offset="0" stop-color="#fae9b0"/><stop offset=".48" stop-color="#e4c06b"/><stop offset="1" stop-color="#bd8b3d"/>
</radialGradient>
<linearGradient id="gArm" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#edd087"/><stop offset="1" stop-color="#c89645"/>
</linearGradient>
<linearGradient id="gMoss" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#a9bd8a"/><stop offset="1" stop-color="#6f8a5f"/>
</linearGradient>
</defs>"""

BODY_PATH = ("M31.5 46.5C18 45.5 7.5 36 7 25.5 6.5 15.5 15 8.5 27 8.5"
             "L30 17.5 34 9.5C46 9.5 55.5 16 56 26 56.5 37 46 45 31.5 46.5Z")


def shadow():
    return '<ellipse cx="31.5" cy="57" rx="15" ry="2.4" fill="#2b2118" opacity=".15"/>'


def limb(d, hx, hy, flip):
    if flip:
        hand = (f'<path d="M{hx} {hy}c2-1 3 1 2 2-2 1-3-1-2-2Z" '
                f'fill="url(#gArm)" stroke="{INK}" stroke-width="1.4"/>')
    else:
        hand = (f'<path d="M{hx} {hy}c-2-1-3 1-2 2 2 1 3-1 2-2Z" '
                f'fill="url(#gArm)" stroke="{INK}" stroke-width="1.4"/>')
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="4.4" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="url(#gArm)" stroke-width="2.5" stroke-linecap="round"/>'
            f'{hand}')


def arms(pose):
    if pose == "up":
        return (limb("M13 33C10 28 8 24 7 20", 7, 20, False) +
                limb("M50 33C53 28 55 24 56 20", 56, 20, True))
    if pose == "hips":
        return (limb("M13 34C8 36 6 40 9 41C12 42 14 40 15 38", 15, 38, False) +
                limb("M50 34C55 36 57 40 54 41C51 42 49 40 48 38", 48, 38, True))
    if pose == "together":
        return (limb("M13 34C10 37 8 40 13 41C17 41 20 40 21 39", 21, 39, False) +
                limb("M50 34C53 37 55 40 50 41C46 41 43 40 42 39", 42, 39, True))
    if pose == "chin":
        return (limb("M13 33C10 34 8 36 12 37C15 38 18 36 19 34", 19, 34, False) +
                limb("M50 33C53 34 56 36 57 39", 57, 39, True))
    if pose == "cheek":
        return (limb("M13 33C10 32 8 31 15 30", 15, 30, False) +
                limb("M50 33C53 34 56 36 57 39", 57, 39, True))
    return (limb("M13 33C9 34 6 36 4 39", 4, 39, False) +
            limb("M50 33C54 34 57 36 59 39", 59, 39, True))


def foot(cx, flip):
    if flip:
        d = (f"M{cx + 3} 52c2 0 3 1 3 2-2 1-5 0-5-1 1-1 1-1 2-1Z")
    else:
        d = (f"M{cx - 3} 52c-2 0-3 1-3 2 2 1 5 0 5-1-1-1-1-1-2-1Z")
    return f'<path d="{d}" fill="url(#gArm)" stroke="{INK}" stroke-width="1.4"/>'


def eye(cx, cy, r=2.2, dx=0, dy=0):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}"/>'
            f'<circle cx="{cx - r * .34 + dx}" cy="{cy - r * .4 + dy}" r="{r * .37}" fill="{CREAM}"/>')


def blush(cx, cy):
    return (f'<ellipse cx="{cx - 11}" cy="{cy + 4}" rx="3.1" ry="1.8" fill="{BLUSH}" opacity=".36"/>'
            f'<ellipse cx="{cx + 11}" cy="{cy + 4}" rx="3.1" ry="1.8" fill="{BLUSH}" opacity=".36"/>')


def face(kind, cx=31.5, cy=31):
    b = blush(cx, cy)
    if kind == "calm":
        return (f'<path d="M{cx - 10} {cy - 5}q3-2 5 0M{cx + 5} {cy - 5}q3-2 5 0" fill="none" '
                f'stroke="{INK}" stroke-width="1.4" opacity=".65"/>{eye(cx - 6, cy)}{eye(cx + 6, cy)}'
                f'<path d="M{cx - 3} {cy + 5}q3 2.5 6 0" fill="none" stroke="{INK}" stroke-width="2" '
                f'stroke-linecap="round"/>{b}')
    if kind == "joy":
        return (f'<path d="M{cx - 9} {cy}q3-3 5 0M{cx + 4} {cy}q3-3 5 0" fill="none" '
                f'stroke="{INK}" stroke-width="2.1" stroke-linecap="round"/>'
                f'<path d="M{cx - 4} {cy + 4}q4 6 8 0" fill="{INK}"/>'
                f'<ellipse cx="{cx}" cy="{cy + 7.6}" rx="2.4" ry="1.4" fill="{BLUSH}"/>{b}'
                f'<path d="M{cx + 13} {cy - 9}l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1Z" '
                f'fill="{CREAM}" opacity=".8"/>')
    if kind == "curious":
        return (f'<path d="M{cx - 11} {cy - 6}q3-3 6-1M{cx + 5} {cy - 4}q2 0 4 1" fill="none" '
                f'stroke="{INK}" stroke-width="1.4" opacity=".65"/>{eye(cx - 6, cy, 2.7)}{eye(cx + 6, cy, 1.9)}'
                f'<circle cx="{cx}" cy="{cy + 5}" r="1.8" fill="{INK}"/>{b}')
    if kind == "think":
        return (f'<path d="M{cx - 10} {cy - 5}q3-2 5 0M{cx + 5} {cy - 5}q3-2 5 0" fill="none" '
                f'stroke="{INK}" stroke-width="1.4" opacity=".65"/>{eye(cx - 6, cy, 2.2, 1, -1)}'
                f'{eye(cx + 6, cy, 2.2, 1, -1)}<path d="M{cx - 3} {cy + 5}h6" fill="none" '
                f'stroke="{INK}" stroke-width="2" stroke-linecap="round"/>{b}')
    if kind == "sleepy":
        return (f'<path d="M{cx - 9} {cy}q2 2 4 0M{cx + 5} {cy}q2 2 4 0" fill="none" '
                f'stroke="{INK}" stroke-width="2" stroke-linecap="round"/>'
                f'<path d="M{cx - 3} {cy + 5}q3 2 6 0" fill="none" stroke="{INK}" stroke-width="1.8" '
                f'stroke-linecap="round"/>{b}'
                f'<path d="M{cx + 12} {cy - 9}h4l-4 4h4M{cx + 15} {cy - 14}h3l-3 3h3" fill="none" '
                f'stroke="#9db58a" stroke-width="1.5" opacity=".8"/>')
    if kind == "surprised":
        return (f'<path d="M{cx - 10} {cy - 7}q3-2 5-1M{cx + 5} {cy - 8}q3-1 5 1" fill="none" '
                f'stroke="{INK}" stroke-width="1.4" opacity=".65"/>{eye(cx - 6, cy, 3.2)}{eye(cx + 6, cy, 3.2)}'
                f'<circle cx="{cx}" cy="{cy + 6}" r="2.5" fill="{INK}"/>{b}')
    if kind == "shy":
        return (f'<path d="M{cx - 9} {cy}q2 2 4 0M{cx + 5} {cy}q2 2 4 0" fill="none" '
                f'stroke="{INK}" stroke-width="1.9" stroke-linecap="round"/>'
                f'<path d="M{cx - 2.5} {cy + 5}q2.5 2 5 0" fill="none" stroke="{INK}" stroke-width="1.8" '
                f'stroke-linecap="round"/>{b}'
                f'<path d="M{cx + 12} {cy + 8}c2-2 4-2 5 0-2 3-5 2-5 0Z" fill="{BLUSH}" opacity=".5"/>')
    if kind == "proud":
        return (f'<path d="M{cx - 9} {cy - 1}q3-3 5 0M{cx + 4} {cy - 1}q3-3 5 0" fill="none" '
                f'stroke="{INK}" stroke-width="2.1" stroke-linecap="round"/>'
                f'<path d="M{cx - 2} {cy + 5}q4 2 7-1" fill="none" stroke="{INK}" stroke-width="2" '
                f'stroke-linecap="round"/>{b}'
                f'<path d="M{cx + 13} {cy - 10}l1.2 2.8 2.8 1.2-2.8 1.2-1.2 2.8-1.2-2.8-2.8-1.2 2.8-1.2Z" '
                f'fill="{CREAM}" opacity=".85"/>')
    return ""


EXPR = {
    "calm": ("down", 0),
    "joy": ("up", -2),
    "curious": ("cheek", -4),
    "think": ("chin", 2),
    "sleepy": ("down", 6),
    "surprised": ("up", 0),
    "shy": ("together", -3),
    "proud": ("hips", 0),
}


def svg(kind, size=64):
    pose, tilt = EXPR[kind]
    body = (
        f'<g transform="rotate({tilt} 31.5 47)">'
        f'<path d="{BODY_PATH}" fill="url(#gLeaf)" stroke="{INK}" stroke-width="2.4"/>'
        '<path d="M7 25.5c.5 8 5 14 12 18M14 41c5 4 11 5 17 5" fill="none" '
        f'stroke="#8f5f2a" stroke-width="1.4" opacity=".42"/>'
        f'<path d="M18 13c-6 4-9 9-10 15" fill="none" stroke="{CREAM}" stroke-width="2" opacity=".35"/>'
        '<path d="M31.5 44.5 14 22M31.5 44.5 22 12M31.5 44.5 31 17M31.5 44.5 40 11M31.5 44.5 49 22" '
        f'stroke="#fff0bf" stroke-width="1.2" opacity=".6"/>'
        '<path d="M18 29l-3-4M24 24l-2-4M40 24l2-4M45 29l3-4M24 37l-4 2M40 37l4 2" '
        f'stroke="#fff0bf" stroke-width=".9" opacity=".42"/>'
        '<path d="M55.5 26c-2-4-5-6-8-7" fill="none" stroke="#9a6b2f" stroke-width="1.2" opacity=".55"/>'
        f'<circle cx="44" cy="19" r="1.8" fill="{CREAM}" opacity=".75"/>'
        '<path d="M31.5 46.5c0 3 1 5 3 6" stroke="#7e9a6b" stroke-width="2.8" stroke-linecap="round"/>'
        f'{foot(24, False)}{foot(39, True)}{arms(pose)}'
        f'<ellipse cx="31.5" cy="31" rx="12" ry="10" fill="{CREAM}" opacity=".10"/>'
        f'{face(kind)}</g>'
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" '
            f'role="img" aria-label="Frame & Grain ginkgo leaf spirit · {kind}">'
            f'{DEFS}{shadow()}{body}</svg>\n')


def main():
    CORE_OUT.mkdir(parents=True, exist_ok=True)
    DIST_OUT.mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    for kind in EXPR:
        text = svg(kind)
        (CORE_OUT / (kind + ".svg")).write_text(text, encoding="utf-8", newline="\n")
        (DIST_OUT / (kind + ".svg")).write_text(text, encoding="utf-8", newline="\n")
        (SAMPLES / ("叶精灵-" + kind + ".svg")).write_text(text, encoding="utf-8", newline="\n")
    fav = svg("calm").replace('width="64" height="64"', 'width="64" height="64"')
    (CORE_OUT / "favicon.svg").write_text(fav, encoding="utf-8", newline="\n")
    (DIST_OUT / "favicon.svg").write_text(fav, encoding="utf-8", newline="\n")
    (SAMPLES / "叶精灵-favicon.svg").write_text(fav, encoding="utf-8", newline="\n")
    print("leaf assets:", len(EXPR) + 1, "files ->", CORE_OUT, DIST_OUT)


if __name__ == "__main__":
    main()
