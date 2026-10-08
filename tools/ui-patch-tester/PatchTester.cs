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

internal static class PatchTester
{
    private const string Managed = @"D:\Steam\steamapps\common\RimWorld\RimWorldWin64_Data\Managed";
    private const string ModOpinions = @"D:\Steam\steamapps\common\RimWorld\Mods\NudityMattersMore_opinions\1.6\Assemblies";
    private const string ModCore = @"D:\Steam\steamapps\common\RimWorld\Mods\RJW-功能-裸体评价\Assemblies";
    private const string ModRjw = @"D:\Steam\steamapps\common\RimWorld\Mods\RJW_核心_本体\1.6\Assemblies";
    private const string HarmonyDll = @"D:\Steam\steamapps\workshop\content\294100\2009463077\Current\Assemblies\0Harmony.dll";
    private const string PatchDll = @"D:\nmm_ui\NMMOpinionsChineseUI.dll";

    private static int pass = 0, fail = 0;

    private static void Main()
    {
        Console.OutputEncoding = Encoding.UTF8;
        AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        Run();
    }

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

    private static void Ok(string m) { pass++; Console.WriteLine("  [OK] " + m); }
    private static void Ng(string m) { fail++; Console.WriteLine("  [!!] " + m); }

    [MethodImpl(MethodImplOptions.NoInlining)]
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

    private static string Show(string s)
    {
        if (s == null) return "(null)";
        return "\"" + s.Replace("\r", "\\r").Replace("\n", "\\n") + "\"";
    }
}
