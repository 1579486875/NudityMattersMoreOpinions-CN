# -*- coding: utf-8 -*-
"""
修正 627 个 OpinionDef_Situational 的 Keyed 正文索引（整体前移一位、删掉废话占位）。

【问题】
原模组读正文的代码（反编译 OpinionTextTranslator.Pick）：

    int num = Rand.Range(0, texts.Count);              // 0..Count-1
    string result = texts[num];
    string key = $"NMM.Opinion.{def.defName}.{fieldName}.{num}";
    if (!Translator.CanTranslate(key)) return result;
    return Translator.Translate(key);

所以 Keyed 下标必须与字段 List 的下标一一对应、总条数必须等于 List.Count。

而这 627 个 Def **没有 ParentName**（不算 BaseSituationalOpinionDef，且没有任何 Def
以它为父），字段里就是自己写的 N 条。当初的批量脚本把它们当成「有继承」的 SexPart，
统一插了一条基类占位（"就这样，还有什么好说的？"）并把原译文整体后移 —— 于是：

    num=0  → 显示"就这样，还有什么好说的？"（跟场景无关）
    num=1  → 显示原文第 1 条的译文（本该是第 0 条）
    ……
    num=N-1→ 显示原文第 N 条的译文
    原文第 N 条（最后一条）的译文被挤到下标 N，而 num 最大只到 N-1 → **永远读不到**

即：**每一条都错位一位，且每个 Def 永久丢一条译文。**

【修法】
对清单里的每个 Def：删掉 .0，把 1..N 前移成 0..N-1。只改键名，不动任何译文文本、
不动缩进与行尾。

用法：
    python 工具/fix-situational-index.py --dry-run     # 只看会改什么
    python 工具/fix-situational-index.py --write       # 真写
"""
import os
import re
import sys
import shutil
import argparse
import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DOCS = os.path.join(REPO, "文档", "_fake-placeholder-list.txt")

# 两个语言目录都要改（游戏按 Prefs.langFolderName 选其中一个，只改一个等于没改）
LANG_DIRS = [
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified"),
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified (简体中文)"),
]

KEY_RE = re.compile(
    r"^(?P<ind>[ \t]*)<NMM\.Opinion\.(?P<def>.+?)\.(?P<field>opinionTexts|texts)\.(?P<idx>\d+)>"
    r"(?P<text>.*?)</NMM\.Opinion\.(?P=def)\.(?P=field)\.(?P=idx)>(?P<tail>[ \t]*)$"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if not args.write:
        args.dry_run = True

    targets = load_targets()
    print("清单：%d 个 (Def, 字段)" % len(targets))

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    total_shift = total_drop = 0

    for lang in LANG_DIRS:
        kdir = os.path.join(lang, "Keyed")
        if not os.path.isdir(kdir):
            print("跳过（无 Keyed）：%s" % lang)
            continue
        print()
        print("=" * 70)
        print(lang)
        if args.write:
            bak = os.path.join(REPO, "文档", "_bak_keyed_%s" % stamp,
                               os.path.basename(lang))
            os.makedirs(bak, exist_ok=True)
            for fn in os.listdir(kdir):
                if fn.endswith(".xml"):
                    shutil.copy2(os.path.join(kdir, fn), os.path.join(bak, fn))
            print("  备份 → %s" % bak)

        for fn in sorted(os.listdir(kdir)):
            if not fn.endswith(".xml"):
                continue
            p = os.path.join(kdir, fn)
            with open(p, "r", encoding="utf-8-sig", newline="") as fh:
                lines = fh.readlines()
            out = []
            shift = drop = 0
            for ln in lines:
                body = ln.rstrip("\r\n")
                eol = ln[len(body):]
                m = KEY_RE.match(body)
                if not m:
                    out.append(ln)
                    continue
                d = m.group("def")
                f = m.group("field")
                if (d, f) not in targets:
                    out.append(ln)
                    continue
                i = int(m.group("idx"))
                if i == 0:
                    drop += 1
                    continue
                newbody = ("%s<NMM.Opinion.%s.%s.%d>%s</NMM.Opinion.%s.%s.%d>%s"
                           % (m.group("ind"), d, f, i - 1, m.group("text"),
                              d, f, i - 1, m.group("tail")))
                out.append(newbody + eol)
                shift += 1
            if shift or drop:
                print("  %-24s 前移 %-5d 删占位 %-4d" % (fn, shift, drop))
                total_shift += shift
                total_drop += drop
                if args.write:
                    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
                        fh.writelines(out)

    print()
    print("合计：前移 %d 条、删占位 %d 条" % (total_shift, total_drop))
    if args.dry_run:
        print("（dry-run，未写盘；加 --write 才真改）")
    return 0


def load_targets():
    t = set()
    with open(DOCS, "r", encoding="utf-8") as fh:
        for ln in fh:
            parts = ln.rstrip("\n").split("\t")
            if len(parts) >= 2:
                t.add((parts[0], parts[1]))
    return t


if __name__ == "__main__":
    sys.exit(main())
