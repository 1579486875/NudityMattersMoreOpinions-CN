#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bump-version.py · 一次改齐「版本号三处」：About + 两个源文件的 assembly 版本。

## 为什么需要它

模板 §1.1 要求版本号三处一致，而本仓的实际做法是
「csproj 不声明版本，版本由源码里的 `[assembly: AssemblyVersion]` 提供」。
于是每发一版要手动改 **7 处**：

| 文件 | 要改的 |
|---|---|
| `About/About.xml` | `<modVersion>` |
| `工具/ui-patch-tester/NMMOpinionsChineseUI.cs` | `AssemblyVersion` / `AssemblyFileVersion` / `AssemblyInformationalVersion` |
| `工具/ui-patch-tester/GNH_NMM_Enhanced_ZH.cs` | 同上 3 处 |

**这件事我已经漏过两次**（1.5.5 时才发现 DLL 停在 1.5.1；1.5.6 时才发现 DLL 停在 1.5.5）。
漏了的后果不是崩，而是「资源管理器里看到的版本与工坊页面不一致」——
排查时极易误判「装的是不是最新版」。所以做成脚本。

## 用法

    python 工具/bump-version.py 1.5.6            # 改到 1.5.6（先打印计划，不写）
    python 工具/bump-version.py 1.5.6 --write    # 真写

脚本会**自动读出当前版本**，不需要手填旧值；改完打印三处结果供核对。
"""
import os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AB = os.path.join(BASE, 'About', 'About.xml')
SRCS = [
    os.path.join(BASE, '工具', 'ui-patch-tester', 'NMMOpinionsChineseUI.cs'),
    os.path.join(BASE, '工具', 'ui-patch-tester', 'GNH_NMM_Enhanced_ZH.cs'),
]

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)
new = sys.argv[1].strip()
write = '--write' in sys.argv
if not re.fullmatch(r'\d+\.\d+(\.\d+)?', new):
    print(f"版本号格式不对：{new}")
    sys.exit(2)

changes = []

# ── About ──
raw = open(AB, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
t = raw.decode('utf-8-sig')
m = re.search(r'<modVersion>\s*([\d.]+)\s*</modVersion>', t)
assert m, 'About 里找不到 modVersion'
old_about = m.group(1)
if old_about != new:
    changes.append((os.path.relpath(AB, BASE), f'<modVersion> {old_about} → {new}'))
    t = t.replace(m.group(0), f'<modVersion>{new}</modVersion>', 1)
    if write:
        open(AB, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + t.encode('utf-8'))

# ── 两个源文件 ──
for p in SRCS:
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    t = raw.decode('utf-8-sig')
    got = re.findall(r'Assembly(?:File|Informational)?Version\("([\d.]+)"\)', t)
    olds = sorted(set(got))
    if olds == [new, new + '.0'] or olds == [f'{new}.0', new] or (len(olds) <= 2 and all(o.startswith(new) for o in olds)):
        continue
    n = 0
    def repl(mm):
        global n
        n += 1
        kind = mm.group(1) or ''      # '' / 'File' / 'Informational'（只有一个捕获组）
        val = new if kind == 'Informational' else f'{new}.0'
        return f'Assembly{kind}Version("{val}")'
    t2 = re.sub(r'Assembly(File|Informational)?Version\("[\d.]+"\)', repl, t)
    if t2 != t:
        changes.append((os.path.relpath(p, BASE), f'程序集版本 {olds} → {new}'))
        if write:
            open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + t2.encode('utf-8'))

print(f"目标版本：{new}")
if not changes:
    print("三处已经是这个版本，不需要改。")
    sys.exit(0)
for f, what in changes:
    print(f"  {f}: {what}")
print(f"\n共 {len(changes)} 处待改" + ("（已写入）" if write else "，加 --write 才会真改"))
if write:
    print("\n⚠ 别忘了重编译两个 DLL，然后跑 工具/sync-deploy.py --write")
