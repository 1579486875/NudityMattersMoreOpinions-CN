# -*- coding: utf-8 -*-
"""
在汉化包 description 的「■ 更新记录」下插入 v1.5.1 条目。

★ 铁律：description 里出现的 `<` `>` `&` 必须写成 &lt; &gt; &amp;，
  否则 About.xml 直接变成非法 XML（实测写裸 `<defName>` 会让游戏整个 About 读不出来）。
   本脚本只写转义形式。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
P = os.path.join(REPO, "About", "About.xml")

raw = open(P, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
txt = raw.decode("utf-8-sig")
m = re.search(r"<description>(.*?)</description>", txt, re.S)
d = m.group(1)

if "【v1.5.1 " in d:
    print("已有 v1.5.1 条目，跳过")
    sys.exit(0)

anchor = "■ 更新记录\n【v1.4.19"
if anchor not in d:
    print("锚点未命中")
    sys.exit(1)

rec = (
    "■ 更新记录\n"
    "\n"
    "【v1.5.1 修好「正文整体错位一位」与两处静默失效】\n"
    "· 627 个「情境看法」的正文全部错位一位。原模组抽正文的逻辑是"
    "`Rand.Range(0, texts.Count)` 取下标、再拼 `NMM.Opinion.&lt;defName&gt;.opinionTexts.&lt;num&gt;` 查译文，"
    "所以键的下标必须与字段列表一一对应。而这批 Def 并没有父模板，却被当成有继承、"
    "统一在前面插了一条占位并整体后移 —— 结果第 0 条永远显示一句跟场景无关的话，"
    "其余每条都显示成隔壁那条，每个 Def 的最后一条译文永远抽不到。"
    "现已逐个前移复位（16,200 条键重排，两份语言目录同步）。\n"
    "· 1.6 下 526 条译文从未加载过。它们指向的 Def 只存在于 1.7 合并版，"
    "却放在两个版本共用的根目录里，于是 1.6 每次启动都要逐条报「Found no ThoughtDef named …」；"
    "现已移进 v1.7\\ 目录，1.6 不再报错、1.7 照常生效。\n"
    "· 一处「目录名不是 Def 类型」的翻译目录被游戏整目录丢弃、且每次启动刷一条红字；"
    "其中 6 条有效译文（拘谨 / 暴露狂 / 视奸狂三个特质的档位名与描述）已按新写法并入 TraitDef\\，"
    "这三个特质首次显示中文。\n"
    "· 数字全部按 2026-11-15 实测重算，并附了复算脚本 `tools/count-numbers.py`。\n"
    "\n"
    "【v1.4.19")

d2 = d.replace(anchor, rec, 1)
out = (b"\xef\xbb\xbf" if bom else b"") + (txt[:m.start(1)] + d2 + txt[m.end(1):]).encode("utf-8")
open(P, "wb").write(out)
print("已插入 v1.5.1 条目，文件 %d 字节" % len(out))
