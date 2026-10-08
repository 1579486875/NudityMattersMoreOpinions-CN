// 裸体评价更多看法 简体汉化 —— 界面补丁
//
// 为什么需要这个补丁：
//   原模组的「看法」标签页（ITab_Pawn_NMMOpinions）把界面文字**直接写死在 C# 代码里**，
//   没有走 RimWorld 的翻译系统。所以无论怎么做 XML 汉化，这些文字都不会变中文。
//   唯一办法是在运行时替换掉编译进 DLL 的英文字符串 —— 这就是本补丁做的事。
//
// 做法：
//   用 Harmony 的 Transpiler 遍历方法的 IL 指令，把里面的英文常量（ldstr 指令的操作数）
//   换成中文。只替换本文件明确列出的那些字符串，别的原样不动。
//
// 特别注意（改这个文件的人务必看）：
//   ① 大写的 "Chest" / "Genitals" / "Anus" 是**查 Def 用的名字**，绝不能替换！
//      要翻译的是小写的显示名 "chest" / "breasts" / "vagina" / "penis" / "genitals"。
//   ② "Не наблюдалось пока." 和 "No opinion def found" 是**代码里做判断用的**，也不能换。
//   ③ 本文件只在 Bootstrap 的静态构造函数里装一次补丁 —— CLR 保证静态构造函数只跑一次，
//      所以不会像 Mod 子类构造函数那样被重复安装（重复安装会让补丁层层叠加）。

using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using Verse;

