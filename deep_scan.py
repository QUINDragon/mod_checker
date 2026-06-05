import datetime
from scanner import scan_mods
from nexus_api import check_nexus_latest_version, get_mod_updated_time
from config import GAME_VERSION_HISTORY
from mod_status import parse_smapi_log
from compatibility import get_game_version


def deep_scan_single(mod_name):
    """对单个MOD进行深度分析"""
    # 获取MOD信息
    all_mods = scan_mods()
    mod = None
    for m in all_mods:
        if m["name"].lower() == mod_name.lower():
            mod = m
            break
    
    if not mod:
        return {"name": mod_name, "error": "未找到该MOD"}
    
    report = {
        "name": mod["name"],
        "version": mod["version"],
        "mod_type": mod["mod_type"],
        "quick_status": {},
        "smapi_status": {},
        "dependencies": {"missing": []},
        "conflicts": [],
        "map_conflicts": [],
        "recommendations": []
    }
    
    # 1. 快筛状态
    nexus_id = mod.get("nexus_id", "")
    updated_time_str = ""
    latest_version = ""
    
    if nexus_id:
        latest_version = check_nexus_latest_version(nexus_id)
        updated_time_str = get_mod_updated_time(nexus_id)
        if not updated_time_str:
            check_nexus_latest_version(nexus_id, force_refresh=True)
            updated_time_str = get_mod_updated_time(nexus_id)
    
    game_version = get_game_version()
    game_date_str = GAME_VERSION_HISTORY.get(game_version, "")
    
    status_text = "无N网ID"
    if updated_time_str and game_date_str:
        try:
            mod_update_str = updated_time_str
            if mod_update_str.endswith("+00:00"):
                mod_update_str = mod_update_str[:-6]
            mod_update = datetime.datetime.fromisoformat(mod_update_str)
            game_date = datetime.datetime.strptime(game_date_str, "%Y-%m-%d")
            
            if mod_update >= game_date:
                status_text = "适配当前版本"
            else:
                status_text = "很久未更新，需要检查"
        except Exception:
            status_text = "无法判断"
    
    report["quick_status"] = {
        "nexus_id": nexus_id,
        "latest_version": latest_version,
        "updated_time": updated_time_str,
        "status_text": status_text
    }
    
    # 2. SMAPI日志状态
    log = parse_smapi_log()
    smapi_text = "日志不存在"
    smapi_detail = ""
    
    if log:
        name_lower = mod["name"].lower()
        in_loaded = any(m2["name"].lower() == name_lower for m2 in log.get("loaded_mods", []) + log.get("loaded_packs", []))
        in_skipped = any(m2["name"].lower() == name_lower for m2 in log.get("skipped", []))
        in_failed = any(m2["name"].lower() == name_lower for m2 in log.get("failed", []))
        
        if in_loaded:
            smapi_text = "已加载"
        elif in_skipped:
            smapi_text = "被跳过"
            for s in log.get("skipped", []):
                if s["name"].lower() == name_lower and s.get("reason"):
                    smapi_detail = s["reason"]
        elif in_failed:
            smapi_text = "加载失败"
            for f in log.get("failed", []):
                if f["name"].lower() == name_lower and f.get("reason"):
                    smapi_detail = f["reason"]
        else:
            smapi_text = "日志中未出现"
    
    report["smapi_status"] = {
        "status_text": smapi_text,
        "detail": smapi_detail
    }
    
    # 3. 依赖检查
    deps = mod.get("dependencies", [])
    required = mod.get("requires", [])
    all_deps = deps + required
    
    if all_deps:
        installed_ids = set()
        for m2 in all_mods:
            uid = m2.get("unique_id", "")
            if uid:
                installed_ids.add(uid)
        
        missing = []
        for dep in all_deps:
            dep_id = dep.get("UniqueID", dep) if isinstance(dep, dict) else dep
            if dep_id not in installed_ids:
                missing.append(dep_id)
        
        report["dependencies"]["missing"] = missing
    
    # 4. CP包冲突（只对ContentPatcher包）
    from conflict_checker.cp_analyzer import analyze_cp_conflicts_for_mod
    if mod["mod_type"] == "ContentPatcher包":
        try:
            conflicts = analyze_cp_conflicts_for_mod(mod["name"])
            report["conflicts"] = conflicts
        except Exception:
            pass
    
    # 4.5 地图文件冲突
    from conflict_checker.map_analyzer import analyze_map_conflicts
    try:
        map_conflicts = analyze_map_conflicts(all_mods)
        # 筛选出涉及当前MOD的地图冲突
        mod_map_conflicts = []
        for mc in map_conflicts:
            for item in mc.get("details", []):
                if item.get("mod", "").lower() == mod["name"].lower():
                    mod_map_conflicts.append({
                        "file": mc["file"],
                        "conflicting_mods": [d["mod"] for d in mc["details"] if d["mod"] != mod["name"]]
                    })
                    break
        report["map_conflicts"] = mod_map_conflicts
    except Exception:
        pass

    # 5. 生成建议
    recs = []

    if smapi_text == "被跳过":
        recs.append(f"MOD被跳过: {smapi_detail}")
    
    # 根据快筛状态
    if status_text == "很久未更新，需要检查":
        recs.append(f"MOD最后更新于 {updated_time_str[:10] if updated_time_str else '未知'}，早于当前游戏版本 ({game_version}, {game_date_str})")
        if latest_version and latest_version != mod["version"]:
            recs.append(f"N网有新版 v{latest_version}，当前使用 v{mod['version']}，建议更新")
    
    # 根据依赖
    if report["dependencies"]["missing"]:
        dep_list = ", ".join(report["dependencies"]["missing"])
        recs.append(f"缺少依赖: {dep_list}")
    
    # 根据冲突
    if report["conflicts"]:
        recs.append(f"与其他MOD有 {len(report['conflicts'])} 处CP包冲突")

    # 根据地图冲突
    if report["map_conflicts"]:
        conflict_files = [mc["file"] for mc in report["map_conflicts"]]
        recs.append(f"与 {len(report['map_conflicts'])} 个地图文件存在冲突: {', '.join(conflict_files[:3])}" + 
                    ("..." if len(conflict_files) > 3 else ""))

    if not recs:
        recs.append("该MOD看起来一切正常")
    
    report["recommendations"] = recs
    
    return report


def deep_scan_multiple(mod_names):
    """对多个MOD进行深度分析"""
    return [deep_scan_single(name) for name in mod_names]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        name = sys.argv[1]
        report = deep_scan_single(name)
        print(report)