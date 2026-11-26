# -*- coding: utf-8 -*-
"""把报告 §2b（注释覆盖）换成 2026-11-15 的实测数据，并补 §1.3 / §1.4。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, "..", "文档", "审查报告-双模组-第6轮-20261115.md"))

NEW_2B = r"""## 2b. 注释覆盖（模板 §3.2 的验收，不许空着）

用 `工具/audit-comments.py` 实测（口径：有方法体的声明，其前 6 行内出现 `//` 或 `///`；
排除 `if/else/for/foreach/while/switch/catch/using/lock/return/new` 这类控制流关键字，
否则 `else if (diff != 0)` 会被误判成方法声明）。

| 范围 | 文件 / 行 | 方法注释 | 类注释 |
|---|---|---|---|
| 汉化包 `工具/ui-patch-tester` | 4 个 .cs / 2,376 行 | **36 / 36 = 100%** | 4 / 7（三个是 Harmony 补丁类，注释写在文件头） |
| 修复补丁 `GNH-LocalFixes/src` | 54 个 .cs / 19,291 行 | **245 / 245 = 100%** | 60 / 61 = 98.4% |

本轮补的 8 处全是「静态构造函数 / override」——此前的口径漏掉了它们：
`Bootstrap()`、`CumpilationSettingsRestoreFix()`、`DocStatsSelfCheck()`、
`VehicleFrameworkDebugFix()`、`MakeNewToils()`、`GetHashCode()`、`ExposeData()`、
`SettingsCategory()`。每处都按「什么时候执行 / 不修会怎样 / 会不会抛」三段式写。

**一项额外的反证**：改完注释重编，两个 DLL 的 SHA256 与改前**逐字节相同**
（`GNH_NMM_Enhanced_ZH.dll` = `000A63BA…`、`NMMOpinionsChineseUI.dll` = `62B7599A…`，
修复补丁 `GNH.LocalFixes.dll` = `FDB0E044…`）—— 证明注释确实不进 IL，
不存在「补注释会不会改坏行为」这个风险。

"""

NEW_13 = r"""### 1.3 性能 —— ✅（本轮补了实测口径）

| 检查项 | 结果 |
|---|---|
| 有没有补到 `Tick` / `TickRare` / `Update` 这类高频方法的 | 修复补丁 22 个 XML 补丁里 **0 个**打在这些方法上；dll 侧只有 `Patch_Thing_DynamicDrawPhase_SwallowRealtimeNre` 落在绘制阶段，且它是「只在抛 NRE 时拦一次、每 500 次才记一条日志」 |
| 汉化包的正文读取路径 | 1.7 走游戏原生 `Translator.CanTranslate(key)`（字典查找），1.6/1.5 走 `OwnInjections` 一次性反射写回，**运行期零反射** |
| 注入器有没有 O(n²) | `OwnListInjector` 只对每个容器做一次 `List<string>` 逐条赋值；`InheritedBaseText` 判据只比较首/末元素，O(1) |
| 日志刷屏 | 本轮加载期日志 18.3 MB（模板基线：18 MB 属正常），`[GNH LocalFixes]` 71 条、总量可控 |

"""

NEW_14 = r"""### 1.4 必要性复核 —— 66 条仍必要 / 0 条冗余 / 1 条待观察

- **0 条冗余**：66 条修复逐条对过「目标模组是否已自行修好」。其中【36】SRAELib
  在 2026-11-05 由上游修好，本补丁已经内置「上游已修好就让路」的判断
  （本次启动日志里可见 `XML 补丁按「上游已自行修好」让路：RJW17_SraeLibFieldCleanup.xml`），
  所以它虽然留着但不会重复修。
- **1 条待观察**：【60】「整数字段被写成小数」只覆盖了定位到的 141 条，
  本次启动仍刷 34 条 `Parsed X as int`（README 里已如实写明「还剩约 40 条没定位」）。
  这属于「已知未覆盖」，不是缺陷。
- 新增的 3 项（627 个 Def 索引复位 / 526 条悬空译文搬迁 / NamedIndex 处置）
  都是「不修就看不出错」的静默失效，属于必要项。

"""


def main():
    txt = open(P, encoding="utf-8").read()
    changed = []

    # 替换 §2b 整段（到下一个 "## 3." 之前）
    import re
    m = re.search(r"## 2b\. 注释覆盖.*?(?=^## 3\.)", txt, re.S | re.M)
    if m:
        txt = txt[:m.start()] + NEW_2B + "\n" + txt[m.end():]
        changed.append("§2b")
    else:
        print("§2b 段落未找到")

    # 替换 §1.3
    m = re.search(r"### 1\.3 性能 —— ✅.*?(?=### 1\.4)", txt, re.S)
    if m:
        txt = txt[:m.start()] + NEW_13 + txt[m.end():]
        changed.append("§1.3")

    # 替换 §1.4
    m = re.search(r"### 1\.4 必要性 ——.*?(?=^---)", txt, re.S | re.M)
    if m:
        txt = txt[:m.start()] + NEW_14 + txt[m.end():]
        changed.append("§1.4")

    open(P, "w", encoding="utf-8", newline="\n").write(txt)
    print("已更新：" + " / ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
