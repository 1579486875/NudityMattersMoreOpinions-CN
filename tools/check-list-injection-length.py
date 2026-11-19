# -*- coding: utf-8 -*-
"""闸门：OwnInjections 的「整列表注入」，译文条数是否等于原模组。

## 为什么需要这道闸门

模板 §B.13「DefInjected 的整列表注入：条数写少一条，就静默丢一条」：

    反编译 `Verse.DefInjectionPackage`：
      · AddDataFromFile —— HasElements 的节点收集所有 <li> 的文本
      · TryAddFullListInjection → CheckErrors：只查「key 含点 / 不重复 /
        不同时替换整表与单项」，**完全不检查列表长度**

    → 译文条目少于原文 = **直接丢掉末尾几条**，日志里没有任何提示。

本仓库的 `OwnInjections/` 就是整列表注入（5,214 个容器）。
原来的 `check-owninjections-targets.py` 只查「键指向的 defName 存不存在」，
**不查条数** —— 于是这条静默丢失路径一直没人守。

## 判据

对 `OwnInjections/ChineseSimplified/DefInjected/` 里每个 `<DefName.field>` 容器：

  ① 在原模组 `NudityMattersMore_opinions` 的 Def 里找到同名 defName 与同名字段；
  ② 比较两侧的**列表长度**（原模组按 `<li>` 数，译文按 `<li>` 数）；
  ③ **少于原文 → 失败**（B.13 会静默丢末尾）；
     多于原文 → 只警告（多出的会被游戏忽略，不至于丢内容）；
     对不上 defName/字段 → 只警告（可能是 1.7 合并版新增的字段）。

## 退出码

0 = 没有「译文少于原文」的容器；1 = 存在。

用法：
    python tools/check-list-injection-length.py
    python tools/check-list-injection-length.py --detail    # 连一致的也打印
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 原模组（两个版本共用 Common\ 下的 Defs）
ORIG_CANDIDATES = [
    r'D:\steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions',
    r'D:\RimWorld-1.6\Mods\NudityMattersMore_opinions',
]

OWN = os.path.join(REPO, 'OwnInjections', 'ChineseSimplified', 'DefInjected')

# 只认两版共用的 Common\ —— 1.5/1.6 子目录里的 Def 是版本专属，不参与比对
SKIP_VERSION_DIRS = ('\\1.5\\', '\\1.6\\', '\\1.7\\', '\\1.4\\', '\\1.3\\')


def pick_orig():
    for p in ORIG_CANDIDATES:
        if os.path.isdir(p):
            return p
    return None


def orig_counts(root_dir):
    """defName → {字段名: 列表长度}。"""
    out = {}
    for b, _, fs in os.walk(root_dir):
        low = b.replace('/', '\\').lower()
        if any(v in low for v in SKIP_VERSION_DIRS):
            continue
        for f in fs:
            if not f.endswith('.xml'):
                continue
            p = os.path.join(b, f)
            try:
                r = ET.parse(p).getroot()
            except Exception:
                continue
            for d in r:
                dn = d.find('defName')
                if dn is None or not (dn.text or '').strip():
                    continue
                fields = {}
                for ch in d:
                    if len(ch) and ch.tag != 'defName':
                        fields[ch.tag] = len(ch)
                out[dn.text.strip()] = (fields, f)
    return out


def trans_counts(own_dir):
    """defName → {字段名: (条数, 文件名)}。"""
    out = {}
    for b, _, fs in os.walk(own_dir):
        for f in fs:
            if not f.endswith('.xml'):
                continue
            t = open(os.path.join(b, f), 'rb').read().decode('utf-8-sig', errors='ignore')
            for m in re.finditer(r'<([A-Za-z_][\w\-]*)\.([A-Za-z_][\w\-]*)>([\s\S]*?)</\1\.\2>', t):
                dn, fld, body = m.group(1), m.group(2), m.group(3)
                out.setdefault(dn, {})[fld] = (len(re.findall(r'<li>', body)), f)
    return out


def main():
    detail = '--detail' in sys.argv

    orig_dir = pick_orig()
    if not orig_dir:
        print('⚠ 找不到原模组 NudityMattersMore_opinions，跳过本闸门')
        print('   查找过：' + ' / '.join(ORIG_CANDIDATES))
        return 0

    if not os.path.isdir(OWN):
        print('❌ 找不到 %s' % OWN)
        return 1

    o = orig_counts(orig_dir)
    tr = trans_counts(OWN)
    print('原模组：%s' % orig_dir)
    print('  原模组 def：%d 个；译文容器 def：%d 个' % (len(o), len(tr)))

    same = short = longer = unk = 0
    shorts, longers = [], []
    for dn, fields in sorted(tr.items()):
        if dn not in o:
            unk += 1
            continue
        ofields, srcfile = o[dn]
        for fld, (tn, tf) in fields.items():
            on = ofields.get(fld)
            if on is None:
                unk += 1
                continue
            if tn == on:
                same += 1
                if detail:
                    print('  ✅ %-50s %-16s %d' % (dn[:50], fld, on))
            elif tn < on:
                short += 1
                shorts.append((dn, fld, on, tn, srcfile, tf))
            else:
                longer += 1
                longers.append((dn, fld, on, tn, srcfile, tf))

    print()
    print('=== 结果 ===')
    print('  一致        : %d' % same)
    print('  ❌ 译少于原 : %d  ← §B.13 会静默丢掉末尾' % short)
    print('  ⚠ 译多于原 : %d  ← 多出的会被游戏忽略' % longer)
    print('  无法对应    : %d  ← 多半是 1.7 合并版新增字段' % unk)

    if shorts:
        print()
        print('  --- 译文少于原文（必须修）---')
        for dn, fld, on, tn, sf, tf in shorts[:25]:
            print('    %-44s %-14s 原 %3d → 译 %3d   (原 %s / 译 %s)'
                  % (dn[:44], fld, on, tn, sf[:20], tf[:20]))
        if len(shorts) > 25:
            print('    …另有 %d 条' % (len(shorts) - 25))
    if longers:
        print()
        print('  --- 译文多于原文（提示，不拦）---')
        for dn, fld, on, tn, sf, tf in longers[:10]:
            print('    %-44s %-14s 原 %3d → 译 %3d' % (dn[:44], fld, on, tn))

    return 1 if short else 0


if __name__ == '__main__':
    sys.exit(main())
