"""
打包脚本 — 将 ModChecker 封装为独立 .exe
用法: python build.py
输出: dist/ModChecker.exe
"""
import os, sys, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")

# 确保项目目录在 path 中，PyInstaller 能正确解析模块
sys.path.insert(0, ROOT)


def clean():
    """清理旧的构建产物"""
    for d in ["dist", "build"]:
        path = os.path.join(ROOT, d)
        if os.path.isdir(path):
            shutil.rmtree(path)
    spec = os.path.join(ROOT, "ModChecker.spec")
    if os.path.isfile(spec):
        os.remove(spec)


def build():
    """运行 PyInstaller"""
    import PyInstaller.__main__ as pyi

    pyi.run([
        os.path.join(ROOT, "main.py"),
        "--name=ModChecker",
        "--onefile",                    # 单文件 exe
        "--noconsole",                 # 不弹出 CMD 窗口，纯 GUI
        "--clean",
        "--add-data", f"web/templates{os.pathsep}web/templates",
        "--add-data", f"web/static{os.pathsep}web/static",
        "--hidden-import", "json5",
        "--hidden-import", "watchdog",
        "--hidden-import", "flask",
        "--hidden-import", "compatibility",
        "--hidden-import", "scanner",
        "--hidden-import", "nexus_api",
        "--hidden-import", "quick_scan",
        "--hidden-import", "deep_scan",
        "--hidden-import", "mod_status",
        "--hidden-import", "fix_mode",
        "--hidden-import", "cli_utils",
        "--hidden-import", "logger",
        "--hidden-import", "webbrowser",
        "--hidden-import", "gui",
        "--hidden-import", "gui.app",
        "--hidden-import", "conflict_checker",
        "--hidden-import", "conflict_checker.cp_analyzer",
        "--hidden-import", "conflict_checker.map_analyzer",
        "--hidden-import", "auto_fix",
        "--hidden-import", "auto_fix.manifest_fixer",
        "--hidden-import", "auto_fix.backup",
        "--hidden-import", "auto_fix.patch_generator",
        "--hidden-import", "data",
        "--hidden-import", "data.patch_record",
        "--distpath", DIST,
        "--workpath", os.path.join(ROOT, "build"),
        "--specpath", ROOT,
    ])


if __name__ == "__main__":
    print("开始打包 ModChecker...")
    print(f"   项目目录: {ROOT}")
    clean()
    build()
    print(f"\n打包完成!")
    print(f"   {os.path.join(DIST, 'ModChecker.exe')}")
    print(f"\n用法:")
    print(f"   ModChecker.exe              GUI 桌面窗口")
    print(f"   ModChecker.exe web          启动 Web 前端")
    print(f"   ModChecker.exe fix --auto   自动修复")
