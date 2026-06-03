import os, json
from config import SMAPI_PATH, GAME_PATH

# ─── 版本工具 ───────────────────────────────────────────────────
def _parse_version(ver_str):
    """将版本字符串转为可比较的整数列表"""
    if not ver_str:
        return None
    v = ver_str.lower().lstrip("v").split("-")[0]  # 去掉v前缀和预发布标签
    try:
        return [int(x) for x in v.split(".")]
    except ValueError:
        return None

def _compare_version_list(a, b):
    """比较两个版本整数列表, a >= b 返回 True"""
    if not a or not b:
        return None
    max_len = max(len(a), len(b))
    a += [0] * (max_len - len(a))
    b += [0] * (max_len - len(b))
    for i in range(max_len):
        if a[i] > b[i]:
            return True
        elif a[i] < b[i]:
            return False
    return True  # 相等


# ─── SMAPI 版本检查 ─────────────────────────────────────────────
import subprocess, re

import subprocess, re, os

def get_local_smapi_version():
    """通过文件属性获取本地SMAPI版本号"""
    smapi_exe = os.path.join(GAME_PATH, "StardewModdingAPI.exe") if GAME_PATH else ""
    
    if not os.path.isfile(smapi_exe):
        print(f"  [WARN] 未找到SMAPI: {smapi_exe}")
        return None
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"(Get-Item '{smapi_exe}').VersionInfo.ProductVersion"],
            capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip()
        if version:
            # 取主版本号（去掉git后缀）
            version = version.split("+")[0].split(",")[0]
            print(f"  [OK] 本地SMAPI版本: v{version}")
            return version
        else:
            print(f"  [WARN] 无法读取SMAPI版本")
            return None
    except Exception as e:
        print(f"  [ERR] 获取SMAPI版本失败: {e}")
        return None
def get_local_game_version():
    """获取本地星露谷物语版本号"""
    game_exe = os.path.join(GAME_PATH, "Stardew Valley.exe") if GAME_PATH else ""
    
    if not os.path.isfile(game_exe):
        print(f"  [WARN] 未找到游戏: {game_exe}")
        return None
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"(Get-Item '{game_exe}').VersionInfo.ProductVersion"],
            capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip()
        if version:
            version = version.split("+")[0].split(",")[0]
            print(f"  [OK] 游戏版本: v{version}")
            return version
        else:
            print(f"  [WARN] 无法读取游戏版本")
            return None
    except Exception as e:
        print(f"  [ERR] 获取游戏版本失败: {e}")
        return None
def check_dependencies(mods):
    """检查所有MOD的依赖是否满足"""
    # 建立所有MOD的索引: UniqueID → MOD信息
    mod_index = {}
    for m in mods:
        uid = m.get("unique_id", "")
        if uid:
            mod_index[uid] = m
    
    results = []
    
    for m in mods:
        deps = []
        manifest_path = m.get("manifest_path", "")
        if not manifest_path or not os.path.isfile(manifest_path):
            results.append({"name": m["name"], "dependencies": [], "status": "无信息"})
            continue
        
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 旧格式: RequiredMods
            for req_id in data.get("RequiredMods", []):
                dep_info = {"id": req_id, "exists": req_id in mod_index, "required_version": "", "actual_version": ""}
                if dep_info["exists"]:
                    dep_info["actual_version"] = mod_index[req_id].get("version", "")
                deps.append(dep_info)
            
            # 新格式: Dependencies
            for dep in data.get("Dependencies", []):
                dep_id = dep.get("UniqueID", "")
                if not dep_id:
                    continue
                req_ver = dep.get("MinimumVersion", "")
                dep_info = {
                    "id": dep_id,
                    "exists": dep_id in mod_index,
                    "required_version": req_ver,
                    "actual_version": mod_index[dep_id].get("version", "") if dep_id in mod_index else ""
                }
                deps.append(dep_info)
            
        except Exception as e:
            print(f"  [ERR] 读取依赖信息失败: {m['name']} - {e}")
        
        if not deps:
            results.append({"name": m["name"], "dependencies": [], "status": "无依赖"})
        else:
            # 判断状态
            missing = [d for d in deps if not d["exists"]]
            version_low = []
            for d in deps:
                if d["exists"] and d["required_version"]:
                    # 检查版本
                    req_parts = _parse_version(d["required_version"])
                    act_parts = _parse_version(d["actual_version"])
                    if req_parts and act_parts and not _compare_version_list(act_parts, req_parts):
                        version_low.append(d)
            
            if missing:
                status = f"缺少 {len(missing)} 个依赖"
            elif version_low:
                status = f"{len(version_low)} 个依赖版本过低"
            else:
                status = "依赖满足"
            
            results.append({"name": m["name"], "dependencies": deps, "status": status})
    
    return results
def check_smapi_compatibility(mod_min_api):
    """检查MOD所需的SMAPI版本是否满足"""
    local_smapi = get_local_smapi_version()
    if not local_smapi:
        return {"compatible": None, "reason": "无法获取本地SMAPI版本"}
    
    if not mod_min_api:
        return {"compatible": True, "reason": "未指定所需版本"}
    
    local_parts = _parse_version(local_smapi)
    required_parts = _parse_version(mod_min_api)
    
    if not local_parts or not required_parts:
        return {"compatible": None, "reason": "版本号格式无法解析"}
    
    if _compare_version_list(local_parts, required_parts):
        return {
            "compatible": True,
            "local_version": local_smapi,
            "required_version": mod_min_api,
            "reason": f"SMAPI v{local_smapi} >= v{mod_min_api}"
        }
    else:
        return {
            "compatible": False,
            "local_version": local_smapi,
            "required_version": mod_min_api,
            "reason": f"SMAPI v{local_smapi} < v{mod_min_api}，需要更新SMAPI"
        }


if __name__ == "__main__":
    print("SMAPI 版本检查测试")
    print("=" * 40)
    
    smapi_ver = get_local_smapi_version()
    
    test_cases = ["4.1.10", "4.0.0", "5.0.0", ""]
    for req in test_cases:
        result = check_smapi_compatibility(req)
        status = "✅" if result["compatible"] else "❌" if result["compatible"] is False else "❓"
        print(f"\n{status} 需要v{req or '未指定':8} → {result['reason']}")
print()
game_ver = get_local_game_version()
if __name__ == "__main__":
    print("SMAPI 版本检查测试")
    print("=" * 40)
    
    smapi_ver = get_local_smapi_version()
    
    test_cases = ["4.1.10", "4.0.0", "5.0.0", ""]
    for req in test_cases:
        result = check_smapi_compatibility(req)
        status = "✅" if result["compatible"] else "❌" if result["compatible"] is False else "❓"
        print(f"\n{status} 需要v{req or '未指定':8} → {result['reason']}")
    
    print()
    game_ver = get_local_game_version()
    
    # 测试依赖检查
    print("\n依赖检查测试")
    print("=" * 40)
    from scanner import scan_mods
    mods = scan_mods()
    dep_results = check_dependencies(mods)
    for r in dep_results:
        emoji = "✅" if r["status"] == "依赖满足" or r["status"] == "无依赖" else "⚠️" if "缺少" in r["status"] else "❌"
        print(f"  {emoji} {r['name']}: {r['status']}")
        for d in r["dependencies"]:
            sym = "✅" if d["exists"] else "❌"
            ver_info = f" (需要 v{d['required_version']}, 本地 v{d['actual_version']})" if d["required_version"] else ""
            print(f"      {sym} {d['id']}{ver_info}")