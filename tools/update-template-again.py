# -*- coding: utf-8 -*-
"""模板再补两处：附录 A 第 30 条升级（heredoc 一律落成 .py 文件）+ §3.2.4 增补注释审计的口径陷阱。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"E:\TAML\提示词库\RimWorld模组-全面审查与修复-通用模板.txt"

raw = open(P, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
txt = raw.decode("utf-8-sig")
CRLF = "\r\n" in txt
if CRLF:
    txt = txt.replace("\r\n", "\n")

changed = []

# ── ① 附录 A 第 30 条：把结论从「注意转义」升级成「一律落成 .py 文件」
old30 = ("| 30 | 在 MSYS bash 的 heredoc（`<< 'EOF'`）或 `python -c` 里写反斜杠 | "
         "**反斜杠会被吃掉一层** —— 实测写 `b'\\\\r'`（想得到「反斜杠 + r」两字符）落进文件却变成了"
         "**裸 CR（0x0D）**，写 `b'\\\\b'` 变成**裸 BS（0x08）**。症状：Markdown 里一条路径渲染成两行、"
         "另一条少了 `\\b` 两个字符，**肉眼在终端里看不出来**（终端把 CR 当换行、把 BS 当退格执行） | "
         "附录 A 第 30 条 |")
if old30 in txt:
    new30 = old30[:-2] + (
        "。**2026-11-15 补：不止会「吃掉」，还会直接报错** —— `python - <<'PY'` 里写 "
        "`Common\\Defs` 会抛 `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes`（`\\D` 被当转义）；"
        "写 `\\N{...}` 更会变成 unicode 名字查找。**升级后的纪律：凡是要写含反斜杠的多行文本，"
        "一律先用 write 工具落成 `.py` 文件再执行 —— 不要在 heredoc 里现场拼** | 附录 A 第 30 条 |")
    txt = txt.replace(old30, new30, 1)
    changed.append("附录 A 第 30 条")
else:
    print("[跳过] 第 30 条锚点未命中")

# ── ② §3.2.4 增补：注释审计的口径陷阱（控制流关键字）
anchor = "### §3.4 修复项的组织规范"
add = """#### 3.2.5 注释审计最常误报的一处：把控制流关键字当成方法声明

用正则统计「方法注释覆盖率」时，如果只写「`名字(参数)` 结尾」这一条，
下面这行会被算成一个方法：

```csharp
else if (diff != 0)          // ← 被当成 "有个叫 diff 的方法"
```

实测后果：某工程 245 个真方法里只有 238 个带注释（97.1%），
但因为混进了 7 个控制流关键字，报表会显示成「有 245 个方法、8 个缺注释」，
于是**修完还是 97%**，白白多跑一轮。

**正确写法**：先排除这些关键字再统计

```python
SKIP = ('if', 'else', 'for', 'foreach', 'while', 'switch',
        'catch', 'using', 'lock', 'return', 'new')
```

**顺带一条判据**：注释改动**不会**改变 DLL 的 IL。实测把 8 处注释补齐后重编，
`GNH.LocalFixes.dll` 的 SHA256 与改前**逐字节相同**（`FDB0E044…`）。
所以「补注释要不要重新实机验证」的答案是**不用** —— 但**版本号**改动会进 IL，那个必须重编重部署。

"""
if anchor in txt and "#### 3.2.5" not in txt:
    txt = txt.replace(anchor, add + anchor, 1)
    changed.append("§3.2.5")
else:
    print("[跳过] §3.2.5（锚点缺失或已存在）")

out = txt.replace("\n", "\r\n") if CRLF else txt
open(P, "wb").write((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8"))
print("已更新：" + " / ".join(changed))
print("文件 %d 字节（CRLF=%s）" % (os.path.getsize(P), CRLF))
