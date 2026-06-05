"""
模块导入测试
确保所有核心模块能正常导入，无循环依赖
"""
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0


def _try_import(module_name):
    global PASS, FAIL
    try:
        __import__(module_name)
        print(f"  ✅ {module_name}")
        PASS += 1
    except Exception as e:
        print(f"  ❌ {module_name}: {e}")
        FAIL += 1


if __name__ == "__main__":
    print("测试模块导入...")
    print("=" * 50)

    modules = [
        "config",
        "scanner",
        "compatibility",
        "nexus_api",
        "quick_scan",
        "deep_scan",
        "mod_status",
        "file_watcher",
        "scan_cli",
        "fix_mode",
        # 子包
        "auto_fix",
        "auto_fix.backup",
        "auto_fix.manifest_fixer",
        "auto_fix.patch_generator",
        "auto_fix.patch_generator.compatibility_patch",
        "auto_fix.patch_generator.update_patch",
        "auto_fix.patch_generator.dotnet_check",
        "conflict_checker",
        "conflict_checker.cp_analyzer",
        "conflict_checker.map_analyzer",
        "conflict_checker.smapi_analyzer",
        "conflict_checker.smapi_analyzer.dep_analyzer",
        "conflict_checker.smapi_analyzer.dll_analyzer",
        "conflict_checker.smapi_analyzer.nexus_deps",
        "data",
        "data.patch_record",
    ]

    for mod in modules:
        _try_import(mod)

    print("=" * 50)
    print(f"结果: ✅ {PASS} 通过 | ❌ {FAIL} 失败")