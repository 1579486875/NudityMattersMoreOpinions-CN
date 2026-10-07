# -*- coding: utf-8 -*-
"""
打包脚本 —— 把本仓库做成一个可以直接扔进 RimWorld Mods 目录的 zip。

怎么用（在 packing 目录里执行）：
    python pack_release.py            # 打包 1.0.0 版
    python pack_release.py 1.0.1      # 打包 1.0.1 版

打完会在 packing 目录下生成一个 zip，文件名形如
    NudityMattersMoreOpinions-CN-v1.0.0.zip

zip 里有一个名为「裸体评价更多看法-简体汉化」的顶层文件夹，
玩家解压后把这个文件夹整个放进 RimWorld 的 Mods 目录即可。

脚本做完打包后会立刻回验一次：把 zip 解开，逐个和仓库里的文件比字节，
确保压缩过程没有损坏任何内容。
"""
import os
import sys
import zipfile

# ── 可调参数 ────────────────────────────────────────────────
VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)              # 仓库根 = packing 的上一级

TOP = "裸体评价更多看法-简体汉化"          # 解压后出现的文件夹名

# 要打进 zip 的东西。故意不包含：
#   .git / .gitignore / .gitattributes   —— git 自己的东西，玩家不需要
#   packing/                             —— 只给开发者用的打包脚本
INCLUDE = [
    "About",            # 模组元数据，游戏靠它识别模组
    "Languages",        # 全部翻译文件
    "tools",            # 自检工具，玩家可用来验证补丁完好
    "汉化说明.md",       # 中文说明
    "README.md",
    "LICENSE",
]

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
                for fn in files:
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

    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
