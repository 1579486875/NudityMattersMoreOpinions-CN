# -*- coding: utf-8 -*-
"""
正文索引对账（audit-text-index.py）—— 查出「译文整体错位一位 / 末条丢失 / 废话占位」这类问题。

为什么要这个脚本
----------------
原模组读正文的代码是（反编译 NudityMattersMore.dll 的 OpinionTextTranslator.Pick）：

    int num = Rand.Range(0, texts.Count);      // num ∈ [0, texts.Count-1]
    string result = texts[num];
    string key = $"NMM.Opinion.{def.defName}.{fieldName}.{num}";
    if (!Translator.CanTranslate(key)) return result;
    return Translator.Translate(key);

也就是说：**Keyed 里的下标 num 与 Def 字段里那个 List 的下标必须一一对应，且总数必须等于
List.Count**。多写一条不会生效（永远不会被抽到），少写一条就出现英文，下标整体偏移一位
则每一条都会显示成隔壁那条 —— 而日志里一个字都不会报。

而 List.Count 不是 XML 里写了几个 <li> 就算几个：若该 Def 带 ParentName，RimWorld 的
XmlInheritance 会把父模板的 <li> **拼接在列表前面**（父先子后），List.Count = 父条数 + 自己条数。
所以「某个 Def 该有多少条正文」必须靠**解析继承链**算出来，不能数文件。

本脚本只做只读对账，不改任何文件。用法：

    python tools/audit-text-index.py                # 全部检查
    python tools/audit-text-index.py --only situ    # 只看 Situational
    python tools/audit-text-index.py --verbose      # 逐条打印

退出码：0 = 全绿；1 = 发现问题。
"""
import os
import re
import sys
import io
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RIM_MODS = r"D:\steam\steamapps\common\RimWorld\Mods"

MOD_17 = os.path.join(RIM_MODS, "RJW-功能-裸体评价", "1.7")
MOD_16_OPINIONS = os.path.join(RIM_MODS, "NudityMattersMore_opinions")
MOD_16_BASE = os.path.join(RIM_MODS, "RJW-功能-裸体评价")

# 我们自己的 Keyed / DefInjected 根目录（1.7 生效的那套）
LANG_17 = os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified")
LANG_ROOT = os.path.join(REPO, "Languages", "ChineseSimplified")

# 运行时注入器认作「基类自带那条英文」的文本，见 OwnListInjector.InheritedBaseText
INHERITED_EN = "Its just there, what to say more?"
INHERITED_ZH = "就这样，还有什么好说的？"

# 关心的字段：字段名 → 是否是 List<string>
FIELDS = ("opinionTexts", "texts")

problems = []
notes = []


