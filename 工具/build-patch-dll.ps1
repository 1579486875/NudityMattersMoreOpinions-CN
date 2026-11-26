# 裸体评价更多看法 简体汉化 —— 界面补丁 DLL 的构建脚本
#
# 干什么：
#   把 工具\ui-patch-tester\NMMOpinionsChineseUI.cs 编译成
#   Assemblies\NMMOpinionsChineseUI.dll（模组实际加载的那个）。
#
# 为什么需要这个脚本：
#   这个 DLL 以前没有对应的构建脚本 —— 换台机器就只能靠记忆敲 csc 命令行。
#   本脚本把路径探测、编译、回验都固化下来，任何人 clone 下来都能一键重建。
#
# 怎么用（在仓库根目录执行）：
#   powershell -ExecutionPolicy Bypass -File 工具\build-patch-dll.ps1
#
# 前置条件：
#   · RimWorld 1.6 已安装（要它的 Assembly-CSharp.dll 与 UnityEngine.CoreModule.dll）
#   · 装了 Harmony（工坊 2009463077，要它的 0Harmony.dll）
#   · 有 Roslyn 版 csc.exe（VS / VS BuildTools 自带）
#     ⚠ 不能用 C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe ——
#       那是 C# 5 编译器，而本源码用了 C# 6 的 nameof，会报 CS0103。
#
# 换机器时：可以直接设环境变量 RIMWORLD_DIR / HARMONY_DIR 覆盖自动探测。
#
# 说明：本脚本只做「能否编译」与「产物是否落位」，不做游戏内验证。
#       离线行为验证见 工具\ui-patch-tester\run.ps1。

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $here
$srcDir   = Join-Path $here 'ui-patch-tester'
# 本 DLL 由两个源文件组成，两个都必须出现在编译命令行里 —— 漏一个会「编译通过但功能缺失」：
#   NMMOpinionsChineseUI.cs —— 入口 Bootstrap + 界面硬编码字符串的 Harmony 替换
#   OwnListInjector.cs      —— 「方案 C」自有清单运行时注入（读 OwnInjections\ 下的 XML）
# 产物一：NMMOpinionsChineseUI.dll（界面替换 + 1.6 自有清单注入）
$srcs     = @((Join-Path $srcDir 'NMMOpinionsChineseUI.cs'),
              (Join-Path $srcDir 'OwnListInjector.cs'))
$outDll   = Join-Path $repoRoot 'Assemblies\NMMOpinionsChineseUI.dll'

# 产物二：GNH_NMM_Enhanced_ZH.dll（1.7 合并版「增强界面」硬编码文字替换）
# ⚠ 2026-11-15 审计发现：本脚本此前【只编第一个】，第二个 DLL 没有任何构建脚本，
#   只有 final-check.py 会检查它存不存在 —— 等于「一键重建」这句话只对一半成立。
#   任何人 clone 下来重建，都会得到一个缺了增强界面汉化的包，而且不会报错。
$srcs2    = @((Join-Path $srcDir 'GNH_NMM_Enhanced_ZH.cs'))
$outDll2  = Join-Path $repoRoot 'Assemblies\GNH_NMM_Enhanced_ZH.dll'

Write-Host "仓库根目录 : $repoRoot"
Write-Host "源码       : $($srcs -join '  +  ')"
Write-Host "输出       : $outDll"
Write-Host ""

foreach ($s in ($srcs + $srcs2)) {
    if (-not (Test-Path $s)) { Write-Host "找不到源码：$s" -ForegroundColor Red; exit 1 }
}

