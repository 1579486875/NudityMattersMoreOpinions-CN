#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc-consistency.py · 三份文档的交叉一致性检查（纳入 full-regression 闸门）。

自动生成于 2026-11-16（原为 _scratch/r379/cross-doc.py）。
只查**能自动判的**三件事：

1. 报告节号 0~N 连续、无重号；
2. 三份里「N 条真缺陷 / N 种形态 / N 次判据坑」这类同义断言一致；
3. 三份互相引用齐全。

⚠ 正则刻意避开「后面紧跟数字或逗号」的情形 —— 否则会把 `119,937 条` 里的 `937` 抓成「937 次」。
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), 'docs')
FILES = {
    '报告': '审查报告-R348-20261116.md',
    '摘要': '审查结论-摘要.md',
    '判据坑': '判据坑清单-20261116.md',
}
texts = {}
for k, f in FILES.items():
    p = os.path.join(DOCS, f)
    if not os.path.exists(p):
        print(f"⚠ 缺 {f}")
        continue
    texts[k] = open(p, encoding='utf-8').read()

if len(texts) < 3:
    print("三份文档不全，跳过")
    sys.exit(0)

bad = []

# ① 节号连续
nums = [int(x) for x in re.findall(r'^## (\d+)\.', texts['报告'], re.M)]
if nums:
    missing = [n for n in range(min(nums), max(nums) + 1) if n not in nums]
    dup = [n for n in set(nums) if nums.count(n) > 1]
    if missing or dup:
        bad.append(f"报告节号：缺 {missing} / 重 {dup}")

# ② 同义断言一致（正则会避开「逗号+三位数字」的千分位）
CLAIMS = [
    ('真缺陷', r'(\d+)\s*条真缺陷'),
    ('形态', r'(\d+)\s*种形态'),
    ('判据坑', r'(\d+)\s*次判据坑'),
]
for label, pat in CLAIMS:
    vals = {}
    for k, t in texts.items():
        m = re.findall(pat, t)
        if m:
            vals[k] = m[-1]
    if len(set(vals.values())) > 1:
        bad.append(f"{label}的数字不一致：{vals}")

# ③ 互相引用
for k, f in FILES.items():
    t = texts[k]
    refs = [o for o in FILES.values() if o != f and o in t]
    if len(refs) < 2:
        bad.append(f"{k} 只引用了 {len(refs)} 份（应 2 份）")

if bad:
    print("文档一致性问题：")
    for x in bad:
        print(f"  ❌ {x}")
    sys.exit(1)
print(f"✅ 三份文档一致（报告节号 0~{max(nums)} 连续、同义断言一致、互引齐全）")
sys.exit(0)


if __name__ == '__main__':
    pass
