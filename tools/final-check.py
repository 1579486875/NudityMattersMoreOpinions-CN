# -*- coding: utf-8 -*-
"""交付前自检：把模板 §2 五层零错误里能静态验的一次跑完。

跑完给出「全绿 / 有红项」的结论，红项逐条指出下一步该看哪里。

用法：python final-check.py
"""

import hashlib
import os
import sys
import xml.etree.ElementTree as ET

MOD = r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"
GIT = r"E:\TAML\_work\nmzh-git"

green = []
red = []


def ok(msg):
    green.append(msg)
    print("  [OK] " + msg)


def bad(msg):
    red.append(msg)
    print("  [!!] " + msg)


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
    t = open(p, "rb").read().decode("utf-16-le", errors="ignore")
    found = re.findall(r"1\.\d+\.\d+", t)[:1]
    if found and found[0] == ver:
        ok("%s.dll 程序集版本 = %s" % (name, found[0]))
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
sys.exit(0)
