import urllib.request, urllib.error, json

from config import NEXUS_API_KEY, NEXUS_USER_AGENT

def check_nexus_latest_version(nexus_id):
    """查询N网MOD的最新版本号"""
    if not nexus_id:
        return None
    
    url = f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{nexus_id}.json"
    
    req = urllib.request.Request(url)
    req.add_header("apikey", NEXUS_API_KEY)
    req.add_header("User-Agent", "Stardew-MOD-Checker/1.0")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            version = data.get("version", "")
            return version if version else None
            
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  [ERR] API Key无效 (mod_id={nexus_id})")
            return "API_KEY_INVALID"
        elif e.code == 404:
            print(f"  [ERR] MOD不存在 (mod_id={nexus_id})")
        else:
            print(f"  [ERR] HTTP {e.code} (mod_id={nexus_id})")
        return None
    except urllib.error.URLError as e:
        print(f"  [ERR] 网络错误: {e.reason}")
        return "NETWORK_ERROR"
    except Exception as e:
        print(f"  [ERR] 查询失败: {e}")
        return None