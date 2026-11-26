#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R394 · 第 30 轮最终取证（修正版：LocalFixes 没有 final-check.py，改用 docstats）。

上一版的错：我把 NMM 的 `final-check.py` 也拿去跑 LocalFixes，
`subprocess` 找不到脚本 → `exit 2`，被我误记成「不合格项 1」。
**这是判据坑第 38 条：跨仓库套用脚本。**
"""
import os, subprocess, datetime, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # tools 的父目录的父目录 = 工作区根
NM = os.path.join(ROOT, 'NudityMattersMoreOpinions-CN')
LF = os.path.join(ROOT, 'modfix', 'GNH-LocalFixes')


def run(cwd, script, *args):
    p = os.path.join(cwd, script)
    if not os.path.exists(p):
        return None, ['（该仓库没有这个脚本）']
    r = subprocess.run([sys.executable, p] + list(args), cwd=cwd,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '').strip().split('\n')


def git(cwd, *args):
    r = subprocess.run(['git'] + list(args), cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.stdout.strip()


now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
print(f"最终取证 · {now}\n")

rows = []

# ① 两个仓库的 full-regression（各自的闸门集合）
for label, repo in (('NMM', NM), ('LocalFixes', LF)):
    code, out = run(repo, '工具/full-regression.py')
    s = [l for l in out if '通过' in l and '失败' in l]
    rows.append((f'{label} full-regression', code, s[-1] if s else ''))

# ② NMM 用 final-check，LocalFixes 用 docstats
code, out = run(NM, '工具/final-check.py')
rows.append(('NMM final-check', code, out[-1] if out else ''))
code, out = run(LF, '工具/docstats.py', '--check')
rows.append(('LocalFixes docstats --check', code, out[-1] if out else ''))

# ③ 文档一致性
code, out = run(NM, '工具/doc-consistency.py')
rows.append(('三份文档一致性', code, out[-1] if out else ''))

# ④ git
for label, repo in (('NMM', NM), ('LocalFixes', LF)):
    br = git(repo, 'rev-parse', '--abbrev-ref', 'HEAD')
    h = git(repo, 'rev-parse', '--short', 'HEAD')
    rem = git(repo, 'rev-parse', '--short', f'origin/{br}')
    dirty = len([x for x in git(repo, 'status', '--porcelain').split('\n') if x.strip()])
    rows.append((f'{label} git', 0 if (h == rem and dirty == 0) else 1,
                 f'{h} == {rem}, 未提交 {dirty}'))

print(f"{'项':<30} {'exit':>5}  输出")
print('-' * 92)
bad = 0
for name, code, note in rows:
    ok = (code == 0)
    if not ok:
        bad += 1
    print(f"{'✅' if ok else '❌'} {name:<28} {str(code):>5}  {note[:52]}")

print('-' * 92)
print(f"不合格项：{bad}")
sys.exit(1 if bad else 0)
