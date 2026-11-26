# -*- coding: utf-8 -*-
"""
1.6 侧完整性审计（audit-16.py）。

背景
----
我们的汉化包 LoadFolders.xml 是：

    <v1.6><li>/</li></v1.6>
    <v1.7><li>/</li><li>v1.7</li></v1.7>

即 1.6 只加载**根目录**：Languages/ + OwnInjections/。
1.7 加载根目录**再加** v1.7/。

而 1.6 的原模组只有 `NudityMattersMore_opinions`（RJW-功能-裸体评价 的 LoadFolders
里只有 <v1.7>，1.6 下不提供任何 Def），它的 Defs 全在 `Common/Defs`（1.6 目录只有
Assemblies/Source，没有 Defs）。

1.6 的正文翻译走**整列表注入**（OwnInjections/，由我们自己的 OwnListInjector 在
[StaticConstructorOnStartup] 里反射写回），因为：
  · 原模组的 opinionTexts / texts 都是裸的 List<string>，没有 [TranslationCanChangeCount]，
    整列表写在 Languages/ 下会被游戏拒绝；
  · 1.6 的 assembly 里也没有 OpinionTextTranslator.Pick（那是 1.7 合并版新增的 Keyed 读取），
    所以不需要 Keyed 那套 NMM.Opinion.* 键。

因此 1.6 侧要保证的只有一件事：**每个容器的 li 条数必须等于该 Def 字段的实际 List.Count**。
条数不符时 OwnListInjector 会整条跳过（宁可漏译，绝不串行错位）—— 也就是说错了会静默漏译，
必须靠本脚本提前查出来。

用法：python 工具/audit-16.py [--verbose]
"""
import os
import sys
import re
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MOD = r"D:\steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions"
LANG = os.path.join(REPO, "Languages", "ChineseSimplified")
OWN = os.path.join(REPO, "OwnInjections", "ChineseSimplified")

FIELDS = ("opinionTexts", "texts")
problems = []


