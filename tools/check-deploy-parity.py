#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-deploy-parity.py · 仓库 ↔ **每一个** 部署目标的逐文件全量一致性

## 为什么要它（2026-11-16 审查 D-01）

原有的检查链是：

    tools/sync-deploy.py        只比对 About/ 与 Assemblies/ 的 6 个文件，且只对 1.7
    tools/sync-deploy-all.py    只比对三棵语言树，且只对 1.7
    tools/final-check.py 第 4 节 只对 1.7
    tools/full-regression.py    调的是 sync-deploy.py 的 dry-run

四个环节**没有一个看过 1.6 副本**。实测后果：1.6 副本的 About 停在 v1.4.23
（1.7 已 1.5.7）、Languages 缺 19 个文件、OwnInjections 有 4 个文件是旧的。

所以本脚本的口径是「**全部**、**双向**、**每个目标**」：

  · 全部 —— About / Assemblies / Languages / OwnInjections / v1.7\\Languages / LoadFolders.xml
  · 双向 —— 仓库有而部署缺 = 缺；部署有而仓库没有 = 多余（.bak* 除外）
  · 每个目标 —— TARGETS 里每一行都查

## 它不做的事

不写盘。要修就跑 `tools/sync-deploy-all.py --write` + `tools/sync-deploy.py --write`。
本脚本只负责在闸门里 exit 1 拦下「部署 ≠ 仓库」。

## 排除规则

`*.bak` / `*.bak-sync` / `*.bak-r*` —— 同步脚本自己留的备份，不是发布内容；
`About/PublishedFileId.txt` —— 本地副本按惯例不该有（模板 B.8），有也不报。
"""
import os
import sys
import hashlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (显示名, 部署路径)
TARGETS = [
    ("1.7 主安装", r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"),
    ("1.6 引擎副本", r"D:\RimWorld-1.6\Mods\裸体评价更多看法-汉化修复"),
]

# 游戏真正会读取的路径（相对模组根）。`Source/` `tools/` `docs/` `packing/`
# `_backup/` 与根目录的 *.md 都不在内 —— 它们不参与加载，部署侧本来就不该带。
DIRS = [
    "About",
    "Assemblies",
    "Languages",
    "OwnInjections",
    os.path.join("v1.7", "Languages"),
]
FILES = ["LoadFolders.xml"]

SKIP_SUFFIX = (".bak",)
SKIP_MARK = (".bak-",)          # .bak-sync / .bak-r364
SKIP_REL = {os.path.join("About", "PublishedFileId.txt")}


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def skipped(rel):
    return rel in SKIP_REL or rel.endswith(SKIP_SUFFIX) or any(m in rel for m in SKIP_MARK)


def collect(root):
    """返回 {相对路径: 绝对路径}，只收 DIRS/FILES 里那些。"""
    out = {}
    for d in DIRS:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            for fn in fns:
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, root)
                if skipped(rel):
                    continue
                out[rel] = p
    for f in FILES:
        p = os.path.join(root, f)
        if os.path.isfile(p):
            out[f] = p
    return out


def main():
    repo_files = collect(REPO)
    print("仓库应发布文件：%d 个" % len(repo_files))
    print()

    total_bad = 0
    for label, deploy in TARGETS:
        print("=" * 72)
        print("目标：%s" % label)
        print("    %s" % deploy)
        print("=" * 72)
        if not os.path.isdir(deploy):
            print("  ❌ 部署目录不存在")
            total_bad += 1
            print()
            continue

        dep_files = collect(deploy)
        miss = sorted(set(repo_files) - set(dep_files))
        extra = sorted(set(dep_files) - set(repo_files))
        diff = sorted(k for k in set(repo_files) & set(dep_files)
                      if h(repo_files[k]) != h(dep_files[k]))

        print("  部署侧文件：%d 个" % len(dep_files))
        if miss:
            print("  ❌ 缺 %d 个：" % len(miss))
            for k in miss[:20]:
                print("       %s" % k)
            if len(miss) > 20:
                print("       …另有 %d 个" % (len(miss) - 20))
        if diff:
            print("  ❌ 内容不同 %d 个：" % len(diff))
            for k in diff[:20]:
                print("       %s" % k)
            if len(diff) > 20:
                print("       …另有 %d 个" % (len(diff) - 20))
        if extra:
            print("  ⚠ 多余 %d 个（仓库里没有）：" % len(extra))
            for k in extra[:20]:
                print("       %s" % k)
            if len(extra) > 20:
                print("       …另有 %d 个" % (len(extra) - 20))
        if not miss and not diff:
            print("  ✅ 一致（缺 0 / 不同 0）")

        # 「多余」不算失败：常见成因是部署侧留着历史文件，删不删都不影响加载。
        # 真正的判据是「该有的都在、内容都对」。
        total_bad += len(miss) + len(diff)
        print()

    print("=" * 72)
    print("合计不一致：%d 个（缺 + 内容不同）" % total_bad)
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
