# -*- coding: utf-8 -*-
"""把「向下兼容」一节插入第 6 轮审查报告（用文件写，避免 heredoc 吃掉反斜杠）。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "文档", "审查报告-双模组-第6轮-20261115.md")
P = os.path.abspath(P)

ADD = r"""### 1.2b 向下兼容：1.5 与「别人手里的旧版原模组」

这一节是本轮新增的实测（`工具/audit-oldversions.py` + 反编译 1.5 的 dll）。

**① 游戏 1.5**：原模组 `NudityMattersMore_opinions` 的 `loadFolders.xml` 是

```xml
<v1.5><li>Common</li><li>1.5</li></v1.5>
<v1.6><li>Common</li><li>1.6</li></v1.6>
```

`1.5` 与 `1.6` 目录里**都只有 Assemblies 和 Source、没有 Defs** —— 两个版本的 Def 全部来自共用的 `Common\Defs`。所以 1.5 与 1.6 的 Def 集合**完全相同**，我们的根目录翻译对 1.5 一样有效。

反编译 `1.5\Assemblies\NudityMattersMore_opinions.dll`（MVID `38b48b07…`，67 类型 / 211 方法）：

| 检查项 | 结果 |
|---|---|
| `OpinionDef_SexPart.opinionTexts` | `List<String>` ✓ 与 1.6 一致 |
| `OpinionDef_Situational.opinionTexts` | `List<String>` ✓ |
| 有无 `OpinionTextTranslator` / `NMM.Opinion` 字面量 | **0 处** → 1.5 与 1.6 一样走整列表注入，没有 Keyed 通道 |

**② 原模组的历史版本**（用户提到的「别人可能还装着旧版」）：

| 版本 | commit | 实际 Def | 与当前版本的差异 | 我们的汉化 |
|---|---|---|---|---|
| **1.0.8** | `474998c` | 5,342 | 文件级 `diff -rq` 与当前 `Common/Defs` **0 个文件不同** | **100% 生效** |
| **1.0.7** | `a8ad41d` | 5,342 | defName / 条数全部一致（5,214 个组合逐条核对） | **100% 生效** |
| 1.0.5 | `45e1d4e` | 5,264 | 9 个「睡姿」Def 的条数从 3~6 变成 20 | 这 9 个 Def 显示英文（其余 5,127 个组合正常） |
| 1.0.3 | `5f12374` | 5,264 | 同上 | 同上 |

**为什么 1.0.5/1.0.3 这 9 个不能硬兼容**（本轮查得最细的一处）：

作者在 1.0.7→1.0.8 之间把正文里的占位符从 `{PAWN_nameShort}` 改成了 `{OBSERVED_nameShort}`。逐条比对旧版与当前版本的原文：

```
iSaw_sleeping_naked_Male_Negative   旧 'As I walked in, my gaze fell upon {PAWN_nameShortPossessive}…'
                                    新 'As I walked in, my gaze fell upon {OBSERVED_nameShortPossessive}…'
```

9 个里只有 2 个（Unisex_Negative / Neutral）旧版原文是当前版本的前缀，其余 7 个都是**占位符改名**。

如果按「取前 min(N,M) 条」硬注入，我们译文里的 `{OBSERVED_nameShort}` 在旧版里**不会被替换**，玩家会看到字面量 `{OBSERVED_nameShort}` —— 比显示英文更糟。

所以注入器现在的行为（条数不符就整条跳过，宁可漏译不串行）是**唯一安全**的选择，本轮维持不变，并在描述里写明这条限制。

"""


def main():
    txt = open(P, encoding="utf-8").read()
    anchor = "### 1.3 性能 —— ✅"
    if "### 1.2b" in txt:
        print("已存在，跳过")
        return 0
    if anchor not in txt:
        print("锚点未命中")
        return 1
    txt = txt.replace(anchor, ADD + anchor, 1)
    open(P, "w", encoding="utf-8", newline="\n").write(txt)
    print("已插入 §1.2b（%d 字节）" % len(txt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
