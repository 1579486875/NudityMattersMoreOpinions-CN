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

⚠ 同步范围**只限** `About/`、`Assemblies/`、`LoadFolders.xml`、三份发布文档
（`README.md` / `汉化说明.md` / `LICENSE`）与 `Languages/` ——
语言目录归 `tools/sync-deploy-all.py` 管（它要按三棵树逐文件比对）。

## 2026-11-16 订正（审查 D-01）

旧版 `MOD` 是**单个路径**，只指向 1.7 主安装。于是「1.6 引擎副本」从来没被
任何同步 / 校验环节覆盖过 —— 实测它的 About 停在 v1.4.23、语言树缺 105 个文件。
现在改成 `TARGETS` 列表，两个环境一起同步、一起复核。
"""
import os, shutil, hashlib, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (显示名, 部署路径) —— 加环境就往这里加一行
# 2026-11-17 加：备份目录要落在仓库里，不能落在部署目录里（见下面 sync 里那段注释）。
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    ("1.7 主安装", r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"),
    ("1.6 引擎副本", r"D:\RimWorld-1.6\Mods\裸体评价更多看法-汉化修复"),
]

# 两边应当一致的文件（与 final-check.py 第 4 节同一份清单）
ITEMS = [
    r"About\About.xml",
    r"About\ModIcon.png",
    r"About\Preview.png",
    r"LoadFolders.xml",
    r"Assemblies\NMMOpinionsChineseUI.dll",
    r"Assemblies\GNH_NMM_Enhanced_ZH.dll",
    # 2026-11-16 加（审查 D-09）：这三份是发布内容 —— 玩家从工坊订阅后
    # 能在模组目录里直接读到。此前它们不受任何检查，实测仓库 / 1.7 / 1.6
    # 三份各不相同（README 三个 hash：88c78b08 / 9ce855bc / d51fe66d）。
    r"README.md",
    r"汉化说明.md",
    r"LICENSE",
]

write = '--write' in sys.argv


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def sync_target(label, mod):
    print("=" * 90)
    print("目标：%s" % label)
    print("    %s" % mod)
    print("=" * 90)
    print(f"{'文件':<40} {'状态':<28} 处理")
    print('-' * 90)
    diff = 0
    if not os.path.isdir(mod):
        print("  ❌ 部署目录不存在，整目标跳过")
        return 1

    for rel in ITEMS:
        a = os.path.join(mod, rel)     # 部署侧
        b = os.path.join(BASE, rel)    # 仓库侧
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
            # 2026-11-17 改：备份**不再写进部署目录**。
            # 旧写法 `shutil.copy2(a, a + '.bak-sync')` 会在
            # `Mods\<模组>\Assemblies\` 里堆一串 `.bak-sync` / `.bak-r*`。
            # 2026-11-17 实测：1.7 环境 6 个、1.6 环境 2 个，共 8 个文件约 250 KB。
            # 它们不会被游戏加载（RimWorld 只认 `*.dll`），但属于**交付目录里的开发过程垃圾**：
            # 玩家打开目录会以为那是模组文件，而且 `check-deploy-parity.py` 明确把 `.bak*`
            # 从「多余文件」里豁免掉了，于是它们可以在里面躺几个月没人发现。
            # 现在统一落到仓库 `_backup/deploy-sync/<环境>/`，回滚照样能用。
            _bdir = os.path.join(REPO, '_backup', 'deploy-sync',
                                 _label.replace(' ', '_').replace('/', '_'))
            os.makedirs(_bdir, exist_ok=True)
            shutil.copy2(a, os.path.join(_bdir, rel.replace('\\', '_').replace('/', '_')))
            shutil.copy2(b, a)
            ok = sha(a) == sha(b)
            print(f"{'':<40} {'→ 同步后一致 ✅' if ok else '→ 仍不一致 ❌':<28}")

    print('-' * 90)
    print(f"差异 {diff} 项{'，已同步' if write and diff else ''}")
    print()
    return diff


total = 0
for _label, _mod in TARGETS:
    total += sync_target(_label, _mod)

print("=" * 90)
print(f"两个目标合计差异 {total} 项")
if not write and total:
    print("要真正写入请加 --write")


# 2026-11-16 加：有差异就让调用方知道（原先只 print、永远 exit 0）
#   · dry-run 有差异 → exit 1（提醒「该同步了」）
#   · --write 后仍有差异 → exit 1（同步失败）
sys.exit(1 if total else 0)
