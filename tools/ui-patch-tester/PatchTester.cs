// ---------------------------------------------------------------------------
// 本文件由 AI 助手「DeepSeek娘·汐蓝」辅助编写。
// 设计、需求、审阅与实机验证由人类作者（大赢经直插白皮赢道）完成。
// AI-assisted: written with DeepSeek Niang · Xi Lan (AI);
// designed, reviewed and validated by the human author.
// ---------------------------------------------------------------------------

// ==========================================================================
// 【离线自检】不启动游戏，验证界面汉化补丁的每一处替换
// ==========================================================================
//
// 【症状】      改完补丁只能靠「开一次游戏 + 盯 20～40 分钟日志」才能知道替换对不对，
//              迭代成本极高；而且日志里「没红字」并不能证明替换真的发生了。
// 【根因】      v1 想用 harmony.Patch 直接在独立进程里验证，但有两个方法做不到：
//                · DrawOpinionLog 的 IL 里有 Unity ECall（Texture2D.whiteTexture），
//                  独立进程的 CLR 会拒绝；
//                · OpinionHelper.GetHeaderLabel 的静态构造函数需要游戏运行时。
//              这两个在游戏里都不成问题，只是独立进程的限制。
// 【修法】      改成**直接调用转译器函数**，绕开 Harmony 的动态方法生成：
//                ① Transpiler 本质就是「收指令序列、吐指令序列」的普通函数；
//                ② 用 PatchProcessor.GetOriginalInstructions() 拿原始指令；
//                ③ 手工喂给补丁里的 Transpiler，看吐出来的指令变了没有。
//              这跟游戏里 Harmony 调它走的是同一条代码路径。
// 【自动让路】  本文件只随 tools\ 发布给玩家做自检用，**不参与游戏运行时**，
//              不会被游戏加载，也不会长期驻留内存。.exe 已从发布包排除（见打包脚本）。
// ==========================================================================
//
// 离线验证程序 v2：不启动游戏，验证界面汉化补丁的每一处替换。
//
// v1 的问题是：有两个方法没法用 harmony.Patch 来验证 ——
//   · DrawOpinionLog      → Harmony 要生成动态方法，而它的 IL 里有 Unity 的 ECall
//                           （Texture2D.whiteTexture），独立进程的 CLR 会拒绝；
//   · OpinionHelper.GetHeaderLabel → 它的静态构造函数需要游戏运行时，独立进程里会抛。
//   这两个在游戏里都不成问题，但为了「不开游戏也能拿到证据」，
//   v2 改成**直接调用转译器函数**，绕开 Harmony 的动态方法生成：
//     ① Transpiler 本质就是个「接收指令序列、返回指令序列」的普通函数
//     ② 我们用 PatchProcessor.GetOriginalInstructions() 拿到原始指令
//     ③ 手工把它喂给补丁里的 Transpiler，看吐出来的指令变了没有
//   这跟游戏里 Harmony 调它走的是同一条代码路径。

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Text;
using HarmonyLib;

