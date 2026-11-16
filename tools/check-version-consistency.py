#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-version-consistency.py · NMM 汉化包的版本号「五处一致 + 两环境一致」

## 为什么要它

2026-11-16 上一轮（R348）修过一条同类缺陷：
**About 已到 1.5.4，两个 DLL 的 `AssemblyVersion` 还停在 1.5.1。**
再往前，`R364` 也修过「部署副本 About 停在 1.5.1」。

同一个错已经犯过两次，所以把它变成闸门 —— 判据不看人记不记得，看数字。

## 五处

1. `About/About.xml` 的 `<modVersion>`
2. `Assemblies/NMMOpinionsChineseUI.dll` 的 `AssemblyVersion`
3. `Assemblies/GNH_NMM_Enhanced_ZH.dll` 的 `AssemblyVersion`
4. `tools/ui-patch-tester/NMMOpinionsChineseUI.cs` 的 `[assembly: AssemblyVersion("…")]`
5. `tools/ui-patch-tester/GNH_NMM_Enhanced_ZH.cs` 的同上

⚠ 第 4/5 处是**源码侧的真源**：两个 csproj 都写着
「版本号由源码里的 [assembly: AssemblyVersion] 提供，不要在这里重复声明」，
所以只改 csproj 不会生效 —— 必须改这两行源码再重编。

## 两环境

部署到 `D:\\steam\\...\\Mods\\裸体评价更多看法-汉化修复`（1.7 主安装）
与 `D:\\RimWorld-1.6\\Mods\\裸体评价更多看法-汉化修复`（1.6 引擎副本）的
`About/About.xml` 与两个 DLL，全部要与仓库逐字节一致。
"""
import os
import re
import sys
import json
import hashlib
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABOUT = os.path.join(REPO, "About", "About.xml")
DLLS = [
    "NMMOpinionsChineseUI.dll",
    "GNH_NMM_Enhanced_ZH.dll",
]
SRCS = [
    os.path.join(REPO, "tools", "ui-patch-tester", "NMMOpinionsChineseUI.cs"),
    os.path.join(REPO, "tools", "ui-patch-tester", "GNH_NMM_Enhanced_ZH.cs"),
]
TARGETS = [
    ("1.7 主安装", r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"),
    ("1.6 引擎副本", r"D:\RimWorld-1.6\Mods\裸体评价更多看法-汉化修复"),
]

fails = []


def bad(m):
    fails.append(m)
    print("  ❌ %s" % m)


def ok(m):
    print("  ✅ %s" % m)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def read_about_version(p):
    r = ET.fromstring(open(p, "rb").read().decode("utf-8-sig"))
    e = r.find("modVersion")
    return (e.text or "").strip() if e is not None else None


def read_dll_version(p):
    ps = (
        "$ErrorActionPreference='Stop';"
        "$a=[System.Reflection.AssemblyName]::GetAssemblyName('%s');"
        "$a.Version.ToString()"
    ) % p.replace("'", "''")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
    except Exception as ex:                        # noqa: BLE001
        bad("读 DLL 版本时调用 powershell 失败：%s" % ex)
        return None
    out = (r.stdout or "").strip().splitlines()
    if r.returncode != 0 or not out:
        bad("读 DLL 版本失败（%s）：%s" % (p, ((r.stderr or "")[:200])))
        return None
    return out[-1].strip()


def read_src_version(p):
    if not os.path.exists(p):
        return None
    t = open(p, "rb").read().decode("utf-8-sig", errors="replace")
    m = re.search(r'\[assembly:\s*(?:System\.Reflection\.)?AssemblyVersion\(\s*"([^"]+)"\s*\)\s*\]', t)
    return m.group(1) if m else None


def main():
    print("=" * 72)
    print("版本号一致性（五处 + 两环境）")
    print("=" * 72)

    v_about = read_about_version(ABOUT)
    print("  About.xml <modVersion>      : %s" % v_about)
    if v_about is None:
        bad("About.xml 没有 <modVersion>")

    dll_versions = {}
    for name in DLLS:
        p = os.path.join(REPO, "Assemblies", name)
        if not os.path.exists(p):
            bad("缺 %s" % p)
            continue
        v = read_dll_version(p)
        dll_versions[name] = v
        print("  %-28s: %s" % (name, v))
        if v and v_about and ".".join(v.split(".")[:3]) != v_about:
            bad("%s 的 AssemblyVersion %s 前三段 ≠ About %s"
                % (name, ".".join(v.split(".")[:3]), v_about))

    for p in SRCS:
        v = read_src_version(p)
        print("  源码 %-24s: %s" % (os.path.basename(p), v))
        if v is None:
            bad("%s 里找不到 [assembly: AssemblyVersion(\"…\")]（版本号真源丢了）" % os.path.basename(p))
        elif v_about and ".".join(v.split(".")[:3]) != v_about:
            bad("%s 的 AssemblyVersion %s 前三段 ≠ About %s"
                % (os.path.basename(p), ".".join(v.split(".")[:3]), v_about))

    print()
    print("-" * 72)
    print("部署目标")
    print("-" * 72)
    repo_files = {r"About\About.xml": os.path.join(REPO, "About", "About.xml")}
    for name in DLLS:
        repo_files[os.path.join("Assemblies", name)] = os.path.join(REPO, "Assemblies", name)

    for label, d in TARGETS:
        print("[%s]" % label)
        if not os.path.isdir(d):
            bad("%s：部署目录不存在" % label)
            continue
        p_about_dep = os.path.join(d, "About", "About.xml")
        if not os.path.exists(p_about_dep):
            bad("%s：缺 About/About.xml" % label)
        else:
            dv = read_about_version(p_about_dep)
            if dv != v_about:
                bad("%s：部署 About modVersion %s ≠ 仓库 %s" % (label, dv, v_about))
            else:
                ok("%s：部署 About 一致（%s）" % (label, dv))
        for rel, rp in repo_files.items():
            dp = os.path.join(d, rel)
            if not os.path.exists(dp):
                bad("%s：缺 %s" % (label, rel))
            elif sha(dp) != sha(rp):
                bad("%s：%s 与仓库不同 SHA256" % (label, rel))
            else:
                ok("%s：%s 同 SHA256（%s…）" % (label, rel, sha(rp)[:12]))
        print()

    print("=" * 72)
    if fails:
        print("❌ 失败 %d 项" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("✅ 全部一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
