# -*- coding: utf-8 -*-
"""
裸体评价更多看法 简体汉化 —— 完整性自检工具

用途：随时检查这个汉化补丁是否完好。
用法：python verify_patch.py
说明：不需要任何额外文件，工具会自己去读游戏目录里的原模组做比对。

路径解析顺序（可换电脑不用改代码）：
  汉化包目录：环境变量 NMMO_PATCH  → 脚本所在目录的上一级 → 常见安装路径
  原模组目录：环境变量 NMMO_MOD   （更多看法 opinions）
             环境变量 NMMO_MOD2  （裸体评价本体）       → 常见安装路径

修订记录
--------
2026-10-08
  1. 修复「重复键检测」永远报正常的 bug —— 原实现遍历的是 dict，天然不可能出现重复。
  2. 新增「DefInjected 子目录名是否对应真实 Def 类型」检查。目录名写错会让整类翻译被
     RimWorld 静默丢弃，这是本汉化当初要解决的核心问题，原版自检反而没查。
  3. 路径不再写死单一路径。
  4. 新增两条【提示】（不计入失败）：label 覆盖情况、会显示成「名字's」的所有格占位符。

2026-10-15（对应 v1.2.9）
  5. 【3】补上「原版 Def 类型」常识表。原先只认识原模组 XML 里出现过的类型，
     于是原版类型 HediffDef / ThoughtDef / TraitDef 被误判成「目录名写错」。
  6. 【4】把「裸体评价」本体也纳入扫描。原先只扫 opinions 一个模组，
     于是指向本体的键（BraStatus.* 等 326 条）被误判成悬空引用。
  7. 【2】【7】把 OwnInjections\\ 一并纳入统计。v1.2.7 起正文已改走
     「自有清单整列表注入」，原先只看 Languages\\ 会把 5076 个容器全误判成「没翻译」。
  8. 【5】新增「整列表条数与原模组是否一致」校验（原先只查索引式下标越界）。
  9. 新增【11】：防止 OwnInjections\\ 被误移回 Languages\\（移回去 = 译文全部失效）。
"""
import os, re, sys, io
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AMP = chr(38)      # & 符号本身，用 chr() 写出来避免转义混乱

HERE = os.path.dirname(os.path.abspath(__file__))
RIM_MODS = r"D:\steam\steamapps\common\RimWorld\Mods"
RIM_MODS2 = r"D:\Steam\steamapps\common\RimWorld\Mods"

CAND_PATCH = [
    os.environ.get("NMMO_PATCH"),
    os.path.dirname(HERE),
    os.path.join(RIM_MODS, "裸体评价更多看法-汉化修复"),
    os.path.join(RIM_MODS2, "裸体评价更多看法-汉化修复"),
]
CAND_MOD = [                     # 更多看法（opinions）
    os.environ.get("NMMO_MOD"),
    os.path.join(RIM_MODS, "NudityMattersMore_opinions"),
    os.path.join(RIM_MODS2, "NudityMattersMore_opinions"),
]
CAND_MOD2 = [                    # 裸体评价本体（Nudity Matters More）
    os.environ.get("NMMO_MOD2"),
    os.path.join(RIM_MODS, "RJW-功能-裸体评价"),
    os.path.join(RIM_MODS2, "RJW-功能-裸体评价"),
]

# 原版 Def 类型常识表：汉化包会覆盖原版/前置本体的类型，但它们不在原模组 XML 里出现，
# 只按「原模组扫到的类型」判断目录名会把它们误报成错误。
VANILLA_TYPES = {
    "HediffDef", "ThoughtDef", "TraitDef", "PawnKindDef", "ThingDef", "RecipeDef",
    "ResearchProjectDef", "FactionDef", "MemeDef", "PreceptDef", "RitualPatternDef",
    "RitualBehaviorDef", "RitualOutcomeEffectDef", "GeneDef", "XenotypeDef", "AbilityDef",
    "BodyPartDef", "DamageDef", "SoundDef", "InteractionDef", "MentalStateDef", "JobDef",
    "WorkTypeDef", "TerrainDef", "BiomeDef", "WeatherDef", "IncidentDef", "QuestScriptDef",
    "StatDef", "RoomRoleDef", "LifeStageDef", "HairDef", "BeardDef", "TattooDef",
    "ApparelLayerDef", "BodyTypeDef", "HeadTypeDef", "NeedDef", "ConceptDef",
    "DesignationDef", "PawnRelationDef", "PsychicRitualDef", "ScenPartDef", "RulePackDef",
    "LetterDef", "DutyDef", "MoteDef", "EffecterDef", "FleckDef", "FilthDef",
    "StuffCategoryDef", "ThingCategoryDef", "SpecialThingFilterDef", "StockGeneratorDef",
    "PawnGroupMakerDef", "SitePartDef", "WorldObjectDef", "TileMutatorDef", "RoomStatDef",
    "ThoughtDef", "MeditationFocusDef", "HediffGiverSetDef", "SoundDef", "SongDef",
}

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
MOD2 = pick(CAND_MOD2, "About")

