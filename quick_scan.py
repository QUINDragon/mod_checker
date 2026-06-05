import datetime
from scanner import scan_mods
from nexus_api import check_nexus_latest_version, check_mod_abandoned, get_mod_updated_time,get_cached_version, get_cached_updated_time
from config import GAME_VERSION_HISTORY
from logger import log
from compatibility import get_game_version


def get_game_version_date(version):
    """获取游戏版本的发布日期"""
    return GAME_VERSION_HISTORY.get(version)


def get_previous_version(version):
    """获取当前版本的上一个版本号"""
    versions = list(GAME_VERSION_HISTORY.keys())
    if version in versions:
        idx = versions.index(version)
        if idx + 1 < len(versions):
            return versions[idx + 1]
    return None


def quick_scan():
    """第一层快筛：快速定位可能有问题需要深度分析的MOD"""
    print("快筛")
    print("=" * 50)
    
    # 获取当前游戏版本
    game_version = get_game_version()
    game_date_str = get_game_version_date(game_version)
    
    if game_date_str:
        game_date = datetime.datetime.strptime(game_date_str, "%Y-%m-%d")
    else:
        log.warning(f"未知游戏版本 {game_version} 的发布日期")
        return []
    
    prev_version = get_previous_version(game_version)
    prev_date = None
    if prev_version:
        prev_date_str = get_game_version_date(prev_version)
        if prev_date_str:
            prev_date = datetime.datetime.strptime(prev_date_str, "%Y-%m-%d")
    
    print(f"当前游戏版本: v{game_version} ({game_date_str})")
    if prev_version:
        print(f"上一个游戏版本: v{prev_version} ({get_game_version_date(prev_version)})")
    print()
    
    # 扫描MOD
    mods = scan_mods()
    
    results = []
    for m in mods:
        nexus_id = m.get("nexus_id", "")
        name = m["name"]
        local_ver = m["version"]
        
        if not nexus_id:
            results.append({
                "name": name,
                "version": local_ver,
                "status": "no_nexus",
                "status_text": "❓ 无N网ID",
                "mod_type": m["mod_type"]
            })
            continue
        
        # 只从缓存读取，不请求网络
        latest_ver = get_cached_version(nexus_id)
        updated_time_str = get_cached_updated_time(nexus_id)
        
        # 判断状态
        status = ""
        status_text = ""
        
        if updated_time_str:
            try:
                # 解析MOD更新时间
                mod_update_str = updated_time_str
                if mod_update_str.endswith("+00:00"):
                    mod_update_str = mod_update_str[:-6]
                mod_update = datetime.datetime.fromisoformat(mod_update_str)
                
                # 与游戏版本发布时间比较
                if mod_update >= game_date:
                    status = "ok"
                    status_text = "✅ 适配当前版本"
                elif prev_date and mod_update >= prev_date:
                    status = "warning"
                    status_text = "⚠️ 在上个版本后更新，可能未完全适配"
                else:
                    status = "risk"
                    status_text = "🔴 很久未更新，需要检查"
            except Exception:
                status = "unknown"
                status_text = "❓ 无法解析更新时间"
        else:
            status = "unknown"
            status_text = "❓ 无更新时间信息"
        
        results.append({
            "name": name,
            "version": local_ver,
            "latest_version": latest_ver,
            "updated_time": updated_time_str,
            "status": status,
            "status_text": status_text,
            "mod_type": m["mod_type"]
        })
    
    # 输出结果
    print("快筛结果:")
    print("-" * 50)
    
    ok_count = 0
    warn_count = 0
    risk_count = 0
    unknown_count = 0
    
    for r in results:
        status_info = f"  {r['status_text']}"
        if r.get("latest_version") and r["latest_version"] != r["version"]:
            status_info += f" (N网有新版 v{r['latest_version']})"
        if r.get("updated_time"):
            status_info += f" - 最后更新: {r['updated_time'][:10]}"
        
        print(f"  {r['name']} v{r['version']}")
        print(f"    {status_info}")
        
        if r["status"] == "ok":
            ok_count += 1
        elif r["status"] == "warning":
            warn_count += 1
        elif r["status"] == "risk":
            risk_count += 1
        else:
            unknown_count += 1
    
    print()
    print("=" * 50)
    print(f"统计: ✅ {ok_count} | ⚠️ {warn_count} | 🔴 {risk_count} | ❓ {unknown_count}")
    print()
    
    # 输出建议
    if risk_count > 0 or warn_count > 0:
        print("建议:")
        print("  以下MOD可能需要进一步检查:")
        for r in results:
            if r["status"] in ("risk", "warning"):
                print(f"    - {r['name']} v{r['version']} ({r['status_text']})")
        print()
        print("  运行 fix_mode.py 启动游戏获取最新SMAPI日志")
        print("  运行 mod_status.py 查看MOD实际加载状态")

    return results


if __name__ == "__main__":
    quick_scan()
