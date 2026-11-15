# -*- coding: utf-8 -*-
"""
同步 README.md / 汉化说明.md 里的实测数字与一处重复表头。

本轮改动后的权威口径（tools/count-numbers.py 可复算）：
    正文 Keyed（1.7）        130,766 条
    界面与自有键              498 条
    DefInjected（1.6 根）    11,283 条 / 11 个文件
    DefInjected（1.7 专用）   1,190 条 / 38 个文件
    整列表注入            5,214 个容器 / 125,750 条 / 47 个文件
    增强界面                  103 条

用法：python tools/sync-readme-numbers.py [--write]
"""
import os
import sys
import argparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FILES = [os.path.join(REPO, "README.md"), os.path.join(REPO, "汉化说明.md")]

SUBS = [
    # 顶部导语
    ("**1.7 合并版** 走原生 Keyed（126,245 条正文 ＋ 486 条界面键）；\n"
     "> **1.6 两个原版** 走整列表注入（5,214 个容器）＋ DefInjected（11,809 条）。",
     "**1.7 合并版** 走原生 Keyed（130,766 条正文 ＋ 498 条界面键）；\n"
     "> **1.6 两个原版** 走整列表注入（5,214 个容器 / 125,750 条）＋ DefInjected（11,283 条）。"),

    # 表格重复表头 → 只留一行
    ("| 内容 | 数量 | 对应游戏里的什么 |\n"
     "|---|---|---|\n"
     "| 内容 | 实测数量 | 对应游戏里的什么 |\n"
     "|---|---|---|\n",
     "| 内容 | 实测数量 | 对应游戏里的什么 |\n"
     "|---|---|---|\n"),

    # 表格各行
    ("| 正文 Keyed（1.7） | **126,245** 条 |",
     "| 正文 Keyed（1.7） | **130,766** 条 |"),
    ("| 界面与自有键 | **486** 条 |",
     "| 界面与自有键 | **498** 条 |"),
    ("| DefInjected（1.6） | **11,809** 条 / 30 个文件 |",
     "| DefInjected（1.6 根） | **11,283** 条 / 11 个文件 |\n"
     "| DefInjected（1.7 专用） | **1,190** 条 / 38 个文件 |"),
    ("| 整列表注入（1.6） | **5,208** 个容器 / 47 个文件 |",
     "| 整列表注入（1.6） | **5,214** 个容器 / 125,750 条 / 47 个文件 |"),
    ("| 增强界面（硬编码） | 约 **90** 条 |",
     "| 增强界面（硬编码） | **103** 条 |"),

    # 对账段
    ("· **正着数**：本包写出了多少条译文 —— 1.7 通道 126,245 ＋ 486；"
     "1.6 通道 5,214 个容器 ＋ 11,809 条",
     "· **正着数**：本包写出了多少条译文 —— 1.7 通道 130,766 ＋ 498 ＋ 1,190；"
     "1.6 通道 5,214 个容器 / 125,750 条 ＋ 11,283 条"),

    # 对账段的注入容器数
    ("注入容器 5,208 个全部与原 def 的列表条数一致",
     "注入容器 5,214 个全部与原 def 的列表条数一致"),

    # 双通道表
    ("| **1.7 合并版** | 原生 Keyed（`v1.7/Languages/ChineseSimplified/Keyed/`，"
     "已摊平到根，与全库一千多个模组写法一致） | 126,245 |",
     "| **1.7 合并版** | 原生 Keyed（`v1.7/Languages/ChineseSimplified/Keyed/`，"
     "已摊平到根，与全库一千多个模组写法一致） | 130,766 |"),
    ("| **1.6 两个原版** | 运行时注入（`OwnInjections/`，反射写回 `List<string>`）"
     "＋ `Languages/DefInjected/` | 5,208 容器 ＋ 11,809 条 |",
     "| **1.6 两个原版** | 运行时注入（`OwnInjections/`，反射写回 `List<string>`）"
     "＋ `Languages/DefInjected/` | 5,214 容器 ＋ 11,283 条 |"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    for p in FILES:
        if not os.path.exists(p):
            print("跳过（不存在）：%s" % p)
            continue
        txt = open(p, encoding="utf-8", newline="").read()
        orig = txt
        eol = "\r\n" if "\r\n" in txt else "\n"
        hits = 0
        for old, new in SUBS:
            o = old.replace("\n", eol)
            n = new.replace("\n", eol)
            if o in txt:
                txt = txt.replace(o, n, 1)
                hits += 1
        print("%-12s 命中 %d/%d 条替换" % (os.path.basename(p), hits, len(SUBS)))
        # 剩余的旧数字
        for bad in ("126,245", "5,208", "11,809", "**486**"):
            if bad in txt:
                idx = txt.find(bad)
                line = txt[:idx].count("\n") + 1
                print("    [残留] %s 在第 %d 行" % (bad, line))
        if args.write and txt != orig:
            open(p, "w", encoding="utf-8", newline="").write(txt)
            print("    已写入")
    if not args.write:
        print()
        print("（dry-run，加 --write 才真改）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