def fail(m):
    problems.append(m)
    print("  [问题] " + m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("=" * 74)
    print("1.6 侧完整性审计")
    print("=" * 74)
    print("  原模组：%s" % MOD)
    print("  我们：  %s" % LANG)

    if not os.path.isdir(MOD):
        print("找不到 1.6 原模组")
        return 1

    print()
    print("【1】解析 1.6 原模组（LoadFolders 的 v1.6 分支只加载 Common/）")
    defs = parse_defs()
    print("      Def %d 个（抽象 %d）" % (len(defs["all"]), len(defs["abs"])))
    withtexts = {k: v for k, v in defs["all"].items() if any(c > 0 for c in v["counts"].values())}
    print("      其中有正文列表的 %d 个" % len(withtexts))

    print()
    print("【2】读我们的 OwnInjections 整列表（1.6 的正文主通道）")
    own = read_own()
    print("      文件 %d 个、容器 %d 个" % (own["files"], len(own["items"])))

    print()
    print("【3】逐容器核对条数")
    print("      判据与 OwnListInjector 保持一致：diff = 字段条数 - 清单条数")
    print("        diff == 0 → 无继承，逐一对应")
    print("        diff == 1 → 继承了一条（BaseSexPartOpinionDef 那句），注入器按偏移写")
    print("        其它     → 注入器整条跳过（静默漏译，必须在这里查出来）")
    bad = []
    ghost = []
    n_ok0 = n_ok1 = 0
    for (name, field), (lis, src) in sorted(own["items"].items()):
        info = defs["all"].get(name)
        if info is None:
            ghost.append((name, field, src))
            continue
        want = info["counts"].get(field)
        if want is None:
            ghost.append((name, field, src + " (字段不存在)"))
            continue
        diff = want - len(lis)
        if diff == 0:
            n_ok0 += 1
        elif diff == 1:
            n_ok1 += 1
        else:
            bad.append((name, field, want, len(lis), src))

    print("      无继承（diff=0）：%d 个；继承一条（diff=1）：%d 个" % (n_ok0, n_ok1))
    if bad:
        fail("有 %d 个容器条数差超过 1（这些会被注入器整条跳过 → 静默漏译）：" % len(bad))
        for t in bad[:15]:
            print("        %-56s %-13s 应有 %d 实有 %d  (%s)" % t)
    else:
        print("  [正常] 全部容器条数都在注入器可接受范围内")

    if ghost:
        fail("有 %d 个容器指向 1.6 原模组里不存在的 Def / 字段：" % len(ghost))
        for t in ghost[:15]:
            print("        %-56s %-13s %s" % t)
    else:
        print("  [正常] 没有悬空容器")

    print()
    print("【4】覆盖率：1.6 有正文的 Def 里，我们翻了多少")
    covered = set(k[0] for k in own["items"])
    missing = []
    for name, info in sorted(withtexts.items()):
        for field, cnt in info["counts"].items():
            if cnt > 0 and (name, field) not in own["items"]:
                missing.append((name, field, cnt, info["cls"]))
    if missing:
        bycls = defaultdict(int)
        for t in missing:
            bycls[t[3]] += 1
        print("  [提示] 有 %d 个 (Def,字段) 没有整列表注入，按类型：" % len(missing))
        for k, v in sorted(bycls.items(), key=lambda x: -x[1]):
            print("        %-46s %d" % (k, v))
        for t in missing[:12]:
            print("        %-56s %-13s 应有 %d 条  (%s)" % (t[0], t[1], t[2], t[3]))
    else:
        print("  [正常] 1.6 有正文的 Def 全部有整列表注入")

    print()
    print("【5】Languages/DefInjected 的悬空键（1.6）")
    di_bad = check_definjected(defs)
    if di_bad:
        fail("有 %d 个 DefInjected 键在 1.6 原模组里找不到：" % len(di_bad))
        for t in di_bad[:10]:
            print("        %s" % (t,))
    else:
        print("  [正常] DefInjected 键全部指向真实存在的 Def")

    print()
    print("=" * 74)
    if problems:
        print("结论：发现 %d 个问题" % len(problems))
        return 1
    print("结论：全绿")
    return 0


def parse_defs():
    """解析 1.6 实际加载的 Def：Common/Defs + Common/Patches（1.6 目录没有 Defs）。"""
    rec = {}
    for sub in ("Defs", "Patches"):
        base = os.path.join(MOD, "Common", sub)
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            for fn in fns:
                if not fn.endswith(".xml"):
                    continue
                p = os.path.join(dp, fn)
                try:
                    tree = ET.parse(p)
                except Exception:
                    continue
                for el in tree.iter():
                    if not isinstance(el.tag, str):
                        continue
                    d = el.find("defName")
                    nm = (d.text or "").strip() if d is not None else ""
                    if not nm:
                        nm = (el.get("Name") or "").strip()
                    if not nm or nm in rec:
                        continue
                    cnt = {}
                    for f in FIELDS:
                        fe = el.find(f)
                        if fe is not None:
                            cnt[f] = len([x for x in fe if isinstance(x.tag, str)])
                    rec[nm] = {"counts": cnt, "parent": el.get("ParentName"),
                               "cls": (el.get("Class") or el.tag).split(".")[-1],
                               "abs": (el.get("Abstract") or "").lower() == "true"}

    def resolve(n, seen=None):
        seen = seen or set()
        if n in seen:
            return {}
        seen.add(n)
        r = rec.get(n)
        if not r:
            return {}
        out = resolve(r["parent"], seen) if r["parent"] else {}
        for f, c in r["counts"].items():
            out[f] = out.get(f, 0) + c
        return out

    allr = {}
    absr = {}
    for n, r in rec.items():
        if r["abs"]:
            absr[n] = r
            continue
        allr[n] = {"counts": resolve(n), "cls": r["cls"], "parent": r["parent"]}
    return {"all": allr, "abs": absr}


KEY_RE = re.compile(r"^(.+)\.(opinionTexts|texts)$")


def read_own():
    items = {}
    nfiles = 0
    for dp, dn, fns in os.walk(OWN):
        for fn in fns:
            if not fn.endswith(".xml"):
                continue
            nfiles += 1
            p = os.path.join(dp, fn)
            try:
                tree = ET.parse(p)
            except Exception:
                continue
            for el in tree.getroot():
                if not isinstance(el.tag, str):
                    continue
                m = KEY_RE.match(el.tag)
                if not m:
                    continue
                lis = [x for x in el if isinstance(x.tag, str)]
                items[(m.group(1), m.group(2))] = (lis, os.path.relpath(p, OWN))
    return {"items": items, "files": nfiles}


def check_definjected(defs):
    bad = []
    base = os.path.join(LANG, "DefInjected")
    if not os.path.isdir(base):
        return bad
    for dp, dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith(".xml"):
                continue
            p = os.path.join(dp, fn)
            try:
                tree = ET.parse(p)
            except Exception:
                continue
            for el in tree.getroot():
                if not isinstance(el.tag, str):
                    continue
                name = el.tag.split(".")[0]
                if name not in defs["all"]:
                    bad.append((el.tag, os.path.relpath(p, LANG)))
    return bad


if __name__ == "__main__":
    sys.exit(main())
