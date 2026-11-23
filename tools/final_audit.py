# -*- coding: utf-8 -*-
"""Final static sanity check for the built site."""
import os
import re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root
NEXT = os.path.join(ROOT, "next")
DIST = os.path.join(NEXT, "dist")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

class Check(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("extra </%s>" % tag)
            return
        if self.stack[-1] != tag:
            self.errors.append("expected </%s>, got </%s>" % (self.stack[-1], tag))
            if tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.stack.pop()
                if self.stack:
                    self.stack.pop()
        else:
            self.stack.pop()

paths = [
    os.path.join(DIST, "main", "index.html"),
    os.path.join(DIST, "photo", "index.html"),
    os.path.join(DIST, "paint", "index.html"),
    os.path.join(DIST, "main", "themes", "index.html"),
    os.path.join(DIST, "main", "timeline", "index.html"),
    os.path.join(DIST, "main", "today", "index.html"),
    os.path.join(DIST, "main", "today", "11-19.html"),
    os.path.join(DIST, "main", "story", "apollo-11-1969.html"),
    os.path.join(DIST, "main", "legal", "index.html"),
    os.path.join(DIST, "main", "search", "index.html"),
    os.path.join(DIST, "main", "404.html"),
    os.path.join(NEXT, "images", "pre19century", "index.html"),
    os.path.join(NEXT, "images", "19century", "index.html"),
    os.path.join(NEXT, "images", "20century", "index.html"),
    os.path.join(NEXT, "images", "21century", "index.html"),
]

for p in paths:
    if not os.path.exists(p):
        print("MISSING", os.path.relpath(p, NEXT))
        continue
    text = open(p, encoding="utf-8", errors="ignore").read()
    c = Check()
    c.feed(text)
    if c.errors or c.stack:
        print("TAG", os.path.relpath(p, NEXT), c.errors[:4], c.stack[-6:])
    count = len(re.findall(r'<a\b[^>]*class="[^"]*(?:desknav|g-nav)[^"]*"', text))
    # a few content-level checks
    extra = []
    for phrase in ("故事只有一篇", "入口应该有三个", "75001", "同一个档案馆", "三种读法", "这一天有 1 个故事", "今天有 1 个故事"):
        if phrase in text:
            extra.append(phrase)
    print("OK", os.path.relpath(p, NEXT), "bytes", len(text), "extra", extra)