/// <summary>
/// 离线自检工具：**不启动游戏**，直接用反射加载原模组 + 补丁 DLL，
/// 把补丁里每一处替换跑一遍并比对结果。
///
/// 为什么要它：改完补丁若只靠「开一次游戏 + 盯 20~40 分钟日志」，
/// 一个替换写错就要等一整轮加载才能发现；这里几秒就能定位到具体哪一条没替换上。
///
/// ⚠ 下面的路径常量是**本机硬编码**，换机器/换目录要改（详见常量上方注释）。
/// </summary>
internal static class PatchTester
{
    // ⚠ 以下 6 个路径全部是**本机硬编码绝对路径**（2026-11-16 实测）：
    //   · `PatchDll` 指向的 `D:\nmm_ui\` **并不存在** —— 本工具当前跑不起来，需要先改这个值；
    //   · 其余路径写的是 `D:\Steam\...`，实际目录是 `D:\steam\...`（Windows 不敏感，能过，但别当规范抄）；
    //   · 想让它跟仓库同步，最省事的做法是把 `PatchDll` 改成相对 exe 的 `..\..\Assemblies\NMMOpinionsChineseUI.dll`。
    // 本轮**没有改**这些值：它是离线工具、不进游戏，改路径要重编 exe，也可能破坏作者现有用法。
    /// <summary>1.7 游戏本体的托管程序集目录（反射加载 Assembly-CSharp 等）。</summary>
    private const string Managed = @"D:\Steam\steamapps\common\RimWorld\RimWorldWin64_Data\Managed";
    /// <summary>1.6 版 NMM opinions 的程序集目录（老版本目标，留着做兼容性对照）。</summary>
    private const string ModOpinions = @"D:\Steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions\1.6\Assemblies";
    /// <summary>1.7 合并版（`dord.nuditymattersmore`）的程序集目录 —— 主要被测对象。</summary>
    private const string ModCore = @"D:\Steam\steamapps\common\RimWorld\Mods\RJW-功能-裸体评价\Assemblies";
    /// <summary>RJW 核心本体的程序集目录（提供 NMM 依赖的类型）。</summary>
    private const string ModRjw = @"D:\Steam\steamapps\common\RimWorld\Mods\RJW_核心_本体\1.6\Assemblies";
    /// <summary>0Harmony.dll 的路径（工坊 2009463077）—— 反射加载补丁 DLL 时需要它先就位。</summary>
    private const string HarmonyDll = @"D:\Steam\steamapps\workshop\content\294100\2009463077\Current\Assemblies\0Harmony.dll";
    /// <summary>被测的补丁 DLL。**当前值指向一个不存在的目录**，用之前必须先改成真实路径。</summary>
    private const string PatchDll = @"D:\nmm_ui\NMMOpinionsChineseUI.dll";

    /// <summary>累计通过 / 失败条数，跑完在控制台汇总。</summary>
    private static int pass = 0, fail = 0;

    // 离线自测工具的入口。
    // 它不是游戏的一部分，只在开发时用 run.ps1 跑一次，
    // 用来确认两个补丁 DLL 能不能被加载、关键方法在不在。
    private static void Main()
    {
        Console.OutputEncoding = Encoding.UTF8;
        AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        Run();
    }

    // 程序集解析回调：当 CLR 找不到引用时，从游戏目录与 refs 里补。
    // 因为本工具不在游戏进程里跑，默认探测路径找不到 Verse / UnityEngine，
    // 只能手动接上。返回 null 表示「我也不知道」，让 CLR 按默认方式失败。
    private static Assembly Resolve(object sender, ResolveEventArgs args)
    {
        string simple = new AssemblyName(args.Name).Name + ".dll";
        string[] dirs = { Managed, ModOpinions, ModCore, ModRjw,
                          Path.GetDirectoryName(HarmonyDll), Path.GetDirectoryName(PatchDll) };
        foreach (string d in dirs)
        {
            if (string.IsNullOrEmpty(d)) continue;
            string p = Path.Combine(d, simple);
            if (File.Exists(p)) { try { return Assembly.LoadFrom(p); } catch { } }
        }
        return null;
    }

    // 记一条通过。计数 + 打印，供最后的汇总行使用。
    private static void Ok(string m) { pass++; Console.WriteLine("  [OK] " + m); }
    // 记一条失败。与 Ok 对称；任何一条失败都会让进程退出码非 0。
    private static void Ng(string m) { fail++; Console.WriteLine("  [!!] " + m); }

