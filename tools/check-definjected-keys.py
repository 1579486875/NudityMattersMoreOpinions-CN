# -*- coding: utf-8 -*-
"""检查 NMM 汉化包的 DefInjected 键是否悬空 / 是否重复（本轮新增的独立取证）。

## 为什么要这个

模板 §B.12 第 2 条：
> 「日志里 `doesn't correspond to any def type` 出现 0 次 → 所有 DefInjected 目录名都对」
> 是**假判据** —— 那串是 `LoadedLanguage.loadErrors` 的内容，**`loadErrors` 从不写进 Player.log**。

同理，「键的 defName 在 def 数据库里找不到」也只进 `loadErrors`，
玩家看到的是「这条译文不生效」，日志里一个字都没有。

所以必须**静态对账**：把我们的每个 DefInjected 键的第一段拿去环境里的 def 集合里查。

## 两种缺陷

| 类型 | 判据 | 后果 |
|---|---|---|
| **悬空键** | 键的第一段 defName 在当前环境的 def 集合里不存在 | 那条译文永不生效（静默） |
| **重复键** | 同一个键在同一个 Def 类型目录下出现两次以上 | 后者覆盖前者（静默） |

## 版本段过滤（模板 §24）

路径里出现 `1.3` / `1.4` / `1.5` 的目录**排除**（游戏不加载）；
`1.6` / `1.7` / 无版本段 → **保留**。

## 用法

    python tools/check-definjected-keys.py            # 报告
    python tools/check-definjected-keys.py --verbose  # 列出每条悬空键
"""
import os
import re
import sys
import glob
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠ 2026-11-17 订正（本轮）：第一版只扫了 Mods + workshop，**漏了原版与 DLC 的 `Data\\`**，
# 于是 `Wait` / `Wait_Combat` / `Wait_MaintainPosture` 三个原版 JobDef
# （定义在 `Data\\Core\\Defs\\JobDefs\\Jobs_Misc.xml`）被误报成「悬空键」。
# 判据必须覆盖四个来源：原版 Core、DLC（Royalty/Ideology/Biotech/Anomaly/Odyssey）、
# 本地 Mods、工坊 workshop。少任何一个都会产出假阴性。
ROOTS = [r"D:\steam\steamapps\common\RimWorld\Data",
         r"D:\steam\steamapps\common\RimWorld\Mods",
         r"D:\steam\steamapps\workshop\content\294100"]

# 我们的 DefInjected 根（两个语言目录 + v1.7 树）
TREES = [
    os.path.join(REPO, "Languages", "ChineseSimplified", "DefInjected"),
    os.path.join(REPO, "Languages", "ChineseSimplified (简体中文)", "DefInjected"),
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified", "DefInjected"),
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified (简体中文)", "DefInjected"),
]

SKIP_VER = re.compile(r"[\\/](1\.[0-5])[\\/]")


def collect_defnames(root):
    """扫一个目录下所有 XML，收集 <defName> 值（排除 1.0–1.5 版本段）。"""
    out = set()
    for dp, dn, fns in os.walk(root):
        if SKIP_VER.search(dp + os.sep):
            continue
        for f in fns:
            if not f.endswith(".xml"):
                continue
            p = os.path.join(dp, f)
            try:
                raw = open(p, "rb").read()
                if b"<defName>" not in raw:
                    continue
                t = raw.decode("utf-8-sig", errors="ignore")
            except Exception:                    # noqa: BLE001
                continue
            for m in re.finditer(r"<defName>\s*([^<\s]+)\s*</defName>", t):
                out.add(m.group(1))
    return out


def collect_keys(tree):
    """返回 [(typeDir, key, file)]。"""
    rows = []
    if not os.path.isdir(tree):
        return rows, []
    for dp, dn, fns in os.walk(tree):
        rel = os.path.relpath(dp, tree)
        type_dir = rel.split(os.sep)[0] if rel != "." else ""
        for f in fns:
            if not f.endswith(".xml"):
                continue
            p = os.path.join(dp, f)
            try:
                r = ET.fromstring(open(p, "rb").read().decode("utf-8-sig"))
            except Exception as e:               # noqa: BLE001
                print("  ⚠ XML 解析失败 %s: %s" % (p, e))
                continue
            for e in r.iter():
                if e.tag in ("li", "LanguageData"):
                    continue
                rows.append((type_dir, e.tag, os.path.relpath(p, tree)))
    return rows, []


def main():
    verbose = "--verbose" in sys.argv

    print("=" * 74)
    print("收集环境里的 def 名（Mods + workshop，排除 1.0–1.5）")
    print("=" * 74)
    all_defs = set()
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        n0 = len(all_defs)
        all_defs |= collect_defnames(root)
        print("  %s：+%d（累计 %d）" % (root, len(all_defs) - n0, len(all_defs)))

    print()
    print("=" * 74)
    print("检查我们的 DefInjected")
    print("=" * 74)

    total_keys = 0
    dangling = []
    dup = []
    per_tree = []

    for tree in TREES:
        if not os.path.isdir(tree):
            print("  （不存在）%s" % tree)
            continue
        rows, _ = collect_keys(tree)
        seen = {}
        d_here = []
        for type_dir, key, f in rows:
            total_keys += 1
            first = key.split(".")[0]
            if first not in all_defs:
                d_here.append((type_dir, key, f))
            k2 = (type_dir, key)
            seen.setdefault(k2, []).append(f)
        for k2, fs in seen.items():
            if len(fs) > 1:
                dup.append((k2[0], k2[1], fs))
        print("  %-56s 键 %6d  悬空 %3d" %
              (os.path.relpath(tree, REPO), len(rows), len(d_here)))
        dangling += d_here
        per_tree.append((tree, len(rows), len(d_here)))

    print()
    print("=" * 74)
    print("结果")
    print("=" * 74)
    print("  总键数：%d" % total_keys)
    print("  悬空键：%d" % len(dangling))
    print("  重复键：%d" % len(dup))

    if dangling:
        print()
        print("  --- 悬空键（前 20 条）---")
        for type_dir, key, f in dangling[:20]:
            print("    [%s] %s    (%s)" % (type_dir, key, f))
        if len(dangling) > 20:
            print("    …另有 %d 条" % (len(dangling) - 20))
    if dup:
        print()
        print("  --- 重复键（前 10 条）---")
        for type_dir, key, fs in dup[:10]:
            print("    [%s] %s  in %s" % (type_dir, key, fs))
    if verbose:
        print()
        print("  --- 全部悬空键 ---")
        for type_dir, key, f in dangling:
            print("    [%s] %s    (%s)" % (type_dir, key, f))

    return 0 if (not dangling and not dup) else 1


if __name__ == "__main__":
    sys.exit(main())
