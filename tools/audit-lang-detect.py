#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit-lang-detect.py · 语言判定判据表（两个 DLL 的镜像实现 + 场景断言）

## 为什么要它

2026-11-16 审查 D-03 改了两个 DLL 的「是不是中文环境」判据：

    NMMOpinionsChineseUI.dll · Zh.IsChineseLanguage(folderName, nativeName, englishName)
    GNH_NMM_Enhanced_ZH.dll  · EnhancedText.IsChinese()

改的原因是**旧版兜底 `return true`** 会把俄语 / 日语 / 德语玩家也判成中文，
于是 12 个 Transpiler 与 OwnListInjector 一起把界面和正文换成中文 —— 语言错乱。

改判据是**必须验证**的一类改动：判错一边，要么非中文玩家被误伤（原来的 bug），
要么中文玩家看到满屏英文（更糟，那是拉不回口碑的）。
所以这里把两份 C# 逻辑**逐行镜像成 Python**，用一张场景表跑一遍。

## 口径纪律

镜像代码必须与 C# 逐条对应，**改 C# 就要改这里**，否则这张表会开始骗人。
两处的对应关系写在各函数头上。

## 判据只有一条

**中文场景必须 true，非中文场景必须 false。**
任何一格不符 → exit 1。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ────────────────────────────────────────────────────────────────────────────
# 镜像 ①：NMMOpinionsChineseUI.Zh.IsChineseLanguage(folderName, nativeName, englishName)
#   源文件 tools/ui-patch-tester/NMMOpinionsChineseUI.cs 第 728 行起
# ────────────────────────────────────────────────────────────────────────────
def is_chinese_language(folder, native, english):
    # ① 明确是英文
    if folder and folder.strip().lower() == "english":
        return False

    # ② folderName 含 ChineseSimplified
    if folder and "chinesesimplified" in folder.lower():
        return True

    # ③ nativeName 含 简体 / 简中
    if native and ("简体" in native or "简中" in native):
        return True

    # ④ englishName 含 Simplified Chinese
    if english and "simplified chinese" in english.lower():
        return True

    # ⑤ 明确是繁体 → false
    if folder and ("traditional" in folder.lower() or "繁體" in folder or "繁体" in folder):
        return False
    if native and ("繁體" in native or "繁体" in native):
        return False
    if english and "traditional" in english.lower():
        return False

    # ⑥ 正向中文判据（本轮新增）
    if folder and "chinese" in folder.lower():
        return True
    if english and "chinese" in english.lower():
        return True
    if native and ("中文" in native or "漢" in native or "汉" in native):
        return True

    # ⑦ 判不出来 → 不是中文（本轮由 true 改成 false）
    return False


# ────────────────────────────────────────────────────────────────────────────
# 镜像 ②：GNH.NMM.Combined.ZH.EnhancedText.IsChinese()
#   源文件 tools/ui-patch-tester/GNH_NMM_Enhanced_ZH.cs 第 303 行起
#   注意：它**只看 folderName**，不看 nativeName / englishName —— 这是它原有的设计。
# ────────────────────────────────────────────────────────────────────────────
def enhanced_is_chinese(folder):
    fn = folder or ""
    if fn.lower() == "english":
        return False
    if ("traditional" in fn.lower() or "繁體" in fn or "繁体" in fn):
        return False
    if ("chinese" in fn.lower()
            or "中文" in fn
            or "漢" in fn
            or "汉" in fn):
        return True
    return False


# ────────────────────────────────────────────────────────────────────────────
# 场景表：(说明, folderName, nativeName, englishName, 期望结果)
# ────────────────────────────────────────────────────────────────────────────
CASES = [
    ("本机当前语言（带后缀的简中）", "ChineseSimplified (简体中文)", "简体中文", "ChineseSimplified", True),
    ("不带后缀的简中", "ChineseSimplified", "简体中文", "ChineseSimplified", True),
    ("别写法的简中（只有 nativeName 命中）", "Chinese (Simplified)", "简体中文", "Chinese (Simplified)", True),
    ("别写法的简中（只有 folderName 带 Chinese）", "ChineseSimplified (中文)", "中文", "Chinese", True),
    ("繁体（folderName）", "ChineseTraditional (繁體中文)", "繁體中文", "Traditional Chinese", False),
    ("繁体（只有 nativeName 是繁体）", "SomeFolder", "繁體中文", "SomeLang", False),
    ("英文", "English", "English", "English", False),
    ("俄语", "Russian (Русский)", "Русский", "Russian", False),
    ("日语", "Japanese (日本語)", "日本語", "Japanese", False),
    ("德语", "German (Deutsch)", "Deutsch", "German", False),
    ("法语", "French (Français)", "Français", "French", False),
    ("韩语", "Korean (한국어)", "한국어", "Korean", False),
    ("西班牙语", "Spanish (Español)", "Español", "Spanish", False),
    ("空文件夹名", "", "Русский", "Russian", False),
    ("全空", "", "", "", False),
]

# 增强 DLL 只看 folderName，所以它的期望值单独列（用同一批 folderName）
ENH_CASES = [
    ("ChineseSimplified (简体中文)", True),
    ("ChineseSimplified", True),
    ("Chinese (Simplified)", True),
    ("ChineseSimplified (中文)", True),
    ("ChineseTraditional (繁體中文)", False),
    ("English", False),
    ("Russian (Русский)", False),
    ("Japanese (日本語)", False),
    ("German (Deutsch)", False),
    ("", False),
]


def main():
    fails = 0
    print("=" * 78)
    print("① 主补丁 Zh.IsChineseLanguage(folderName, nativeName, englishName)")
    print("=" * 78)
    print("%-32s %-28s %-18s %-5s %-5s %s" % ("场景", "folderName", "englishName", "期望", "实际", "结果"))
    print("-" * 108)
    for label, f, n, e, want in CASES:
        got = is_chinese_language(f, n, e)
        okk = (got == want)
        if not okk:
            fails += 1
        print("%-32s %-28s %-18s %-5s %-5s %s"
              % (label, f, e, want, got, "✅" if okk else "❌"))

    print()
    print("=" * 78)
    print("② 增强界面 DLL EnhancedText.IsChinese()（只看 folderName）")
    print("=" * 78)
    print("%-34s %-5s %-5s %s" % ("folderName", "期望", "实际", "结果"))
    print("-" * 60)
    for f, want in ENH_CASES:
        got = enhanced_is_chinese(f)
        okk = (got == want)
        if not okk:
            fails += 1
        print("%-34s %-5s %-5s %s" % (f or "<空>", want, got, "✅" if okk else "❌"))

    print()
    print("=" * 78)
    if fails:
        print("❌ %d 格不符" % fails)
        return 1
    print("✅ 全部 %d 格符合（主补丁 %d + 增强界面 %d）" % (len(CASES) + len(ENH_CASES), len(CASES), len(ENH_CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
