# -*- coding: utf-8 -*-
"""README「汉化了哪些地方」那张表需要的全部细项数字。"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LANG = "ChineseSimplified"

BODY_KEY = re.compile(r"^NMM\.Opinion\..+\.(opinionTexts|texts)\.\d+$")


def stats(base):
    if not os.path.isdir(base):
        return None
    files = keys = conts = leaves = full = 0
    for dp, dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith(".xml"):
                continue
            files += 1
            try:
                t = ET.parse(os.path.join(dp, fn))
            except Exception:
                continue
            for el in t.getroot():
                if not isinstance(el.tag, str):
                    continue
                keys += 1
                conts += 1
                kids = [x for x in el if isinstance(x.tag, str)]
                if kids:
                    leaves += len(kids)
                    full += 1
                else:
                    leaves += 1
    return {"files": files, "keys": keys, "conts": conts, "leaves": leaves, "full": full}


def field_stats(base):
    c = Counter()
    for dp, dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith(".xml"):
                continue
            try:
                t = ET.parse(os.path.join(dp, fn))
            except Exception:
                continue
            for el in t.getroot():
                if not isinstance(el.tag, str):
                    continue
                tag = el.tag
                if re.search(r"\.(opinionTexts|texts)\.\d+$", tag):
                    c["索引式正文键"] += 1
                elif re.search(r"\.(opinionTexts|texts)$", tag):
                    c["整列表正文容器"] += len([x for x in el if isinstance(x.tag, str)])
                else:
                    last = tag.rsplit(".", 1)[-1]
                    c[last] += 1
    return c


def main():
    root = os.path.join(REPO, "Languages", LANG)
    v17 = os.path.join(REPO, "v1.7", "Languages", LANG)
    own = os.path.join(REPO, "OwnInjections", LANG)

    print("=" * 62)
    for label, p in (
        ("根 Keyed", os.path.join(root, "Keyed")),
        ("根 DefInjected", os.path.join(root, "DefInjected")),
        ("v1.7 Keyed", os.path.join(v17, "Keyed")),
        ("v1.7 DefInjected", os.path.join(v17, "DefInjected")),
        ("OwnInjections", own),
    ):
        s = stats(p)
        if s is None:
            print("%-18s （无）" % label)
            continue
        print("%-18s 文件 %3d  键 %6d  容器 %6d  叶子 %6d  整列表容器 %4d"
              % (label, s["files"], s["keys"], s["conts"], s["leaves"], s["full"]))

    # v1.7 Keyed 里正文 vs 自有
    body = other = 0
    for dp, dn, fns in os.walk(os.path.join(v17, "Keyed")):
        for fn in fns:
            if not fn.endswith(".xml"):
                continue
            try:
                t = ET.parse(os.path.join(dp, fn))
            except Exception:
                continue
            for el in t.getroot():
                if isinstance(el.tag, str):
                    if BODY_KEY.match(el.tag):
                        body += 1
                    else:
                        other += 1
    print()
    print("v1.7 Keyed：正文 %d / 自有键 %d" % (body, other))

    print()
    print("根 DefInjected 按字段：")
    for k, v in field_stats(os.path.join(root, "DefInjected")).most_common(12):
        print("   %-22s %d" % (k, v))
    print()
    print("v1.7 DefInjected 按字段：")
    for k, v in field_stats(os.path.join(v17, "DefInjected")).most_common(12):
        print("   %-22s %d" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
