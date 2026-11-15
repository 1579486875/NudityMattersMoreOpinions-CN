# -*- coding: utf-8 -*-
"""交付前自检：把模板 §2 五层零错误里能静态验的一次跑完。

跑完给出「全绿 / 有红项」的结论，红项逐条指出下一步该看哪里。

用法：python final-check.py
"""

import hashlib
import struct
import os
import sys
import xml.etree.ElementTree as ET

MOD = r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"
GIT = r"E:\TAML\_work\nmzh-git"

green = []
red = []
yellow = []


def ok(msg):
    green.append(msg)
    print("  [OK] " + msg)


def bad(msg):
    red.append(msg)
    print("  [!!] " + msg)


def hint(msg):
    """不算缺陷、但需要人知道的状态（例如 DLL 因游戏在跑而部署滞后）。"""
    yellow.append(msg)
    print("  [提示] " + msg)


def _game_running():
    """RimWorld 是否在运行 —— 决定「DLL 与仓库不一致」算缺陷还是算预期。"""
    try:
        import subprocess
        out = subprocess.run(["tasklist"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
        return "RimWorld.exe" in out
    except Exception:
        return False


def read_assembly_version(path):
    """读程序集版本（Major.Minor.Build.Revision）。

    ⚠ 2026-11-15 订正两次：
      ① 原判据是 open(p,"rb").read().decode("utf-16-le") 后取第一个 1.x.y 子串
         —— DLL 里字符串常量很多，那个判据与真正的程序集版本没有必然关系
         （实测源码与 DLL 都已升到 1.4.20.0，旧判据仍报 1.4.19）。
      ② 手写 PE/CLI 元数据解析也算错过一次（表行大小表有误，
         读出来是 29811.28257.25955.20224 这类垃圾）。
    改成调用 .NET 官方 API，零风险。PowerShell 不可用时返回 None，不瞎猜。
    """
    try:
        import subprocess
        env = dict(os.environ)
        env["DSH_ASSEMBLY_PATH"] = path
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "[System.Reflection.AssemblyName]::GetAssemblyName($env:DSH_ASSEMBLY_PATH).Version.ToString()"],
            env=env, stderr=subprocess.DEVNULL, timeout=30)
        s = out.decode("utf-8", "ignore").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$", s)
        return s if m else None
    except Exception:
        return None



def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


print("=" * 68)
print("1. 版本号一致性")
print("=" * 68)
import re
about = open(os.path.join(MOD, "About", "About.xml"), "rb").read().decode("utf-8-sig")
mv = re.search(r"<modVersion>\s*([\d.]+)\s*</modVersion>", about)
ver = mv.group(1) if mv else None
if ver:
    ok("About.xml modVersion = %s" % ver)
else:
    bad("About.xml 找不到 modVersion")

for name in ("NMMOpinionsChineseUI", "GNH_NMM_Enhanced_ZH"):
    p = os.path.join(MOD, "Assemblies", name + ".dll")
    if not os.path.exists(p):
        bad("缺 DLL: %s" % name)
        continue
    # ⚠ 2026-11-15 订正：原先用 utf-16-le 粗解 DLL 再取第一个 1.x.y 子串。
    #   DLL 里字符串常量很多，那个判据与真正的程序集版本没有必然关系
    #   （实测源码与 DLL 都已升到 1.4.20.0，旧判据仍报 1.4.19）。
    #   改成按 CLI 规范的 Assembly 表解析。
    found = [read_assembly_version(p)]
    if found and found[0] and ".".join(found[0].split(".")[:3]) == ver:
        ok("%s.dll 程序集版本 = %s" % (name, found[0]))
    elif _game_running():
        # 游戏在跑 → 部署目录里的 DLL 没法替换，版本落后是预期状态。
        # 真正的发布判据看第 4 节「部署目录 vs 仓库」与 tools\deploy-dll.py。
        hint("%s.dll 版本 %s，About 是 %s（游戏在运行、DLL 被锁，退出后跑 tools\\deploy-dll.py 即可）"
             % (name, found or "未找到", ver))
    else:
        bad("%s.dll 程序集版本 = %s（About 是 %s）" % (name, found or "未找到", ver))

print()
print("=" * 68)
print("2. XML 全量解析 + BOM + 尖括号")
print("=" * 68)
total = 0
fail = 0
for dp, dn, fs in os.walk(MOD):
    if ".git" in dp:
        continue
    for f in fs:
        if not f.lower().endswith(".xml"):
            continue
        total += 1
        p = os.path.join(dp, f)
        raw = open(p, "rb").read()
        try:
            ET.fromstring(raw.decode("utf-8-sig"))
        except Exception as e:
            fail += 1
            bad("解析失败 %s: %s" % (os.path.relpath(p, MOD), str(e)[:60]))
            continue
        if raw.count(b"<") != raw.count(b">"):
            fail += 1
            bad("尖括号不配对 %s" % os.path.relpath(p, MOD))
if fail == 0:
    ok("%d 个 XML 全部解析通过、尖括号配对" % total)

