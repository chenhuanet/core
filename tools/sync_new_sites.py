# -*- coding: utf-8 -*-
"""Create/populate the four new v3.2 site repos from workspace/release.

Does not push, does not touch existing live repos.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "workspace" / "release"
TEMPLATE = ROOT / "repos" / "main" / ".github" / "workflows" / "pages.yml"
SITES = ("painting", "photography", "ai", "aiera")
DESC = {
    "painting": ("学习绘画", "painting.chenhua.net"),
    "photography": ("学习摄影", "photography.chenhua.net"),
    "ai": ("AI 图像", "ai.chenhua.net"),
    "aiera": ("AI 影像库", "aiera.chenhua.net"),
}

for site in SITES:
    src = RELEASE / site
    dst = ROOT / "repos" / site
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    wf = dst / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE, wf / "pages.yml")
    zh, domain = DESC[site]
    (dst / "README.md").write_text(
        "# %s\n\n%s（%s）的生成页面仓。页面由 `repos/core/tools/build_v32.py` 生成，请勿手改 HTML/CSS/导航。\n"
        % (site, zh, domain), encoding="utf-8")
    print(site, sum(1 for _ in dst.rglob("*") if _.is_file()))