SKIP_TAGS = ("Def", "Patch", "Operation", "li", "members", "assembly")


def is_definjected(sub):
    """这个相对目录是不是 DefInjected。

    Keyed 键（Languages\\<lang>\\Keyed\\*.xml）与 Def 没有对应关系，不能拿去做
    「键名是否指向真实 Def」的检查 —— 否则 NMM_PrudeDraft 这类由 C# 用
    Translate() 读取的键会被误报成悬空引用。"""
    return "DefInjected" in sub.replace("\\", "/").split("/")


def collect_defs(mod_dirs):
    """从原模组（可多个）收集：Def 名 -> 正文条数；有 label 的 Def 名；出现过的 Def 类型名。"""
    info = {}
    labelled = set()
    types = set()
    for mod_dir in mod_dirs:
        if not os.path.isdir(mod_dir):
            continue
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
                    if name not in info or cnt:
                        info[name] = cnt
                    if has_label:
                        labelled.add(name)
    return info, labelled, types


def find_definjected(patch, top):
    langs = os.path.join(patch, top)
    if not os.path.isdir(langs):
        return None
    for lang in sorted(os.listdir(langs)):
        cand = os.path.join(langs, lang, "DefInjected")
        if os.path.isdir(cand):
            return cand
    return None


def collect_patch_keys(patch):
    """收集汉化包里的全部键。Languages\\ 与 OwnInjections\\ 都要读。

    返回 entries: (相对目录, 键名) -> (文本, 子元素个数)
    """
    entries = {}
    order = []
    nfile = nkey = 0
    bad = []
    dups = []
    for top in ("Languages", "OwnInjections"):
        base = os.path.join(patch, top)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".xml"):
                    continue
                p = os.path.join(root, fn)
                nfile += 1
                try:
                    r = ET.parse(p).getroot()
                except Exception as e:
                    bad.append((top + "/" + fn, str(e)))
                    continue
                if r.tag != "LanguageData":
                    bad.append((top + "/" + fn, "根标签是 %s" % r.tag))
                for el in r:
                    nkey += 1
                    key = (os.path.relpath(root, patch), el.tag)
                    if key in entries:
                        dups.append((fn, el.tag))
                    else:
                        order.append(key)
                    entries[key] = (el.text or "", len(list(el)))
    return entries, order, nfile, nkey, bad, dups


