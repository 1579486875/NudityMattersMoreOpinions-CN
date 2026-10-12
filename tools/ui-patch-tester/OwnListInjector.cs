// 裸体评价更多看法 简体汉化 —— 自有注入清单（「方案 C」）
//
// ① 这个类修什么问题
//   RimWorld 的翻译系统（DefInjected）在翻译「整个列表字段」时，要求该字段带
//   [TranslationCanChangeCount] 特性。规则见 Verse.DefInjectionPackage.SetDefFieldAtPath：
//
//       else if (!isPlaceholder && ensureFieldType != typeof(string)
//                && !fieldNamed.HasAttribute<TranslationCanChangeCountAttribute>())
//           loadErrors.Add("Tried to translate field ... doesn't have [TranslationCanChangeCount] ...");
//       else if (!isPlaceholder) { fieldNamed.SetValue(obj, value); result2 = true; }   // ← 只有这条才真正写入
//
//   而原模组的 OpinionDef_SexPart.opinionTexts、BodyPartOpinionDef.texts 等都是裸的
//   public List<string>，没有这个特性 → 整列表写在 Languages\ 下会被游戏「拒绝并记一条翻译错误」，
//   译文一条都不生效（v1.2.7 的 123,015 条正文就是这样丢的）。
//   老写法（索引式 <Def.opinionTexts.0>…）不受该限制，但键数会从 1.1 万涨回 13.7 万、加载明显变慢。
//   所以走「方案 C」：把清单文件搬到游戏不扫描的 OwnInjections\，由本类在运行时反射逐条写回。
//
// ② 为什么这样修
//   · 清单放在 OwnInjections\ 下 —— 游戏只扫描 Defs\、Patches\、Languages\，这个目录名不在其中，
//     游戏完全不会读它，所以不会再产生任何翻译错误（"翻译文件写好了但没被加载"也不存在）。
//   · 注入时机用 [StaticConstructorOnStartup]：StaticConstructorOnStartupUtility.CallAll() 的唯一
//     调用者是 Verse.PlayDataLoader.<DoPlayLoad>b__4_4，发生在「全部 Def 载入 + 跨引用解析」之后，
//     此时 DefDatabase 已经可以安全查询。
//   · 逐条赋值（list[i] = 译文）而不是整体 SetValue：不改字段里那个 List 的引用，
//     语义最接近游戏原生的索引注入；条数不符时也能立刻发现，而不是静默错位。
//
// ③ 什么情况下会跳过 / 失效（每一步都会在日志里留痕，不会被静默吞掉）
//   · 游戏语言不是中文（Zh.GameIsChinese() == false）  → 整个注入跳过，只打一条 Message。
//   · 找不到本模组根目录，或 OwnInjections 目录不存在   → 跳过 + Warning。
//   · 某个清单文件认不出 Def 类型                      → 只跳过该文件 + Warning，其余文件继续。
//   · 某个 Def 名在 DefDatabase 里查不到（前置没装/改名） → 跳过该容器，计入汇总「Def 未找到」。
//   · 字段不存在、或不是 List<string>                  → 跳过该容器，计入汇总「字段不符」。
//   · 译文条数 ≠ Def 字段当前条数                       → 整条容器跳过 + Warning（宁可漏译，绝不串行错位）。
//
// ④ 幂等性
//   [StaticConstructorOnStartup] 由 CLR 保证静态构造函数只执行一次；另外用静态标志 ran 再兜一层。
//   （本项目历史事故：重复安装 Harmony 补丁会导致层层叠加、越玩越卡。）
//
// ⑤ 改这个文件的人务必注意
//   · 清单 XML 的键名格式是 <Def名称.字段名称>，字段名是从键名里现取的，**不要在代码里写死**。
//   · 不要把 OwnInjections\ 里的文件移回 Languages\ —— 移回去就等于这些译文全部失效。
//   · AccessTools.Method(type, name, parameters, generics) 的第 4 个参数是「泛型类型参数」，
//     不是返回类型；对非泛型方法必须传 null。（本项目历史事故点，本类没有用到它。）

using HarmonyLib;
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Xml;
using Verse;

namespace NMMOpinionsChineseUI
{
    /// <summary>
    /// 读取本模组 OwnInjections 目录下的「自有清单」，在运行时把整列表译文反射写回 Def 字段。
    /// 静态构造函数由 CLR 保证只执行一次。
    /// </summary>
    [StaticConstructorOnStartup]
    public static class OwnListInjector
    {
        /// <summary>本汉化包的 packageId —— 用来在已加载模组里认出自己（不要改）。</summary>
        private const string MyPackageId = "shark510.nuditymattersmoreopinions.zhfix";

