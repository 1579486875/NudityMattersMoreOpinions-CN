// ==========================================================================
// 【翻译补丁】1.7 合并版「增强界面」的硬编码文字汉化
// ==========================================================================
//
// 【症状】    [OWL] NMM Combined Edition 把小人标签页做成两套样式，
//             「增强版」（Enhanced）那一套的标题、分组名、提示语全是英文，
//             且 Keyed / DefInjected 都覆盖不到。
//
// 【根因】    合并版新增的 NudityMattersMore.EnhancedNmmTabRenderer 把界面文字
//             全部硬编码在 C# 里，没有走 Translator.Translate。
//             证据：反编译该类可见大量 ldstr "Opinions"/"No saved opinions ..." 常量。
//
// 【修法】    给该类型所有 DeclaredOnly 方法挂同一个 Transpiler，
//             把 IL 里的 ldstr 常量按字典换成中文；字典外的原样不动。
//             为什么用反射遍历方法而不是逐个 [HarmonyPatch]：
//               作者可能加方法，反射能自动覆盖到，不用回来改代码。
//             禁改清单（Def 名 / Keyed 键名，替换了会查不到表）：
//               "Chest" "Genitals" "Gonads" "Anus" "Testicles"
//               "NMM_PrudeScore" "NMM_VoyScore" "NMM_ExhibScore" "MessageCantSelectOffMapPawn"
//
// 【自动让路】 TypeByName("NudityMattersMore.EnhancedNmmTabRenderer") 返回 null 时
//             直接 return —— 1.6 原版没有这个类，所以整段不执行，只留一条日志。
//             单方法 patch 失败也只记一条警告，不影响其它方法。
// ==========================================================================

// [OWL] NMM Combined Edition —— 增强界面（EnhancedNmmTabRenderer）汉化补丁
//
// 背景：合并版新增的「增强版」小人标签页渲染器（NudityMattersMore.EnhancedNmmTabRenderer）
//       把界面文字**全部硬编码**在 C# 里，没有走 Translator.Translate，
//       所以 Keyed / DefInjected 都覆盖不到。
// 做法：给该类型的每个方法挂 Transpiler，把 IL 里的 ldstr 常量换成中文。
//       只替换下表明确列出的串，其余原样不动。
// 注意：下面这些**绝对不能**替换（它们是 Def 名 / Keyed 键名，用于查表）：
//       "Chest" "Genitals" "Gonads" "Anus" "Testicles"
//       "NMM_PrudeScore" "NMM_VoyScore" "NMM_ExhibScore" "MessageCantSelectOffMapPawn"

using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System;
using System.Collections.Generic;
using HarmonyLib;
using Verse;

// 版本号与 About\About.xml 的 <modVersion> 保持一致（模组纪律，游戏不校验它）。
[assembly: System.Reflection.AssemblyVersion("1.5.7.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.5.7.0")]
[assembly: System.Reflection.AssemblyInformationalVersion("1.5.7")]

namespace GNH.NMM.Combined.ZH
{
    [StaticConstructorOnStartup]
    /// <summary>
    /// 独立 DLL 的入口：给 `NudityMattersMore.EnhancedNmmTabRenderer` 的**全部**方法挂同一个 Transpiler，
    /// 把 IL 里的 `ldstr` 常量按 `EnhancedText.Map` 换成中文。
    ///
    /// 为什么单独做成一个 DLL：合并版的「增强界面」文案改动频繁，单独一个程序集
    /// 可以只重编它（13 KB）而不动 45 KB 的主补丁，发布时也便于说清「哪个文件管哪块」。
    ///
    /// ⚠ 它与 `NMMOpinionsChineseUI.dll` 里那份 `Zh.EnhancedText`（33 条）**功能重叠**，
    /// 本 DLL 的 103 条是超集且安装更早，所以实际生效的是本 DLL —— 详见主补丁里那张表上方的注释。
    /// </summary>
    public static class Bootstrap
    {
        /// <summary>Harmony 实例 id。**改了等于换了一个补丁集合**：旧 id 装的补丁不会被卸载，会叠加。</summary>
        private const string HarmonyId = "gnh.cn.cys.nmm.combined.zh";
        /// <summary>安装守卫：静态构造理论上只跑一次，这里再兜一层，防止将来被改成非静态构造后重复 Patch。</summary>
        private static bool installed;

