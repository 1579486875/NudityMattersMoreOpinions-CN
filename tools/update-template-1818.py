# -*- coding: utf-8 -*-
"""给通用模板的附录 A 追加第 36/37/38 条踩坑，并新增 B.18 小节。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"E:\TAML\提示词库\RimWorld模组-全面审查与修复-通用模板.txt"

raw = open(P, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
txt = raw.decode("utf-8-sig")
CRLF_IN = "\r\n" in txt
if CRLF_IN:
    txt = txt.replace("\r\n", "\n")

ROW36 = (
    "| 36 | 给 `Abstract=\"True\"` 的**抽象模板 Def** 写 `<模板名.字段>` 的翻译键 | "
    "抽象 Def **不在 DefDatabase**（`GenDefDatabase.GetDefSilentFail(type, name)` 返回 null），"
    "而 `SetDefFieldAtPath` 进来第一件事就是查它、查不到就 `loadErrors.Add(\"Found no … named …\")` 并 return false "
    "—— 这条键永远无效。**但报错不进 Player.log**（见第 28 条），所以它是完全静默的失效。"
    "抽象模板自带的那些 `<li>`（例如 `BaseSexPartOpinionDef` 的 "
    "`Its just there, what to say more?`）只能靠**运行时注入**去替换 | "
    "2026-11-15 实测：汉化包 `DefInjected\\NamedIndex\\` 里 3 条 "
    "`BaseSexPartOpinionDef.opinionTexts.0` / `BaseSituationalOpinionDef.label` / `.opinionTexts.0` 从来没生效过 | "
    "附录 B.18 |"
)

ROW37 = (
    "| 37 | 把「列表元素按名字定位」（`degreeDatas.exhibitionist` / `stages.jealous`）当成不支持的写法 | "
    "**1.7 支持**。`DefInjectionPackage.SetDefFieldAtPath` 遇到「既不是数字、也不是字段名」的路径段会走 "
    "`DefInjectionPathPartKind.ListHandle` 分支，用 `TranslationHandleUtility.GetElementIndexByHandle` "
    "按**带 `[TranslationHandle]` 特性的字段值**定位元素（`TraitDegreeData` / `HediffStage` / `ThoughtStage` / "
    "`PawnKindLifeStage` / `RoomStatScoreStage` 的 `untranslatedLabel` 都带）。两个前提："
    "① 路径段与某个**字段名**同名时会被当成字段优先匹配，所以句柄不能撞字段名；"
    "② 句柄值必须与 Def 里那个字段的原文一致（归一化后比较），写错会 "
    "`throw \"None of the list elements have a handle named X\"` | "
    "2026-11-15 实测：`degreeDatas.exhibitionist` 有效（原模组 label 就是 `exhibitionist`），"
    "`stages.unwelcome_comparison` 无效（实际 label 是 `envy body`） | 附录 B.18 |"
)

ROW38 = (
    "| 38 | `DefInjected\\` 的子目录名**不是 Def 类型名** | "
    "`LoadedLanguage.LoadData` 会 `GenTypes.GetTypeInAnyAssembly(目录名)`（解析不到还会去掉末位字符再试一次），"
    "仍然解析不到就 `loadErrors.Add(\"... dir X doesn't correspond to any def type. Skipping...\")` 然后 "
    "`continue` —— **整目录的翻译全部丢弃**。这条错误同样只进 `loadErrors`（见第 28 条），"
    "`Player.log` 里一个字都没有，唯一的日志痕迹是汇总行 "
    "`Translation data for language … has N errors`。常见成因：为了「命名索引」自建 `NamedIndex\\`、"
    "或按功能而不是按 Def 类型建目录 | "
    "2026-11-15 实测：`DefInjected\\NamedIndex\\` 下 19 条键全部无效；其中 6 条 TraitDef 的句柄其实是正确的，"
    "搬到 `TraitDef\\` 后「拘谨 / 暴露狂 / 视奸狂」三个特质才首次显示中文 | 附录 B.18 |"
)

anchor = "\n\n---\n\n## 附录 B：1.6 → 1.7 迁移与 dll 级修复"
if "| 36 |" not in txt:
    if anchor not in txt:
        print("附录 A 表尾锚点未命中")
        sys.exit(1)
    txt = txt.replace(anchor, "\n" + ROW36 + "\n" + ROW37 + "\n" + ROW38 + anchor, 1)
    print("已插入第 36/37/38 条")
else:
    print("第 36 条已存在，跳过")

B18 = """
### B.18 四条「数据层看着没问题、游戏里却完全不生效」的判据（2026-11-15 实测）