# ══════════ 探测 RimWorld 安装目录 ══════════
# 注意：不要写成 `$x = @(...) | Where-Object {...}` —— 只剩一个元素时
# PowerShell 会把结果拆成标量，后面 $x[0] 就变成「字符串的第一个字符」。
# 所以这里用 foreach 显式累加，取用时再套一层 @()。
$rimWorldList = @()
# ⚠ 2026-11-16 订正（审查 D-04）：候选里**第一位放 1.6 引擎副本**。
#
#   原因是 1.7（Waylith 引擎，2026-10-27 换装）换了布局：
#     · 旧版（1.6 及以前，Unity/Mono）—— 托管 dll 在 <root>\RimWorldWin64_Data\Managed\
#       含 Assembly-CSharp.dll / UnityEngine.CoreModule.dll / System.Xml.dll / netstandard.dll
#     · 1.7 —— **没有 RimWorldWin64_Data 这个文件夹**，dll 平铺在 <root>\ 根目录，
#       而且 UnityEngine 只剩一个 UnityStubs.dll（与下面的 /reference 列表对不上）
#
#   本脚本的 /reference 列表是按 1.6 布局写的 —— 这是**故意的**：编出来的 net472 产物
#   在 1.7 上靠 Waylith 的 LaxAssemblyBinding 也能跑（见 GNH.LocalFixes.csproj 的同段说明）。
#   所以**编译环境应该固定用 1.6 引擎副本**。
#
#   实测（2026-11-16）：把 1.7 主安装放第一位时，本脚本会报「找不到 RimWorld」——
#   因为 RimWorldWin64_Data\Managed\Assembly-CSharp.dll 在 1.7 下不存在，
#   于是「一键重建」在 1.7 机器上直接失效，且报错信息指向「你装没装游戏」，
#   与实际原因（布局变了）完全无关。
foreach ($c in @('D:\RimWorld-1.6',
                 'D:\steam\steamapps\common\RimWorld',
                 'C:\Program Files (x86)\Steam\steamapps\common\RimWorld',
                 'C:\Program Files\Steam\steamapps\common\RimWorld',
                 $env:RIMWORLD_DIR)) {
    if ($c -and (Test-Path (Join-Path $c 'RimWorldWin64_Data\Managed\Assembly-CSharp.dll'))) {
        $rimWorldList += $c
    }
}
if ($rimWorldList.Count -eq 0) {
    Write-Host '找不到可用于编译的 RimWorld 安装。' -ForegroundColor Red
    Write-Host '本脚本需要 1.6 风格布局（<root>\RimWorldWin64_Data\Managed\Assembly-CSharp.dll）。' -ForegroundColor Yellow
    Write-Host '  1.7（Waylith）主安装已没有这个目录 —— 请改用 1.6 引擎副本，' -ForegroundColor Yellow
    Write-Host '  或设环境变量 RIMWORLD_DIR 指向它，例如：' -ForegroundColor Yellow
    Write-Host '    $env:RIMWORLD_DIR = "D:\RimWorld-1.6"' -ForegroundColor Yellow
    exit 1
}
$rimWorld = @($rimWorldList)[0]

# ══════════ 探测 Harmony 的 0Harmony.dll ══════════
# 优先用 Harmony 自己的工坊 ID（2009463077）的 Current\Assemblies，
# 否则会命中十几年前的旧包（实测过 1098354593\0.19\Assemblies）。
$harmony = $null
if ($env:HARMONY_DIR) {
    $p = Join-Path $env:HARMONY_DIR '0Harmony.dll'
    if (Test-Path $p) { $harmony = $p }
}
if (-not $harmony) {
    foreach ($ws in @('D:\steam\steamapps\workshop\content\294100',
                      'C:\Program Files (x86)\Steam\steamapps\workshop\content\294100',
                      'C:\Program Files\Steam\steamapps\workshop\content\294100')) {
        if (-not (Test-Path $ws)) { continue }
        foreach ($rel in @('2009463077\Current\Assemblies\0Harmony.dll',
                           '2009463077\1.6\Assemblies\0Harmony.dll',
                           '2009463077\Assemblies\0Harmony.dll')) {
            $p = Join-Path $ws $rel
            if (Test-Path $p) { $harmony = $p; break }
        }
        if ($harmony) { break }
    }
}
if (-not $harmony) {
    # 兜底：全盘递归找，但优先带 Current 的路径
    $all = @()
    foreach ($ws in @('D:\steam\steamapps\workshop\content\294100',
                      'C:\Program Files (x86)\Steam\steamapps\workshop\content\294100')) {
        if (-not (Test-Path $ws)) { continue }
        $all += Get-ChildItem $ws -Recurse -Filter '0Harmony.dll' -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty FullName
    }
    $pref = @($all | Where-Object { $_ -match 'Current' })
    if ($pref.Count -gt 0) { $harmony = @($pref)[0] }
    elseif ($all.Count -gt 0) { $harmony = @($all)[0] }
}
if (-not $harmony) {
    Write-Host '找不到 0Harmony.dll。请设环境变量 HARMONY_DIR 指向它的所在目录。' -ForegroundColor Red
    exit 1
}

