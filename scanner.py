import os, json

from config import VORTEX_MODS

def scan_mods():
    """扫描Vortex MOD文件夹，读取所有manifest.json"""
    mods = []
    if not os.path.isdir(VORTEX_MODS):
        print(f"MOD路径不存在: {VORTEX_MODS}")
        return mods
    
    print(f"正在扫描: {VORTEX_MODS}")
    
    for folder in sorted(os.listdir(VORTEX_MODS)):
        folder_path = os.path.join(VORTEX_MODS, folder)
        if not os.path.isdir(folder_path):
            continue
        
        manifest = os.path.join(folder_path, "manifest.json")
        if os.path.isfile(manifest):
            m = _read_manifest(manifest)
            if m:
                mods.append(m)
            continue
        
        for sub in sorted(os.listdir(folder_path)):
            sub_path = os.path.join(folder_path, sub)
            if os.path.isdir(sub_path):
                manifest2 = os.path.join(sub_path, "manifest.json")
                if os.path.isfile(manifest2):
                    m = _read_manifest(manifest2)
                    if m:
                        mods.append(m)
    
    return mods

def _read_manifest(path):
    """读取单个manifest.json，提取关键信息"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        nexus_id = ""
        for key in data.get("UpdateKeys", []):
            if key.lower().startswith("nexus:"):
                nexus_id = key.split(":")[-1]
                break
        
        mod = {
            "name": data.get("Name", "未知"),
            "author": data.get("Author", "未知"),
            "version": data.get("Version", "未知"),
            "min_api": data.get("MinimumApiVersion", ""),
            "unique_id": data.get("UniqueID", ""),
            "nexus_id": nexus_id,
            "manifest_path": path
        }
        
        print(f"  [OK] {mod['name']} v{mod['version']}  N网ID={nexus_id or '-'}")
        return mod
        
    except json.JSONDecodeError:
        print(f"  [ERR] JSON格式错误: {path}")
        return None
    except Exception as e:
        print(f"  [ERR] 读取失败: {path} - {e}")
        return None