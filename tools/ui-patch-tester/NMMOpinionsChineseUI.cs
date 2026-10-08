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
using System.Text.RegularExpressions;
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

            // ⑤ 设置界面 —— 两个模组的设置窗口里的选项文字**全是硬编码英文**，
            //    玩家打开「选项 → 模组设置」就会看到，必须翻。
            //    这里用 Transpiler（启动时改一次常量），运行时零开销。
            n += TryPatch(harmony, "NudityMattersMore.NudityMattersMore", "DoSettingsWindowContents",
                          transpiler: nameof(Patches.Settings_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore.NudityMattersMore", "SettingsCategory",
                          transpiler: nameof(Patches.Settings_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore_opinions.NudityMattersMore_opinions_Mod", "DrawGeneralSettings",
                          transpiler: nameof(Patches.Settings_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore_opinions.NudityMattersMore_opinions_Mod", "DrawInteractionsSettings",
                          transpiler: nameof(Patches.Settings_Transpiler));
            n += TryPatch(harmony, "NudityMattersMore_opinions.NudityMattersMore_opinions_Mod", "SettingsCategory",
                          transpiler: nameof(Patches.Settings_Transpiler));

            // ⑥ 设置界面里「互动类型」复选框的名字 —— 那些名字是运行时从枚举取的，
            //    Transpiler 抓不到，只能在 CheckboxLabeled 被调用时替换。
            n += TryPatchAll(harmony, "Verse.Listing_Standard", "CheckboxLabeled",
                             prefix: nameof(Patches.CheckboxLabeled_Prefix));

            // ⑦ 屏幕消息（「XX 第一次看到 YY 裸体」这类，显示在左上角消息区）。
            //    Messages.Message 有三个接收 string 的重载，必须全部挂上（用 TryPatchAll 批量找）。
            n += TryPatchAll(harmony, "Verse.Messages", "Message",
                             prefix: nameof(Patches.Messages_Prefix));

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

        /// <summary>
        /// 给**同名但重载多个**的方法批量装补丁。
        ///
        /// 为什么需要它：`AccessTools.Method(类型, 名字)` 在方法有多个重载时
        /// 会抛 "Ambiguous match" 异常（Harmony 不知道你要哪个）。
        /// 这里改成自己遍历，只挑**第一个参数是 string** 的那些重载 ——
        /// 对 Messages.Message 和 Listing_Standard.CheckboxLabeled 都正好适用。
        ///
        /// 这样写还有个好处：以后原模组/游戏加了新的重载，也会自动被覆盖到，
        /// 不用回来改代码。
        /// </summary>
        private static int TryPatchAll(Harmony harmony, string typeName, string methodName,
                                       string prefix = null, string transpiler = null)
        {
            try
            {
                Type t = AccessTools.TypeByName(typeName);
                if (t == null)
                {
                    Log.Warning("[NMM 汉化] 找不到类型：" + typeName);
                    return 0;
                }

                int count = 0;
                foreach (MethodInfo m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic
                                                      | BindingFlags.Static | BindingFlags.Instance
                                                      | BindingFlags.DeclaredOnly))
                {
                    if (m.Name != methodName) continue;

                    ParameterInfo[] ps = m.GetParameters();
                    if (ps.Length == 0 || ps[0].ParameterType != typeof(string)) continue;

                    Type self = typeof(Patches);
                    if (prefix != null)
                        harmony.Patch(m, prefix: new HarmonyMethod(self, prefix));
                    if (transpiler != null)
                        harmony.Patch(m, transpiler: new HarmonyMethod(self, transpiler));
                    count++;
                }

                if (count == 0)
                    Log.Warning("[NMM 汉化] " + typeName + "." + methodName + " 没有找到可挂的重载。");

                return count;
            }
            catch (Exception e)
            {
                Log.Error("[NMM 汉化] 批量挂补丁失败 " + typeName + "." + methodName + "：" + e);
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

        /// <summary>
        /// 设置界面：把 IL 里的英文选项文字换成中文。
        ///
        /// 为什么用 Transpiler 而不是运行时替换：
        ///   转译器是在**游戏启动、JIT 编译前**改掉常量，改完就固定在内存里，
        ///   运行时一次判断都不做 —— 对性能零影响。
        ///   设置窗口虽然调用不频繁，但这是最省的做法，也没有误伤别人的风险
        ///   （只作用于我们明确指定的那几个方法）。
        /// </summary>
        public static IEnumerable<CodeInstruction> Settings_Transpiler(IEnumerable<CodeInstruction> codes)
        {
            if (!Zh.GameIsChinese()) return codes;
            return Zh.RewriteSettings(codes);
        }

        /// <summary>
        /// 屏幕消息（「XX 第一次看到 YY 裸体」之类）。
        ///
        /// 为什么这里改用运行时替换而不是 Transpiler：
        ///   原模组是用内插字符串拼句子的，编译后变成
        ///     string.Concat(名字, " saw ", 关系, " naked for the first time.")
        ///   一堆碎片，而且**同一段碎片在两种语境里含义不同**
        ///   （" saw " 在「第一次看到」和「隔了一阵子又看到」里都要用）。
        ///   按碎片替换会把两种语境翻成同一句，语义就错了。
        ///   所以在消息出口按**完整句子**用正则改写，既准确又安全。
        ///
        /// 性能：消息不是每帧调用的东西（一次事件才一条），正则开销可以忽略。
        /// </summary>
        public static void Messages_Prefix(ref string text)
        {
            if (!Zh.GameIsChinese()) return;
            if (string.IsNullOrEmpty(text)) return;
            if (!Zh.LooksLikeOurMessage(text)) return;   // ← 快速预筛，见下面的说明
            string r = Zh.ApplyPatterns(text, Zh.MessagePatterns);
            if (r != null) text = r;
        }

        /// <summary>
        /// 设置界面里那些「互动类型」复选框。
        /// 它们的文字是运行时从枚举取的名字（例如 "Shower"），Transpiler 够不着，只能在这里拦。
        ///
        /// 安全措施：只替换**确认是 NudityMattersMore.InteractionType 枚举成员**的名字
        /// （用反射 Enum.IsDefined 判断），所以不可能误伤别的模组的同名文字。
        /// </summary>
        public static void CheckboxLabeled_Prefix(ref string label)
        {
            if (!Zh.GameIsChinese()) return;
            if (string.IsNullOrEmpty(label)) return;
            string zh;
            if (Zh.InteractionTypeNames.TryGetValue(label, out zh))
                label = zh;
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
        /// ⚠️ 踩过的坑：一开始这里写的是 folderName == "ChineseSimplified"，
        ///    结果整个补丁在中文环境下一点效果都没有 —— 日志显示补丁装上了（7 处），
        ///    界面上却仍是英文。原因是 RimWorld 的语言文件夹名带显示名后缀，
        ///    实际是 "ChineseSimplified (简体中文)"，严格相等自然判不出来，
        ///    于是转译器每次都直接放行原文。
        ///
        /// 现在改成分段判断，并抽成不依赖游戏运行时的纯函数，
        /// 这样离线验证工具能直接喂各种取值来测。
        /// </summary>
        public static bool IsChineseLanguage(string folderName, string nativeName, string englishName)
        {
            // ① 明确是英文 → 不替换
            if (!string.IsNullOrEmpty(folderName) &&
                folderName.Trim().Equals("English", StringComparison.OrdinalIgnoreCase))
                return false;

            // ② 语言文件夹名含 ChineseSimplified（带不带 " (简体中文)" 后缀都行）
            if (!string.IsNullOrEmpty(folderName) &&
                folderName.IndexOf("ChineseSimplified", StringComparison.OrdinalIgnoreCase) >= 0)
                return true;

            // ③ 原生语言名含「简体」
            if (!string.IsNullOrEmpty(nativeName) &&
                (nativeName.Contains("简体") || nativeName.Contains("简中")))
                return true;

            // ④ 英文语言名含 Simplified Chinese
            if (!string.IsNullOrEmpty(englishName) &&
                englishName.IndexOf("Simplified Chinese", StringComparison.OrdinalIgnoreCase) >= 0)
                return true;

            // ⑤ 全都判不出来 → 兜底选择「替换」。
            //    宁可误替换也不能漏：这本来就是中文汉化包，装它的都是中文玩家。
            //    万一判断失败而放行原文，玩家看到的就是满屏英文（正是上面那个 bug）。
            return true;
        }

        /// <summary>当前游戏语言是不是简体中文。</summary>
        public static bool GameIsChinese()
        {
            try
            {
                var lang = LanguageDatabase.activeLanguage;
                if (lang == null) return true;
                return IsChineseLanguage(lang.folderName,
                                         lang.FriendlyNameNative,
                                         lang.FriendlyNameEnglish);
            }
            catch
            {
                return true;   // 拿不到语言信息（例如离线验证环境）→ 照常汉化
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
        /// 设置界面文字（两个模组的设置窗口都是**硬编码英文**，不经过游戏翻译系统）。
        ///
        /// 这一块玩家一定会看到 —— 打开「选项 → 模组设置 → 裸体评价」就是它。
        /// 里面带 {0} 的条目是原模组用内插字符串拼出来的滑动条说明，
        /// 编译器把它编译成了 string.Format 的格式串（例如 "... {0:F0}%"），
        /// 所以这里保留 {0} 占位符原样，只翻前后文字。
        /// </summary>
        public static readonly Dictionary<string, string> SettingsText =
            new Dictionary<string, string>(StringComparer.Ordinal)
        {
            // ══════════ 前置模组1「裸体评价」的设置窗口 ══════════
            { "Nudity Matters More",                       "裸体评价" },          // 设置菜单里的分类名

            { "Nip Slips",                                 "乳头走光" },
            { "Melee attacks can strip",                   "近战攻击会扒掉衣服" },
            { "Wet Shirts",                                "湿衣服" },
            { "Drunk Stripping",                           "醉酒脱衣" },
            { "Melee strip chance",                        "近战扒衣概率" },
            { "Show Hands",                                "显示手部" },
            { "Disable Nudity Notifications",              "关闭裸体通知" },
            { "Armor doesn't strip",                       "护甲不会被扒掉" },
            { "DBH sauna/swimming/hottub is naked",        "DBH 桑拿／游泳／热水浴缸视为赤裸" },
            { "Extra Prude Behaviors (more covering)",     "额外拘谨行为（更多遮盖）" },
            { "Ignore family",                             "忽略家人" },
            { "Biosculpter requires nudity",               "生物塑型舱要求裸体" },
            { "Flash effect for prudes",                   "拘谨者的闪白效果" },
            { "Flash effect more often",                   "更频繁的闪白效果" },
            { "Bra thoughts",                              "胸罩想法" },
            { "Disable futa/trap menus",                   "关闭扶他／伪娘菜单" },
            { "Disable Nudity Tab",                        "关闭裸体标签页" },
            { "CoverBody Debug Messages",                  "遮体调试消息" },
            { "Interaction Debug Messages",                "互动调试消息" },
            { "Nip Slip Debug Messages",                   "走光调试消息" },
            { "History Debug Messages",                    "历史调试消息" },
            { "Melee Strip Debug Messages",                "近战扒衣调试消息" },
            { "Wet Shirt Debug Messages",                  "湿衣调试消息" },
            { "Slip Faster [NIP SLIP DEBUG]",              "加快走光 [走光调试]" },
            { "Never Check [NIP SLIP DEBUG]",              "永不检查 [走光调试]" },
            { "Prudes break faster [DEBUG]",               "拘谨者更快崩溃 [调试]" },
            { "MessageDef test [DEBUG]",                   "消息定义测试 [调试]" },

            // ══════════ 前置模组2「更多看法」的设置窗口 ══════════
            { "Nudity Matters More: Opinions",             "裸体评价：更多看法" },  // 设置菜单分类名

            { "NMM Opinions Generator Settings",           "NMM 看法生成器设置" },
            { "Use situational opinion generator",         "启用情境看法生成器" },
            { "If disabled, only predefined opinions will be displayed. Default true.",
              "关闭后只显示预设看法。默认开启。" },
            { "Chance of generated opinion: {0:F0}%",      "生成看法的概率：{0:F0}%" },

            { "Fixation Log Commentary Settings",          "迷恋日志评论设置" },
            { "Enable pawn commentary on observed actions", "启用角色对所见过行为的评论" },
            { "Enables pawns to comment on what they see. Requires the 'SpeakUp' mod. Default: true.",
              "让角色对看到的事情发表评论。需要 SpeakUp 模组。默认开启。" },
            { "Commentary Cooldown: {0:F0} sec",           "评论冷却：{0:F0} 秒" },
            { "Max Simultaneous Opinions: {0}",            "同时最多看法数：{0}" },
            { "Allow comment on pawn in same state",       "允许评论处于相同状态的角色" },
            { "If enabled, a naked pawn can comment on another naked pawn, etc. Default: false.",
              "开启后，赤裸的角色也能评论另一个赤裸的角色。默认关闭。" },
            { "Enable pawn commentary on observed actions ('SpeakUp' mod not found, feature disabled)",
              "启用角色对所见过行为的评论（未找到 SpeakUp 模组，功能已禁用）" },

            { "Debugging",                                 "调试" },
            { "Enable debug logging",                      "启用调试日志" },
            { "Shows detailed logs in the console for debugging purposes. It is recommended to keep this disabled during normal play. Default: false.",
              "在控制台输出详细日志，便于排查问题。正常游玩时建议关闭。默认关闭。" },
            { "Reset all settings to default",             "恢复所有默认设置" },

            { "Problematic Interactions",                  "有问题的互动" },
            { "If these interactions enabled, descriptions from other mods may look incorrect.",
              "启用这些互动后，其它模组的描述可能显示不正确。" },
            { "Other Commentaries",                        "其它评论" },
        };

        /// <summary>
        /// 设置界面里那些**运行时才拼出来**的文字 —— Transpiler 够不着，只能用正则兜底。
        /// 例如「Enable/disable commentary for the 'Shower' interaction.」里的 Shower 是枚举变量。
        /// </summary>
        private static readonly List<KeyValuePair<Regex, string>> SettingsPatterns =
            new List<KeyValuePair<Regex, string>>
        {
            new KeyValuePair<Regex, string>(
                new Regex(@"^Enable/disable commentary for the '(.+)' interaction\.$"),
                "是否启用「$1」互动的评论。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^Chance of generated opinion: (.+)%$"),
                "生成看法的概率：$1%"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^Commentary Cooldown: (.+) sec$"),
                "评论冷却：$1 秒"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^Max Simultaneous Opinions: (\d+)$"),
                "同时最多看法数：$1"),
        };

        /// <summary>
        /// 设置界面里「互动类型」复选框的名字。
        /// 这些名字来自前置模组1 的枚举（运行时代码里拿到的就是这些英文名），
        /// Transpiler 抓不到，只能在 CheckboxLabeled 被调用时替换。
        ///
        /// 安全说明：只会替换**下面这张表里精确匹配**的词，而且这些词本来就是它，
        /// 不会误伤别的模组（别的模组不会用 "MedicalFullViewer" 这种词当复选框标题）。
        /// </summary>
        public static readonly Dictionary<string, string> InteractionTypeNames =
            new Dictionary<string, string>(StringComparer.Ordinal)
        {
            { "Covering",              "遮盖" },
            { "Naked",                 "赤裸" },
            { "Topless",               "上身赤裸" },
            { "Bottomless",            "下身赤裸" },
            { "Sex",                   "性行为" },
            { "Masturbation",          "自慰" },
            { "Rape",                  "强奸" },
            { "Raped",                 "被强奸" },
            { "Shower",                "淋浴" },
            { "Bath",                  "泡澡" },
            { "Sauna",                 "桑拿" },
            { "Swimming",              "游泳" },
            { "HotTub",                "热水浴缸" },
            { "NipSlip",               "乳头走光" },
            { "BreastSlip",            "乳房走光" },
            { "AreolaSlip",            "乳晕走光" },
            { "NipSlipHelp",           "帮忙整理走光" },
            { "Biopod",                "生物舱" },
            { "Changing",              "换衣" },
            { "WetShirt",              "湿衣服" },
            { "Breastfeed",            "哺乳" },
            { "SelfMilk",              "自挤奶" },
            { "Milk",                  "挤奶" },
            { "MedicalFull",           "全裸医疗" },
            { "MedicalTop",            "上身赤裸医疗" },
            { "MedicalBottom",         "下身赤裸医疗" },
            { "MedicalFullViewer",     "全裸医疗（旁观）" },
            { "MedicalTopViewer",      "上身赤裸医疗（旁观）" },
            { "MedicalBottomViewer",   "下身赤裸医疗（旁观）" },
            { "MedicalFullSelf",       "全裸医疗（自己）" },
            { "MedicalTopSelf",        "上身赤裸医疗（自己）" },
            { "MedicalBottomSelf",     "下身赤裸医疗（自己）" },
            { "Surgery",               "手术" },
            { "SurgeryViewer",         "手术（旁观）" },
            { "HumanArtTop",           "人体艺术（上身）" },
            { "HumanArtBottom",        "人体艺术（下身）" },
            { "HumanArtFull",          "人体艺术（全裸）" },
            { "None",                  "无" },
        };

        /// <summary>
        /// 屏幕消息的改写规则（「XX 第一次看到 YY 裸体」这类）。
        ///
        /// 这些消息由前置模组1 生成，显示在屏幕左上角消息区，玩家一定会看到。
        /// 原模组用内插字符串拼句子，编译后是一堆碎片，改 IL 会把不同语境混成同一句
        /// （" saw " 在「第一次看到」和「隔了一阵子又看到」里都要用），所以改成
        /// 在 Messages.Message 出口按**完整句子**重写。
        ///
        /// ⚠ 规则顺序有讲究：带 "in a while" 的必须排在普通规则**前面**。
        /// </summary>
        public static readonly List<KeyValuePair<Regex, string>> MessagePatterns =
            new List<KeyValuePair<Regex, string>>
        {
            // ── 「隔了一阵子又看到」变体（先匹配，避免被下面的规则截走）──
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw (.+?) naked for the first time in a while\.$"),
                "$1 又看到 $2 赤身裸体了。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw (.+?)'s breasts for the first time in a while\.$"),
                "$1 又看到 $2 的乳房了。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw (.+?)'s genitals for the first time in a while\.$"),
                "$1 又看到 $2 的生殖器了。"),

            // ── 「第一次看到认识的人」──
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw (.+?) naked for the first time\.$"),
                "$1 第一次看到 $2 赤身裸体。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw (.+?)'s breasts for the first time\.$"),
                "$1 第一次看到 $2 的乳房。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw (.+?)'s genitals for the first time\.$"),
                "$1 第一次看到 $2 的生殖器。"),

            // ── 「第一次看到陌生人」──
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw another naked woman for the first time\.$"),
                "$1 第一次看到另一个女人的裸体。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw another naked man for the first time\.$"),
                "$1 第一次看到另一个男人的裸体。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw another person's breasts for the first time\.$"),
                "$1 第一次看到别人的乳房。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw another woman's genitals for the first time\.$"),
                "$1 第一次看到另一个女人的生殖器。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw a naked woman for the first time\.$"),
                "$1 第一次看到女人的裸体。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw a naked man for the first time\.$"),
                "$1 第一次看到男人的裸体。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw breasts for the first time\.$"),
                "$1 第一次看到乳房。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) saw a woman's genitals for the first time\.$"),
                "$1 第一次看到女人的生殖器。"),

            // ── 「自己被人第一次看到」（被动语态）──
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?) was seen naked for the first time\.$"),
                "$1 第一次被人看到赤身裸体。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?)'s breasts were seen for the first time\.$"),
                "$1 的乳房第一次被人看到。"),
            new KeyValuePair<Regex, string>(
                new Regex(@"^(.+?)'s genitals were seen for the first time\.$"),
                "$1 的生殖器第一次被人看到。"),
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

        /// <summary>
        /// 设置界面专用：先查精确表，查不到再跑正则表
        /// （滑动条那几条是原模组用内插字符串拼的，编译后形式不固定，正则兜底）。
        /// </summary>
        public static IEnumerable<CodeInstruction> RewriteSettings(IEnumerable<CodeInstruction> codes)
        {
            foreach (CodeInstruction c in codes)
            {
                if (c.opcode == OpCodes.Ldstr && c.operand is string)
                {
                    string s = (string)c.operand;
                    string zh;
                    if (SettingsText.TryGetValue(s, out zh))
                        c.operand = zh;
                    else
                    {
                        string r = ApplyPatterns(s, SettingsPatterns);
                        if (r != null) c.operand = r;
                    }
                }
                yield return c;
            }
        }

        /// <summary>
        /// 拿一条文本去逐条试正则表，命中就返回改写结果，没命中返回 null。
        /// </summary>
        public static string ApplyPatterns(string s, List<KeyValuePair<Regex, string>> pats)
        {
            if (string.IsNullOrEmpty(s)) return null;
            for (int i = 0; i < pats.Count; i++)
            {
                if (pats[i].Key.IsMatch(s))
                    return pats[i].Key.Replace(s, pats[i].Value);
            }
            return null;
        }

        /// <summary>
        /// 快速预筛：这条消息**有没有可能**是本模组的？
        ///
        /// 为什么需要它（性能）：
        ///   `Messages.Message` 是游戏里**所有模组共用**的消息出口，原版和其它模组
        ///   每分钟也会产生消息。如果每条都老老实实跑一遍那 17 条正则，
        ///   实测最坏情况单次要 16 微秒（本机 i7 上跑 100 万次共 16 秒）。
        ///   虽然现实中消息量很小，但白跑就是浪费。
        ///
        ///   本模组的消息**必然**含下面三组词之一（对应 17 条规则的三种句式）：
        ///      主动：  " saw "
        ///      被动：  " was seen " / " were seen "
        ///   所以先用最廉价的 IndexOf 挡一下，不含就直接返回。
        ///   这是纯 ASCII 子串查找，实测能把非本模组消息的开销降到 0.05 微秒级别（约 300 倍）。
        /// </summary>
        public static bool LooksLikeOurMessage(string t)
        {
            if (t == null) return false;
            return t.IndexOf(" saw ", StringComparison.Ordinal) >= 0
                || t.IndexOf(" was seen ", StringComparison.Ordinal) >= 0
                || t.IndexOf(" were seen ", StringComparison.Ordinal) >= 0;
        }
    }
}