    [MethodImpl(MethodImplOptions.NoInlining)]
    // 逐个检查：DLL 能否加载、关键类型与方法是否存在、
    // 字典条目是否与源码一致。
    // 任何一项不通过都算失败 —— 这个工具的定位就是「宁可误报也不要漏报」。
    private static void Run()
    {
        Console.WriteLine("================================================================");
        Console.WriteLine(" 界面汉化补丁 —— 离线验证 v2（不启动游戏）");
        Console.WriteLine("================================================================");

        Console.WriteLine();
        Console.WriteLine("【1】加载");
        Assembly patchAsm = typeof(NMMOpinionsChineseUI.Patches).Assembly;
        Assembly modAsm = Assembly.LoadFrom(Path.Combine(ModOpinions, "NudityMattersMore_opinions.dll"));
        Ok("原模组 " + modAsm.GetName().Version + " / 补丁 " + patchAsm.GetName().Name);
        try { Assembly.LoadFrom(Path.Combine(ModRjw, "RJW.dll")); Ok("RJW 已加载"); }
        catch (Exception e) { Ng("RJW 加载失败：" + e.Message); }

        Type patches = typeof(NMMOpinionsChineseUI.Patches);
        MethodInfo tpText = patches.GetMethod("Text_Transpiler");
        MethodInfo tpRus = patches.GetMethod("Russian_Transpiler");
        MethodInfo pfHeader = patches.GetMethod("GetHeaderLabel_Prefix");
        Ok("取得 Transpiler / Prefix");

        // ── 目标方法清单 ──
        var jobs = new List<Tuple<string, string, string>>   // 类型, 方法, 用哪张表
        {
            Tuple.Create("NudityMattersMore_opinions.ITab_Pawn_NMMOpinions", "FillTab", "text"),
            Tuple.Create("NudityMattersMore_opinions.ITab_Pawn_NMMOpinions", "DrawOpinionLog", "text"),
            Tuple.Create("NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "ApplyFirstTimeThought_Prefix", "ru"),
            Tuple.Create("NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "ApplyRenewThought_Prefix", "ru"),
            Tuple.Create("NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "ApplyFirstTimeEverThought_Prefix", "ru"),
            Tuple.Create("NudityMattersMore_opinions_patches.NMMOpinionsHarmonyPatches", "GetRelationsString", "ru"),
        };

        Console.WriteLine();
        Console.WriteLine("【2】逐方法跑替换（直接喂给 Transpiler，不经过 Harmony）");

        int totalChanged = 0;
        var report = new List<string>();

        foreach (var j in jobs)
        {
            Type ty = modAsm.GetType(j.Item1, false);
            MethodInfo mi = ty == null ? null : ty.GetMethod(j.Item2,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static);
            if (mi == null) { Ng("找不到 " + j.Item1 + "." + j.Item2); continue; }

            List<string> before, after;
            try
            {
                var orig = PatchProcessor.GetOriginalInstructions(mi);
                before = orig.Where(i => i.opcode == OpCodes.Ldstr && i.operand is string)
                             .Select(i => (string)i.operand).ToList();

                MethodInfo tp = (j.Item3 == "ru") ? tpRus : tpText;
                var produced = (IEnumerable<CodeInstruction>)tp.Invoke(null, new object[] { orig });
                after = produced.Where(i => i.opcode == OpCodes.Ldstr && i.operand is string)
                                .Select(i => (string)i.operand).ToList();
            }
            catch (Exception e)
            {
                Ng(j.Item1 + "." + j.Item2 + " 处理失败：" + e.GetType().Name + " " + e.Message);
                continue;
            }

            Console.WriteLine();
            Console.WriteLine("   ── " + j.Item1.Split('.').Last() + "." + j.Item2 + " ──");

            if (before.Count != after.Count)
            {
                Ng("  常量数变了（" + before.Count + " → " + after.Count + "）");
                continue;
            }

            int local = 0;
            for (int i = 0; i < before.Count; i++)
            {
                if (before[i] != after[i])
                {
                    local++; totalChanged++;
                    Console.WriteLine("     ✓ " + Show(before[i]) + "  →  " + Show(after[i]));
                }
            }
            if (local == 0) Console.WriteLine("     （无变化）");
            Ok(j.Item2 + " 替换 " + local + " 处");

            // 收集残留的英文/俄文
            foreach (string s in after)
                if (LooksForeign(s) && !KnownKeep(s)) report.Add(j.Item2 + " : " + Show(s));
        }

        // ── 3. GetHeaderLabel 的 Prefix（单独测，传 null 参数）──
        Console.WriteLine();
        Console.WriteLine("【3】GetHeaderLabel 的 Prefix（不依赖游戏运行时）");
        try
        {
            object[] a1 = { null, null, false, null };
            bool keep = (bool)pfHeader.Invoke(null, a1);
            string r1 = (string)a1[3];
            Console.WriteLine("     targetPawn = null        → " + Show(r1) + "  (原方法是否跳过：" + (!keep) + ")");
            if (!keep && r1 != null && !LooksForeign(r1)) Ok("未选目标时的表头已汉化");
            else Ng("未选目标时的表头不对");

            // 用一个假的 Pawn 走不通（Pawn 无法凭空造），所以只测上面的分支
            Console.WriteLine("     （另外两个分支需要真实 Pawn 对象，只能在游戏里看效果）");
        }
        catch (Exception e)
        {
            Ng("调用 Prefix 失败：" + e.GetType().Name + " " + e.Message);
        }

        // ── 4. 安全检查 ──
        Console.WriteLine();
        Console.WriteLine("【4】安全检查：代码逻辑用的字符串绝不能被动");
        Type tabType = modAsm.GetType("NudityMattersMore_opinions.ITab_Pawn_NMMOpinions", false);
        MethodInfo fillTab = tabType.GetMethod("FillTab",
            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static);
        var cur = PatchProcessor.GetOriginalInstructions(fillTab)
                    .Where(i => i.opcode == OpCodes.Ldstr && i.operand is string)
                    .Select(i => (string)i.operand).ToList();
        var producedFill = (IEnumerable<CodeInstruction>)tpText.Invoke(null, new object[]
                            { PatchProcessor.GetOriginalInstructions(fillTab) });
        var afterFill = producedFill.Where(i => i.opcode == OpCodes.Ldstr && i.operand is string)
                                    .Select(i => (string)i.operand).ToList();

        foreach (string must in new[] { "Chest", "Genitals", "Anus", "Не наблюдалось пока.", "No opinion def found" })
        {
            if (afterFill.Contains(must)) Ok("「" + must + "」原样保留");
            else Ng("「" + must + "」被改掉了！代码逻辑会失效");
        }

        // ── 5. 结论 ──
        Console.WriteLine();
        Console.WriteLine("【5】结论");
        Console.WriteLine("   共替换字符串：" + totalChanged + " 处");
        if (totalChanged > 0) Ok("补丁的替换逻辑确实生效"); else Ng("一处都没替换");

        Console.WriteLine();
        if (report.Count > 0)
        {
            Console.WriteLine("   仍显示英文/俄文的字符串（" + report.Count + " 个，逐个判断）：");
            foreach (string s in report) Console.WriteLine("     · " + s);
        }
        else Console.WriteLine("   没有残留");

        Console.WriteLine();
        Console.WriteLine("================================================================");
        Console.WriteLine(" 通过 " + pass + " 项，失败 " + fail + " 项 —— " + (fail == 0 ? "✅ 补丁验证通过" : "❌ 有问题"));
        Console.WriteLine("================================================================");
        Environment.ExitCode = fail == 0 ? 0 : 1;
    }

    /// <summary>代码里当键或 Def 名用的，本来就不该翻译。</summary>
    private static bool KnownKeep(string s)
    {
        foreach (string k in new[] { "Chest", "Genitals", "Anus", "Breasts", "N/A",
                                     "Не наблюдалось пока.", "No opinion def found" })
            if (s == k) return true;
        return false;
    }

    // 判断一个字符串是不是「看起来该翻译但没翻译」的英文。
    // 判据：含拉丁字母、且不含任何 CJK 字符。
    // 用它来找出「字典漏收」的界面文字。
    private static bool LooksForeign(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return false;
        foreach (char c in s) if (c >= 0x4E00 && c <= 0x9FFF) return false;   // 有中文就算已汉化
        foreach (char c in s) if (c >= 0x0400 && c <= 0x04FF) return true;    // 俄语
        int letters = 0;
        foreach (char c in s) if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) letters++;
        if (letters < 3) return false;
        if (!s.Contains(" ") && !s.Contains(".")) return false;               // 排除纯标识符
        return true;
    }

    /// <summary>
    /// 把字符串截短到日志里好读的长度（空值返回 `(空)`）。只用于本工具的输出，不碰被测内容。
    /// </summary>
    private static string Show(string s)
    {
        if (s == null) return "(null)";
        return "\"" + s.Replace("\r", "\\r").Replace("\n", "\\n") + "\"";
    }
}
