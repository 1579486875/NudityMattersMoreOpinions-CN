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
using HarmonyLib;
using Verse;

// 版本号与 About\About.xml 的 <modVersion> 保持一致（模组纪律，游戏不校验它）。
[assembly: System.Reflection.AssemblyVersion("1.4.8.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.4.8.0")]
[assembly: System.Reflection.AssemblyInformationalVersion("1.4.8")]

namespace GNH.NMM.Combined.ZH
{
    [StaticConstructorOnStartup]
    public static class Bootstrap
    {
        private const string HarmonyId = "gnh.cn.cys.nmm.combined.zh";
        private static bool installed;

        static Bootstrap()
        {
            if (installed) return;
            installed = true;
            try
            {
                var t = AccessTools.TypeByName("NudityMattersMore.EnhancedNmmTabRenderer");
                if (t == null)
                {
                    Log.Warning("[NMM 汉化] 找不到 EnhancedNmmTabRenderer —— 原模组可能更新了，增强界面保持英文。");
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

    public static class EnhancedText
    {
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

        public static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> codes)
        {
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
