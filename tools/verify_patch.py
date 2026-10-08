# -*- coding: utf-8 -*-
"""
裸体评价更多看法 简体汉化 —— 完整性自检工具

用途：随时检查这个汉化补丁是否完好。
用法：python verify_patch.py
说明：不需要任何额外文件，工具会自己去读游戏目录里的原模组做比对。

路径解析顺序（可换电脑不用改代码）：
  汉化包目录：环境变量 NMMO_PATCH → 脚本所在目录的上一级 → 常见安装路径
  原模组目录：环境变量 NMMO_MOD   → 常见安装路径

2026-10-08 修订记录：
  1. 修复「重复键检测」永远报正常的 bug —— 原实现遍历的是 dict，天然不可能出现重复。
  2. 新增「DefInjected 子目录名是否对应真实 Def 类型」检查。目录名写错会让整类翻译被
     RimWorld 静默丢弃，这是本汉化当初要解决的核心问题，原版自检反而没查。
  3. 路径不再写死单一路径。
  4. 新增两条【提示】（不计入失败）：label 覆盖情况、会显示成「名字's」的所有格占位符。
"""
import os, re, sys, io
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AMP = chr(38)      # & 符号本身，用 chr() 写出来避免转义混乱

HERE = os.path.dirname(os.path.abspath(__file__))
CAND_PATCH = [
    os.environ.get("NMMO_PATCH"),
    os.path.dirname(HERE),
    r"D:\steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复",
    r"D:\Steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复",
]
CAND_MOD = [
    os.environ.get("NMMO_MOD"),
    r"D:\steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions",
    r"D:\Steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions",
]

fails = []


def fail(msg):
    fails.append(msg)
    print("  [有问题] " + msg)


def ok(msg):
    print("  [正常] " + msg)


def hint(msg):
    print("  [提示] " + msg)


def pick(cands, marker):
    for c in cands:
        if c and os.path.isdir(os.path.join(c, marker)):
            return c
    for c in cands:
        if c and os.path.isdir(c):
            return c
    return cands[-1]


PATCH = pick(CAND_PATCH, "Languages")
MOD = pick(CAND_MOD, "About")

SKIP_TAGS = ("Def", "Patch", "Operation", "li", "members", "assembly")


def collect_defs(mod_dir):
    """从原模组里收集：Def 名 -> 正文条数；另外返回有 label 的 Def 名、出现过的 Def 类型名。"""
    info = {}
    labelled = set()
    types = set()
    for root, dirs, files in os.walk(mod_dir):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            try:
                r = ET.parse(os.path.join(root, fn)).getroot()
            except Exception:
                continue     # 原模组自带的教程文件不是合法 XML，跳过
            if r.tag != "Defs":
                continue
            for el in list(r):
                if not isinstance(el.tag, str):
                    continue
                cls = el.get("Class")
                if cls:
                    types.add(cls)
                elif el.tag not in SKIP_TAGS and ("." in el.tag or el.tag.endswith("Def")):
                    types.add(el.tag)
                name = None
                has_label = False
                for ch in el:
                    if not isinstance(ch.tag, str):
                        continue
                    if ch.tag == "defName":
                        name = (ch.text or "").strip()
                    elif ch.tag == "label" and (ch.text or "").strip():
                        has_label = True
                if not name:
                    continue
                cnt = 0
                for ch in el:
                    if isinstance(ch.tag, str) and ch.tag.endswith("opinionTexts"):
                        cnt = len(list(ch))
                info[name] = cnt
                if has_label:
                    labelled.add(name)
    return info, labelled, types


def find_definjected(patch):
    langs = os.path.join(patch, "Languages")
    if not os.path.isdir(langs):
        return None
    for lang in sorted(os.listdir(langs)):
        cand = os.path.join(langs, lang, "DefInjected")
        if os.path.isdir(cand):
            return cand
    return None


