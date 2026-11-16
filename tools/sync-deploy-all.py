# -*- coding: utf-8 -*-
"""把仓库里的语言相关目录全量对齐到**每一个**部署目标，并逐文件 hash 校验。

同步范围（只碰这三块，绝不碰 About / Assemblies / Source）：
    Languages\\                    （1.6 与 1.7 共用）
    OwnInjections\\                （自有整列表清单，1.6 的正文主通道）
    v1.7\\Languages\\              （只 1.7 加载）

⚠ 2026-11-16 订正（本轮审查 D-01）：
    旧版的 DEPLOY 是**单个路径**，只指向 1.7 主安装。于是
        · `tools/sync-deploy.py`（About/Assemblies 那 6 个文件）
        · 本脚本（三棵语言树）
        · `tools/final-check.py` 第 4 节
        · `tools/full-regression.py` 的「部署目录同步」闸门
    串成一条链，**没有任何一环检查过 1.6 副本**。实测后果：
        1.6 副本的 `About` 停在 v1.4.23（1.7 已是 1.5.7），
        `Languages` 缺 19 个文件、另有 3 个内容不同；
        `OwnInjections` 有 4 个文件内容不同（那是 125,750 条整列表注入的正文通道）。
    判据全部来自 `About\\About.xml` 的 `modVersion` 与实际文件 hash 比对。

    现在改成 TARGETS 列表，**两个环境一起同步、一起校验**。
    谁再加环境，只要往 TARGETS 里加一行。

⚠ 为什么 1.6 也要放 `ChineseSimplified (简体中文)` 那一套：
    `Prefs.xml` 的 `<langFolderName>` 是 `ChineseSimplified (简体中文)`，而 `Config/`
    在两个环境之间是**共用**的。反编译 `Verse.LoadedLanguage.AllDirectories` 可见
    「先找 folderName，存在就 continue、不再找 legacyFolderName」：
        · 只放无括号版 → 找不到括号版 → 回退到 legacyFolderName（`ChineseSimplified`）→ 能加载
        · 两套都放且字节一致 → 加载括号版 → 同样正确
    选后者：结构两个环境完全一致，同步脚本不必分叉，也天然满足
    「两套都改、两套都核 hash」这条纪律（模板 B.17.4）。

用法：
    python tools/sync-deploy-all.py            # dry-run，列出差异
    python tools/sync-deploy-all.py --write    # 真同步并复核
"""
import os
import sys
import shutil
import hashlib
import argparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 每个部署目标一行：(显示名, 路径, 是否包含 v1.7 树)
#   1.6 引擎不加载 `v1.7\\`（LoadFolders 的 <v1.6> 分支只有 <li>/</li>），
#   但**照样同步**：这样「部署 = 仓库」这条断言在所有目标上都成立，
#   不必为某个目标写特例；多占 37 MB 磁盘，换脚本零分叉，值。
TARGETS = [
    ("1.7 主安装", r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复", True),
    ("1.6 引擎副本", r"D:\RimWorld-1.6\Mods\裸体评价更多看法-汉化修复", True),
]

TREES = [
    ("Languages", "Languages"),
    ("OwnInjections", "OwnInjections"),
    (os.path.join("v1.7", "Languages"), os.path.join("v1.7", "Languages")),
]


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def sync_one(label, deploy, write, include_v17):
    """把仓库三棵树对齐到单个部署目标，返回 (added, updated, removed, same)。"""
    added = updated = removed = same = 0
    trees = TREES if include_v17 else TREES[:2]
    print("=" * 78)
    print("目标：%s" % label)
    print("    path: %s" % deploy)
    print("=" * 78)

    if not os.path.isdir(deploy):
        print("  ❌ 部署目录不存在，整目标跳过")
        return 0, 0, 0, 0, 1          # 最后一位 = 错误数

    for src_rel, dst_rel in trees:
        s = os.path.join(REPO, src_rel)
        d = os.path.join(deploy, dst_rel)
        if not os.path.isdir(s):
            print("  跳过（仓库无此目录）：%s" % src_rel)
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
    print("  新增 %d / 更新 %d / 删除 %d / 一致 %d" % (added, updated, removed, same))
    print()
    return added, updated, removed, same, 0


def verify_one(label, deploy, include_v17):
    """同步后复核：逐文件 hash 比对，返回不一致条数。"""
    bad = 0
    trees = TREES if include_v17 else TREES[:2]
    for src_rel, dst_rel in trees:
        s = os.path.join(REPO, src_rel)
        d = os.path.join(deploy, dst_rel)
        if not os.path.isdir(s):
            continue
        for dp, dn, fns in os.walk(s):
            for fn in fns:
                ps = os.path.join(dp, fn)
                pd = os.path.join(d, os.path.relpath(ps, s))
                if not os.path.exists(pd) or h(ps) != h(pd):
                    bad += 1
                    print("  [不一致] %s\\%s" % (dst_rel, os.path.relpath(ps, s)))
    # 反向：部署侧多出来的文件也算不一致
    for src_rel, dst_rel in trees:
        s = os.path.join(REPO, src_rel)
        d = os.path.join(deploy, dst_rel)
        if not os.path.isdir(d):
            continue
        for dp, dn, fns in os.walk(d):
            for fn in fns:
                pd = os.path.join(dp, fn)
                ps = os.path.join(s, os.path.relpath(pd, d))
                if not os.path.exists(ps):
                    bad += 1
                    print("  [多余] %s\\%s" % (dst_rel, os.path.relpath(pd, d)))
    print("  %s：%d 个文件不一致" % (label, bad))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    write = args.write

    total_err = 0
    for label, deploy, inc17 in TARGETS:
        _, _, _, _, err = sync_one(label, deploy, write, inc17)
        total_err += err

    if not write:
        print("=" * 78)
        print("（dry-run，加 --write 才真同步）")
        return 0

    print("=" * 78)
    print("同步后复核")
    print("=" * 78)
    bad = 0
    for label, deploy, inc17 in TARGETS:
        bad += verify_one(label, deploy, inc17)

    print()
    print("总结：%d 个文件不一致" % bad)
    return 0 if (bad == 0 and total_err == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
