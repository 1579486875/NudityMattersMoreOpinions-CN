# 裸体评价更多看法 简体汉化

> **📦 下载**：[最新版本（Release）](https://github.com/1579486875/NudityMattersMoreOpinions-CN/releases/latest)
> 下载 zip，解压后把整个文件夹放进 RimWorld 的 `Mods\` 目录即可。

> **一句话**：把「Nudity Matters More opinions」的 **123,021 条看法正文**翻成中文 ——
> 并且让它**真正在游戏里生效**。

| | |
|---|---|
| 适用版本 | RimWorld **1.6** |
| 汉化版本 | **1.0.0** |
| packageId | `shark510.nuditymattersmoreopinions.zhfix` |
| 前置模组 | `dord.nuditymattersmore`（Nudity Matters More）<br>`shark510.nuditymattersmoreopinions`（Nudity Matters More opinions） |
| 翻译条目 | **132,454** 条，覆盖 **5,082** 个 Def |
| 是否修改原模组 | **完全不碰**，不改动任何原模组文件 |
| 是否需要新开档 | **不需要**，旧档直接可用 |
| 卸载后残留 | **无** |

---

## 你遇到过这种情况吗？

### 情况一：装了汉化，看法还是全英文

你订阅过某个汉化包，模组列表里它也好端端地启用了，但游戏里点开角色 → 社交，
那些看法条目的内容**从头到尾还是英文**。

**这不是汉化没做，是汉化放错了地方** —— 具体原因见下一节。

### 情况二：条目名字是中文了，点开内容还是英文

有些汉化包只翻了「条目名称」（比如「赤裸上身」），
但**正文一句没翻**。因为正文是另一种数据类型，需要另一种写法才能翻。

### 情况三：想自己修，但不知道从哪下手

网上的教程大多只讲 `<Name.label>` 这种简单情况，
遇到模组自定义的 Def 类型就没人说了。

**这三个问题，本汉化一次性解决。**

---

## 为什么原来的汉化不生效

这一节是给想搞明白原理的人看的，普通玩家可以跳过。

### 根因：RimWorld 按「Def 的类型」建目录

RimWorld 加载翻译时，是**按目录名去找 Def 的**：

```
Languages\ChineseSimplified\DefInjected\<Def的类型全名>\<任意文件名>.xml
```

这个模组的看法用的**不是**原版的 `Def` 或 `ThoughtDef`，
而是它自己定义的类型：

```
NudityMattersMore_opinions.OpinionDef_SexPart
NudityMattersMore_opinions.OpinionDef_Situational
```

而现成的翻译包把译文放进了 `DefInjected\Def\` 目录。

**目录名对不上 → 游戏找不到对应类型的 Def → 整批翻译被静默忽略。**

注意「静默」两个字：**不报错、不提示、日志里一个字都没有**，
游戏里就是纯英文，让你完全不知道问题出在哪。

### 修法

把译文放进**正确类型名**的目录：

```
Languages\ChineseSimplified\DefInjected\NudityMattersMore_opinions.OpinionDef_SexPart\
Languages\ChineseSimplified\DefInjected\NudityMattersMore_opinions.OpinionDef_Situational\
```

### 第二个坑：正文是列表，一条条翻

看法正文 `opinionTexts` 的类型是 `List<string>`（字符串列表）。
翻列表要用**带下标的键名**，一条一个键：

```xml
<SomeDef.opinionTexts.0>第一条正文</SomeDef.opinionTexts.0>
<SomeDef.opinionTexts.1>第二条正文</SomeDef.opinionTexts.1>
<SomeDef.opinionTexts.2>第三条正文</SomeDef.opinionTexts.2>
```

**键名里的序号绝不能写错**：写超了（比如 Def 只有 20 条，你写到 `.25`），
游戏会抛 `Index out of bounds` 异常，**导致整个翻译包失效** —— 比不翻还糟。

本汉化已逐条核对全部 123,021 个下标，全部落在合法范围内，且**完全连续无缺口**。

---

## 翻译内容

| 项目 | 数量 |
|---|---|
| 看法正文（`opinionTexts`） | **123,021** 条 |
| 看法条目名称（`label`） | **3,690** 条 |
| 互动日志（`InteractionDef`） | **128** 条 |
| 互动看法（`InteractionOpinionDef` 等） | 其余条目 |
| **键总数** | **132,454** 个 |
| 覆盖 Def | **5,082** 个 |
| 唯一原文 | **90,155** 条 |
| 译文总字数 | 约 **1,161 万**字符 |
| XML 分片 | **42** 个（每片 ≤ 3,000 条，便于阅读与维护） |

---

## 安装

1. 下载 [最新 Release](https://github.com/1579486875/NudityMattersMoreOpinions-CN/releases/latest) 的 zip
2. 解压出 `裸体评价更多看法-简体汉化` 文件夹
3. 放进 RimWorld 的 `Mods\` 目录：

   ```
   D:\Steam\steamapps\common\RimWorld\Mods\裸体评价更多看法-简体汉化\
   ```

4. 在游戏「模组」页面启用它，**排在原模组之后**（`About.xml` 里已经声明了 `loadAfter`，正常情况会自动排好）
5. 重启游戏

> **需要重新开档吗？** 不需要。翻译是纯文本替换，旧存档载入后立刻显示中文。

---

## 完整性验证

仓库自带一个独立的自检工具，**不需要任何额外文件**，
它会自己去读游戏目录里的原模组做比对：

```powershell
python tools\verify_patch.py
```

它会检查 7 项：

| # | 检查项 | 说明 |
|---|---|---|
| 1 | 原模组 Def 清单 | 读出原模组共有多少个 Def |
| 2 | 文件可解析性 | 每个 XML 能否被解析、共多少条翻译 |
| 3 | **键名有效性** | 每个键指向的 Def 是否真实存在（防悬空引用） |
| 4 | **下标合法性** | 每个下标是否落在该 Def 的实际条目数内（防越界） |
| 5 | 键唯一性 | 有无跨文件重复键（重复会报错） |
| 6 | 覆盖完整性 | 每个 Def 的正文是否全部翻译到位 |
| 7 | XML 转义 | 正文里有无会破坏 XML 的裸 `&` `<` `>` |

本仓库发布前已跑过一次，**7 项全部通过**。

> 工具顶部有两行路径配置，换电脑时改那两行即可。

---

## ⚠️ 关于启动开销（如实说明）

**这是本汉化唯一需要你知情的代价，我不打算藏着。**

RimWorld 加载翻译时有一段 **O(N²)** 的重复键检查
（`Verse.DefInjectionPackage.SetDefFieldAtPath`：每注入一个键，都要把整个注入字典重扫一遍）。

本汉化译文量极大（119,083 个键集中在同一个 Def 类型下），实测：

| 键数 | 迭代次数 | 耗时 |
|---|---|---|
| **119,083**（本汉化正文包） | 1.418 × 10¹⁰ | **约 146 秒** |
| 7,671 | 5.9 × 10⁷ | 约 0.6 秒 |
| 5,744 | 3.3 × 10⁷ | 约 0.3 秒 |
| **合计** | | **约 2.5 分钟** |

作为对比：第二大翻译包（AI 翻译包最大的一个类型）只有 10,864 键，耗时约 1.2 秒。

### 会影响什么

- **发生时机**：只在**游戏启动、加载模组时**一次。
- **不影响**：游戏运行时的帧数、加载存档速度、游戏流畅度。
- **量级参照**：如果你装了上千个模组，启动本来就要数分钟，本汉化会再增加约 2.5 分钟。

### 为什么不能优化（已逐一实测排除）

| 方案 | 为什么不行 |
|---|---|
| 改用「整列表」注入（1 键替代 26 键） | 游戏要求目标字段带 `[TranslationCanChangeCount]` 特性才允许。实测该模组 **0 个字段**带此特性，走这条路会报错且**完全不生效** |
| 把键分散到多个类型目录 | 目录名必须等于 Def 的真实类型，改了游戏就找不到 Def，翻译全失效 |
| 减少条目 | 会破坏翻译完整性 |

**结论：逐下标翻译是唯一正确且可行的写法，2.5 分钟是这条路的固有代价。**

> 唯一能消除它的办法是写 Harmony 补丁替换游戏那段循环。
> 本项目**不做** —— 需改写游戏核心方法，出错会让**所有模组**的翻译失效，
> 与其它 Harmony 模组冲突风险高，且游戏更新后可能失效。

---

## 目录结构

```
NudityMattersMoreOpinions-CN\
├── About\
│   └── About.xml                              模组元数据
├── Languages\ChineseSimplified\DefInjected\
│   ├── NudityMattersMore_opinions.OpinionDef_SexPart\
│   │   ├── OpinionTexts_Part001.xml ... Part039.xml    12.3 万条正文（39 片）
│   │   └── Opinions_SexPart.xml                        条目名称
│   ├── NudityMattersMore_opinions.OpinionDef_Situational\
│   │   └── OpinionTexts_Part001.xml ... Part003.xml      情境看法正文
│   └── InteractionDef\
│       └── Interactions.xml                            互动日志
├── tools\
│   └── verify_patch.py                        自检工具（7 项检查）
├── 汉化说明.md                                 中文说明（同 README）
├── README.md
└── LICENSE
```

每个 XML 分片里都写了中文注释，说明这个文件是干什么的、每一行怎么读、
**为什么必须一条条写而不能整个列表一起写**、以及修改时不能碰哪些东西
（键名、`{...}` 占位符、`[...]`、`& < >` 转义）。用词面向非程序员。

---

## 许可

MIT License —— 见 [LICENSE](LICENSE)。

本汉化是纯翻译文件，**不包含也不修改**原模组的任何内容。
原模组的著作权归其原作者所有。