        /// <summary>自有清单的目录名（这个名字不在游戏扫描的目录列表里，所以不会变成翻译错误）。</summary>
        private const string OwnFolderName = "OwnInjections";

        /// <summary>清单语言子目录（与 Languages 下的写法保持一致，便于日后扩展繁中）。</summary>
        private const string LangFolderName = "ChineseSimplified";

        /// <summary>
        /// 原模组抽象基类 BaseSexPartOpinionDef 自带的那条 opinionTexts 原文。
        /// 出处：&lt;前置模组&gt;\Common\Defs\OpinionDef_SexPart.xml。
        /// 它不会被 DefInjected 翻译（抽象 Def 不在 DefDatabase 里，索引式键定位不到它），
        /// 所以运行时它始终是这句英文 —— 可以安全地当作判据。
        /// </summary>
        private const string InheritedBaseText = "Its just there, what to say more?";

        /// <summary>
        /// 上面那句继承来的英文，在中文环境下的对应译文。
        /// 为什么要单独写它：读取端是 GenCollection.RandomElement（**无序候选池**，顺序无语义），
        /// 所以列表里剩下的那条英文同样会被按 1/(N+1) 的概率抽中显示给玩家。
        /// 实测 4509 个 SexPart 容器的 N 分布在 5..90 之间 → 抽中概率约 1.10% ~ 16.67%，
        /// 平均约 4.3%（玩家平均每 ~23 次正文生成会遇到一次英文）。
        /// 只替换这一条、**不改列表长度** —— RemoveAt 会同时改变本文件的条数判据（diff），得不偿失。
        /// </summary>
        private const string InheritedBaseTextZh = "就这样，还有什么好说的？";

        private static int inheritedHead;      // 基类那条在列表头部 → 整体后移 1 条
        private static int inheritedTail;      // 基类那条在列表尾部 → 偏移 0
        private static int inheritedUnknown;   // 判不准 → 按尾部处理
        private static int inheritedHeadFilled; // 基类在头时，顺手把 target[0] 换成中文的次数

        private static string Clip(string s)
        {
            if (string.IsNullOrEmpty(s))
            {
                return "(空)";
            }
            s = s.Trim();
            return s.Length <= 40 ? s : s.Substring(0, 40) + "…";
        }

        /// <summary>只跑一次的兜底标志（正常情况下 CLR 已经保证了一次）。</summary>
        private static bool ran;

        static OwnListInjector()
        {
            if (ran)
            {
                return;
            }
            ran = true;

            try
            {
                Run();
            }
            catch (Exception ex)
            {
                Log.Error("[NMM 汉化] 自有清单注入整体失败（正文可能仍是英文）：" + ex);
            }
        }

        private static void Run()
        {
            // 非中文环境直接退出：英文原版玩家不该看到任何中文残留，也不该白花时间读清单。
            if (!Zh.GameIsChinese())
            {
                Log.Message("[NMM 汉化] 当前游戏语言不是中文，自有清单注入跳过（不影响原版文本）。");
                return;
            }

            string root = FindMyRootDir();
            if (root == null)
            {
                Log.Warning("[NMM 汉化] 找不到本模组根目录，自有清单注入跳过 —— 正文评价会保持英文。");
                return;
            }

            string dir = Path.Combine(Path.Combine(root, OwnFolderName), LangFolderName);
            if (!Directory.Exists(dir))
            {
                Log.Warning("[NMM 汉化] 自有清单目录不存在，注入跳过：" + dir);
                return;
            }

            string[] files;
            try
            {
                files = Directory.GetFiles(dir, "*.xml", SearchOption.AllDirectories);
            }
            catch (Exception ex)
            {
                Log.Error("[NMM 汉化] 列举自有清单文件失败：" + ex);
                return;
            }

            int containers = 0;   // 读到的容器总数
            int applied = 0;      // 真正写进去的译文条数
            int skipDef = 0;      // Def 没找到
            int skipField = 0;    // 字段不存在 / 类型不对
            int skipCount = 0;    // 条数不符（防错位）
            int failedFiles = 0;  // 整文件解析失败

            for (int i = 0; i < files.Length; i++)
            {
                try
                {
                    InjectOneFile(files[i], ref containers, ref applied, ref skipDef, ref skipField, ref skipCount);
                }
                catch (Exception ex)
                {
                    failedFiles++;
                    Log.Warning("[NMM 汉化] 自有清单文件注入失败（其余文件继续）：" + files[i] + " —— " + ex.Message);
                }
            }

            int skipped = skipDef + skipField + skipCount;
            Log.Message(string.Format(
                "[NMM 汉化] 自有清单注入：容器 {0}、生效 {1} 条、跳过 {2}（Def 未找到 {3} / 字段不符 {4} / 条数不符 {5} / 文件失败 {6}）"
                + " ｜ 继承补偿：基类在头 {7}（其中已补中文 {10}）/ 在尾 {8} / 判不准 {9}",
                containers, applied, skipped, skipDef, skipField, skipCount, failedFiles,
                inheritedHead, inheritedTail, inheritedUnknown, inheritedHeadFilled));
        }

