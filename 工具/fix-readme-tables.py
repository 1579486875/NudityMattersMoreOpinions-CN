# -*- coding: utf-8 -*-
"""重写 README / 汉化说明 里两处过时的明细表（路径表 + DefInjected 字段表）。
数字全部来自 工具/count-detail.py 的实测输出。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FILES = [os.path.join(REPO, "README.md"), os.path.join(REPO, "汉化说明.md")]

OLD1 = """| 路径 | 文件 | 条目 | 放的是什么 |
|---|---|---|---|
| `v1.7\\Languages\\ChineseSimplified\\Keyed\\` | 29 | **126,261** 条 | 1.7 合并版的看法正文（键形如 `NMM.Opinion.<defName>.opinionTexts.<序号>`）＋ 22 条原模组自有键 |
| `OwnInjections\\ChineseSimplified\\DefInjected\\` | 47 | **5,214 个容器 / 125,750 条** | 1.6 原版的看法正文 —— 条数已与原 def 逐条核对一致（不符 0 个） |
| `Languages\\ChineseSimplified\\DefInjected\\` | 30 | **11,809** 条（含 192 个整列表容器） | 看法条目名称、生成器模板、描述、互动日志句式 |
| `Languages\\ChineseSimplified\\Keyed\\` | 7 | **485** 条 | 界面键：设置窗口、看法标签页、通知、社交感受（1.7 层另有 1 条独有键，去重合计 486） |
| **合计（单份语言目录）** | **113** | **126,261 ＋ 11,809 ＋ 491 ＝ 138,561 条单条键，外加 5,208 个整列表容器（内含 125,750 条 `<li>`）** | — |"""

NEW1 = """| 路径 | 文件 | 条目 | 放的是什么 |
|---|---|---|---|
| `v1.7\\Languages\\ChineseSimplified\\Keyed\\` | 28 | **130,767** 条 | 1.7 合并版的看法正文（键形如 `NMM.Opinion.<defName>.opinionTexts.<序号>`）＋ 1 条自有键 |
| `v1.7\\Languages\\ChineseSimplified\\DefInjected\\` | 38 | **1,190** 条 | 只在 1.7 合并版里存在的定义：特质档位、心情、健康状态、任务名 |
| `OwnInjections\\ChineseSimplified\\DefInjected\\` | 47 | **5,214 个容器 / 125,750 条** | 1.6 原版的看法正文 —— 条数已与原 def 逐条核对一致（不符 0 个） |
| `Languages\\ChineseSimplified\\DefInjected\\` | 11 | **11,283** 条（叶子 16,706；含 192 个整列表容器） | 看法条目名称、生成器模板、描述、互动日志句式 |
| `Languages\\ChineseSimplified\\Keyed\\` | 7 | **497** 条 | 界面键：设置窗口、看法标签页、通知、社交感受 |
| **合计（单份语言目录）** | **131** | **130,767 ＋ 1,190 ＋ 11,283 ＋ 497 ＝ 143,737 条单条键，外加 5,214 个整列表容器（内含 125,750 条 `<li>`）** | — |"""

OLD2 = """DefInjected 那 11,809 条按字段拆开（只列前四位）：

| 字段 | 条数 | 是什么 |
|---|---|---|
| `label` | **5,626** | 看法条目名称、健康状态名、特质名 |
| 索引式正文键（`.0` / `.1` / …） | 约 **1,100** | 零星正文补充（大头在 `OwnInjections\\`） |
| `description` | **242** | 描述文本 |
| `rulesStrings` | **192** 个整列表容器 | 互动日志句式（每个容器内是多条 `<li>`） |"""

NEW2 = """DefInjected 合计 **12,473** 条（根 11,283 ＋ 1.7 专用 1,190），按字段拆开：

| 字段 | 条数 | 是什么 |
|---|---|---|
| 索引式正文键（`.0` / `.1` / …） | **6,541** | 零星正文补充（大头在 `OwnInjections\\`） |
| `label` | **5,590** | 看法条目名称、健康状态名、特质名 |
| `rulesStrings` | **192** 个整列表容器 | 互动日志句式（每个容器内是多条 `<li>`） |
| `description` | **147** | 描述文本（1.7 特有的心情 / 健康状态） |
| `reportString` | **3** | 任务报告行 |"""


def main():
    write = "--write" in sys.argv
    for p in FILES:
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8", newline="").read()
        eol = "\r\n" if "\r\n" in txt else "\n"
        orig = txt
        n = 0
        for old, new in ((OLD1, NEW1), (OLD2, NEW2)):
            o = old.replace("\n", eol)
            nn = new.replace("\n", eol)
            if o in txt:
                txt = txt.replace(o, nn, 1)
                n += 1
        print("%-12s 命中 %d/2" % (os.path.basename(p), n))
        if write and txt != orig:
            open(p, "w", encoding="utf-8", newline="").write(txt)
            print("    已写入")
    if not write:
        print("（dry-run，加 --write 才真改）")


if __name__ == "__main__":
    main()
