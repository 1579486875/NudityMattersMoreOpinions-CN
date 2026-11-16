# -*- coding: utf-8 -*-
"""
修复 DefInjected/NamedIndex/ —— 目录名不是任何 Def 类型，游戏会整目录跳过并每次启动报红字。

判据（反编译 1.7.5005 rev1082 Verse.LoadedLanguage.LoadData）：

    foreach (VirtualDirectory directory4 in directory2.GetDirectories("*", TopDirectoryOnly))
    {
        string name = directory4.Name;
        Type typeInAnyAssembly = GenTypes.GetTypeInAnyAssembly(name);
        if (typeInAnyAssembly == null && name.Length > 3)
            typeInAnyAssembly = GenTypes.GetTypeInAnyAssembly(name.Substring(0, name.Length - 1));
        if (typeInAnyAssembly == null)
        {
            loadErrors.Add("Error loading language from ...: dir " + directory4.Name
                           + " doesn't correspond to any def type. Skipping...");
            continue;                         // ← 整目录丢弃
        }
        ...
    }

`NamedIndex` 解析不到任何类型 → 该目录 19 条键全部无效，且每次启动刷一条 loadError。

逐条判定这 19 条：
  · 10 条 ThoughtDef 命名索引 → 句柄写错（写的是 unwelcome_comparison / jealous_feelings，
    而原模组实际 stage label 是 "envy body" / "jealous" / "deeply jealous" …）。
    TranslationHandleUtility.GetElementIndexByHandle 找不到句柄会 throw
    "None of the list elements have a handle named X"，所以**不能**移到 ThoughtDef/。
    好在 ThoughtDef/ 目录里已有等价的数字索引版（stages.0.label / .description）→ 功能不缺。
  · 6 条 TraitDef 命名索引 → 句柄**完全正确**（原模组 degreeDatas 的 label 就是
    exhibitionist / prudish / voyeur，而 TraitDegreeData.untranslatedLabel 带
    [TranslationHandle]）。这 6 条是这 3 个特质唯一的中文来源 → **必须救回**，移到 TraitDef/。
  · 3 条指向抽象 Def（BaseSexPartOpinionDef / BaseSituationalOpinionDef）→ 抽象 Def 不在
    DefDatabase，GetDefSilentFail 返回 null → 必报 "Found no ... named ..." → 删。

本脚本：① 写出 TraitDef/GNH_TraitDegrees_Handle.xml；② 删除 NamedIndex 目录。
"""
import os
import sys
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 2026-11-16 改：原先硬编码 E:\TAML\_work\nmzh-git（旧 clone）
LANGS = [
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified", "DefInjected"),
    os.path.join(REPO, "v1.7", "Languages", "ChineseSimplified (简体中文)", "DefInjected"),
]

BODY = """<?xml version="1.0" encoding="utf-8"?>
<!--
  三个性向特质的「档位」译文（TraitDef.degreeDatas）。

  为什么用命名索引（degreeDatas.exhibitionist）而不是数字索引（degreeDatas.0）：
    RimWorld 的 TraitDegreeData.untranslatedLabel 带 [TranslationHandle] 特性，
    而 DefInjectionPackage.SetDefFieldAtPath 在遇到「既不是数字、也不是字段名」的
    路径段时会走 DefInjectionPathPartKind.ListHandle 分支，用
    TranslationHandleUtility.GetElementIndexByHandle 按「原始英文 label」定位元素。
    所以 degreeDatas.exhibitionist 精确指向 label="exhibitionist" 的那个 li ——
    作者以后往 degreeDatas 前面插新档位也不会错位。

  为什么必须放在 TraitDef/ 目录下：
    LoadedLanguage.LoadData 会把 DefInjected/ 每个子目录的名字当作 Def 类型名去
    GenTypes.GetTypeInAnyAssembly 解析；解析不到就
        loadErrors.Add("... dir X doesn't correspond to any def type. Skipping...")
    并把整个目录跳过。这三个键原先躺在 DefInjected/NamedIndex/ 下，而 NamedIndex
    不是任何 Def 类型 —— 于是它们从来没生效过（还每次启动刷一条红字）。

  句柄已逐个核对（1.7 原模组 Defs/TraitDefs/Traits_Singular.xml）：
    NMM_Exhibitionist → <label>exhibitionist</label>
    NMM_Prude         → <label>prudish</label>
    NMM_Voyeur        → <label>voyeur</label>
-->
<LanguageData>
  <NMM_Exhibitionist.degreeDatas.exhibitionist.label>&lt;color=#cc0099&gt;暴露狂&lt;/color&gt;</NMM_Exhibitionist.degreeDatas.exhibitionist.label>
  <NMM_Exhibitionist.degreeDatas.exhibitionist.description>{PAWN_nameDef}几乎是强迫性地想让人们看到{PAWN_objective}的裸体，经常为了刺激而不择手段。</NMM_Exhibitionist.degreeDatas.exhibitionist.description>
  <NMM_Prude.degreeDatas.prudish.label>&lt;color=#FFFFFF&gt;拘谨&lt;/color&gt;</NMM_Prude.degreeDatas.prudish.label>
  <NMM_Prude.degreeDatas.prudish.description>{PAWN_nameDef}的颜面是{PAWN_possessive}最重要的财产。{PAWN_pronoun}有时宁愿死也不愿失去它。</NMM_Prude.degreeDatas.prudish.description>
  <NMM_Voyeur.degreeDatas.voyeur.label>&lt;color=#FF9900&gt;视奸狂&lt;/color&gt;</NMM_Voyeur.degreeDatas.voyeur.label>
  <NMM_Voyeur.degreeDatas.voyeur.description>{PAWN_nameDef}痴迷于看别人裸体。如果{PAWN_pronoun}在看着你，{PAWN_pronoun}很可能是在想你衣服下面是什么。</NMM_Voyeur.degreeDatas.voyeur.description>
</LanguageData>
"""


def main():
    for di in LANGS:
        if not os.path.isdir(di):
            print("跳过（不存在）：%s" % di)
            continue
        tr = os.path.join(di, "TraitDef")
        if not os.path.isdir(tr):
            os.makedirs(tr)
        out = os.path.join(tr, "GNH_TraitDegrees_Handle.xml")
        with open(out, "w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write(BODY)
        print("写出 %s（%d 字节）" % (out, os.path.getsize(out)))

        ni = os.path.join(di, "NamedIndex")
        if os.path.isdir(ni):
            shutil.rmtree(ni)
            print("删除 %s" % ni)
        else:
            print("（无 NamedIndex）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
