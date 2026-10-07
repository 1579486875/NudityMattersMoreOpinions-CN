# -*- coding: utf-8 -*-
"""
裸体评价更多看法 简体汉化 —— 完整性自检工具

用途：随时检查这个汉化补丁是否完好。
用法：python verify_patch.py
说明：不需要任何额外文件，工具会自己去读游戏目录里的原模组做比对。
"""
import os, re, sys, io
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============ 路径配置（换电脑只需改这两行）============
PATCH = r"D:\Steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-汉化修复"
MOD   = r"D:\Steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions"
# ======================================================

AMP = chr(38)      # & 符号本身，用 chr() 写出来避免转义混乱
fails = []


def fail(msg):
    """记录一条「有问题」"""
    fails.append(msg)
    print("  [有问题] " + msg)


def ok(msg):
    """记录一条「正常」"""
    print("  [正常] " + msg)


def collect_defs(mod_dir):
    """从原模组里收集：每个 Def 的名字 → 它有多少条正文"""
    info = {}
    for root, dirs, files in os.walk(mod_dir):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            try:
                r = ET.parse(os.path.join(root, fn)).getroot()
            except Exception:
                continue     # 模组自带的教程文件不是合法 XML，跳过
            for el in list(r):
                if not isinstance(el.tag, str):
                    continue
                name = None
                for ch in el:
                    if isinstance(ch.tag, str) and ch.tag == "defName":
                        name = (ch.text or "").strip()
                if not name:
                    continue
                cnt = 0
                for ch in el:
                    if isinstance(ch.tag, str) and ch.tag.endswith("opinionTexts"):
                        cnt = len(list(ch))
                info[name] = cnt
    return info


def main():
    print("=" * 66)
    print("裸体评价更多看法 简体汉化 —— 完整性自检")
    print("=" * 66)

    if not os.path.isdir(PATCH):
        print("找不到汉化补丁目录：" + PATCH)
        return 1
    if not os.path.isdir(MOD):
        print("找不到原模组目录：" + MOD)
        return 1

    print()
    print("【1】读取原模组，取得所有 Def 名字")
    real = collect_defs(MOD)
    ok("原模组共有 %d 个 Def" % len(real))

    print()
    print("【2】逐个检查 XML 文件能否正常打开")
    nfile = nkey = 0
    entries = {}
    langdir = os.path.join(PATCH, "Languages")
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
                entries[(os.path.basename(root), el.tag)] = el.text or ""
    ok("%d 个文件全部正常，共 %d 条翻译" % (nfile, nkey))

    print()
    print("【3】检查键名是否指向真实存在的 Def（悬空引用会让翻译失效）")
    dangling = [tag for (sub, tag) in entries if tag.split(".")[0] not in real]
    if dangling:
        fail("有 %d 个键找不到对应的 Def，例如：%s" % (len(dangling), dangling[:3]))
    else:
        ok("全部键名有效，没有悬空引用")

    print()
    print("【4】检查正文下标是否越界（越界会让整个文件失效）")
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
    print("【5】检查有没有同一个键被翻译两次")
    dups = []
    seen = set()
    for k in entries:
        if k in seen:
            dups.append(k[1])
        seen.add(k)
    if dups:
        fail("有 %d 个重复键，例如：%s" % (len(dups), dups[:3]))
    else:
        ok("没有重复键")

    print()
    print("【6】检查有没有漏译的正文")
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
    print("【7】检查译文正文里有没有会破坏 XML 的裸符号")
    print("       （注释里的 " + AMP + " 号是合法的，不参与检查）")
    bad = []
    for root, dirs, files in os.walk(langdir):
        for fn in files:
            if not fn.endswith(".xml"):
                continue
            txt = io.open(os.path.join(root, fn), encoding="utf-8-sig").read()
            # 先把整段注释删掉，只检查剩下的正文
            body = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
            for m in re.finditer(AMP + r"(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", body):
                bad.append((fn, body[max(0, m.start() - 30):m.start() + 30]))
    if bad:
        fail("有 %d 处未转义的 " + AMP + " 符号，例如：%s" % (len(bad), bad[:2]))
    else:
        ok("正文里没有会破坏 XML 的裸符号")

    print()
    print("=" * 66)
    if fails:
        print("自检发现问题 %d 项，请看上面的 [有问题] 行" % len(fails))
        return 1
    print("自检全部通过 —— 汉化补丁完好")
    return 0


if __name__ == "__main__":
    sys.exit(main())
