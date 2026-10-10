# 裸体评价更多看法 简体汉化 —— 界面补丁 DLL 的构建脚本
#
# 干什么：
#   把 tools\ui-patch-tester\NMMOpinionsChineseUI.cs 编译成
#   Assemblies\NMMOpinionsChineseUI.dll（模组实际加载的那个）。
#
# 为什么需要这个脚本：
#   这个 DLL 以前没有对应的构建脚本 —— 换台机器就只能靠记忆敲 csc 命令行。
#   本脚本把路径探测、编译、回验都固化下来，任何人 clone 下来都能一键重建。
#
# 怎么用（在仓库根目录执行）：
#   powershell -ExecutionPolicy Bypass -File tools\build-patch-dll.ps1
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
#       离线行为验证见 tools\ui-patch-tester\run.ps1。

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $here
$src      = Join-Path $here 'ui-patch-tester\NMMOpinionsChineseUI.cs'
$outDll   = Join-Path $repoRoot 'Assemblies\NMMOpinionsChineseUI.dll'

Write-Host "仓库根目录 : $repoRoot"
Write-Host "源码       : $src"
Write-Host "输出       : $outDll"
Write-Host ""

if (-not (Test-Path $src)) { Write-Host "找不到源码：$src" -ForegroundColor Red; exit 1 }

# ══════════ 探测 RimWorld 安装目录 ══════════
# 注意：不要写成 `$x = @(...) | Where-Object {...}` —— 只剩一个元素时
# PowerShell 会把结果拆成标量，后面 $x[0] 就变成「字符串的第一个字符」。
# 所以这里用 foreach 显式累加，取用时再套一层 @()。
$rimWorldList = @()
foreach ($c in @('D:\steam\steamapps\common\RimWorld',
                 'C:\Program Files (x86)\Steam\steamapps\common\RimWorld',
                 'C:\Program Files\Steam\steamapps\common\RimWorld',
                 $env:RIMWORLD_DIR)) {
    if ($c -and (Test-Path (Join-Path $c 'RimWorldWin64_Data\Managed\Assembly-CSharp.dll'))) {
        $rimWorldList += $c
    }
}
if ($rimWorldList.Count -eq 0) {
    Write-Host '找不到 RimWorld。请设环境变量 RIMWORLD_DIR 指向安装目录。' -ForegroundColor Red
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

Write-Host '编译中…' -ForegroundColor Cyan
& $csc /target:library /out:"$outDll" /codepage:65001 /nologo /optimize+ /deterministic `
    /reference:"$managed\Assembly-CSharp.dll" `
    /reference:"$managed\UnityEngine.CoreModule.dll" `
    /reference:"$harmony" `
    $src
if ($LASTEXITCODE -ne 0) { Write-Host '编译失败' -ForegroundColor Red; exit 1 }
if (-not (Test-Path $outDll)) { Write-Host '编译成功但产物不存在' -ForegroundColor Red; exit 1 }

$after = (Get-FileHash $outDll -Algorithm SHA256).Hash
Write-Host ""
Write-Host "构建完成 : $outDll" -ForegroundColor Green
Write-Host ("大小     : {0:N0} 字节" -f (Get-Item $outDll).Length)
Write-Host "SHA256   : $after"
Write-Host ""
Write-Host "说明：本脚本已加 /deterministic（确定性编译）。" -ForegroundColor DarkGray
Write-Host "      同一份源码重复编译应当得到完全相同的 SHA256 ——" -ForegroundColor DarkGray
Write-Host "      也就是说，以后「仓库里的 DLL 是不是这份源码编出来的」可以直接用哈希核对。" -ForegroundColor DarkGray
Write-Host "      若哈希仍与上一次不同，那通常意味着源码确实改过了（这正是我们想看到的信号）。" -ForegroundColor DarkGray
Write-Host ""
Write-Host '下一步：跑 tools\ui-patch-tester\run.ps1 做离线行为验证。' -ForegroundColor Cyan
