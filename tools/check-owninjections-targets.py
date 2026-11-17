# -*- coding: utf-8 -*-
"""闸门：`OwnInjections/` 里的每个键，其 defName 必须在**独立版**的 Def 集合里存在。

## 为什么

`OwnInjections` 是「legacy 通道」——只在 `HasKeyedPath()` 为 false 时启用，也就是
**装了 1.5 / 1.6 的独立版 NMM**（那个 DLL 里没有 `OpinionTextTranslator`）时才走这条路。
它靠 `OwnListInjector` 在 `[StaticConstructorOnStartup]` 里反射拿 `List<string>` 再逐条写回。

**键的 defName 在 Def 集合里找不到时会走 `skipDef++` 静默跳过** ——
不是错误、不进 `loadErrors`、`Player.log` 里一个字都没有。玩家看到的是「这句还是英文」。

## 判据（与 `check-definjected-keys.py` 的区别）

| 闸门 | 覆盖范围 | defName 该在哪 |
|---|---|---|
| `check-definjected-keys.py` | `Languages/**/DefInjected/` | **全库**（原版 + 所有模组 + 工坊） |
| **本闸门** | `OwnInjections/**` | **只用独立版 NMM 自己的 Def 集合** |

两者的口径不同是有意的：`OwnInjections` 注入的是 NMM 自己定义的
`OpinionDef_SexPart` / `BodyPartOpinionDef`，它们的 defName 只可能来自独立版。

独立版的 `LoadFolders.xml` 是：
    <v1.5><li>Common</li><li>1.5</li></v1.5>
    <v1.6><li>Common</li><li>1.6</li></v1.6>
所以 1.5 视图 = `Common` + `1.5`，1.6 视图 = `Common` + `1.6`。

## 用法

    python tools/check-owninjections-targets.py
    python tools/check-owninjections-targets.py -v

退出码：0 = 两个视图下都 0 悬空；1 = 有悬空
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
OWN = os.path.join(REPO, 'OwnInjections', 'ChineseSimplified', 'DefInjected')
MOD = r'D:\steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions'


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
        for m in re.finditer(r'<(?:defName|Name)>\s*([^<\s]+)\s*</(?:defName|Name)>', t):
            s.add(m.group(1))
    return s


def main():
    verbose = '-v' in sys.argv
    if not os.path.isdir(OWN):
        print('❌ 找不到 %s' % OWN)
        return 1
    if not os.path.isdir(MOD):
        # 2026-11-17：环境缺失按 **skip** 处理（exit 0），不按失败处理。
        # 理由：这条闸门判的是「我们自己的键对不对」，而判据依赖另一台机器上
        # 装没装独立版 NMM。把它算失败，会让别人的 CI 永远红 —— 那不是代码问题。
        # 但也不能静默：必须把「本项未核」明确打出来，读报告的人一眼能看到。
        print('⏭ 跳过：找不到独立版 NMM')
        print('   %s' % MOD)
        print('   本项**未核**（不是通过）—— 装上独立版再跑一次才算数。')
        return 0

    files = collect(OWN)
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
    print('OwnInjections：%d 个文件 / %d 条键' % (len(files), len(keys)))

    common = defnames(collect(os.path.join(MOD, 'Common')))
    v15 = defnames(collect(os.path.join(MOD, '1.5')))
    v16 = defnames(collect(os.path.join(MOD, '1.6')))
    print('独立版 Def：Common %d / 1.5 %d / 1.6 %d' % (len(common), len(v15), len(v16)))

    bad = 0
    for label, bag in (('1.5 视图', common | v15), ('1.6 视图', common | v16)):
        miss = [k for k in keys if k[0] not in bag]
        uniq = sorted({k[0] for k in miss})
        print('\n=== %s：悬空 %d 条 / %d 个 defName ===' % (label, len(miss), len(uniq)))
        if miss:
            bad += len(miss)
            for dn, sub, f in miss[:12]:
                print('  ❌ %-48s (%s ← %s)' % (dn, sub, f))
            if len(miss) > 12:
                print('  …另有 %d 条' % (len(miss) - 12))
        else:
            print('  ✅ 全部 %d 条都在' % len(keys))
        if verbose and not miss:
            for dn, sub, f in keys[:5]:
                print('     %s → %s' % (dn, sub))

    print('\n' + '=' * 74)
    if bad:
        print('❌ 有悬空键 —— 那些译文在 1.5/1.6 下会被静默跳过')
        return 1
    print('✅ 两个视图下全部可达')
    return 0


if __name__ == '__main__':
    sys.exit(main())
