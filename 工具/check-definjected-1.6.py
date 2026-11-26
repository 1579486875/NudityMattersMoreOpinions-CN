# -*- coding: utf-8 -*-
"""闸门：**根目录**的 `Languages/ChineseSimplified/DefInjected/` 键，在 **1.6 环境**下是否可达。

## 为什么单独做一个

`check-definjected-keys.py` 用的是**单一全库索引**（1.7 的 `Data` + `Mods` + 工坊）。
那对 1.7 是够的，但**对 1.6 是过宽的**：

某个 def 只存在于「1.7 才有的模组」里时，全库索引会认为这个键「找到了」，
而 1.6 那边那个模组根本不在场 —— 键在 1.6 下悬空，逐条报 `Found no …`（只进
`loadErrors`，`Player.log` 里一个字都没有）。

而 NMM 的 `LoadFolders.xml` 是：

    <v1.5><li>/</li></v1.5>
    <v1.6><li>/</li></v1.6>
    <v1.7><li>/</li><li>v1.7</li></v1.7>

→ **根目录同时被 1.5 / 1.6 / 1.7 加载**（模板 §B.18.4：根目录 = 两版共用不是免责条款，是义务）。

## 判据

把根目录每个键的第一段（defName）拿去 **1.6 环境的 def 集合**里查：

    D:\\RimWorld-1.6\\Data
    D:\\RimWorld-1.6\\Mods
    独立版 NMM 的 Common + 1.6    ← 它自己的 OpinionDef / InteractionDef

`v1.7/` 目录下的键**不查** —— 它们只被 1.7 加载，对 1.6 没有义务。

## 用法

    python 工具/check-definjected-1.6.py
    python 工具/check-definjected-1.6.py -v

退出码：0 = 0 悬空（或 1.6 环境不存在时 skip）；1 = 有悬空
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS_16 = [r'D:\RimWorld-1.6\Data', r'D:\RimWorld-1.6\Mods']
NMM_STANDALONE = r'D:\steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions'

DEFNAME = re.compile(r'<(?:defName|Name)>\s*([^<\s]+)\s*</(?:defName|Name)>')


def collect(d):
    out = []
    for b, _, fs in os.walk(d):
        for f in fs:
            if f.lower().endswith('.xml'):
                out.append(os.path.join(b, f))
    return out


def defnames(paths):
    s = set()
    for f in paths:
        try:
            t = open(f, 'rb').read().decode('utf-8-sig', errors='ignore')
        except Exception:
            continue
        for m in DEFNAME.finditer(t):
            s.add(m.group(1))
    return s


def main():
    verbose = '-v' in sys.argv
    if not os.path.isdir(ROOTS_16[0]):
        print('⏭ 跳过：没有 1.6 引擎副本（%s）' % ROOTS_16[0])
        print('   本项**未核**（不是通过）。')
        return 0

    # 只扫根目录的那一份（不含 v1.7 子树）
    langdir = os.path.join(REPO, 'Languages', 'ChineseSimplified', 'DefInjected')
    if not os.path.isdir(langdir):
        print('❌ 找不到 %s' % langdir)
        return 1
    files = collect(langdir)
    keys = []
    for f in files:
        sub = os.path.basename(os.path.dirname(f))
        try:
            root = ET.parse(f).getroot()
        except Exception as e:
            print('  !! %s: %s' % (os.path.basename(f), e))
            continue
        for el in root:
            keys.append((el.tag.split('.')[0], sub, os.path.basename(f)))
    print('根目录 DefInjected：%d 个文件 / %d 条键' % (len(files), len(keys)))

    bag = defnames(collect(ROOTS_16[0]))
    n_data = len(bag)
    for r in ROOTS_16[1:]:
        bag |= defnames(collect(r))
    n_mods = len(bag) - n_data
    if os.path.isdir(NMM_STANDALONE):
        for sub in ('Common', '1.6'):
            bag |= defnames(collect(os.path.join(NMM_STANDALONE, sub)))
    print('1.6 环境 defName：Data %d + Mods %d + 独立版 NMM = 合计 %d'
          % (n_data, n_mods, len(bag)))

    miss = [k for k in keys if k[0] not in bag]
    print('\n=== 1.6 下悬空：%d 条 / %d 个 defName ==='
          % (len(miss), len({k[0] for k in miss})))
    if miss:
        from collections import Counter
        by = Counter(k[1] for k in miss)
        for sub, n in by.most_common():
            uniq = sorted({k[0] for k in miss if k[1] == sub})
            print('  ❌ %-52s %d 条 / %d 个 defName' % (sub, n, len(uniq)))
            for d in uniq[:6]:
                print('       %s' % d)
            if len(uniq) > 6:
                print('       …另有 %d 个' % (len(uniq) - 6))
    else:
        print('  ✅ 全部 %d 条都能在 1.6 环境里找到' % len(keys))

    if verbose and not miss:
        for dn, sub, f in keys[:6]:
            print('     %s → %s' % (dn, sub))

    print('\n' + '=' * 74)
    if miss:
        print('❌ 根目录有 %d 条键在 1.6 下悬空 —— 那些译文在 1.6 下会静默不生效' % len(miss))
        return 1
    print('✅ 根目录全部可达（1.6 环境）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