namespace NMMOpinionsChineseUI
{
    /// <summary>加载入口。静态构造函数由 CLR 保证只执行一次。</summary>
    [StaticConstructorOnStartup]
    public static class Bootstrap
    {
        static Bootstrap()
        {
            var harmony = new Harmony("shark510.nuditymattersmoreopinions.zhfix.ui");
            int n = 0;

            // ① 看法标签页的主绘制方法（玩家看到的那一页）
            n += TryPatch(harmony, "NudityMattersMore_opinions.ITab_Pawn_NMMOpinions", "FillTab",
                          transpiler: nameof(Patches.Text_Transpiler));

            // ② 标签页下方的「情境看法日志」
            n += TryPatch(harmony, "NudityMattersMore_opinions.ITab_Pawn_NMMOpinions", "DrawOpinionLog",
                          transpiler: nameof(Patches.Text_Transpiler));

            // ③ 「A 对 B 的身体的看法：」这句表头（用 Prefix 直接给出中文，不走原方法）
            n += TryPatch(harmony, "NudityMattersMore_opinions.OpinionHelper", "GetHeaderLabel",
                          prefix: nameof(Patches.GetHeaderLabel_Prefix));

            // ④ 原模组作者留下的**俄语**弹窗消息（「XX 看到 YY 遮住身体」）
            n += TryPatch(harmony, "NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "ApplyFirstTimeThought_Prefix",
                          transpiler: nameof(Patches.Russian_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "ApplyRenewThought_Prefix",
                          transpiler: nameof(Patches.Russian_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "ApplyFirstTimeEverThought_Prefix",
                          transpiler: nameof(Patches.Russian_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "GetRelationsString",
                          transpiler: nameof(Patches.Russian_Transpiler));

            if (n > 0)
                Log.Message("[NMM 汉化] 界面补丁已应用，共处理 " + n + " 处。");
            else
                Log.Warning("[NMM 汉化] 界面补丁没找到任何目标方法 —— 原模组可能更新了，界面文字会保持英文。");
        }

        /// <summary>找到目标方法就装补丁，找不到只记一条警告，绝不让游戏崩。</summary>
        private static int TryPatch(Harmony harmony, string typeName, string methodName,
                                    string transpiler = null, string prefix = null)
        {
            try
            {
                Type t = AccessTools.TypeByName(typeName);
                if (t == null)
                {
                    Log.Warning("[NMM 汉化] 找不到类型：" + typeName);
                    return 0;
                }

                MethodBase target = AccessTools.Method(t, methodName);
                if (target == null)
                {
                    Log.Warning("[NMM 汉化] 找不到方法：" + typeName + "." + methodName);
                    return 0;
                }

                Type self = typeof(Patches);
                if (transpiler != null)
                    harmony.Patch(target, transpiler: new HarmonyMethod(self, transpiler));
                if (prefix != null)
                    harmony.Patch(target, prefix: new HarmonyMethod(self, prefix));

                return 1;
            }
            catch (Exception e)
            {
                Log.Error("[NMM 汉化] 给 " + typeName + "." + methodName + " 装补丁失败：" + e);
                return 0;
            }
        }
    }

    /// <summary>实际干活的补丁方法。</summary>
    public static class Patches
    {
        /// <summary>把 IL 里的英文界面文字换成中文。</summary>
        public static IEnumerable<CodeInstruction> Text_Transpiler(IEnumerable<CodeInstruction> codes)
        {
            if (!Zh.GameIsChinese()) return codes;      // 不是中文环境就原样放行
            return Zh.Rewrite(codes, Zh.UiText);
        }

        /// <summary>把 IL 里的俄语弹窗消息换成中文。</summary>
        public static IEnumerable<CodeInstruction> Russian_Transpiler(IEnumerable<CodeInstruction> codes)
        {
            if (!Zh.GameIsChinese()) return codes;
            return Zh.Rewrite(codes, Zh.RussianText);
        }

        /// <summary>
        /// 「A 对 B 的身体的看法：」这句表头。
        /// 直接返回中文并跳过原方法，比逐词替换更干净。
        /// </summary>
        public static bool GetHeaderLabel_Prefix(Pawn currentPawn, Pawn targetPawn,
                                                 bool isObserverMode, ref string __result)
        {
            if (!Zh.GameIsChinese()) return true;       // 不是中文环境就走原方法
            string a = (currentPawn != null) ? currentPawn.LabelCap.ToString() : "选中的角色";
            string b = (targetPawn != null) ? targetPawn.LabelCap.ToString() : "列表中的角色";

            if (targetPawn == null)
                __result = "对所选角色身体的看法：";
            else if (isObserverMode)
                __result = a + " 对 " + b + " 的身体的看法：";
            else
                __result = b + " 对 " + a + " 的身体的看法：";

            return false;   // 跳过原方法
        }
    }

    /// <summary>字符串替换表 + 替换引擎。</summary>
    internal static class Zh
    {
        /// <summary>
        /// 当前游戏语言是不是简体中文。
        ///
        /// 为什么要判断：补丁是无条件替换 IL 里的字符串的。如果不看语言，
        /// 玩家把游戏切成英文时，Def 里的翻译会失效（显示英文原文），
        /// 但界面文字仍然是中文 —— 变成中英混杂。所以只在中文环境下动手。
        ///
        /// 拿不到语言信息时返回 true（照常汉化）：游戏里不会走到这个分支，
        /// 但离线验证工具里没有语言系统，这样能让验证照常进行。
        /// </summary>
        public static bool GameIsChinese()
        {
            try
            {
                var lang = LanguageDatabase.activeLanguage;
                if (lang == null) return true;
                return lang.folderName == "ChineseSimplified";
            }
            catch
            {
                return true;
            }
        }

        /// <summary>
        /// 界面文字。
        /// 说明：这些字符串是原模组 C# 里内插字符串被编译器拆出来的**碎片**
        /// （例如 $"{a}'s opinion about {b}'s breasts:" 会变成
        ///   a + "'s opinion about " + b + "'s " + "breasts" + ":"），
        /// 所以替换值也要按碎片给，前后空格要保留 —— 拼接起来才是通顺的中文。
        /// </summary>
        public static readonly Dictionary<string, string> UiText =
            new Dictionary<string, string>(StringComparer.Ordinal)
        {
            // ── 顶部中间那行关系文字 ──
            { " observes Self",                    " 观察自己" },
            { " observes ",                        " 观察 " },

            // ── 下拉框与切换按钮 ──
            { "No pawn selected",                  "未选择角色" },
            { "Select Pawn...",                    "选择角色…" },
            { "Observe Self (",                    "观察自己（" },
            { "No pawns found",                    "没有找到角色" },
            { "Interaction Log",                   "互动日志" },
            { "Thoughts",                          "想法" },

            // ── 提示与错误 ──
            { "No pawn selected to view opinions.", "未选择角色，无法查看看法。" },
            { "Error: Cannot display opinion. Either observer, observed pawn, or observer's memory is missing.",
              "错误：无法显示看法。观察者、被观察者或观察者的记忆缺失。" },

            // ── 「谁对谁哪个部位的看法：」三处 ──
            { "'s opinion about ",                 " 对 " },
            { "'s ",                               " 的 " },
            { ":",                                 "：" },          // 半角冒号换全角，中文语境下总是对的
            { "'s anus:",                          " 的肛门：" },
            { " doesn't have any specific opinion about ", " 对 " },
            { "'s chest/nipples.",                 " 的胸部/乳头没有特别的看法。" },

            // ── 部位显示名（只换小写！大写的是 Def 名，见文件头的警告）──
            { "breasts",                           "乳房" },
            { "chest",                             "胸部" },
            { "vagina",                            "阴道" },
            { "penis",                             "阴茎" },
            { "genitals",                          "生殖器" },

            // ── 检测不到时的兜底提示 ──
            { "Chest opinion: N/A (No breasts detected)",     "胸部看法：无（未检测到乳房）" },
            { "Genitals opinion: N/A (No genitals detected)", "生殖器看法：无（未检测到生殖器）" },
            { "Anus opinion: N/A (No anus detected)",         "肛门看法：无（未检测到肛门）" },
            { "No situational opinions recorded yet.",        "暂未记录任何情境看法。" },
        };

        /// <summary>
        /// 俄语弹窗消息（原模组作者留下的）。
        /// 这些会以「消息」形式弹在屏幕左上角，玩家一定会看到。
        /// </summary>
        public static readonly Dictionary<string, string> RussianText =
            new Dictionary<string, string>(StringComparer.Ordinal)
        {
            { " увидел, как ",                                  " 看到 " },
            { " увидел, как кто-то впервые прикрывает ",        " 看到有人第一次遮住了 " },
            { " впервые прикрывает ",                           " 第一次遮住了 " },
            { " снова прикрывает ",                             " 又遮住了 " },
            { " впервые был(а) замечен(а) прикрывающим(ся) ",   " 第一次被发现遮住了 " },
            { " наготу.",                                       " 的身体。" },
            { " соперник ",                                     " 对手 " },
            { " друг ",                                         " 朋友 " },
        };

        /// <summary>
        /// 遍历 IL：遇到 ldstr（"把字符串常量压栈"）就查表，命中就换掉操作数。
        /// 用 yield return 逐条放行，不影响其它任何指令。
        /// </summary>
        public static IEnumerable<CodeInstruction> Rewrite(
            IEnumerable<CodeInstruction> codes, Dictionary<string, string> map)
        {
            foreach (CodeInstruction c in codes)
            {
                if (c.opcode == OpCodes.Ldstr && c.operand is string)
                {
                    string zh;
                    if (map.TryGetValue((string)c.operand, out zh))
                        c.operand = zh;
                }
                yield return c;
            }
        }
    }
}