        /// <summary>
        /// 模组入口：由 CLR 在 `[StaticConstructorOnStartup]` 类首次被访问时执行一次。
        /// 这一半装的是「增强界面文字替换」—— 合并版把大量文案写死在 C# 里，
        /// 只能反射找到那些界面方法、把它们返回的字符串换成中文。
        /// 目标方法找不到就跳过并记一行日志，不会抛异常。
        /// </summary>
        static Bootstrap()
        {
            if (installed) return;
            installed = true;
            try
            {
                var t = AccessTools.TypeByName("NudityMattersMore.EnhancedNmmTabRenderer");
                if (t == null)
                {
                    // 【2026-11-16 改】分池实测：EnhancedNmmTabRenderer 只在 1.7 的合并版里存在，
                    // 1.6 的两个独立模组本来就没有「增强界面」这个概念。
                    // 所以 1.6 下这条缺失**是预期内的**，不该打 Warning（那会让 1.6 玩家每次启动都以为坏了）。
                    // 判据：OpinionTextTranslator 在不在 —— 那是主补丁里已经用来区分两条正文通道的同一个信号。
                    bool isCombined17 = AccessTools.TypeByName(
                        "NudityMattersMore_opinions.OpinionTextTranslator") != null;
                    if (isCombined17)
                        Log.Warning("[NMM 汉化] 找不到 EnhancedNmmTabRenderer —— 原模组可能更新了，增强界面保持英文。");
                    else
                        Log.Message("[NMM 汉化] 1.6 的两个独立模组没有「增强界面」（EnhancedNmmTabRenderer），"
                                    + "本补丁不适用；正文由 OwnInjections 通道提供。");
                    return;
                }
                var harmony = new Harmony(HarmonyId);
                int n = 0;
                foreach (var m in t.GetMethods(BindingFlags.Instance | BindingFlags.Static |
                                               BindingFlags.Public | BindingFlags.NonPublic |
                                               BindingFlags.DeclaredOnly))
                {
                    if (m.IsAbstract || m.ContainsGenericParameters) continue;
                    if (m.GetMethodBody() == null) continue;
                    try
                    {
                        harmony.Patch(m, null, null,
                            new HarmonyMethod(typeof(EnhancedText), nameof(EnhancedText.Transpiler)));
                        n++;
                    }
                    catch (System.Exception e)
                    {
                        Log.Warning("[NMM 汉化] 跳过 " + m.Name + "：" + e.Message);
                    }
                }
                Log.Message("[NMM 汉化] 增强界面补丁已应用，共 " + n + " 个方法。");
            }
            catch (System.Exception e)
            {
                Log.Warning("[NMM 汉化] 增强界面补丁未应用：" + e.Message);
            }
        }
    }

