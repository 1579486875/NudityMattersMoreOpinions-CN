# -*- coding: utf-8 -*-
"""占位符对账：英文原文 Keyed ↔ 我们的中文 Keyed（模板 §2 翻译层）。

## 判据（为什么不是「完全相等」）

模板 §2 要求「格式占位符（`{0}`、`{PAWN_nameDef}`）原样保留」。但本仓库有一条
**刻意的改写**：v1.4.17 把 168 处 `{PAWN_nameShortPossessive}` 改成了
`{PAWN_nameShort}的` —— 因为中文语言包没有 LanguageWorker，
`…Possessive` 会被按英文规则渲染成「冯俊晧's」。

所以判据要分三档：

| 情况 | 判定 | 理由 |
|---|---|---|
| 中文有、英文没有 | **❌ 错误** | 那个占位符会原样显示成 `{XXX}` |
| 英文有、中文没有 | **⚠ 需人工看** | 可能是刻意改写，也可能是漏了 |
| 多重集完全相等 | ✅ | — |

## 已知白名单

`KNOWN_INTENTIONAL` 里放「确认过是刻意改写」的（键, 占位符）组合，不报 ⚠。

## 用法

    python 工具/check-placeholders.py            # 汇总
    python 工具/check-placeholders.py --detail   # 列出全部 ⚠ 与 ❌
"""
import os
import re
import sys
import glob
import xml.etree.ElementTree as ET
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EN_DIR = r"D:\steam\steamapps\common\RimWorld\Mods\RJW-功能-裸体评价\1.7\Languages\English\Keyed"
ZH_DIRS = [
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified", "Keyed"),
    os.path.join(REPO, "Languages", "ChineseSimplified", "Keyed"),
]

RE_PH = re.compile(r"\{[A-Za-z_0-9]+\}|\{[0-9]+\}")

# 确认过是刻意改写的：(键, 被去掉的占位符)
#   v1.4.17：中文没有 LanguageWorker，…Possessive 会渲染成「名字's」→ 统一改成 {…}的
#   2026-11-17 本轮确认的 4 条：英文用 `{SELF_objective}self` 拼反身代词（himself/herself），
#     中文没有这种构词法，直接写「遮挡身体 / 的裸体」，所以少一个 {SELF_objective} 是正确的。
KNOWN_INTENTIONAL = {
    "*": {"{PAWN_nameShortPossessive}", "{PAWN_possessive}",
          "{SELF_possessive}", "{OTHER_possessive}",
          "{PAWN_nameFullPossessive}"},
    "NMM.Log.Covering.Default.Unaware": {"{SELF_objective}"},
    "NMM.Log.Covering.Uncaring.Unaware": {"{SELF_objective}"},
    "NMM.Log.Naked.Unable.Unaware": {"{SELF_objective}"},
    "NMM.Log.Naked.Unallowed.Unaware": {"{SELF_objective}"},
}


def load_keyed(d):
    """返回 {键: 值}；同键多次出现时后者覆盖（与游戏一致），并把重复记下来。"""
    out = {}
    dups = []
    for f in sorted(glob.glob(os.path.join(d, "**", "*.xml"), recursive=True)):
        try:
            r = ET.fromstring(open(f, "rb").read().decode("utf-8-sig"))
        except Exception as e:                   # noqa: BLE001
            print("  ⚠ 解析失败 %s: %s" % (f, e))
            continue
        for e in r:
            if e.tag == "LanguageData":
                continue
            if e.tag in out:
                dups.append((e.tag, os.path.basename(f)))
            out[e.tag] = (e.text or "")
    return out, dups


def main():
    detail = "--detail" in sys.argv

    if not os.path.isdir(EN_DIR):
        # ⚠ 不是缺陷：玩家可能没装合并版（1.6 环境下就是）。
        #   这时没法对账，**安静跳过**而不是 exit 1 —— 否则闸门会在 1.6 环境下误红。
        print("⏭ 英文原文目录不存在（合并版未安装），本项跳过：%s" % EN_DIR)
        return 0

    en, en_dup = load_keyed(EN_DIR)
    print("英文原文：%d 键（重复 %d）" % (len(en), len(en_dup)))

    total_common = 0
    total_err = 0
    total_warn = 0
    errs = []
    warns = []

    for zd in ZH_DIRS:
        if not os.path.isdir(zd):
            print("  （不存在）%s" % zd)
            continue
        zh, zh_dup = load_keyed(zd)
        common = sorted(set(en) & set(zh))
        err = []
        warn = []
        for k in common:
            pe = Counter(RE_PH.findall(en[k]))
            pz = Counter(RE_PH.findall(zh[k]))
            extra = pz - pe
            missing = pe - pz
            if extra:
                err.append((k, dict(extra), en[k][:60], zh[k][:60]))
            if missing:
                # 白名单：整类改写的（…Possessive）+ 逐键确认的（反身代词）
                wl = set(KNOWN_INTENTIONAL.get("*", set()))
                wl |= set(KNOWN_INTENTIONAL.get(k, set()))
                missing = Counter({p: n for p, n in missing.items() if p not in wl})
                if missing:
                    warn.append((k, dict(missing), en[k][:60], zh[k][:60]))
        print()
        print("  %-52s 中文 %6d 键 / 两边都有 %5d" % (os.path.relpath(zd, REPO), len(zh), len(common)))
        print("     ❌ 中文多出占位符：%d    ⚠ 英文有中文没有：%d    （中文内部重复键 %d）"
              % (len(err), len(warn), len(zh_dup)))
        total_common += len(common)
        total_err += len(err)
        total_warn += len(warn)
        errs += err
        warns += warn
        if detail and err:
            print("     --- ❌ 明细（前 15）---")
            for k, d, e, z in err[:15]:
                print("       %s  %s" % (k, d))
                print("         EN: %s" % e)
                print("         ZH: %s" % z)

    print()
    print("=" * 74)
    print("合计：对比 %d 键 / ❌ %d / ⚠ %d" % (total_common, total_err, total_warn))
    if detail and warns:
        print()
        print("--- ⚠ 明细（前 20）---")
        for k, d, e, z in warns[:20]:
            print("  %s  %s" % (k, d))
            print("    EN: %s" % e)
            print("    ZH: %s" % z)
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
