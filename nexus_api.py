import os, json, datetime, urllib.request, urllib.error
from typing import Optional, Union
from logger import log

# 动态获取 API Key（支持运行时修改）
def _get_api_key() -> str:
    from config import get_api_key
    return get_api_key()

# 缓存配置
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "nexus_cache.json")
CACHE_EXPIRE_HOURS = 24  # 缓存过期时间（小时）


def _ensure_cache():
    """确保缓存文件夹和文件存在"""
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    if not os.path.isfile(CACHE_FILE):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load_cache():
    """加载缓存"""
    _ensure_cache()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    """保存缓存"""
    _ensure_cache()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _is_cache_valid(cached_at):
    """检查缓存是否在有效期内"""
    if not cached_at:
        return False
    try:
        cached_time = datetime.datetime.fromisoformat(cached_at)
        now = datetime.datetime.now()
        diff = now - cached_time
        return diff.total_seconds() < CACHE_EXPIRE_HOURS * 3600
    except Exception:
        return False


def check_nexus_latest_version(nexus_id: str, force_refresh: bool = False) -> Optional[str]:
    """查询N网MOD的最新版本号（带缓存）"""
    if not nexus_id:
        return None
    
    # 先检查缓存
    if not force_refresh:
        cache = _load_cache()
        if nexus_id in cache:
            entry = cache[nexus_id]
            if _is_cache_valid(entry.get("cached_at")):
                return entry.get("version")
    
    # 缓存没有或已过期，调API查询
    api_key = _get_api_key()
    if not api_key:
        log.warning("N网 API Key 未配置，跳过在线查询")
        return None

    url = f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{nexus_id}.json"

    req = urllib.request.Request(url)
    req.add_header("apikey", api_key)
    req.add_header("User-Agent", "Stardew-MOD-Checker/1.0")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            version = data.get("version", "")
            updated_time = data.get("updated_time", "")
            
            if version:
                # 存入缓存
                cache = _load_cache()
                cache[nexus_id] = {
                    "version": version,
                    "updated_time": updated_time,
                    "dependencies": data.get("dependencies", []),
                    "cached_at": datetime.datetime.now().isoformat()
                }
                _save_cache(cache)
                return version
            return None
            
    except urllib.error.HTTPError as e:
        if e.code == 401:
            log.warning("N网 API Key 无效或已过期，请在设置中更新")
            return "API_KEY_INVALID"
        elif e.code == 403:
            log.error(f"API Key无效 (mod_id={nexus_id})")
            return "API_KEY_INVALID"
        elif e.code == 404:
            log.error(f"MOD不存在 (mod_id={nexus_id})")
        else:
            log.error(f"HTTP {e.code} (mod_id={nexus_id})")
        return None
    except urllib.error.URLError as e:
        log.error(f"网络错误: {e.reason}")
        return "NETWORK_ERROR"
    except Exception as e:
        log.error(f"查询失败: {e}")
        return None


def get_mod_updated_time(nexus_id: str) -> Optional[str]:
    """获取MOD的最后更新时间"""
    if not nexus_id:
        return None
    cache = _load_cache()
    if nexus_id in cache:
        return cache[nexus_id].get("updated_time")
    return None


def check_mod_abandoned(nexus_id: str, months: int = 6) -> tuple[bool, str]:
    """
    判断MOD是否可能停止维护
    返回: (是否废弃, 最后更新时间的字符串)
    """
    updated_time_str = get_mod_updated_time(nexus_id)
    if not updated_time_str:
        # 缓存中没有，尝试查询一次
        check_nexus_latest_version(nexus_id)
        updated_time_str = get_mod_updated_time(nexus_id)
        if not updated_time_str:
            return (False, "未知")
    
    try:
        # 解析时间
        if updated_time_str.endswith("+00:00"):
            updated_time_str = updated_time_str[:-6]
        updated = datetime.datetime.fromisoformat(updated_time_str)
        now = datetime.datetime.now()
        diff = now - updated
        days = diff.days
        months_since = days / 30.44  # 平均每月天数
        
        if months_since >= months:
            return (True, f"{int(days)}天前 ({updated.strftime('%Y-%m-%d')})")
        else:
            return (False, f"{int(days)}天前 ({updated.strftime('%Y-%m-%d')})")
    except Exception:
        return (False, updated_time_str)


def clear_cache():
    """清空缓存"""
    _ensure_cache()
    _save_cache({})
    log.info("N网缓存已清空")


def get_cached_mods():
    """获取缓存中所有MOD的信息"""
    cache = _load_cache()
    return cache
def get_cached_version(nexus_id: str) -> Optional[str]:
    """只从缓存读取版本信息，不请求网络"""
    if not nexus_id:
        return None
    cache = _load_cache()
    if nexus_id in cache:
        return cache[nexus_id].get("version")
    return None


def get_cached_updated_time(nexus_id: str) -> Optional[str]:
    """只从缓存读取更新时间，不请求网络"""
    if not nexus_id:
        return None
    cache = _load_cache()
    if nexus_id in cache:
        return cache[nexus_id].get("updated_time")
    return None


def refresh_mod_cache(nexus_id):
    """强制刷新单个MOD的缓存"""
    return check_nexus_latest_version(nexus_id, force_refresh=True)


def refresh_all_cache(silent: bool = False) -> list[str]:
    """强制刷新所有缓存中MOD的N网信息，返回失败的ID列表"""
    cache = _load_cache()
    count = len(cache)
    if not silent:
        log.info(f"正在刷新 {count} 个MOD的N网信息...")
    failed = []
    for i, nexus_id in enumerate(cache, 1):
        if not silent:
            try:
                from cli_utils import progress_bar
                import sys
                sys.stderr.write(progress_bar(i - 1, count, label="刷新: "))
                sys.stderr.flush()
            except Exception:
                pass
        result = check_nexus_latest_version(nexus_id, force_refresh=True)
        if not result:
            failed.append(nexus_id)
            failed.append(nexus_id)
    if not silent:
        try:
            import sys
            sys.stderr.write("\r" + " " * 60 + "\r")
            sys.stderr.flush()
        except Exception:
            pass
        log.info(f"刷新完成！共刷新 {count} 个MOD，{len(failed)} 个失败")
    return failed


if __name__ == "__main__":
    print("N网缓存测试")
    print("=" * 40)
    
    # 测试查询
    for nid, name in [("1915", "Content Patcher"), ("10532", "Valley Girls"), ("4399", "Xtardew SVE")]:
        print(f"\n{name}:")
        ver = check_nexus_latest_version(nid)
        abandoned, time_str = check_mod_abandoned(nid)
        status = "🔴 可能停止维护" if abandoned else "✅ 正常更新"
        print(f"  v{ver}, 最后更新: {time_str}")
        print(f"  {status}")