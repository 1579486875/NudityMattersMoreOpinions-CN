# -*- coding: utf-8 -*-
"""把仓库里的语言相关目录全量对齐到部署目录，并逐文件 hash 校验。

同步范围（只碰这三块，绝不碰 About / Assemblies / Source）：
    Languages\\                    （1.6 与 1.7 共用）
    OwnInjections\\                （自有整列表清单，1.6 的正文主通道）
    v1.7\\Languages\\              （只 1.7 加载）

用法：python tools/sync-deploy-all.py [--write]
"""
import os
import sys
import shutil
import hashlib
import argparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 2026-11-16 改：原先硬编码 E:\TAML\_work\nmzh-git（旧 clone）
DEPLOY = r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"

TREES = [
    ("Languages", "Languages"),
    ("OwnInjections", "OwnInjections"),
    (os.path.join("v1.7", "Languages"), os.path.join("v1.7", "Languages")),
]


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    write = args.write

    added = updated = removed = same = 0
    for src_rel, dst_rel in TREES:
        s = os.path.join(REPO, src_rel)
        d = os.path.join(DEPLOY, dst_rel)
        if not os.path.isdir(s):
            print("跳过（仓库无此目录）：%s" % src_rel)
            continue
        rels = []
        for dp, dn, fns in os.walk(s):
            for fn in fns:
                rels.append(os.path.relpath(os.path.join(dp, fn), s))
        for rel in sorted(rels):
            ps, pd = os.path.join(s, rel), os.path.join(d, rel)
            if not os.path.exists(pd):
                added += 1
                print("  + %s\\%s" % (dst_rel, rel))
                if write:
                    os.makedirs(os.path.dirname(pd), exist_ok=True)
                    shutil.copy2(ps, pd)
            elif h(ps) != h(pd):
                updated += 1
                print("  ~ %s\\%s" % (dst_rel, rel))
                if write:
                    shutil.copy2(ps, pd)
            else:
                same += 1
        if os.path.isdir(d):
            for dp, dn, fns in os.walk(d):
                for fn in fns:
                    pd = os.path.join(dp, fn)
                    ps = os.path.join(s, os.path.relpath(pd, d))
                    if not os.path.exists(ps):
                        removed += 1
                        print("  - %s\\%s" % (dst_rel, os.path.relpath(pd, d)))
                        if write:
                            os.remove(pd)
            for dp, dn, fns in sorted(os.walk(d), key=lambda x: -len(x[0])):
                if not os.listdir(dp):
                    print("  (删空目录 %s\\%s)" % (dst_rel, os.path.relpath(dp, d)))
                    if write:
                        os.rmdir(dp)

    print()
    print("新增 %d / 更新 %d / 删除 %d / 一致 %d" % (added, updated, removed, same))
    if not write:
        print("（dry-run，加 --write 才真同步）")
        return 0

    bad = 0
    for src_rel, dst_rel in TREES:
        s = os.path.join(REPO, src_rel)
        d = os.path.join(DEPLOY, dst_rel)
        if not os.path.isdir(s):
            continue
        for dp, dn, fns in os.walk(s):
            for fn in fns:
                ps = os.path.join(dp, fn)
                pd = os.path.join(d, os.path.relpath(ps, s))
                if not os.path.exists(pd) or h(ps) != h(pd):
                    bad += 1
                    print("  [不一致] %s\\%s" % (dst_rel, os.path.relpath(ps, s)))
    print("最终：%d 个文件不一致" % bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