def fail(msg):
    problems.append(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="只查名字含该子串的 Def")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("=" * 74)
    print("正文索引对账 —— Keyed 下标 vs Def 字段实际 List.Count")
    print("=" * 74)
    print("  原模组(1.7)：%s" % MOD_17)
    print("  我们的 Keyed：%s" % LANG_17)

    if not os.path.isdir(MOD_17):
        print("找不到 1.7 原模组目录")
        return 1
    if not os.path.isdir(LANG_17):
        print("找不到 1.7 语言目录")
        return 1

    # ---------- 1. 解析原模组，建 Def 表 ----------
    print()
    print("【1】解析原模组 Defs（含继承链）")
    defs = parse_defs(MOD_17)
    print("      Def 元素 %d 个，其中抽象 %d 个、实际 %d 个"
          % (len(defs["all"]), len(defs["abstract"]), len(defs["concrete"])))

    # ---------- 2. 读我们的 Keyed ----------
    print()
    print("【2】读我们的 Keyed（NMM.Opinion.* 键）")
    keyed = read_keyed(LANG_17)
    print("      文件 %d 个、NMM.Opinion 键 %d 条、涉及 Def %d 个"
          % (keyed["files"], keyed["nkeys"], len(keyed["idx"])))

    # ---------- 3. 读我们的 DefInjected（索引式） ----------
    print()
    print("【3】读我们的 DefInjected（索引式 / 整列表）")
    definj = read_definjected(LANG_17)
    print("      索引式 %d 条、整列表 %d 条、涉及 Def %d 个"
          % (definj["nidx"], definj["nfull"], len(definj["idx"])))

    # ---------- 4. 对账 ----------
    print()
    print("【4】逐 Def 对账")
    ncheck = 0
    bad_count = []
    bad_range = []
    bad_extra = []
    bad_missing = []
    fake_placeholder = []
    not_in_keyed = []

    for name, info in sorted(defs["concrete"].items()):
        if args.only and args.only.lower() not in name.lower():
            continue
        for field, count in info["counts"].items():
            if count is None or count <= 0:
                continue
            ncheck += 1
            got = keyed["idx"].get((name, field), set())
            if not got:
                # 索引式 DefInjected 也算覆盖（游戏原生索引注入不需要 Keyed）
                got = definj["idx"].get((name, field), set())
                if not got:
                    not_in_keyed.append((name, field, count))
                    continue
            want = set(range(count))
            missing = want - got
            extra = got - want
            if extra:
                if len(extra) == len(got) and got == set(range(1, count + 1)):
                    bad_range.append((name, field, count, sorted(got)[:3], sorted(got)[-1]))
                else:
                    bad_extra.append((name, field, count, sorted(extra)[:5]))
            if missing:
                bad_missing.append((name, field, count, sorted(missing)[:5]))
            if count != len(got):
                bad_count.append((name, field, count, len(got)))
            # 第 0 条是不是那句废话，而该 Def 根本没有继承
            k0 = (name, field, 0)
            if keyed["text"].get(k0) == INHERITED_ZH and info["parents"] == []:
                fake_placeholder.append((name, field))

    print("      参与对账的 (Def, 字段) 组合：%d" % ncheck)
    if args.verbose:
        for name, info in sorted(defs["concrete"].items()):
            if args.only and args.only.lower() not in name.lower():
                continue
            for field, count in info["counts"].items():
                if count and count > 0:
                    print("        %-60s %-14s count=%d parents=%s"
                          % (name, field, count, info["parents"]))

    print()

    def report(title, rows, fmt, okmsg):
        if rows:
            msg = title % len(rows)
            fail(msg)
            print("  [问题] " + msg)
            for t in rows[:10]:
                print("        " + fmt % t)
            if len(rows) > 10:
                print("        …… 另有 %d 个未列出" % (len(rows) - 10))
        else:
            print("  [正常] " + okmsg)

    report("【整体错位】%d 个 Def 的索引是 1..N 而不是 0..N-1（每条都会显示成隔壁那条）：",
           bad_range, "%-56s %-13s 应有 %d 条(0..%d)，实际 %s..%d",
           "没有「索引整体偏移一位」的 Def")
    report("【越界】%d 个 Def 写了超出 List.Count 的下标（这些永远读不到）：",
           bad_extra, "%-56s %-13s count=%d 多余下标 %s",
           "没有越界下标")
    report("【缺失】%d 个 Def 有下标没写（会显示英文）：",
           bad_missing, "%-56s %-13s count=%d 缺 %s",
           "没有缺失下标")
    report("【废话占位】%d 个 Def 本身没有继承，却把第 0 条写成了那句废话（该 def 的每条译文都会后移一位）：",
           fake_placeholder, "%-56s %s", "没有「无继承却塞废话」的 Def")

    if not_in_keyed:
        notes.append("有 %d 个 (Def,字段) 组合完全没有译文（Keyed 与 DefInjected 都没有）"
                     % len(not_in_keyed))
        for t in not_in_keyed[:10]:
            print("        [无译文] %-50s %-13s count=%d" % t)
    else:
        print("  [正常] 所有 Def 都有译文")

    # ---------- 5. 反向：Keyed 里有、原模组里没有的 Def ----------
    print()
    print("【5】反向核对：Keyed 里的 Def 是否都真实存在")
    ghost = sorted({k[0] for k in keyed["idx"]} - set(defs["concrete"]))
    if ghost:
        msg = ("有 %d 个 Keyed 里的 Def 在原模组里找不到（悬空，译文无效）：%s"
               % (len(ghost), ghost[:8]))
        fail(msg)
        print("  [问题] " + msg)
    else:
        print("  [正常] Keyed 里的 Def 全部真实存在")

    # ---------- 汇总 ----------
    print()
    print("=" * 74)
    for n in notes:
        print("  [提示] " + n)
    if problems:
        print("结论：发现 %d 个问题" % len(problems))
        return 1
    print("结论：全绿")
    return 0


