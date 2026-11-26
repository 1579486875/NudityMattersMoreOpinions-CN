# -*- coding: utf-8 -*-
"""
C# 注释覆盖实测（模板 §3.2 的验收项，不许空着）。

口径：
  · 只统计「有方法体」的方法声明（`名字(参数)` 后面跟 `{` 或表达式体 `=>`），
    排除字段、属性、构造函数以外的东西；
  · 「有注释」= 方法声明前 6 行内出现 `///`（XML 文档注释）或 `//`（行注释）；
  · 同时统计类级注释（`class X` 前 6 行内有注释）。

用法：python 工具/audit-comments.py <目录1> [<目录2> ...]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

METHOD_RE = re.compile(
    r'^\s*(?:public|private|protected|internal|static|override|virtual|async|sealed|new|extern|unsafe|partial|\s)*'
    r'[\w<>\[\],\.\?]+\s+(?P<name>[A-Za-z_]\w*)\s*\([^;]*$')
CLASS_RE = re.compile(r'^\s*(?:public|private|protected|internal|static|sealed|abstract|partial|\s)*class\s+(?P<name>\w+)')

# 这些不是方法声明 —— 不排除的话 `else if (diff != 0)` 会被 METHOD_RE 匹配上，
# 于是「245 个真方法里 238 个有注释」（97.1%）会被算成「有 8 个缺注释」，
# 补完注释还是 97%，白跑一轮。（模板 §3.2.5 记的就是这一条。）
SKIP_NAMES = ('if', 'else', 'for', 'foreach', 'while', 'switch',
              'catch', 'using', 'lock', 'return', 'new', 'throw', 'yield')


def scan(path):
    try:
        lines = open(path, encoding="utf-8-sig", errors="replace").read().split("\n")
    except Exception:
        return None
    methods = documented = 0
    classes = cdocs = 0
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if CLASS_RE.match(ln):
            classes += 1
            if any(("//" in lines[j]) or ("///" in lines[j])
                   for j in range(max(0, i - 6), i)):
                cdocs += 1
            continue
        # 方法：以 ( 结尾且下一行以 { 开头或含 =>
        m = METHOD_RE.match(ln)
        if m and m.group("name") not in SKIP_NAMES and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if not (nxt.startswith("{") or "=>" in nxt or nxt.startswith(")")):
                continue
            methods += 1
            if any(("//" in lines[j]) for j in range(max(0, i - 6), i)):
                documented += 1
    return {"methods": methods, "documented": documented,
            "classes": classes, "cdocs": cdocs, "lines": len(lines)}


def main():
    roots = sys.argv[1:]
    if not roots:
        print("用法：python 工具/audit-comments.py <目录...>")
        return 1
    for root in roots:
        if not os.path.isdir(root):
            print("跳过（不存在）：%s" % root)
            continue
        tm = td = tc = tcd = tf = tl = 0
        worst = []
        for dp, dn, fns in os.walk(root):
            for fn in sorted(fns):
                if not fn.endswith(".cs"):
                    continue
                r = scan(os.path.join(dp, fn))
                if not r or r["methods"] == 0:
                    continue
                tf += 1
                tl += r["lines"]
                tm += r["methods"]
                td += r["documented"]
                tc += r["classes"]
                tcd += r["cdocs"]
                ratio = r["documented"] / r["methods"]
                if ratio < 0.9:
                    worst.append((ratio, fn, r["documented"], r["methods"]))
        if tm == 0:
            print("%s：没有可统计的方法" % root)
            continue
        print("=" * 60)
        print(root)
        print("  .cs 文件 %d 个 / %d 行" % (tf, tl))
        print("  方法注释覆盖：%d / %d = %.1f%%" % (td, tm, 100.0 * td / tm))
        if tc:
            print("  类注释覆盖：  %d / %d = %.1f%%" % (tcd, tc, 100.0 * tcd / tc))
        if worst:
            print("  低于 90%% 的文件：")
            for ratio, fn, d, m in sorted(worst)[:8]:
                print("     %-40s %d/%d = %.0f%%" % (fn, d, m, ratio * 100))
        else:
            print("  ✅ 每个文件的注释覆盖都 ≥ 90%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
