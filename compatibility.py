import json5 as json
import os, subprocess, re, sys
from typing import Optional
from config import SMAPI_PATH, GAME_PATH
from logger import log

# Windows 下隐藏 CMD 窗口
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# ─── 版本工具 ───────────────────────────────────────────────────
def _parse_version(ver_str: Optional[str]) -> Optional[list[int]]:
    """将版本字符串转为可比较的整数列表"""
    if not ver_str:
        return None
    v = ver_str.lower().lstrip("v").split("-")[0]  # 去掉v前缀和预发布标签
    try:
        return [int(x) for x in v.split(".")]
    except ValueError:
        return None

def _compare_version_list(a: Optional[list[int]], b: Optional[list[int]]) -> Optional[bool]:
    """比较两个版本整数列表, a >= b 返回 True（不修改原列表）"""
    if not a or not b:
        return None
    max_len = max(len(a), len(b))
    aa = a + [0] * (max_len - len(a))
    bb = b + [0] * (max_len - len(b))
    for i in range(max_len):
        if aa[i] > bb[i]:
            return True
        elif aa[i] < bb[i]:
            return False
    return True  # 相等


# ─── SMAPI / 游戏版本检测 ──────────────────────────────────────
def get_local_smapi_version() -> Optional[str]:
    """通过文件属性获取本地SMAPI版本号"""
    smapi_exe = os.path.join(GAME_PATH, "StardewModdingAPI.exe") if GAME_PATH else ""

    if not os.path.isfile(smapi_exe):
        log.warning(f"未找到SMAPI: {smapi_exe}")
        return None

    try:
        result = subprocess.run(
            ["powershell", "-Command", f"(Get-Item '{smapi_exe}').VersionInfo.ProductVersion"],
            capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW
        )
        version = result.stdout.strip()
        if version:
            version = version.split("+")[0].split(",")[0]
            log.info(f"本地SMAPI版本: v{version}")
            return version
        else:
            log.warning("无法读取SMAPI版本")
            return None
    except Exception as e:
        log.error(f"获取SMAPI版本失败: {e}")
        return None


def get_local_game_version() -> Optional[str]:
    """获取本地星露谷物语版本号"""
    game_exe = os.path.join(GAME_PATH, "Stardew Valley.exe") if GAME_PATH else ""

    if not os.path.isfile(game_exe):
        log.warning(f"未找到游戏: {game_exe}")
        return None

    try:
        result = subprocess.run(
            ["powershell", "-Command", f"(Get-Item '{game_exe}').VersionInfo.ProductVersion"],
            capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW
        )
        version = result.stdout.strip()
        if version:
            version = version.split("+")[0].split(",")[0]
            log.info(f"游戏版本: v{version}")
            return version
        else:
            log.warning("无法读取游戏版本")
            return None
    except Exception as e:
        log.error(f"获取游戏版本失败: {e}")
        return None


def get_game_version() -> str:
    """自动获取游戏版本：SMAPI日志 → exe文件属性 → 配置默认值"""
    from config import SMAPI_LOG, DEFAULT_GAME_VERSION

    # 1. 从 SMAPI 日志读取
    if os.path.isfile(SMAPI_LOG):
        try:
            with open(SMAPI_LOG, "r", encoding="utf-8") as f:
                first_line = f.readline()
                m = re.search(r"Stardew Valley (\d+\.\d+\.\d+)", first_line)
                if m:
                    return m.group(1)
        except Exception:
            pass

    # 2. 从游戏 exe 文件属性自动检测
    ver = get_local_game_version()
    if ver:
        return ver

    # 3. 回退默认值
    return DEFAULT_GAME_VERSION


# ─── 依赖检查 ──────────────────────────────────────────────────
def check_dependencies(mods: list[dict]) -> list[dict]:
    """检查所有MOD的依赖是否满足"""
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
            log.error(f"读取依赖信息失败: {m['name']} - {e}")

        if not deps:
            results.append({"name": m["name"], "dependencies": [], "status": "无依赖"})
        else:
            missing = [d for d in deps if not d["exists"]]
            version_low = []
            for d in deps:
                if d["exists"] and d["required_version"]:
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


# ─── SMAPI 兼容性 ──────────────────────────────────────────────
def check_smapi_compatibility(mod_min_api: Optional[str]) -> dict:
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


# ─── 版本对比（从 version_check 合并） ──────────────────────────
def compare_versions(local_ver: Optional[str], latest_ver: Optional[str]) -> str:
    """对比两个版本号，返回中文状态描述"""
    if not local_ver or not latest_ver:
        return "无法判断"

    l_parts = _parse_version(local_ver)
    n_parts = _parse_version(latest_ver)

    if l_parts is None or n_parts is None:
        lv = local_ver.lower().lstrip("v")
        nv = latest_ver.lower().lstrip("v")
        if lv == nv:
            return "已是最新版本"
        return "有可用更新" if lv < nv else "本地版本高于N网"

    result = _compare_version_list(l_parts, n_parts)
    if result is None:
        return "已是最新版本"
    if result:
        # 用双向比较判断是否真正相等（处理 1.6 vs 1.6.0 这种长度不同的等价情况）
        if _compare_version_list(n_parts, l_parts):
            return "已是最新版本"
        return "本地版本高于N网"
    else:
        return "有可用更新"


def check_version(mods: list[dict]) -> list[dict]:
    """对每个MOD进行版本对比，返回结果列表"""
    results = []
    for m in mods:
        local_ver = m.get("version", "")
        latest_ver = m.get("latest_version")
        status = compare_versions(local_ver, latest_ver) if latest_ver else "无法获取最新版本"
        results.append({
            "name": m["name"],
            "local_version": local_ver,
            "latest_version": latest_ver,
            "status": status
        })
    return results


# ─── 命令行测试入口 ─────────────────────────────────────────────
if __name__ == "__main__":
    from scanner import scan_mods

    print("兼容性检查测试")
    print("=" * 40)

    # SMAPI 版本
    print("\n[SMAPI 版本]")
    smapi_ver = get_local_smapi_version()
    for req in ["4.1.10", "4.0.0", "5.0.0", ""]:
        result = check_smapi_compatibility(req)
        status = "✅" if result["compatible"] else "❌" if result["compatible"] is False else "❓"
        print(f"  {status} 需要 v{req or '未指定':8} → {result['reason']}")

    # 游戏版本
    print("\n[游戏版本]")
    game_ver = get_local_game_version()

    # 依赖检查
    print("\n[依赖检查]")
    mods = scan_mods()
    dep_results = check_dependencies(mods)
    for r in dep_results:
        emoji = "✅" if r["status"] in ("依赖满足", "无依赖") else "⚠️" if "缺少" in r["status"] else "❌"
        print(f"  {emoji} {r['name']}: {r['status']}")
        for d in r["dependencies"]:
            sym = "✅" if d["exists"] else "❌"
            ver_info = f" (需要 v{d['required_version']}, 本地 v{d['actual_version']})" if d["required_version"] else ""
            print(f"      {sym} {d['id']}{ver_info}")