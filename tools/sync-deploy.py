#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R370i · 同一个错犯第二次了：发布时又忘了同步部署目录的 `About/`。

## 事实

上一轮（R364）刚修过「部署副本 About 停在 1.5.1」，这轮发 1.5.6 时**又忘了**：
```
About\\About.xml 字节不一致（部署 7270 / 仓库 7120）
```

根因：我的发布脚本只负责「复制 DLL + 改 About + 搬更新记录」，**不含同步部署这一步**；
而 `final-check.py` 把它当独立判据查，于是每次都要事后补一刀。

## 这次的做法：把它变成发布流程的一步

1. 先把这次的差异同步掉；
2. 在**仓库里**放一个 `tools/sync-deploy.py`（只读判断 + 可选写入），
   以后发版跑 `python tools/sync-deploy.py --write` 就一步到位；
3. 顺手把「部署 vs 仓库该一致的文件」清单收在同一个脚本里，
   与 `final-check.py` 第 4 节共用同一份定义（避免两处漂移）。

⚠ 同步范围**只限** `About/` 与 `Assemblies/` ——
部署副本的语言目录是**另一套结构**（`LoadFolders.xml` + `v1.7\` 分层 / 13 万键），
整目录同步会互相覆盖。
"""
import os, shutil, hashlib, sys

BASE = r"E:\TAML\NudityMattersMoreOpinions-CN"
MOD = r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"

# 两边应当一致的文件（与 final-check.py 第 4 节同一份清单）
ITEMS = [
    r"About\About.xml",
    r"About\ModIcon.png",
    r"About\Preview.png",
    r"LoadFolders.xml",
    r"Assemblies\NMMOpinionsChineseUI.dll",
    r"Assemblies\GNH_NMM_Enhanced_ZH.dll",
]

write = '--write' in sys.argv


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


print(f"{'文件':<40} {'状态':<28} 处理")
print('-' * 90)
diff = 0
for rel in ITEMS:
    a = os.path.join(MOD, rel)
    b = os.path.join(BASE, rel)
    if not os.path.exists(b):
        print(f"{rel:<40} {'仓库缺':<28} 跳过")
        continue
    if not os.path.exists(a):
        print(f"{rel:<40} {'部署缺':<28} {'复制' if write else '（dry-run）'}")
        if write:
            os.makedirs(os.path.dirname(a), exist_ok=True)
            shutil.copy2(b, a)
        diff += 1
        continue
    if sha(a) == sha(b):
        print(f"{rel:<40} {'一致':<28} —")
        continue
    diff += 1
    print(f"{rel:<40} {'**不一致**':<28} {'同步' if write else '（dry-run）'}")
    if write:
        shutil.copy2(a, a + '.bak-sync')
        shutil.copy2(b, a)
        ok = sha(a) == sha(b)
        print(f"{'':<40} {'→ 同步后一致 ✅' if ok else '→ 仍不一致 ❌':<28}")

print('-' * 90)
print(f"差异 {diff} 项{'，已同步' if write and diff else ''}")
if not write and diff:
    print("\n要真正写入请加 --write")