def main():
    print("=" * 66)
    print("裸体评价更多看法 简体汉化 —— 完整性自检")
    print("=" * 66)
    print("  汉化包：  " + PATCH)
    print("  原模组①：" + MOD + "   (opinions)")
    print("  原模组②：" + MOD2 + "   (本体)")

    if not os.path.isdir(PATCH):
        print("找不到汉化补丁目录：" + PATCH)
        return 1
    if not os.path.isdir(MOD) and not os.path.isdir(MOD2):
        print("找不到原模组目录：" + MOD)
        return 1

    print()
    print("【1】读取原模组，取得所有 Def 名字与类型")
    real, labelled, types = collect_defs([MOD, MOD2])
    ok("原模组共有 %d 个 Def、%d 种 Def 类型" % (len(real), len(types)))

    langdir = os.path.join(PATCH, "Languages")
    owndir = os.path.join(PATCH, "OwnInjections")

    print()
    print("【2】逐个检查 XML 文件能否正常打开（Languages + OwnInjections）")
    entries, order, nfile, nkey, bad, dups = collect_patch_keys(PATCH)
    if bad:
        for fn, e in bad[:5]:
            fail("%s 打不开：%s" % (fn, e))
    nlang = sum(1 for k in entries if k[0].split(os.sep)[0] == "Languages")
    nown = sum(1 for k in entries if k[0].split(os.sep)[0] == "OwnInjections")
    ok("%d 个文件、%d 个容器（Languages %d / OwnInjections %d）" % (nfile, nkey, nlang, nown))

    print()
    print("【3】检查 DefInjected 子目录名是否对应真实存在的 Def 类型")
    print("       （目录名写错 = 该目录下所有翻译被游戏静默丢弃）")
    known = set(types) | VANILLA_TYPES
    for top in ("Languages", "OwnInjections"):
        defdir = find_definjected(PATCH, top)
        if defdir is None:
            continue
        subs = [d for d in sorted(os.listdir(defdir)) if os.path.isdir(os.path.join(defdir, d))]
        bad_dirs = []
        for d in subs:
            if d in known:
                continue
            if len(d) > 3 and d[:-1] in known:      # 游戏自己也允许目录名末尾多一个字符
                continue
            bad_dirs.append(d)
        if bad_dirs:
            fail("[%s] 有 %d 个目录名不对应任何 Def 类型（其翻译会被整批丢弃）：%s"
                 % (top, len(bad_dirs), bad_dirs))
            hint("已知类型（原模组 + 原版）共 %d 种；原模组里出现过的有：%s"
                 % (len(known), sorted(types)[:8]))
        else:
            ok("[%s] 全部 %d 个目录都指向真实存在的 Def 类型" % (top, len(subs)))

    print()
    print("【4】检查键名是否指向真实存在的 Def（悬空引用会让翻译无效）")
    dangling = [tag for (sub, tag) in entries
                if is_definjected(sub) and tag.split(".")[0] not in real]
    if dangling:
        fail("有 %d 个键找不到对应的 Def，例如：%s" % (len(dangling), dangling[:3]))
    else:
        ok("全部键名有效，没有悬空引用")

    print()
    print("【5】检查正文条数（索引式下标越界 / 整列表条数不符）")
    oob = []          # 索引式：下标越界
    cntbad = []       # 整列表：条数与原模组不一致
    for (sub, tag), (text, kids) in entries.items():
        m = re.match(r"^(.+)\.opinionTexts\.(\d+)$", tag)
        if m:
            name, idx = m.group(1), int(m.group(2))
            if name in real and idx >= real[name]:
                oob.append(tag)
            continue
        m = re.match(r"^(.+)\.opinionTexts$", tag)
        if m:
            name = m.group(1)
            want = real.get(name)
            if want is not None and kids != want:
                cntbad.append((tag, want, kids))
    if oob:
        fail("有 %d 个索引式下标越界，例如：%s" % (len(oob), oob[:3]))
    else:
        ok("索引式下标全部合法")
    if cntbad:
        fail("有 %d 个整列表条数与原模组不一致，例如：%s" % (len(cntbad), cntbad[:3]))
    else:
        ok("整列表条数与原模组一致")

    print()
    print("【6】检查有没有同一个键被翻译两次")
    if dups:
        fail("有 %d 个重复键，例如：%s" % (len(dups), dups[:3]))
    else:
        ok("没有重复键")

    print()
    print("【7】检查有没有漏译的正文（两种写法都算覆盖：整列表 / 索引式）")
    covered_full = set()
    covered_idx = {}
    for (sub, tag) in entries:
        m = re.match(r"^(.+)\.opinionTexts$", tag)
        if m:
            covered_full.add(m.group(1))
            continue
        m = re.match(r"^(.+)\.opinionTexts\.(\d+)$", tag)
        if m:
            covered_idx.setdefault(m.group(1), set()).add(int(m.group(2)))
    notfull = []
    for name, cnt in real.items():
        if cnt == 0:
            continue
        if name in covered_full:
            continue
        if len(covered_idx.get(name, set())) == cnt:
            continue
        notfull.append((name, cnt, len(covered_idx.get(name, set()))))
    if notfull:
        fail("有 %d 个 Def 的正文没翻译完整，例如：%s" % (len(notfull), notfull[:3]))
    else:
        ok("全部 %d 个 Def 的正文都翻译完整" % len([1 for c in real.values() if c > 0]))

    print()
    print("【8】检查译文正文里有没有会破坏 XML 的裸符号")
    print("       （注释里的 " + AMP + " 号是合法的，不参与检查）")
    bad_amp = []
    for top in ("Languages", "OwnInjections"):
        base = os.path.join(PATCH, top)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".xml"):
                    continue
                txt = io.open(os.path.join(root, fn), encoding="utf-8-sig").read()
                body = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
                for m in re.finditer(AMP + r"(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", body):
                    bad_amp.append((fn, body[max(0, m.start() - 30):m.start() + 30]))
    if bad_amp:
        fail("有 %d 处未转义的 " + AMP + " 符号，例如：%s" % (len(bad_amp), bad_amp[:2]))
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
    pcount = sum(text.count(ph) for (text, _k) in entries.values() for ph in poss)
    if pcount:
        hint("译文里有 %d 处 %s 之类的占位符。" % (pcount, poss[0]))
        hint("原模组把它们替换成「名字 + 's」（英文撇号 s），中文文本里会显示成「张三's」。")
    else:
        ok("没有会显示成「名字's」的占位符")

    print()
    print("【11】提示：OwnInjections 是否被误移回 Languages（移回去 = 正文全部失效）")
    wrong = [sub for (sub, tag) in entries
             if sub.split(os.sep)[0] == "Languages" and re.search(r"\.opinionTexts$", tag)]
    if wrong:
        fail("Languages\\ 下出现了 %d 个「整列表」键（游戏会拒绝并记翻译错误）：%s"
             % (len(wrong), sorted(set(wrong))[:3]))
        hint("这些应该放在 OwnInjections\\ 下，由补丁 DLL 在运行时注入。")
    else:
        ok("没有错位的整列表键")

    print()
    print("=" * 66)
    if fails:
        print("自检发现问题 %d 项，请看上面的 [有问题] 行" % len(fails))
        return 1
    print("自检全部通过 —— 汉化补丁完好")
    return 0


if __name__ == "__main__":
    sys.exit(main())