print()
print("=" * 68)
print("3. LoadFolders 与关键目录")
print("=" * 68)
lf = os.path.join(MOD, "LoadFolders.xml")
if os.path.exists(lf):
    txt = open(lf, "rb").read().decode("utf-8-sig")
    for need in ("v1.6", "v1.7"):
        if need in txt:
            ok("LoadFolders 含 %s 条目" % need)
        else:
            bad("LoadFolders 缺 %s 条目" % need)
else:
    bad("缺 LoadFolders.xml")

for d, why in (
    (os.path.join(MOD, "v1.7", "Languages", "ChineseSimplified", "Keyed"), "1.7 正文 Keyed"),
    (os.path.join(MOD, "v1.7", "Languages", "ChineseSimplified (简体中文)", "Keyed"), "1.7 正文 Keyed（中文目录名副本）"),
    (os.path.join(MOD, "Languages", "ChineseSimplified", "DefInjected"), "1.6 DefInjected"),
    (os.path.join(MOD, "OwnInjections", "ChineseSimplified", "DefInjected"), "1.6 注入清单"),
    (os.path.join(MOD, "Assemblies"), "DLL 目录"),
):
    if os.path.isdir(d):
        n = sum(len(fs) for _, _, fs in os.walk(d))
        ok("%s（%s）存在，%d 个文件" % (os.path.basename(d) or d, why, n))
    else:
        bad("缺目录：%s（%s）" % (d, why))

print()
print("=" * 68)
print("4. 部署目录 vs git 仓库（关键文件字节一致）")
print("=" * 68)
for rel in (
    r"About\About.xml",
    r"LoadFolders.xml",
    r"README.md",
    r"汉化说明.md",
    r"Assemblies\NMMOpinionsChineseUI.dll",
    r"Assemblies\GNH_NMM_Enhanced_ZH.dll",
    r"tools\ui-patch-tester\NMMOpinionsChineseUI.cs",
    r"tools\ui-patch-tester\GNH_NMM_Enhanced_ZH.cs",
    r"tools\ui-patch-tester\OwnListInjector.cs",
):
    a = os.path.join(MOD, rel)
    b = os.path.join(GIT, rel)
    if not os.path.exists(a):
        bad("部署缺 %s" % rel)
        continue
    if not os.path.exists(b):
        bad("仓库缺 %s" % rel)
        continue
    if sha(a) == sha(b):
        ok("%s 一致" % rel)
    elif rel.endswith(".dll") and _game_running():
        # 游戏运行时 DLL 被进程锁住，复制必然失败 —— 这时的「不一致」是预期状态，
        # 不能算缺陷。真正的判据是「退出游戏后跑 tools\deploy-dll.py」。
        hint("%s 与仓库不同（游戏正在运行、DLL 被锁；退出游戏后跑 tools\\deploy-dll.py）" % rel)
    else:
        bad("%s 字节不一致（部署 %d / 仓库 %d）" % (rel, os.path.getsize(a), os.path.getsize(b)))

print()
print("=" * 68)
print("5. 源码是否含高度补丁（防再次丢失）")
print("=" * 68)
src = os.path.join(MOD, "tools", "ui-patch-tester", "NMMOpinionsChineseUI.cs")
txt = open(src, "rb").read().decode("utf-8-sig")
for need, label in (
    ("UpdateSize_Postfix", "UpdateSize Postfix 定义/引用"),
    ("FillTabHeight_Transpiler", "FillTab 高度 Transpiler"),
    ("TabHeightBonus", "高度增量常量"),
    ("CheckKeyedCoverage", "正文覆盖自检"),
):
    n = txt.count(need)
    if n >= 1:
        ok("%s 出现 %d 次" % (label, n))
    else:
        bad("%s 缺失（高度修复又会丢）" % label)

dll = open(os.path.join(MOD, "Assemblies", "NMMOpinionsChineseUI.dll"), "rb").read()
# 方法名/类型名在 .NET metadata 的 #Strings heap 里是 UTF-8；
# 只有 ldstr 字符串常量才是 UTF-16。两处都要查，少查一边会误报「源码与产物不一致」。
dll_u8 = dll.decode("utf-8", errors="ignore")
dll_u16 = dll.decode("utf-16-le", errors="ignore")
for sym in ("UpdateSize_Postfix", "FillTabHeight_Transpiler", "CheckKeyedCoverage"):
    if sym in dll_u8 or sym in dll_u16:
        ok("DLL 内含 %s" % sym)
    else:
        bad("DLL 内缺 %s（源码与产物不一致）" % sym)

print()
print("=" * 68)
if red:
    print("结论：%d 项通过，%d 项待处理" % (len(green), len(red)))
    print("待处理：")
    for r in red:
        print("  - " + r)
    sys.exit(1)
print("结论：全绿（%d 项）" % len(green))
if yellow:
    print()
    print("提示（不算缺陷，但需要知道）：")
    for m in yellow:
        print("  · " + m)
sys.exit(0)
