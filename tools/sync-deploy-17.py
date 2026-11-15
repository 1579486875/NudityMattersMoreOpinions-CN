# -*- coding: utf-8 -*-
"""把仓库的 v1.7/Languages 两套目录与部署目录做双向对齐（仓库为准），并逐文件 hash 校验。"""
import os
import sys
import shutil
import hashlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"E:\TAML\_work\nmzh-git\v1.7\Languages"
DST = r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复\v1.7\Languages"
LANGS = ["ChineseSimplified", "ChineseSimplified (简体中文)"]


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    added = removed = updated = same = 0
    for lang in LANGS:
        s = os.path.join(SRC, lang)
        d = os.path.join(DST, lang)
        if not os.path.isdir(s):
            print("仓库缺目录：%s" % s)
            continue
        rels = []
        for dp, dn, fns in os.walk(s):
            for fn in fns:
                p = os.path.join(dp, fn)
                rels.append(os.path.relpath(p, s))
        for rel in sorted(rels):
            ps = os.path.join(s, rel)
            pd = os.path.join(d, rel)
            if not os.path.exists(pd):
                os.makedirs(os.path.dirname(pd), exist_ok=True)
                shutil.copy2(ps, pd)
                added += 1
                print("  + %s\\%s" % (lang, rel))
            elif h(ps) != h(pd):
                shutil.copy2(ps, pd)
                updated += 1
                print("  ~ %s\\%s" % (lang, rel))
            else:
                same += 1
        # 部署里多出来的文件（仓库已删）
        for dp, dn, fns in os.walk(d):
            for fn in fns:
                pd = os.path.join(dp, fn)
                rel = os.path.relpath(pd, d)
                ps = os.path.join(s, rel)
                if not os.path.exists(ps):
                    os.remove(pd)
                    removed += 1
                    print("  - %s\\%s" % (lang, rel))
        # 清空目录
        for dp, dn, fns in sorted(os.walk(d), key=lambda x: -len(x[0])):
            if not os.listdir(dp):
                os.rmdir(dp)
                print("  (删除空目录 %s)" % os.path.relpath(dp, d))

    print()
    print("新增 %d / 更新 %d / 删除 %d / 一致 %d" % (added, updated, removed, same))

    # 最终全量校验
    bad = 0
    for lang in LANGS:
        s = os.path.join(SRC, lang)
        d = os.path.join(DST, lang)
        for dp, dn, fns in os.walk(s):
            for fn in fns:
                ps = os.path.join(dp, fn)
                rel = os.path.relpath(ps, s)
                pd = os.path.join(d, rel)
                if not os.path.exists(pd) or h(ps) != h(pd):
                    bad += 1
                    print("  [不一致] %s\\%s" % (lang, rel))
    print("最终：%d 个文件不一致" % bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
