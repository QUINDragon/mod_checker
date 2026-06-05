"""
SMAPI DLL 分析器
分析 .dll 文件的依赖关系和潜在冲突
"""
import os


def analyze_dll(dll_path):
    """分析单个 DLL 文件，提取依赖信息"""
    if not os.path.isfile(dll_path):
        return {"error": f"文件不存在: {dll_path}"}

    result = {
        "path": dll_path,
        "name": os.path.basename(dll_path),
        "dependencies": [],
        "error": None,
    }

    # TODO: 使用 pythonnet 或 dnlib 解析 .NET 程序集依赖
    # 当前为占位实现，后续可集成 Mono.Cecil 或直接解析 PE 头
    try:
        with open(dll_path, "rb") as f:
            header = f.read(4)
            if header[:2] != b"MZ":
                result["error"] = "不是有效的 PE/DLL 文件"
                return result
    except Exception as e:
        result["error"] = str(e)

    return result


def scan_mod_dlls(mod_path):
    """扫描 MOD 目录下所有 DLL 文件"""
    dlls = []
    if not os.path.isdir(mod_path):
        return dlls

    for root, _dirs, files in os.walk(mod_path):
        for f in files:
            if f.lower().endswith(".dll"):
                dlls.append(os.path.join(root, f))

    return dlls


def check_dll_conflicts(mod_paths):
    """检查多个 MOD 之间是否存在 DLL 版本冲突"""
    all_dlls = {}

    for mod_path in mod_paths:
        mod_name = os.path.basename(mod_path)
        dll_files = scan_mod_dlls(mod_path)
        for dll in dll_files:
            dll_name = os.path.basename(dll).lower()
            if dll_name not in all_dlls:
                all_dlls[dll_name] = []
            all_dlls[dll_name].append(mod_name)

    conflicts = []
    for dll_name, owners in all_dlls.items():
        if len(owners) > 1:
            conflicts.append({
                "dll": dll_name,
                "owners": owners,
                "message": f"DLL '{dll_name}' 被多个MOD包含: {', '.join(owners)}"
            })

    return conflicts