def main():
    print("=" * 66)
    print("裸体评价更多看法 简体汉化 —— 完整性自检")
    print("=" * 66)
    print("  汉化包：" + PATCH)
    print("  原模组：" + MOD)

    if not os.path.isdir(PATCH):
        print("找不到汉化补丁目录：" + PATCH)
        return 1
    if not os.path.isdir(MOD):
        print("找不到原模组目录：" + MOD)
        return 1

    print()
    print("【1】读取原模组，取得所有 Def 名字与类型")
    real, labelled, types = collect_defs(MOD)
    ok("原模组共有 %d 个 Def、%d 种 Def 类型" % (len(real), len(types)))

    langdir = os.path.join(PATCH, "Languages")

    print()
    print("【2】逐个检查 XML 文件能否正常打开")
    nfile = nkey = 0
    entries = {}
    dups = []
    for root, dirs, files in os.walk(langdir):
        for fn in files:
            if not fn.endswith(".xml"):
                continue
            p = os.path.join(root, fn)
            nfile += 1
            try:
                r = ET.parse(p).getroot()
            except Exception as e:
                fail("%s 打不开：%s" % (fn, e))
                continue
            if r.tag != "LanguageData":
                fail("%s 的根标签应该是 LanguageData，实际是 %s" % (fn, r.tag))
            for el in r:
                nkey += 1
                key = (os.path.basename(root), el.tag)
                if key in entries:
                    dups.append((fn, el.tag))
                entries[key] = el.text or ""
    ok("%d 个文件、%d 条翻译" % (nfile, nkey))

    print()
    print("【3】检查 DefInjected 子目录名是否对应真实存在的 Def 类型")
    print("       （目录名写错 = 该目录下所有翻译被游戏静默丢弃）")
    defdir = find_definjected(PATCH)
    if defdir is None:
        fail("在 %s 下找不到 DefInjected 目录" % langdir)
    else:
        subs = [d for d in sorted(os.listdir(defdir)) if os.path.isdir(os.path.join(defdir, d))]
        bad_dirs = []
        for d in subs:
            if d in types:
                continue
            if len(d) > 3 and d[:-1] in types:      # 游戏自己也允许目录名末尾多一个字符
                continue
            bad_dirs.append(d)
        if bad_dirs:
            fail("有 %d 个目录名不对应任何 Def 类型（其翻译会被整批丢弃）：%s" % (len(bad_dirs), bad_dirs))
            hint("原模组里出现过的类型有：%s" % (sorted(types),))
        else:
            ok("全部 %d 个目录都指向真实存在的 Def 类型：%s" % (len(subs), subs))

    print()
    print("【4】检查键名是否指向真实存在的 Def（悬空引用会让翻译无效）")
    dangling = [tag for (sub, tag) in entries if tag.split(".")[0] not in real]
    if dangling:
        fail("有 %d 个键找不到对应的 Def，例如：%s" % (len(dangling), dangling[:3]))
    else:
        ok("全部键名有效，没有悬空引用")

    print()
    print("【5】检查正文下标是否越界")
    oob = []
    for (sub, tag) in entries:
        m = re.match(r"^(.+)\.opinionTexts\.(\d+)$", tag)
        if not m:
            continue
        name, idx = m.group(1), int(m.group(2))
        if name in real and idx >= real[name]:
            oob.append(tag)
    if oob:
        fail("有 %d 个下标越界，例如：%s" % (len(oob), oob[:3]))
    else:
        ok("全部正文下标都在合法范围内")

    print()
    print("【6】检查有没有同一个键被翻译两次")
    if dups:
        fail("有 %d 个重复键，例如：%s" % (len(dups), dups[:3]))
    else:
        ok("没有重复键")

    print()
    print("【7】检查有没有漏译的正文")
    covered = {}
    for (sub, tag) in entries:
        m = re.match(r"^(.+)\.opinionTexts\.(\d+)$", tag)
        if m:
            covered.setdefault(m.group(1), set()).add(int(m.group(2)))
    notfull = []
    for name, cnt in real.items():
        if cnt == 0:
            continue
        if len(covered.get(name, set())) != cnt:
            notfull.append((name, cnt, len(covered.get(name, set()))))
    if notfull:
        fail("有 %d 个 Def 的正文没翻译完整，例如：%s" % (len(notfull), notfull[:3]))
    else:
        ok("全部 %d 个 Def 的正文都翻译完整" % len([1 for c in real.values() if c > 0]))

    print()
    print("【8】检查译文正文里有没有会破坏 XML 的裸符号")
    print("       （注释里的 " + AMP + " 号是合法的，不参与检查）")
    bad = []
    for root, dirs, files in os.walk(langdir):
        for fn in files:
            if not fn.endswith(".xml"):
                continue
            txt = io.open(os.path.join(root, fn), encoding="utf-8-sig").read()
            body = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
            for m in re.finditer(AMP + r"(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", body):
                bad.append((fn, body[max(0, m.start() - 30):m.start() + 30]))
    if bad:
        fail("有 %d 处未转义的 " + AMP + " 符号，例如：%s" % (len(bad), bad[:2]))
    else:
        ok("正文里没有会破坏 XML 的裸符号")

    print()
    print("【9】提示：label 覆盖情况（不计入失败）")
    covered_label = set(tag.split(".")[0] for (sub, tag) in entries if tag.endswith(".label"))
    missing_label = sorted(labelled - covered_label)
    if missing_label:
        hint("原模组有 %d 个 Def 写了 label，其中 %d 个没有中文 label（例如 %s）"
             % (len(labelled), len(missing_label), missing_label[:3]))
        hint("这类 label 只在开发者工具、翻译报告等地方显示，正常游玩看不到。")
    else:
        ok("原模组的 label 全部有中文")

    print()
    print("【10】提示：会显示成「名字's」的占位符（不计入失败）")
    poss = ["{PAWN_nameShortPossessive}", "{OBSERVER_nameShortPossessive}", "{OBSERVED_nameShortPossessive}"]
    pcount = 0
    for (sub, tag), text in entries.items():
        for ph in poss:
            pcount += text.count(ph)
    if pcount:
        hint("译文里有 %d 处 %s 之类的占位符。" % (pcount, poss[0]))
        hint("原模组把它们替换成「名字 + 's」（英文撇号 s），中文文本里会显示成「张三's」。")
        hint("改成 {PAWN_nameShort}的 可规避；批量替换前要先处理已经是「占位符 + 的」的地方。")
    else:
        ok("没有会显示成「名字's」的占位符")

    print()
    print("=" * 66)
    if fails:
        print("自检发现问题 %d 项，请看上面的 [有问题] 行" % len(fails))
        return 1
    print("自检全部通过 —— 汉化补丁完好")
    return 0


if __name__ == "__main__":
    sys.exit(main())