    /// <summary>
    /// 增强界面的英文 → 中文对照表 + Transpiler。
    ///
    /// `Map` 是**超集**（103 条），主补丁里那份 `Zh.EnhancedText`（33 条）全部被它覆盖。
    /// 要改增强界面的译文请改这里；改另一份不会在游戏里生效。
    ///
    /// 禁改清单（Def 名 / Keyed 键名，替换了会让运行时查不到表）：
    /// `Chest` / `Genitals` / `Gonads` / `Anus` / `Testicles` / `NMM_PrudeScore` / `NMM_VoyScore`
    /// / `NMM_ExhibScore` / `MessageCantSelectOffMapPawn` —— 这些字符串既当界面文字又当键，必须原样透传。
    /// </summary>
    public static class EnhancedText
    {
        /// <summary>
        /// 英文 → 中文对照表（103 条）。键是 IL 里的 `ldstr` 原文，值是中文。
        /// **表里没有的字符串会原样透传** —— 所以宁可少收几条，也不要把 Def 名/键名误收进来。
        /// </summary>
        public static readonly Dictionary<string, string> Map =
            new Dictionary<string, string>
            {
                // ── 顶栏 ──
                { "Awareness", "觉察" },
                { "Style: Vanilla", "样式：原版" },
                { "Style: Enhanced", "样式：增强" },
                { "Overview", "概览" },
                { "Relationships", "关系" },
                { "History", "历史" },

                // ── 部位表行标题 ──
                // 2026-11-14 反编译 DrawOpinionDirection 发现 "Testicles" 是硬编码。
                // 4 个列头（Body part / Opinion / Size / Seen / aware）已在下方的
                // 「对比表头」段存在，这里**不能重复** —— 集合初始化器重复键会在
                // 运行时抛 ArgumentException，编译期查不出来。
                { "Testicles", "睾丸" },

                // ── 概览页 ──
                { "CURRENT STATE", "当前状态" },
                { "Force not covering", "强制不遮挡" },
                { "When enabled, this pawn will not cover their body with their hands.",
                  "启用后，这个小人不会用手遮挡身体。" },
                { "SELF ASSESSMENT", "自我评价" },
                { "RECORDED OBSERVATIONS", "已记录的观察" },
                { "Counts recorded NMM observation events, not unique pawns. Repeated observations can increase these totals.",
                  "统计的是已记录的观察事件次数，不是人数。反复观察会让这些数字增加。" },
                { "Seen by this pawn", "此小人看过" },
                { "Lifetime count of recorded NMM events where this pawn observed another pawn.",
                  "此小人观察他人以来累计记录的事件数。" },
                { "Involving this pawn", "涉及此小人" },
                { "Lifetime count of recorded NMM events where another pawn observed this pawn.",
                  "他人观察此小人以来累计记录的事件数。" },
                { "Last five days", "近五天" },
                { "Recorded NMM events in either direction during the last five in-game days.",
                  "最近五个游戏日内，任一方向记录的 NMM 事件数。" },

                // ── 当前状态 ──
                { "ACTIVE STATE", "生效状态" },
                { "Fixated on: ", "迷恋对象：" },
                { "Fixation level: ", "迷恋等级：" },
                { " / 4", " / 4" },
                { "Type: ", "类型：" },
                { "Lover", "情人" },
                { "Voyeur interest", "窥视兴趣" },
                { " · repeat interest", " · 重复兴趣" },
                { "Focus: ", "关注点：" },
                { "Partial exposure", "部分暴露" },
                { "Full observation", "完整观察" },
                { "Next stage: ", "下一阶段：" },
                { "Modesty", "体面" },
                { "Voyeurism", "窥视" },
                { "Exhibitionism", "暴露" },
                { "No active NMM fixation or score applies to this pawn.",
                  "此小人当前没有生效的 NMM 迷恋或评分。" },

                // ── 评分档位 ──
                { "Intact", "完好" },
                { "Breached", "被突破" },
                { "Compromised", "受损" },
                { "Stripped", "被剥光" },
                { "Frustrated", "欲求不满" },
                { "Interested", "感兴趣" },
                { "Pleased", "满意" },
                { "Thrilled", "兴奋难耐" },
                { "Amused", "觉得有趣" },

                // ── 通用 ──
                { "Unknown", "未知" },

                // ── 名册页 ──
                { "People", "人物" },
                { "Search by pawn name.", "按小人名字搜索。" },
                { "Cycles relation, name, and most-recently-seen order.",
                  "在「关系／名字／最近见过」之间循环切换。" },
                { "Choose All, Female (including Trap and Futa), or Male.",
                  "可选「全部」、「女性（含伪娘与扶她）」或「男性」。" },
                { "Choose All, Female, Male, Trap, or Futa.",
                  "可选「全部」、「女性」、「男性」、「伪娘」或「扶她」。" },
                { "Sort:", "排序：" },
                { "Click to compare. Right-click to switch this tab to ", "点击对比。右键把此页切换到 " },
                { "No matching pawns.", "没有符合条件的小人。" },
                { "People: ", "人物：" },
                { "Gender: All", "性别：全部" },
                { "Gender: ", "性别：" },
                { "Colony", "殖民地" },
                { "Prison", "监狱" },
                { "Other", "其他" },
                { "All", "全部" },
                { "Female", "女性" },
                { "Male", "男性" },
                { "Trap", "伪娘" },
                { "Futa", "扶她" },
                { "Name", "名字" },
                { "Recent", "最近" },
                { "Relation", "关系" },

                // ── 关系标签 ──
                { "No relationship", "无关系" },
                { "Rival", "敌对" },
                { "Friend", "朋友" },
                { "Family", "家人" },
                { "Colonist", "殖民者" },
                { "Caravan", "商队" },
                { "Prisoner", "囚犯" },
                { "Away", "外出" },
                { "Off map · ", "地图外 · " },
                { "Off map", "地图外" },
                { "Elsewhere", "在别处" },
                { "Hostile", "敌对势力" },
                { "Visitor", "访客" },
                { "On map", "在地图上" },

                // ── 对比表头 ──
                { "Body part", "部位" },
                { "Opinion", "看法" },
                { "Size", "尺寸" },
                { "Seen / aware", "看过／知情" },
                { ": unavailable", "：不可用" },
                { "Not observed", "未观察" },
                { "Not seen", "未看过" },
                { "Now", "刚刚" },
                { " · aware", " · 知情" },
                { " · unaware", " · 不知情" },
                { " was aware that ", " 知道 " },
                { " saw them.", " 看到了自己。" },
                { " was not aware when ", " 不知道 " },

                // ── 关系详情 ──
                { "Choose a pawn from the list to see what each pawn thinks about the other.",
                  "从列表中选择一名小人，查看双方彼此的看法。" },
                { " · comparison in both directions", " · 双向对比" },
                { " about ", " 对 " },

                // ── 历史页 ──
                { "'s history", "的历史" },
                { "Opinions", "看法" },
                { "Actions", "行为" },
                { "No saved opinions have been recorded for this pawn yet.",
                  "此小人还没有任何已保存的看法记录。" },
                { "No NMM actions have been recorded for this pawn yet.",
                  "此小人还没有任何 NMM 行为记录。" },
                { "Day ", "第 " },
            };

