# -*- coding: utf-8 -*-
"""
汉化包 About.xml 里所有数字的权威统计（描述里声称「每个数都能拿脚本复算」，就靠这个脚本）。

口径（与 About.xml 的「内容覆盖」一节一致）：
  · 正文 Keyed：键形如 NMM.Opinion.<defName>.opinionTexts.<序号>
  · 界面与自有键：Keyed 里其余全部键（NMM.OpinionTab.* / NMM.Log.* / NMM.Settings.* …）
  · DefInjected：按**叶子文本节点**计（<Def.field>文本</Def.field> 记 1；
    <Def.list><li>…</li></Def.list> 按每个 <li> 记 1，不按容器记）
  · 整列表注入：OwnInjections 的容器数与其中 <li> 总数
  · 增强界面：GNH_NMM_Enhanced_ZH.cs 里 Map 的条目数

用法：python 工具/count-numbers.py
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LANGS = ["ChineseSimplified", "ChineseSimplified (简体中文)"]

BODY_KEY = re.compile(r"^NMM\.Opinion\..+\.(opinionTexts|texts)\.\d+$")


def walk_xml(base):
    for dp, dn, fns in os.walk(base):
        for fn in fns:
            if fn.endswith(".xml"):
                yield os.path.join(dp, fn)


def count_keyed(base):
    body = ui = 0
    files = 0
    for p in walk_xml(base):
        files += 1
        try:
            t = ET.parse(p)
        except Exception:
            continue
        for el in t.getroot():
            if not isinstance(el.tag, str):
                continue
            if BODY_KEY.match(el.tag):
                body += 1
            else:
                ui += 1
    return body, ui, files


def count_definj(base):
    leaves = files = 0
    containers = 0
    for p in walk_xml(base):
        files += 1
        try:
            t = ET.parse(p)
        except Exception:
            continue
        for el in t.getroot():
            if not isinstance(el.tag, str):
                continue
            containers += 1
            kids = [x for x in el if isinstance(x.tag, str)]
            leaves += len(kids) if kids else 1
    return leaves, containers, files


def count_own(base):
    cont = li = files = 0
    for p in walk_xml(base):
        files += 1
        try:
            t = ET.parse(p)
        except Exception:
            continue
        for el in t.getroot():
            if not isinstance(el.tag, str):
                continue
            cont += 1
            li += len([x for x in el if isinstance(x.tag, str)])
    return cont, li, files


def count_enhanced():
    """数 EnhancedText.Map 里的条目。注意有条目跨行写（键一行、值下一行），
    所以按「以 { " 开头的行」计数，不能要求单行成对（那样会少数 12 条）。"""
    p = os.path.join(HERE, "ui-patch-tester", "GNH_NMM_Enhanced_ZH.cs")
    if not os.path.exists(p):
        return 0
    n = 0
    for ln in open(p, encoding="utf-8"):
        if re.match(r'^\s*\{\s*"', ln):
            n += 1
    return n


def main():
    print("=" * 62)
    print("汉化包数字权威统计")
    print("=" * 62)
    grand_body = grand_ui = 0
    for lang in LANGS:
        print()
        print("【%s】" % lang)
        root = os.path.join(REPO, "Languages", lang)
        v17 = os.path.join(REPO, "v1.7", "Languages", lang)
        b1, u1, f1 = count_keyed(os.path.join(root, "Keyed")) if os.path.isdir(os.path.join(root, "Keyed")) else (0, 0, 0)
        b2, u2, f2 = count_keyed(os.path.join(v17, "Keyed")) if os.path.isdir(os.path.join(v17, "Keyed")) else (0, 0, 0)
        print("  Keyed（根）      正文 %6d / 界面 %4d / %d 文件" % (b1, u1, f1))
        print("  Keyed（v1.7）    正文 %6d / 界面 %4d / %d 文件" % (b2, u2, f2))
        d1 = count_definj(os.path.join(root, "DefInjected")) if os.path.isdir(os.path.join(root, "DefInjected")) else (0, 0, 0)
        d2 = count_definj(os.path.join(v17, "DefInjected")) if os.path.isdir(os.path.join(v17, "DefInjected")) else (0, 0, 0)
        print("  DefInjected（根）   %6d 条 / %d 容器 / %d 文件" % d1)
        print("  DefInjected（v1.7） %6d 条 / %d 容器 / %d 文件" % d2)
        if lang == LANGS[0]:
            grand_body = b1 + b2
            grand_ui = u1 + u2
            own = count_own(os.path.join(REPO, "OwnInjections", lang))
            enh = count_enhanced()
            print("  OwnInjections     %6d 容器 / %d 个 li / %d 文件" % own)
            print("  增强界面替换       %6d 条" % enh)
            print()
            print("  —— 写进 About.xml 的口径 ——")
            print("  正文 Keyed            %d 条" % grand_body)
            print("  界面与自有键          %d 条" % grand_ui)
            print("  DefInjected           %d 条 / %d 个文件"
                  % (d1[0] + d2[0], d1[2] + d2[2]))
            print("  整列表注入            %d 个容器 / %d 条 / %d 个文件"
                  % (own[0], own[1], own[2]))
            print("  增强界面              %d 条" % enh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
