# -*- coding: utf-8 -*-
"""Add a small /themes/ landing page to paint and photo (old pages were redirect stubs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitekit as K  # noqa: E402
import reshell_batch as S  # noqa: E402

for site in ("paint", "photo"):
    for lang in ("zh", "en"):
        title = "主题库" if lang == "zh" else "Themes"
        desc = "跨媒介主题按人间、社会、自然、图像、物与运动组织。" if lang == "zh" else "Cross-media themes across human, society, nature, image, object and motion."
        body = ('<main class="s-main"><h1 class="s-title">%s</h1><p class="s-lede">%s</p>'
                '<p><a class="s-btn gold" href="%s">%s</a></p></main>'
                % (title, desc, "https://chenhua.net/themes/" if lang == "zh" else "https://chenhua.net/en/themes/",
                   "进入主站主题库" if lang == "zh" else "Open the theme library"))
        page = K.page(site, lang, "/themes/", title, desc, body)
        target = K.ROOT / "workspace" / "release" / site / (("en/" if lang == "en" else "") + "themes/index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
    S.rebuild_sitemap(site)
    print(site, "themes landing added")
