# -*- coding: utf-8 -*-
"""尘画 · 使用性质分类 (usage v1.0)

同一条影像的「能不能用」由两件事决定：`tier`（条款）与 `rights_status`（依据强度）。
这一层把它们翻译成用户看得懂的四种使用性质，并给出**必须遵守的义务**与**署名写法**。

   U1 自由商用   PD / CC0                 无需署名（仍建议注明来源）
   U2 商用需署名 CC BY                   必须署名 + 许可链接
   U3 商用需署名 CC BY-SA                 必须署名 + 许可链接；改编作品须同许可
   U4 仅非商用   NKCR / CC BY-NC          仅学习、研究、评论等非商业用途
   U5 仅可外链   INC（权利保留/未评估）    不提供图片，只能跳转源站

设计原则：**不把判断留给前端**。站点、CSV、台账都从这里取同一份结论。
"""
import sys

CLASSES = {
    "U1": {
        "label": "可自由商用",
        "short": "自由商用",
        "desc": "公有领域或权利人已放弃权利（CC0）。可商用、可改编、可再发布。",
        "obligation": "法律上无需署名；本站仍建议保留「来源机构 / 对象页」。",
        "credit": "无需署名",
        "color": "#8fb89a",
    },
    "U2": {
        "label": "可商用 · 须署名",
        "short": "商用需署名",
        "desc": "CC BY 等：可商用、可改编，但必须按权利人指定的方式署名。",
        "obligation": "必须署名 + 附许可名称与链接；不得暗示权利人背书本项目。",
        "credit": "作者 / 来源机构 / 许可名称 + 链接",
        "color": "#7fa8c9",
    },
    "U3": {
        "label": "可商用 · 署名 + 同许可",
        "short": "商用需署名+同许可",
        "desc": "CC BY-SA：可商用，但改编后的作品必须以同一许可发布。",
        "obligation": "署名 + 许可链接；若做改编（裁切、调色、拼贴），衍生作品须同样以 CC BY-SA 发布。",
        "credit": "作者 / 来源机构 / CC BY-SA 版本 + 链接",
        "color": "#d8ad66",
    },
    "U4": {
        "label": "仅非商用 · 学习研究",
        "short": "仅非商用",
        "desc": "来源只声明「未发现版权限制」，或明确为非商业许可（CC BY-NC）。可用于学习、研究、评论、新闻报道等非商业场景。",
        "obligation": "不得用于广告、带货、付费产品、商业导流；转载须署名并链回源站；商用前须逐张取得授权。",
        "credit": "作者 / 来源机构 / 原始声明 + 链接",
        "color": "#cf8580",
    },
    "U5": {
        "label": "仅可外链",
        "short": "仅可外链",
        "desc": "权利保留或状态未评估。本站不存图、不缓存，只提供索引卡与跳转。",
        "obligation": "本站不授予任何使用权；请自行联系权利人。",
        "credit": "—",
        "color": "#8a8378",
    },
}


def classify(tier, rights_status):
    """把 tier + rights_status 映射成使用性质代码。"""
    if tier == "L4":
        return "U5"
    if tier == "L3":
        return "U4"
    if tier == "L1" or rights_status == "CC-BY":
        return "U2"
    if tier == "L2" or rights_status == "CC-BY-SA":
        return "U3"
    if tier == "LU" or rights_status == "NKCR":
        return "U4"
    if tier == "L3" or rights_status == "INC-NC":
        return "U4"
    if tier == "L4" or rights_status == "INC":
        return "U5"
    return "U1"


def describe(tier, rights_status):
    code = classify(tier, rights_status)
    c = dict(CLASSES[code])
    c["code"] = code
    return c


if __name__ == "__main__":
    for t, s in [("L0", "PD"), ("L0", "CC0"), ("L1", "CC-BY"), ("L2", "CC-BY-SA"),
                 ("LU", "NKCR"), ("L3", "INC"), ("L4", "INC")]:
        d = describe(t, s)
        print("%s + %-8s → %s %s" % (t, s, d["code"], d["label"]))
    sys.exit(0)
