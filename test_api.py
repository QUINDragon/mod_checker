import os, urllib.request, json
from config import NEXUS_API_KEY

API_KEY = NEXUS_API_KEY or os.environ.get("NEXUS_API_KEY", "")

def test_api(endpoint_name, url):
    print(f"\n=== 测试: {endpoint_name} ===")
    print(f"URL: {url}")
    
    req = urllib.request.Request(url)
    req.add_header("apikey", API_KEY)
    req.add_header("User-Agent", "Stardew-MOD-Checker/1.0")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"状态码: {resp.status}")
            
            if isinstance(data, list):
                print(f"返回类型: 列表, 长度={len(data)}")
                if len(data) > 0:
                    print(f"第一个元素: {json.dumps(data[0], indent=2, ensure_ascii=False)[:300]}")
            elif isinstance(data, dict):
                print(f"返回类型: 字典, 键={list(data.keys())[:10]}")
                print(f"内容: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
            else:
                print(f"原始数据: {str(data)[:200]}")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP错误: {e.code} {e.reason}")
        print(f"响应: {e.read().decode()[:300]}")
    except Exception as e:
        print(f"错误: {e}")

# 测试不同的接口
MOD_ID = "1915"  # Content Patcher

test_api("版本查询", f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{MOD_ID}/versions.json")

test_api("文件列表(全部)", f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{MOD_ID}/files.json")

test_api("文件列表(主文件)", f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{MOD_ID}/files.json?category=main")

test_api("MOD详情", f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{MOD_ID}.json")

test_api("MOD最新版本", f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{MOD_ID}/latest.json")