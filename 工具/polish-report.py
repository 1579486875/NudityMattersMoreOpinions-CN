# -*- coding: utf-8 -*-
"""收尾修整报告：改 §3.3 标题里不准确的表述、补 §4 已知限制与 §4b 模板问题。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, "..", "文档", "审查报告-双模组-第6轮-20261115.md"))

txt = open(P, encoding="utf-8").read()
changed = []

# ① §3.3 标题
old = "### 3.3 【中】`DefInjected\\NamedIndex\\` 整目录被丢弃 + 每次启动刷红字"
new = "### 3.3 【中】`DefInjected\\NamedIndex\\` 整目录被丢弃（且不写日志）"
if old in txt:
    txt = txt.replace(old, new, 1)
    changed.append("§3.3 标题")

# ② §4 已知限制：补 DLL 部署滞后
old4 = "3. **ThoughtDef 的 10 条命名索引**被丢弃而非改写"
add4 = ("3. **部署目录的 DLL 仍是 1.4.23.0**：本轮把程序集版本号同步到 1.5.1 并重编了，"
        "但游戏正在运行、DLL 被进程锁住，无法复制进 Mods。功能上两份完全一致"
        "（注释不进 IL，重编前后 SHA256 逐字节相同；版本号只影响 About 与程序集的对照），"
        "差异仅一个版本号字符串。**退出游戏后跑一次 `python 工具/deploy-dll.py` 即可**。\n"
        "4. **ThoughtDef 的 10 条命名索引**被丢弃而非改写")
if old4 in txt:
    txt = txt.replace(old4, add4, 1)
    changed.append("§4 已知限制")

# ③ §4b 模板问题：补本轮新踩的坑
old4b = "3. **抽象 Def 的翻译**：`Abstract=\"True\"` 的 Def 不在 DefDatabase，任何 `<模板名.字段>` 的键都会报 `Found no … named …`。模板附录可加这一条。"
add4b = (old4b + "\n"
         "4. **附录 A 第 30 条（heredoc 吃反斜杠）本轮又踩了一次**：往报告里插一段含 "
         "`Common\\Defs` 的文本时用了 `python - <<'PY'`，`\\D` 被当成转义序列，Python 直接抛 "
         "`SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes`。"
         "**结论：那条规则要升级成「凡是要写含反斜杠的多行文本，一律先落成 .py 文件再执行，"
         "不要在 heredoc 里现场拼」。** 本轮之后所有报告/源码插入都改成写脚本文件。\n"
         "5. **注释审计的口径要写明「排除控制流关键字」**：不排除的话 `else if (diff != 0)` 会被"
         "正则当成方法声明，于是覆盖率被误报成 97%（实际 100%）。这与 §3.2.4 列的六种误报是同一类。")
if old4b in txt:
    txt = txt.replace(old4b, add4b, 1)
    changed.append("§4b 模板问题")

open(P, "w", encoding="utf-8", newline="\n").write(txt)
print("已更新：" + " / ".join(changed))
print("文件 %d 字节" % len(txt.encode("utf-8")))
