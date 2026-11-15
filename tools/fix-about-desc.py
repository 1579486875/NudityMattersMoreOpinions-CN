# -*- coding: utf-8 -*-
"""
重排汉化包 About.xml 的 <description>：
  ① 去掉首行空行；
  ② 把真正的简介句（原第 18 行）提到最前 —— 现在它被三份更新日志压在中间；
  ③ 全部小节加 ■ 前缀，统一版式；
  ④ 更新过时数字（正文 Keyed / 界面键 / DefInjected 条数与文件数 / 整列表注入条数）；
  ⑤ 更新记录整体下沉到「模组信息」之前。
只调顺序与版式，正文一字不删。

用法：python tools/fix-about-desc.py [--write]
"""
import os
import re
import sys
import argparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ABOUT = os.path.join(REPO, "About", "About.xml")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    raw = open(ABOUT, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    txt = raw.decode("utf-8-sig")
    m = re.search(r"<description>(.*?)</description>", txt, re.S)
    d = m.group(1)
    L = d.split("\n")

    def seg(a, b):
        """取 [a, b) 行（0-based），去掉首尾空行。"""
        chunk = L[a:b]
        while chunk and not chunk[0].strip():
            chunk.pop(0)
        while chunk and not chunk[-1].strip():
            chunk.pop()
        return chunk

    parts = []
    parts += seg(17, 18)                    # 简介句
    parts += [""]
    parts += seg(19, 23)                    # 一套文件同时服务三个目标
    parts += [""]
    parts += ["■ 内容覆盖（2026-11-15 按文件实测，每个数都能拿 tools/count-numbers.py 复算）"]
    parts += seg(38, 46)
    parts += [""]
    parts += ["■ 两条正文通道为什么要分开"]
    parts += seg(48, 52)
    parts += [""]
    parts += ["■ 三个版本怎么共存"]
    parts += seg(30, 36)
    parts += [""]
    parts += ["■ 怎么用"]
    parts += seg(63, 66)
    parts += [""]
    parts += ["■ 结构说明"]
    parts += seg(68, 73)
    parts += [""]
    parts += ["■ 顺手修掉的原模组缺陷"]
    parts += seg(58, 61)
    parts += [""]
    parts += ["■ 合并版顺手变好的地方"]
    parts += seg(54, 56)
    parts += [""]
    parts += ["■ 依赖与兼容"]
    parts += seg(1, 2)                      # 【适用版本】
    parts += seg(24, 28)                    # 不再硬依赖 + 为什么原先绑死
    parts += [""]
    parts += ["■ 更新记录"]
    parts += seg(3, 17)                     # v1.4.19 / 18 / 17
    parts += [""]
    parts += ["■ 模组信息"]
    parts += seg(74, 82)

    new = "\n".join(parts)

    # 数字更新（逐个替换，替换不到就报出来）
    nums = [
        ("· 正文 Keyed 126,245 条", "· 正文 Keyed 130,766 条"),
        ("· 界面与自有键 413 条", "· 界面与自有键 498 条"),
        ("· DefInjected 17,232 条 / 30 个文件", "· DefInjected 17,896 条 / 49 个文件"),
        ("· 整列表注入 5,214 个容器 / 47 个文件",
         "· 整列表注入 5,214 个容器 / 125,750 条 / 47 个文件"),
    ]
    for old, rep in nums:
        if old in new:
            new = new.replace(old, rep, 1)
            print("[数字] %s" % old)
        else:
            print("[警告] 没找到数字锚点：%s" % old)

    if not args.write:
        print()
        print("（dry-run）行数 %d → %d，字符 %d → %d"
              % (len(L), len(parts), len(d), len(new)))
        print()
        for i, ln in enumerate(new.split(chr(10))):
            print("%3d| %s" % (i + 1, ln[:78]))
        return 0

    out = (b"\xef\xbb\xbf" if bom else b"") + (txt[:m.start(1)] + new + txt[m.end(1):]).encode("utf-8")
    open(ABOUT, "wb").write(out)
    print()
    print("已写入 %d 字节，行数 %d → %d" % (len(out), len(L), len(parts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