        /// <summary>注入一个清单文件里的全部容器。</summary>
        private static void InjectOneFile(string file, ref int containers, ref int applied,
                                          ref int skipDef, ref int skipField, ref int skipCount)
        {
            string typeName = GuessDefTypeName(file);
            Type defType = (typeName == null) ? null : FindType(typeName);
            if (defType == null)
            {
                Log.Warning("[NMM 汉化] 认不出清单文件对应的 Def 类型，整文件跳过：" + file
                            + "（从路径推出的类型名：" + (typeName ?? "无") + "）");
                return;
            }

            XmlDocument doc = new XmlDocument();
            doc.Load(file);

            XmlNode rootNode = doc.DocumentElement;
            if (rootNode == null || rootNode.Name != "LanguageData")
            {
                Log.Warning("[NMM 汉化] 清单文件根节点不是 LanguageData，整文件跳过：" + file);
                return;
            }

            foreach (XmlNode node in rootNode.ChildNodes)
            {
                // 注释、空白一律跳过，只处理真正的元素。
                if (node.NodeType != XmlNodeType.Element)
                {
                    continue;
                }

                // 键名形如 "Def名称.字段名称"（字段名不写死，现取）。
                string tag = node.Name;
                int dot = tag.LastIndexOf('.');
                if (dot <= 0 || dot >= tag.Length - 1)
                {
                    continue;
                }
                string defName = tag.Substring(0, dot);
                string fieldName = tag.Substring(dot + 1);

                List<string> texts = new List<string>();
                foreach (XmlNode child in node.ChildNodes)
                {
                    if (child.NodeType == XmlNodeType.Element && child.Name == "li")
                    {
                        texts.Add(child.InnerText);
                    }
                }
                if (texts.Count == 0)
                {
                    continue;
                }
                containers++;

                Def def = GenDefDatabase.GetDefSilentFail(defType, defName, false);
                if (def == null)
                {
                    skipDef++;
                    continue;
                }

                FieldInfo field = AccessTools.Field(defType, fieldName);
                if (field == null || field.FieldType != typeof(List<string>))
                {
                    skipField++;
                    continue;
                }

                List<string> target = field.GetValue(def) as List<string>;
                if (target == null)
                {
                    skipField++;
                    continue;
                }

                // ── 条数校验 ─────────────────────────────────────────────────
                // 【2026-10-12 修正】原先要求「游戏条数 == 清单条数」，结果 4509 个容器被整条
                // 跳过、正文仍是英文。根因不是版本错配，而是**继承**：
                //   · 原模组所有 OpinionDef_SexPart 子 Def 都写了
                //     ParentName="BaseSexPartOpinionDef"（实测正好 4509 个，与跳过量完全吻合）；
                //   · 那个抽象基类自带一条 <opinionTexts>：「Its just there, what to say more?」
                //     出处：<前置模组>\Common\Defs\OpinionDef_SexPart.xml；
                //   · RimWorld 的 XML 继承对列表是「父 + 子」合并 —— 于是游戏里每个子 Def 的
                //     opinionTexts 都比清单多 1 条。
                // （官方 DefLoadCache 的 .xml.gz 已核实：缓存保存的是未展开的原始结构，
                //   基类文本在整个缓存里只出现 1 次，所以那一条只存在于运行时。）
                //
                // 处理：识别「多 1 条」，再按基类那条的位置决定偏移 ——
                //   基类在头部 → 清单从 [1] 开始写；基类在尾部 → 从 [0] 开始写。
                // 判不准时按「尾部」处理（v1.2.2 索引式时代实测就是这个行为）并留痕。
                int offset = 0;
                int diff = target.Count - texts.Count;
                if (diff == 1)
                {
                    string headText = (target[0] ?? string.Empty).Trim();
                    string tailText = (target[target.Count - 1] ?? string.Empty).Trim();
                    bool headIsBase = string.Equals(headText, InheritedBaseText, StringComparison.Ordinal);
                    bool tailIsBase = string.Equals(tailText, InheritedBaseText, StringComparison.Ordinal);
                    if (headIsBase && !tailIsBase)
                    {
                        offset = 1;   // 基类那条在列表最前面
                        inheritedHead++;
                    }
                    else if (tailIsBase && !headIsBase)
                    {
                        offset = 0;   // 基类那条在列表最后面
                        inheritedTail++;
                    }
                    else
                    {
                        offset = 0;
                        inheritedUnknown++;
                        Log.Warning(string.Format(
                            "[NMM 汉化] 继承文本位置判不准，按尾部处理：{0}（头条 {1} / 末条 {2}）",
                            tag, Clip(headText), Clip(tailText)));
                    }
                }
                else if (diff != 0)
                {
                    skipCount++;
                    Log.Warning(string.Format(
                        "[NMM 汉化] 条数不符，整条容器跳过以防错位：{0}（原模组 {1} 条 / 清单 {2} 条）",
                        tag, target.Count, texts.Count));
                    continue;
                }

                for (int i = 0; i < texts.Count; i++)
                {
                    target[offset + i] = texts[i];
                }

                // 【2026-10-12 补】offset == 1 意味着上面刚判定「基类那条在头部」，
                // 于是 target[0] 仍是继承来的那句英文。读取端是无序的 RandomElement，
                // 不换掉它就会按 1/(N+1) 的概率把英文混进中文正文（平均约 4.3%）。
                // 只在确凿判定 headIsBase 时才走到这里，所以不会误伤别的条目。
                if (offset == 1)
                {
                    target[0] = InheritedBaseTextZh;
                    inheritedHeadFilled++;
                }
                applied += texts.Count;
            }
        }

