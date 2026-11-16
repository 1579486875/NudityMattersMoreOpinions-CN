# -*- coding: utf-8 -*-
"""
补最后 8 处缺失的方法注释（模板 §3.2 要求「方法注释必须让小白看懂」）。

这 8 处全部是「静态构造函数 / override」，此前的审计脚本因为判定口径把它们漏掉了。
只加注释，不改任何代码。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 2026-11-16 改：原先硬编码 E:\TAML\_work\nmzh-git（旧 clone）
MOD = r"E:\TAML\modfix\GNH-LocalFixes"

JOBS = [
    # (文件, 锚点, 注释, 缩进)
    (
        os.path.join(REPO, "tools", "ui-patch-tester", "GNH_NMM_Enhanced_ZH.cs"),
        "        static Bootstrap()\n",
        "        /// <summary>\n"
        "        /// 模组入口：由 CLR 在 `[StaticConstructorOnStartup]` 类首次被访问时执行一次。\n"
        "        /// 这一半装的是「增强界面文字替换」—— 合并版把大量文案写死在 C# 里，\n"
        "        /// 只能反射找到那些界面方法、把它们返回的字符串换成中文。\n"
        "        /// 目标方法找不到就跳过并记一行日志，不会抛异常。\n"
        "        /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "CumpilationSettingsRestoreFix.cs"),
        "        static CumpilationSettingsRestoreFix()\n",
        "        /// <summary>\n"
        "        /// 静态构造函数：CLR 保证只执行一次。\n"
        "        /// 做的事是「等所有延迟动作跑完之后，让 Cumpilation 自己重新读一次盘」——\n"
        "        /// 那个模组每次启动都会把 9 个开关强行写成 false（源码里 11 行赋值），\n"
        "        /// 玩家在设置里打开也没用。本类只在玩家没关掉本项、且 Cumpilation 真的在时安装。\n"
        "        /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "DocStatsSelfCheck.cs"),
        "        static DocStatsSelfCheck()\n",
        "        /// <summary>\n"
        "        /// 静态构造函数：把「文档里写的数字」与「仓库里的实际文件」对一次账。\n"
        "        /// 只打日志、不改任何东西 —— 用它的原因是 About.xml / README 里的数字\n"
        "        /// 曾经多次与实物脱节，手抄很容易漏。\n"
        "        /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "VehicleFrameworkDebugFix.cs"),
        "        static VehicleFrameworkDebugFix()\n",
        "        /// <summary>\n"
        "        /// 静态构造函数：CLR 保证只执行一次。\n"
        "        /// Vehicles 的 `Patch_Debug` 会把「这辆车被刷出来了」打成 Debug 消息，\n"
        "        /// 装了载具框架又开着调试日志的玩家会看到满屏刷。这里只把那个方法静音，\n"
        "        /// 载具本身的生成逻辑一点不动。\n"
        "        /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "JobDriver_BestialityInvite_Watching.cs"),
        "        protected override IEnumerable<Toil> MakeNewToils()\n",
        "        /// <summary>\n"
        "        /// 任务流程：邀请 → 等对方过来 → 旁观。\n"
        "        /// 四条「做到一半就放弃」的条件在方法体内逐条判断，任一成立就正常结束\n"
        "        /// （不报错、不把小人卡在原地）。\n"
        "        /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "DuplicateAssignableCompFix.cs"),
        "            public int GetHashCode(ThingWithComps obj)\n",
        "            /// <summary>\n"
        "            /// 按「对象引用」取哈希 —— 这些组件是按 Thing 实例比较的，\n"
        "            /// 不能按 def 或运行时 id 算（那样两个不同的小人会撞成同一个 key，\n"
        "            /// 于是第二个人的组件会被误判成重复而被丢掉）。\n"
        "            /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "GNHLocalFixesSettings.cs"),
        "        public override void ExposeData()\n",
        "        /// <summary>\n"
        "        /// 存档读写：只存玩家在这一页改过的开关状态。读的时候缺字段按默认值补，\n"
        "        /// 所以老存档升级上来不会丢设置，新增开关也不会让旧存档报错。\n"
        "        /// </summary>\n",
    ),
    (
        os.path.join(MOD, "src", "LocalFixesMod.cs"),
        "        public override string SettingsCategory()\n",
        "        /// <summary>\n"
        "        /// 「选项 → 模组设置」列表里显示的那个名字。走翻译键，取不到才回退到中文常量，\n"
        "        /// 这样英文客户端也不会看到一个中文分类名。\n"
        "        /// </summary>\n",
    ),
]


def main():
    write = "--write" in sys.argv
    ok = skip = fail = 0
    for path, anchor, comment in JOBS:
        if not os.path.exists(path):
            print("[缺失] %s" % path)
            fail += 1
            continue
        raw = open(path, "rb").read()
        bom = raw.startswith(b"\xef\xbb\xbf")
        txt = raw.decode("utf-8-sig")
        eol = "\r\n" if "\r\n" in txt else "\n"
        a = anchor.replace("\n", eol)
        c = comment.replace("\n", eol)
        if c + a in txt:
            print("[已存在] %-46s" % os.path.basename(path))
            skip += 1
            continue
        if a not in txt:
            print("[锚点未命中] %-40s %r" % (os.path.basename(path), anchor.strip()[:50]))
            fail += 1
            continue
        if txt.count(a) != 1:
            print("[锚点不唯一] %-40s 出现 %d 次" % (os.path.basename(path), txt.count(a)))
            fail += 1
            continue
        txt = txt.replace(a, c + a, 1)
        print("[补注释] %-46s" % os.path.basename(path))
        ok += 1
        if write:
            open(path, "wb").write((b"\xef\xbb\xbf" if bom else b"") + txt.encode("utf-8"))
    print()
    print("补 %d / 已存在 %d / 失败 %d" % (ok, skip, fail))
    if not write:
        print("（dry-run，加 --write 才真改）")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
