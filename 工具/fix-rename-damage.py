# -*- coding: utf-8 -*-
"""
修复另一轮「中英文化重命名」在本仓库引入的两处破坏：

① GitHub 的 releases URL 被改成了 `/发布包/latest` —— 这是 github.com 的固定路径，
   中文化之后 6 处链接全部 404。必须改回 `releases`。
② `Source/*.csproj` 里的 `..\\工具\\ui-patch-tester\\` 被改成了 `..\\工具\\...`，
   但仓库里的目录**仍然叫 tools**（`ls` 可见，`工具/` 不存在）→ 编译会直接找不到源码。

顺带核对：`技术说明.md` 里 `E:\\TAML\\_backup` → `E:\\TAML\\备份` 这一处是**对的**
（`_backup` 目录确实已被改名成 `备份`，`Test-Path` 已确认 `_backup` 不存在），保留不动。

用法：python 工具/fix-rename-damage.py [--write]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MODFIX = r"E:\TAML\modfix\GNH-LocalFixes"

# ① GitHub URL：只把路径段 `发布包` 改回 `releases`，显示文字里的「发布包」不碰
URL_FIX = [
    ("https://github.com/1579486875/NudityMattersMoreOpinions-CN/发布包/latest",
     "https://github.com/1579486875/NudityMattersMoreOpinions-CN/releases/latest"),
    ("https://github.com/1579486875/GNH-LocalFixes/发布包/latest",
     "https://github.com/1579486875/GNH-LocalFixes/releases/latest"),
]

# ② csproj 路径
CSPROJ_FIX = [
    (r"..\工具\ui-patch-tester", r"..\工具\ui-patch-tester"),
]


def fix_text(path, pairs, write):
    if not os.path.exists(path):
        return None
    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    txt = raw.decode("utf-8-sig")
    n = 0
    for old, new in pairs:
        c = txt.count(old)
        if c:
            txt = txt.replace(old, new)
            n += c
    if n and write:
        open(path, "wb").write((b"\xef\xbb\xbf" if bom else b"") + txt.encode("utf-8"))
    return n


def main():
    write = "--write" in sys.argv
    total = 0

    print("① GitHub releases URL")
    for rel in ("README.md", "汉化说明.md"):
        n = fix_text(os.path.join(REPO, rel), URL_FIX, write)
        print("   %-16s %s 处" % (rel, n if n is not None else "文件不存在"))
        total += n or 0
    n = fix_text(os.path.join(MODFIX, "README.md"), URL_FIX, write)
    print("   %-16s %s 处（修复补丁）" % ("README.md", n if n is not None else "文件不存在"))
    total += n or 0

    print()
    print("② csproj 的源码路径")
    for rel in ("Source/GNH_NMM_Enhanced_ZH.csproj", "Source/NMMOpinionsChineseUI.csproj"):
        n = fix_text(os.path.join(REPO, rel), CSPROJ_FIX, write)
        print("   %-42s %s 处" % (rel, n if n is not None else "文件不存在"))
        total += n or 0

    print()
    print("③ 核对备份目录名")
    for p in (r"E:\TAML\_backup", r"E:\TAML\备份"):
        print("   %-22s %s" % (p, "存在" if os.path.isdir(p) else "不存在"))

    print()
    print("合计改动 %d 处%s" % (total, "" if write else "（dry-run，加 --write 才写盘）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
