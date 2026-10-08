# 界面汉化补丁 —— 离线验证（不用启动游戏）
#
# 干什么：
#   在本机加载 RimWorld 的程序集与原模组 DLL，把补丁里的转译器函数单独跑一遍，
#   检查英文 / 俄文字符串有没有被换成中文。
#   这跟游戏里 Harmony 调用它走的是同一条代码路径，差别只是不渲染画面。
#
# 怎么用（在仓库根目录执行）：
#   powershell -ExecutionPolicy Bypass -File tools\ui-patch-tester\run.ps1
#
# 前置条件：
#   · RimWorld 1.6 已安装
#   · 原模组 NudityMattersMore_opinions 与其前置已安装
#   · 装了 Harmony（工坊 2009463077）
#   · 有 Visual Studio 的 Roslyn 编译器（VS 自带；没有就把 $Csc 改成别的 csc.exe）

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ══════════ 路径配置（换机器时只改这一段）══════════
$RimWorld   = 'D:\Steam\steamapps\common\RimWorld'
$Workshop   = 'D:\Steam\steamapps\workshop\content\294100'
$HarmonyId  = '2009463077'                       # Harmony 的工坊 ID
$Csc        = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
# ══════════════════════════════════════════════════

$here      = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent (Split-Path -Parent $here)
$managed   = Join-Path $RimWorld 'RimWorldWin64_Data\Managed'
$harmony   = Join-Path $Workshop "$HarmonyId\Current\Assemblies\0Harmony.dll"
$patchDll  = Join-Path $repoRoot 'Assemblies\NMMOpinionsChineseUI.dll'
$outExe    = Join-Path $here 'PatchTester.exe'

Write-Host "仓库根目录 : $repoRoot"
Write-Host "RimWorld   : $RimWorld"
Write-Host "补丁 DLL   : $patchDll"
Write-Host ""

foreach ($p in @($managed, $harmony, $patchDll, $Csc)) {
    if (-not (Test-Path $p)) { Write-Host "找不到：$p" -ForegroundColor Red; exit 1 }
}

Write-Host "编译验证程序…" -ForegroundColor Cyan
& $Csc /target:exe /out:"$outExe" /codepage:65001 /nologo `
    /reference:"$managed\Assembly-CSharp.dll" `
    /reference:"$managed\UnityEngine.CoreModule.dll" `
    /reference:"$managed\System.dll" `
    /reference:"$managed\System.Core.dll" `
    /reference:"$harmony" `
    /reference:"$patchDll" `
    (Join-Path $here 'PatchTester.cs')
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outExe)) {
    Write-Host "编译失败" -ForegroundColor Red
    exit 1
}

Write-Host "运行验证（不会启动游戏）…" -ForegroundColor Cyan
Write-Host ""
& $outExe
exit $LASTEXITCODE
