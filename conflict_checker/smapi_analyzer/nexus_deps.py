import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config import NEXUS_API_KEY, NEXUS_USER_AGENT
from logger import log
import urllib.request, json

def fetch_mod_detail(nexus_id):
    """获取N网MOD的详细信息"""
    if not nexus_id:
        return None
    
    url = f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{nexus_id}.json"
    
    req = urllib.request.Request(url)
    req.add_header("apikey", NEXUS_API_KEY)
    req.add_header("User-Agent", NEXUS_USER_AGENT)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.error(f"查询失败 (mod_id={nexus_id}): {e}")
        return None

def check_nexus_dependencies(mods):
    """检查N网上标注的依赖信息"""
    print("检查N网依赖信息...")
    
    for m in mods:
        nexus_id = m.get("nexus_id", "")
        if not nexus_id:
            continue
        
        data = fetch_mod_detail(nexus_id)
        if not data:
            continue
        
        # 打印所有字段，找依赖相关的
        print(f"\n  {m['name']} (Nexus {nexus_id}):")
        for key, value in data.items():
            if "dep" in key.lower() or "require" in key.lower() or "relat" in key.lower():
                print(f"    {key}: {json.dumps(value, ensure_ascii=False)[:200]}")
        
        # 如果没有上述字段，打印所有键看看
        dep_keys = [k for k in data.keys() if "dep" in k.lower() or "require" in k.lower() or "relat" in k.lower()]
        if not dep_keys:
            print(f"    (没有找到依赖相关字段)")
            print(f"    所有键: {list(data.keys())}")

if __name__ == "__main__":
    print("N网依赖信息测试")
    print("=" * 40)
    
    from scanner import scan_mods
    mods = scan_mods()
    print()
    
    check_nexus_dependencies(mods)