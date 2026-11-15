# -*- coding: utf-8 -*-
"""
把根目录 DefInjected 下「1.6 根本不存在这些 Def」的三个目录搬到 v1.7/。

为什么必须搬
------------
LoadFolders.xml：
    <v1.6><li>/</li></v1.6>
    <v1.7><li>/</li><li>v1.7</li></v1.7>

根目录是**两个版本共用**的，v1.7/ 只有 1.7 才加载。

1.6 的原模组是 `NudityMattersMore_opinions`（它的 LoadFolders v1.6 分支只加载
Common/ 与 1.6/，而 1.6/ 里只有 Assemblies 和 Source，没有 Defs），
`RJW-功能-裸体评价` 的 LoadFolders 只有 <v1.7>，1.6 下不提供任何 Def。

于是根目录里的 ThoughtDef / TraitDef / HediffDef 三类键（526 条、133 个 Def）
在 1.6 下全部悬空 —— 游戏会逐条报
    `Found no ThoughtDef named X to match X.label (文件)`
（判据：Verse.DefInjectionPackage.SetDefFieldAtPath 里
  `if (GenDefDatabase.GetDefSilentFail(defType, defName) == null) { loadErrors.Add("Found no ...") }`）

搬到 v1.7/ 之后：
  · 1.6：不加载 v1.7/ → 不再报错（这些 Def 本来也不存在，没有翻译损失）
  · 1.7：根 + v1.7 都加载 → 照常生效

用法：python tools/move-root-definjected.py [--write]
"""
import os
import sys
import shutil
import argparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = r"E:\TAML\_work\nmzh-git"
MOVED = ["ThoughtDef", "TraitDef", "HediffDef"]
LANGS = ["ChineseSimplified", "ChineseSimplified (简体中文)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    write = args.write

    n = 0
    for lang in LANGS:
        root_di = os.path.join(REPO, "Languages", lang, "DefInjected")
        v17_di = os.path.join(REPO, "v1.7", "Languages", lang, "DefInjected")
        if not os.path.isdir(root_di):
            print("跳过（无此语言目录）：%s" % root_di)
            continue
        print("=" * 70)
        print(lang)
        for d in MOVED:
            src = os.path.join(root_di, d)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(v17_di, d)
            files = sorted(f for f in os.listdir(src) if f.endswith(".xml"))
            print("  %s：%d 个文件" % (d, len(files)))
            for fn in files:
                sp = os.path.join(src, fn)
                dp = os.path.join(dst, fn)
                exists = os.path.exists(dp)
                print("    %s %s%s" % ("覆盖" if exists else "新增", fn,
                                       "  ← 目标已存在！" if exists else ""))
                if write:
                    os.makedirs(dst, exist_ok=True)
                    shutil.copy2(sp, dp)
                n += 1
            if write:
                shutil.rmtree(src)
                print("    已删除源目录 %s" % src)
        print()

    print("合计处理 %d 个文件" % n)
    if not write:
        print("（dry-run，加 --write 才真搬）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
