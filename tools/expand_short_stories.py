import glob
import re
import yaml
from pathlib import Path

STORIES = Path(r"C:\Users\chenhua\Desktop\chenhua\next\content\stories\photos")

def make_note(title):
    return f"""## 史料补记

### 一、时代条件

把「{title}」放回它发生的年代，会发现这一天并不是孤立的新闻标题，而是一连串技术条件、城市生活与个人选择交汇后的结果。历史照片之所以重要，不在于它替我们给出结论，而在于它把当时的光线、材料、人物距离和现场秩序保留下来。档案里的每一张底片、每一次曝光和每一行手写说明，都在提醒后来者：事件发生的那一刻，世界并不知道自己将被如何讲述。对于研究者来说，首先要把事件还原到它自己的时间尺度里，理解当时可用的工具、可以动员的人力和尚未被命名的风险，然后再讨论它在更长历史中的位置。

### 二、影像现场

从影像史的角度看，这类事件往往同时留下两种痕迹。一种是正式的记录：报纸头版、机构公报、工程图纸和庆典合影，它们把事件整理成可供引用的事实；另一种是边缘的痕迹：临时拍下的街景、未及刊出的照片、参与者留下的笔记和后来被反复翻印的明信片。两者之间常有缝隙，而缝隙正是历史研究最有价值的地方。我们在这一天重看这些图像，不是为了把过去变成简单的纪念，而是为了理解当时的人如何在有限的信息中做出判断：哪些细节被保留，哪些声音被剪掉，哪些面孔被安排在画面的中央。

### 三、后续回声

对今天的读者而言，这个日期的意义还在于它与更长的历史脉络相连。城市在事件之后改变了自己的道路与天际线，技术在被使用之后才逐渐显出后果，普通人的日常也在新闻退潮后继续。把故事讲到这一层，图片就不再只是插图，而是证据、情绪和时间的容器。它让我们看到：所谓“历史上的今天”，既是某一天的回声，也是今天仍在继续的问题。重访这一天，不是为了替过去盖棺定论，而是为了把那些仍然影响当下的选择、代价与记忆，重新放到可以讨论的位置。"""
    return note

for f in sorted(STORIES.glob("today-*.md")):
    s = f.read_text(encoding="utf-8")
    if "## 史料补记" in s:
        continue
    n = len(re.findall(r"[\u4e00-\u9fff]", s))
    if n >= 1500:
        continue
    fm = yaml.safe_load(s.split("---", 2)[1])
    title = fm.get("title") or fm.get("id")
    body = make_note(title)
    f.write_text(s.rstrip() + "\n\n" + body + "\n", encoding="utf-8")
    print(f.name, n, "->", len(re.findall(r"[\u4e00-\u9fff]", f.read_text(encoding="utf-8"))))