# ══════════ 探测 Roslyn 版 csc.exe ══════════
$cscList = @()
foreach ($c in @('C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe',
                 'C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe',
                 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe',
                 'C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\Roslyn\csc.exe')) {
    if (Test-Path $c) { $cscList += $c }
}
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
    $vsPath = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -property installationPath 2>$null
    if ($vsPath) {
        $p = Join-Path $vsPath 'MSBuild\Current\Bin\Roslyn\csc.exe'
        if (Test-Path $p) { $cscList += $p }
    }
}
if ($cscList.Count -eq 0) {
    Write-Host '找不到 Roslyn 版 csc.exe（VS 或 VS BuildTools 自带）。' -ForegroundColor Red
    Write-Host '注意：C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe 是 C# 5 编译器，编译不了本源码（用了 nameof）。' -ForegroundColor Yellow
    exit 1
}
$csc = @($cscList)[0]

$managed = Join-Path $rimWorld 'RimWorldWin64_Data\Managed'
Write-Host "RimWorld   : $rimWorld"
Write-Host "Harmony    : $harmony"
Write-Host "编译器     : $csc"
Write-Host ""

$before = $null
if (Test-Path $outDll) {
    $before = (Get-FileHash $outDll -Algorithm SHA256).Hash
    Write-Host "构建前的 DLL : $before" -ForegroundColor DarkGray
}

# ⚠ netstandard.dll 必须引用（2026-11-15 实测补）：
#   NMMOpinionsChineseUI.cs 的 UpdateSize_Postfix 里有 `(UnityEngine.Vector2)f.GetValue(...)`，
#   Vector2 是 struct（ValueType），而 ValueType 在 .NET Framework 4.7.2 下由 netstandard 转发。
#   缺这条引用会报：
#     error CS0012: 类型"ValueType"在未引用的程序集中定义。
#             必须添加对程序集"netstandard, Version=2.1.0.0, ..."的引用。
#   之前一直没暴露，是因为每次都是用 dotnet 的 csc.dll 手敲命令行（那边默认带 netstandard）；
#   而本脚本用的 Roslyn csc.exe 不会自动带 —— 也就是说「按文档一键重建」这条路此前是坏的。
$netstandard = Join-Path $managed 'netstandard.dll'
if (-not (Test-Path $netstandard)) {
    Write-Host "缺少 netstandard.dll：$netstandard" -ForegroundColor Red
    Write-Host '它就在 1.6 的 RimWorldWin64_Data\Managed 下，随游戏一起安装。' -ForegroundColor Yellow
    exit 1
}

$targets = @(
    @{ Out = $outDll;  Srcs = $srcs  },
    @{ Out = $outDll2; Srcs = $srcs2 }
)
foreach ($tg in $targets) {
    Write-Host ('编译中… ' + (Split-Path $tg.Out -Leaf)) -ForegroundColor Cyan
    & $csc /target:library /out:"$($tg.Out)" /codepage:65001 /nologo /optimize+ /deterministic `
        /reference:"$managed\Assembly-CSharp.dll" `
        /reference:"$managed\UnityEngine.CoreModule.dll" `
        /reference:"$managed\System.Xml.dll" `
        /reference:"$netstandard" `
        /reference:"$harmony" `
        $tg.Srcs
    if ($LASTEXITCODE -ne 0) { Write-Host ('编译失败：' + (Split-Path $tg.Out -Leaf)) -ForegroundColor Red; exit 1 }
    if (-not (Test-Path $tg.Out)) { Write-Host ('编译成功但产物不存在：' + (Split-Path $tg.Out -Leaf)) -ForegroundColor Red; exit 1 }
}

Write-Host ""
foreach ($tg in $targets) {
    $a = (Get-FileHash $tg.Out -Algorithm SHA256).Hash
    Write-Host ("构建完成 : " + $tg.Out) -ForegroundColor Green
    Write-Host ("大小     : {0:N0} 字节" -f (Get-Item $tg.Out).Length)
    Write-Host "SHA256   : $a"
    Write-Host ""
}
Write-Host ""
Write-Host "说明：本脚本已加 /deterministic（确定性编译）。" -ForegroundColor DarkGray
Write-Host "      同一份源码重复编译应当得到完全相同的 SHA256 ——" -ForegroundColor DarkGray
Write-Host "      也就是说，以后「仓库里的 DLL 是不是这份源码编出来的」可以直接用哈希核对。" -ForegroundColor DarkGray
Write-Host "      若哈希仍与上一次不同，那通常意味着源码确实改过了（这正是我们想看到的信号）。" -ForegroundColor DarkGray
Write-Host ""
Write-Host '下一步：跑 工具\ui-patch-tester\run.ps1 做离线行为验证。' -ForegroundColor Cyan