        // Transpiler：在 IL 层面把 EnhancedNmmTabRenderer 里那些 ldstr（硬编码英文常量）
        // 换成字典里的中文。
        //
        // 为什么必须用 Transpiler 而不是 Keyed/DefInjected：
        //   合并版把界面文字直接写在 C# 里（不走 Translator.Translate），
        //   翻译表根本覆盖不到。只能在 IL 里改。
        //
        // 匹配策略是「整串精确相等」而不是「包含」——
        //   包含匹配会把 "Style" 这种短词误替换到别的句子里。
        // ── 【2026-11-16 加】语言判断 ──
        // 主补丁里每处 Transpiler 开头都有 `if (!Zh.GameIsChinese()) return codes;`，
        // 而本 DLL 原先**没有** —— 英文/繁体玩家装了本包时，只有「增强界面」这段会变中文，
        // 与其它地方的中英混杂。这里补上同样口径的判断（独立 DLL 不能引用主补丁的 Zh，故自带一份）。
        private static bool? langIsChinese;
        private static string langKey;

        private static bool IsChinese()
        {
            try
            {
                var lang = LanguageDatabase.activeLanguage;
                if (lang == null) return true;          // 语言库还没建好 → 与主补丁同口径，照常汉化
                string fn = lang.folderName ?? string.Empty;
                if (langKey == fn && langIsChinese.HasValue) return langIsChinese.Value;
                bool v;
                if (fn.Equals("English", StringComparison.OrdinalIgnoreCase)
                    || fn.IndexOf("Traditional", StringComparison.OrdinalIgnoreCase) >= 0
                    || fn.IndexOf("繁體", StringComparison.Ordinal) >= 0
                    || fn.IndexOf("繁体", StringComparison.Ordinal) >= 0)
                    v = false;
                else
                    v = true;                            // 兜底：宁可替换（与主补丁一致）
                langKey = fn;
                langIsChinese = v;
                return v;
            }
            catch
            {
                return true;
            }
        }

        public static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> codes)
        {
            // 不是中文环境 → 原样放行（yield 方法里不能直接 return codes）
            if (!IsChinese())
            {
                foreach (var c0 in codes) yield return c0;
                yield break;
            }
            foreach (var c in codes)
            {
                if (c.opcode == OpCodes.Ldstr)
                {
                    var s = c.operand as string;
                    string zh;
                    if (s != null && Map.TryGetValue(s, out zh))
                        c.operand = zh;
                }
                yield return c;
            }
        }
    }
}
