# -*- coding: utf-8 -*-
"""
打包脚本 —— 把本仓库做成一个可以直接扔进 RimWorld Mods 目录的 zip。

怎么用（在 packing 目录里执行）：
    python pack_release.py            # 版本号自动读 About.xml 里的 <modVersion>
    python pack_release.py 1.1.0      # 也可以手动指定版本号

打完会在 packing 目录下生成一个 zip，文件名形如
    NudityMattersMoreOpinions-CN-v1.1.0.zip

zip 里有一个名为「裸体评价更多看法-简体汉化」的顶层文件夹，
玩家解压后把这个文件夹整个放进 RimWorld 的 Mods 目录即可。

脚本做完打包后会立刻回验一次：把 zip 解开，逐个和仓库里的文件比字节，
确保压缩过程没有损坏任何内容。
"""
import os
import re
import sys
import zipfile

# Windows 控制台默认是 GBK，中文和一些符号会打印不出来，这里统一成 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def read_mod_version():
    """从 About/About.xml 里读 <modVersion>，避免文件名写死跟内容对不上。"""
    about = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "About", "About.xml")
    try:
        txt = open(about, encoding="utf-8-sig").read()
        m = re.search(r"<modVersion>(.*?)</modVersion>", txt)
        if m:
            return m.group(1).strip()
    except Exception as e:
        print("  [提示] 读 About.xml 版本号失败：" + str(e))
    return "1.0.0"


# ── 可调参数 ────────────────────────────────────────────────
VERSION = sys.argv[1] if len(sys.argv) > 1 else read_mod_version()

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)              # 仓库根 = packing 的上一级

TOP = "裸体评价更多看法-简体汉化"          # 解压后出现的文件夹名

# 要打进 zip 的东西。故意不包含：
#   .git / .gitignore / .gitattributes   —— git 自己的东西，玩家不需要
#   packing/                             —— 只给开发者用的打包脚本
#                                        （tools/ui-patch-tester/ 会一起打进去，
#                                          高级玩家可以用它自己核对补丁装没装上）
#
# ⚠️ Assemblies 必须打进去！界面汉化补丁（Harmony）就在里面，
#    漏了它玩家下载后「看法」标签页的英文不会变成中文。
INCLUDE = [
    "About",            # 模组元数据，游戏靠它识别模组
    "Assemblies",       # 界面汉化补丁 DLL（少了它界面文字还是英文）
    "Languages",        # 全部翻译文件
    "tools",            # 自检工具，玩家可用来验证补丁完好
    "汉化说明.md",       # 中文说明
    "README.md",
    "LICENSE",
]

# 打包时跳过的目录名与后缀（Python 缓存之类，属于垃圾）
SKIP_DIRS = {"__pycache__", ".vs", "obj", "bin"}
SKIP_EXTS = {".pyc", ".pyo", ".pdb"}

OUT = os.path.join(HERE, "NudityMattersMoreOpinions-CN-v%s.zip" % VERSION)
# ────────────────────────────────────────────────────────────


def collect(zf):
    """把 INCLUDE 列出的文件写进 zip，返回（文件数, 原始字节数）。"""
    count = 0
    raw = 0

    for name in INCLUDE:
        path = os.path.join(REPO, name)

        if os.path.isfile(path):
            zf.write(path, TOP + "/" + name)
            count += 1
            raw += os.path.getsize(path)

        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                # 就地改 dirs，os.walk 就不会往下走进这些目录
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in SKIP_EXTS:
                        continue
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, REPO).replace("\\", "/")
                    zf.write(fp, TOP + "/" + rel)
                    count += 1
                    raw += os.path.getsize(fp)

        else:
            print("  [跳过] 找不到：" + name)

    return count, raw


def verify(zip_path):
    """回验：把 zip 里的每个文件解开，和仓库里的原文件逐字节比。"""
    bad = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            rel = info.filename[len(TOP) + 1:]
            src = os.path.join(REPO, rel.replace("/", os.sep))
            if not os.path.isfile(src):
                print("  [异常] zip 里有仓库中不存在的文件：" + rel)
                bad += 1
            elif zf.read(info) != open(src, "rb").read():
                print("  [异常] 字节不一致：" + rel)
                bad += 1
    return bad


def main():
    if not os.path.isdir(os.path.join(REPO, "About")):
        print("找不到 About 目录 —— 这个脚本要放在仓库的 packing 子目录里运行。")
        return 1

    print("版本号：" + VERSION + "（来自 About.xml 的 modVersion）"
          if len(sys.argv) <= 1 else "版本号：" + VERSION + "（命令行指定）")

    # 关键文件检查 —— 少了这些就是发了个残缺包，直接拦下
    must = [
        "About/About.xml",
        "Assemblies/NMMOpinionsChineseUI.dll",
        "Languages/ChineseSimplified/DefInjected/InteractionDef/Interactions.xml",
    ]
    missing = [m for m in must if not os.path.isfile(os.path.join(REPO, m.replace("/", os.sep)))]
    if missing:
        print("！以下关键文件不存在，打包中止：")
        for m in missing:
            print("    " + m)
        return 1

    if os.path.exists(OUT):
        os.remove(OUT)

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        count, raw = collect(zf)

    size = os.path.getsize(OUT)
    print("打包完成：" + OUT)
    print("  文件数   ：%d" % count)
    print("  原始大小 ：%d 字节" % raw)
    print("  压缩后   ：%d 字节（%.2f MB）" % (size, size / 1048576.0))

    bad = verify(OUT)
    print("  回验差异 ：%d %s" % (bad, "（正常）" if bad == 0 else "（有问题，请检查！）"))

    # 最后再确认一次补丁 DLL 真的在包里
    with zipfile.ZipFile(OUT) as zf:
        names = zf.namelist()
    dll = [n for n in names if n.endswith("NMMOpinionsChineseUI.dll")]
    if dll:
        print("  补丁 DLL ：[OK] 已打进包（" + dll[0] + "）")
    else:
        print("  补丁 DLL ：[NG] 不在包里！界面文字不会变中文")
        bad += 1

    junk = [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
    if junk:
        print("  垃圾文件 ：[NG] 混进了 %d 个（%s）" % (len(junk), junk[0]))
        bad += 1
    else:
        print("  垃圾文件 ：无")

    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
