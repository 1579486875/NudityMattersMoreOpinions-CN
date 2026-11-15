# -*- coding: utf-8 -*-
"""
向下兼容核对：把原模组历史版本（1.0.8 / 1.0.7 / 1.0.5 / 1.0.3）的 Def 集合，
与当前版本（Common/Defs，即 1.0.9）逐条对比：

  · defName 是否还在（我们的键按 defName 定位，名字变了就失效）
  · 同一 def 的 opinionTexts / texts 条数是否一致（整列表注入要求条数匹配）

用法：python tools/audit-oldversions.py <旧版 Defs 根目录> [<旧版 2> ...]
"""
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUR = r"D:\steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions\Common\Defs"
FIELDS = ("opinionTexts", "texts")


def scan(root):
    """返回 {defName: {field: 条数}}（解析 ParentName 继承）。"""
    rec = {}
    for dp, dn, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith(".xml"):
                continue
            try:
                t = ET.parse(os.path.join(dp, fn))
            except Exception:
                continue
            for el in t.iter():
                if not isinstance(el.tag, str):
                    continue
                d = el.find("defName")
                nm = (d.text or "").strip() if d is not None else ""
                if not nm and (el.get("Name") or "").strip():
                    nm = el.get("Name").strip()
                if not nm or nm in rec:
                    continue
                cnt = {}
                for f in FIELDS:
                    fe = el.find(f)
                    if fe is not None:
                        cnt[f] = len([x for x in fe if isinstance(x.tag, str)])
                rec[nm] = {"cnt": cnt, "parent": el.get("ParentName"),
                           "abs": (el.get("Abstract") or "").lower() == "true"}

    def resolve(n, seen=None):
        seen = seen or set()
        if n in seen:
            return {}
        seen.add(n)
        r = rec.get(n)
        if not r:
            return {}
        out = resolve(r["parent"], seen) if r["parent"] else {}
        for f, c in r["cnt"].items():
            out[f] = out.get(f, 0) + c
        return out

    return {k: resolve(k) for k, v in rec.items() if not v["abs"]}


def main():
    cur = scan(CUR)
    print("当前版本（Common/Defs）：%d 个实际 Def" % len(cur))
    for old_root in sys.argv[1:]:
        if not os.path.isdir(old_root):
            print("\n跳过（不存在）：%s" % old_root)
            continue
        old = scan(old_root)
        print("\n" + "=" * 66)
        print("%s：%d 个实际 Def" % (old_root, len(old)))
        gone = sorted(set(old) - set(cur))
        added = sorted(set(cur) - set(old))
        same_cnt = diff_cnt = 0
        diff_list = []
        for name in sorted(set(old) & set(cur)):
            for f, c in old[name].items():
                if c <= 0:
                    continue
                if cur[name].get(f) == c:
                    same_cnt += 1
                else:
                    diff_cnt += 1
                    diff_list.append((name, f, c, cur[name].get(f)))
        print("  旧版有、当前没有的 Def：%d 个 %s" % (len(gone), gone[:6]))
        print("  当前有、旧版没有的 Def：%d 个 %s" % (len(added), added[:6]))
        print("  两边都有且条数一致：(Def,字段) %d 个" % same_cnt)
        print("  两边都有但条数不同：(Def,字段) %d 个" % diff_cnt)
        for t in diff_list[:10]:
            print("      %-52s %-13s 旧 %d → 今 %s" % t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