def parse_defs(root):
    """解析原模组全部 Defs，返回 {all, abstract, concrete}。

    concrete[name] = {"counts": {field: 实际 List.Count}, "parents": [父名...],
                      "cls": Class 属性, "file": 路径}
    List.Count 的算法：自己写的 <li> 数 + 父链上每一层贡献的 <li> 数（父先子后拼接）。
    """
    all_defs = {}
    raw = {}          # name -> {"field_lis": {field: n}, "parent": str|None, "cls":..., "file":...}
    abstracts = {}

    for sub in ("Defs", "Patches"):
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            for fn in filenames:
                if not fn.endswith(".xml"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    tree = ET.parse(p)
                except Exception:
                    continue
                # 递归遍历：Defs 下 def 是顶层子元素，Patches 下则嵌在
                # <Patch><Operation>…</Operation></Patch> 里，必须递归才找得到
                # （实测 Gonadz_Opinions_Patch.xml 注入了 18 个 NMM_Testicles_*，
                #   只扫 Defs 会把这 18 个 Keyed 键误判成悬空）。
                for el in tree.iter():
                    if not isinstance(el.tag, str):
                        continue
                    if el.find("defName") is None and not el.get("Name"):
                        continue
                    # 抽象模板用 Name="..." 标识（没有 defName），必须一并收进来，
                    # 否则 ParentName 链断掉、算不出「父模板贡献了几条」。
                    dn = el.find("defName")
                    declared = (dn.text or "").strip() if dn is not None else ""
                    named = (el.get("Name") or "").strip()
                    name = declared or named
                    if not name or name in all_defs:
                        continue
                    parent = el.get("ParentName")
                    is_abs = (el.get("Abstract") or "").lower() == "true"
                    counts = {}
                    for field in FIELDS:
                        fe = el.find(field)
                        if fe is not None:
                            counts[field] = len([x for x in fe if isinstance(x.tag, str)])
                    rec = {"field_lis": counts, "parent": parent,
                           "cls": el.get("Class") or el.tag, "file": p, "abstract": is_abs}
                    all_defs[name] = rec
                    if is_abs:
                        abstracts[name] = rec
                    else:
                        raw[name] = rec

    # 解析继承链，算实际条数
    def resolve(name, seen=None):
        if seen is None:
            seen = set()
        if name in seen:
            return {}
        seen.add(name)
        rec = all_defs.get(name)
        if rec is None:
            return {}
        base = {}
        if rec["parent"]:
            base = resolve(rec["parent"], seen)
        out = dict(base)
        for field, n in rec["field_lis"].items():
            out[field] = out.get(field, 0) + n
        return out

    concrete = {}
    for name, rec in raw.items():
        totals = resolve(name)
        chain = []
        cur = rec["parent"]
        while cur:
            chain.append(cur)
            nxt = all_defs.get(cur)
            cur = nxt["parent"] if nxt else None
        concrete[name] = {"counts": totals, "parents": chain,
                          "cls": rec["cls"], "file": rec["file"]}
    return {"all": all_defs, "abstract": abstracts, "concrete": concrete}


KEY_RE = re.compile(r"^NMM\.Opinion\.(.+)\.(opinionTexts|texts)\.(\d+)$")


def read_keyed(langdir):
    idx = defaultdict(set)
    text = {}
    nfiles = nkeys = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(langdir, "Keyed")):
        for fn in filenames:
            if not fn.endswith(".xml"):
                continue
            nfiles += 1
            p = os.path.join(dirpath, fn)
            try:
                tree = ET.parse(p)
            except Exception:
                continue
            for el in tree.getroot():
                if not isinstance(el.tag, str):
                    continue
                nkeys += 1
                m = KEY_RE.match(el.tag)
                if not m:
                    continue
                name, field, i = m.group(1), m.group(2), int(m.group(3))
                idx[(name, field)].add(i)
                text[(name, field, i)] = (el.text or "").strip()
    return {"idx": idx, "text": text, "files": nfiles, "nkeys": nkeys}


def read_definjected(langdir):
    idx = defaultdict(set)
    full = set()
    nidx = nfull = 0
    base = os.path.join(langdir, "DefInjected")
    if not os.path.isdir(base):
        return {"idx": idx, "full": full, "nidx": 0, "nfull": 0}
    for dirpath, dirnames, filenames in os.walk(base):
        for fn in filenames:
            if not fn.endswith(".xml"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                tree = ET.parse(p)
            except Exception:
                continue
            for el in tree.getroot():
                if not isinstance(el.tag, str):
                    continue
                for field in FIELDS:
                    m = re.match(r"^(.+)\.%s\.(\d+)$" % field, el.tag)
                    if m:
                        idx[(m.group(1), field)].add(int(m.group(2)))
                        nidx += 1
                        break
                    m = re.match(r"^(.+)\.%s$" % field, el.tag)
                    if m:
                        full.add((m.group(1), field))
                        nfull += 1
                        break
    return {"idx": idx, "full": full, "nidx": nidx, "nfull": nfull}


if __name__ == "__main__":
    sys.exit(main())