> 这一节和 **B.17** 是同一类坑的续集。B.17 讲的是「错位」与「两套语言目录」，
> 这一节讲的是**键本身根本到不了目标**的四种情形。四条的共同点：
> **`Player.log` 里一个字都不会报**（`LoadedLanguage.loadErrors` 不写日志，
> 见 §B.12 与附录 A 第 28 条），只能靠读源码 + 写脚本对账发现。

#### B.18.1 抽象模板 Def（`Abstract="True"`）的键永远无效

```csharp
// Verse.DefInjectionPackage.SetDefFieldAtPath
string defName = path.Split('.')[0];
if (GenDefDatabase.GetDefSilentFail(defType, defName, false) == null)
{
    if (errorOnDefNotFound)
        loadErrors.Add("Found no " + defType + " named " + defName + " to match ...");
    return false;                        // ← 后面全不执行
}
```

抽象 Def 用 `Name="..."` 标识、**没有 `defName`**，也不进 DefDatabase。
所以 `<BaseSexPartOpinionDef.opinionTexts.0>` 这类键必然无效。

**要用它就只能走运行时**：像 `OwnListInjector` 那样在 `[StaticConstructorOnStartup]` 里
反射拿 `List<string>` 再逐条写回。

#### B.18.2 列表句柄（命名索引）是合法的，但有三个前提

```csharp
// SetDefFieldAtPath 里的路径段分类
if (int.TryParse(text3, out result))              defInjectionPathPartKind = ListIndex;
else if (GetFieldNamed(obj.GetType(), text3) != null) defInjectionPathPartKind = Field;
else if (obj.GetType().GetProperty("Count") != null)  defInjectionPathPartKind = ListHandle;   // ← 命名索引
```

前提：

1. **不能与字段名撞**（`Field` 分支优先）；
2. 元素类必须有一个带 `[TranslationHandle]` 的字段 —— 原版里有
   `TraitDegreeData.untranslatedLabel`、`HediffStage.untranslatedLabel`、
   `ThoughtStage.untranslatedLabel`、`PawnKindLifeStage.untranslatedLabel`、
   `RoomStatScoreStage.untranslatedLabel`；
3. **句柄值必须等于那个字段的原文**（`HandlesMatch` 会归一化：小写、去空格与标点）。

写错会直接抛 `None of the list elements have a handle named X`，被外层 catch 记进 `loadErrors`。

#### B.18.3 `DefInjected\` 子目录名必须是 Def 类型名

```csharp
// Verse.LoadedLanguage.LoadData
Type typeInAnyAssembly = GenTypes.GetTypeInAnyAssembly(directory4.Name);
if (typeInAnyAssembly == null && directory4.Name.Length > 3)
    typeInAnyAssembly = GenTypes.GetTypeInAnyAssembly(directory4.Name.Substring(0, directory4.Name.Length - 1));
if (typeInAnyAssembly == null)
{
    loadErrors.Add("Error loading language from " + allDirectory + ": dir " + directory4.Name
                   + " doesn't correspond to any def type. Skipping...");
    continue;                                  // ← 整目录丢弃
}
```

「末尾多一个字符」是游戏自己给的容错（所以 `ThoughtDefs\` 能当 `ThoughtDef\` 用）。

#### B.18.4 两版共用的根目录：每个键都要对**低版本**的 Def 集合查一次存在性

`LoadFolders` 的 `<v1.7><li>/</li><li>v1.7</li></v1.7>` 意味着
**根目录同时被 1.6 和 1.7 加载**。凡是只在高版本存在的 Def，键放根目录就会让低版本
逐条报 `Found no …`（这次是 526 条）。

```python
# 判据：把根目录的每个键，拿去 1.6 的 Def 集合里查
n16 = defnames(MOD16, ["Common"])          # 1.6 的 LoadFolders 只加载 Common + 1.6
for key in root_definjected_keys:
    if key.split(".")[0] not in n16:
        print("这个键在 1.6 下悬空，应移到 v1.7\\")
```

> **口诀**：**「根目录 = 两版共用」不是免责条款，是义务** —— 里面的每一个键都要对最低版本负责。
"""

tail_anchor = "\n---\n\n## 附篇 A：工具、技能与 MCP 清单"
if "### B.18 四条" not in txt:
    if tail_anchor in txt:
        txt = txt.replace(tail_anchor, B18 + tail_anchor, 1)
        print("已插入 B.18")
    else:
        # 退一步：放在文件里最后一个 "#### B.17.6" 段落之后
        print("B.18 尾部锚点未命中，尝试备用锚点")
        alt = "\n---\n\n## 附录"
        print("（放弃自动插入，请手工确认）")
else:
    print("B.18 已存在，跳过")

out = txt.replace("\n", "\r\n") if CRLF_IN else txt
open(P, "wb").write((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8"))
print("已写入 %d 字节" % os.path.getsize(P))