        /// <summary>
        /// 从清单文件路径反推 Def 类型名。约定目录结构与 DefInjected 一致：
        /// &lt;模组根&gt;\OwnInjections\ChineseSimplified\DefInjected\&lt;类型全名&gt;\xxx.xml
        /// </summary>
        private static string GuessDefTypeName(string file)
        {
            string[] parts = file.Split(new char[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar });
            for (int i = 0; i < parts.Length - 1; i++)
            {
                if (string.Equals(parts[i], "DefInjected", StringComparison.OrdinalIgnoreCase))
                {
                    return parts[i + 1];
                }
            }
            return null;
        }

        /// <summary>先按全名找；找不到再在所有已加载类型里按全名/短名兜底找一次。</summary>
        private static Type FindType(string typeName)
        {
            Type t = AccessTools.TypeByName(typeName);
            if (t != null)
            {
                return t;
            }
            try
            {
                foreach (Type candidate in GenTypes.AllTypes)
                {
                    if (candidate == null)
                    {
                        continue;
                    }
                    if (candidate.FullName == typeName || candidate.Name == typeName)
                    {
                        return candidate;
                    }
                }
            }
            catch (Exception)
            {
                // 兜底查找失败不算错误：上层会打 Warning 并跳过这个文件。
            }
            return null;
        }

        /// <summary>
        /// 找到本模组自己的根目录。优先用已加载模组列表按 packageId 认（最可靠）；
        /// 万一拿不到，再从本 DLL 的位置往上推两级（&lt;模组根&gt;\Assemblies\xxx.dll）。
        /// </summary>
        private static string FindMyRootDir()
        {
            try
            {
                List<ModContentPack> mods = LoadedModManager.RunningModsListForReading;
                if (mods != null)
                {
                    for (int i = 0; i < mods.Count; i++)
                    {
                        ModContentPack m = mods[i];
                        if (m != null && m.PackageId == MyPackageId)
                        {
                            return m.RootDir;
                        }
                    }
                }
            }
            catch (Exception)
            {
                // 走下面的兜底方案。
            }

            try
            {
                string location = typeof(OwnListInjector).Assembly.Location;
                if (!string.IsNullOrEmpty(location))
                {
                    DirectoryInfo assembliesDir = Directory.GetParent(location);
                    if (assembliesDir != null && assembliesDir.Parent != null)
                    {
                        return assembliesDir.Parent.FullName;
                    }
                }
            }
            catch (Exception)
            {
                // 两条路都失败时返回 null，上层会打 Warning 并跳过。
            }
            return null;
        }
    }
}
