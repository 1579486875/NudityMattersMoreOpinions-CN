# -*- coding: utf-8 -*-
"""
把仓库里的两个 DLL 部署到 Mods 目录 —— 但只在游戏没运行时。

为什么单独写这个：
  两个 DLL 在游戏运行时被进程锁住，Copy-Item 会抛
  「The process cannot access the file ... because it is being used by another process」。
  而且强行半套部署（新 About + 旧 DLL）比不部署更难排查，所以这里默认拒绝。

用法：
    python tools/deploy-dll.py           # 游戏在跑就只报告，不动
    python tools/deploy-dll.py --force   # 游戏在跑也硬上（不推荐）
"""
import os
import sys
import shutil
import hashlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 2026-11-16 改：原先硬编码 E:\TAML\_work\nmzh-git（旧 clone）
DEPLOY = r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"
DLLS = ["NMMOpinionsChineseUI.dll", "GNH_NMM_Enhanced_ZH.dll"]
EXTRA = [
    ("README.md", "README.md"),
    ("汉化说明.md", "汉化说明.md"),
    ("About/About.xml", "About/About.xml"),
    ("LoadFolders.xml", "LoadFolders.xml"),
]


def game_running():
    """用 tasklist 查 RimWorld 进程。"""
    try:
        import subprocess
        out = subprocess.run(["tasklist"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
        return "RimWorld.exe" in out
    except Exception:
        return False


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    force = "--force" in sys.argv
    running = game_running()
    print("RimWorld 进程：" + ("运行中" if running else "未运行"))
    if running and not force:
        print()
        print("⚠ 游戏正在运行，DLL 被锁。请先完全退出游戏，再跑一次本脚本。")
        print("  （文档类文件不受影响，下面照样会同步。）")

    for src_rel, dst_rel in EXTRA:
        s = os.path.join(REPO, src_rel)
        d = os.path.join(DEPLOY, dst_rel)
        if not os.path.exists(s):
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        print("  OK  %-22s %s" % (dst_rel, sha(d)[:12]))

    ok = fail = 0
    for fn in DLLS:
        s = os.path.join(REPO, "Assemblies", fn)
        d = os.path.join(DEPLOY, "Assemblies", fn)
        if not os.path.exists(s):
            print("  缺失（仓库）：" + s)
            continue
        if running and not force:
            print("  跳过 %-26s （游戏占着）" % fn)
            continue
        try:
            shutil.copy2(s, d)
            same = sha(s) == sha(d)
            print("  %s %-26s %s" % ("OK " if same else "ERR", fn, sha(d)[:12]))
            ok += 1 if same else 0
            fail += 0 if same else 1
        except Exception as e:
            print("  失败 %-26s %s" % (fn, e))
            fail += 1

    print()
    print("DLL 部署成功 %d / 失败 %d" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
