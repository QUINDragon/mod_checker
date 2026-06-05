import os,re
import json5 as json
from typing import Optional
from config import VORTEX_MODS
from logger import log

_SCAN_CACHE = None


def clear_scan_cache():
    """清除扫描缓存，下次调用 scan_mods() 将重新扫描"""
    global _SCAN_CACHE
    _SCAN_CACHE = None


def scan_mods(force_refresh: bool = False) -> list[dict]:
    global _SCAN_CACHE
    if not force_refresh and _SCAN_CACHE is not None:
        return _SCAN_CACHE
    """扫描Vortex MOD文件夹，读取所有manifest.json"""
    mods = []
    if not os.path.isdir(VORTEX_MODS):
        log.error(f"MOD路径不存在: {VORTEX_MODS}")
        return mods
    
    log.info(f"正在扫描: {VORTEX_MODS}")
    
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
    # 从文件夹名继承N网ID（Vortex格式：Name-ID-Version）
    for m in mods:
        if not m.get("nexus_id"):
            folder = os.path.dirname(m.get("manifest_path", ""))
            # 检查当前文件夹名
            m2 = re.search(r"-(\d+)-", os.path.basename(folder))
            if not m2:
                # 检查父文件夹名
                m2 = re.search(r"-(\d+)-", os.path.basename(os.path.dirname(folder)))
            if m2:
                m["nexus_id"] = m2.group(1)
    _SCAN_CACHE = mods
    return mods

def _read_manifest(path: str) -> Optional[dict]:
    """读取单个manifest.json，提取关键信息"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        nexus_id = ""
        for key in data.get("UpdateKeys", []):
            if key.lower().startswith("nexus:"):
                nexus_id = key.split(":")[-1]
                break
        
        # 判断MOD类型
        if data.get("ContentPackFor", {}).get("UniqueID") == "Pathoschild.ContentPatcher":
            mod_type = "ContentPatcher包"
        elif data.get("EntryDll"):
            mod_type = "SMAPI插件"
        else:
            mod_type = "其他"
        
        mod = {
            "name": data.get("Name", "未知").strip(),
            "author": data.get("Author", "未知"),
            "version": data.get("Version", "未知"),
            "min_api": data.get("MinimumApiVersion", ""),
            "unique_id": data.get("UniqueID", ""),
            "nexus_id": nexus_id,
            "mod_type": mod_type,
            "requires": data.get("RequiredMods", []),
            "dependencies": data.get("Dependencies", []),
            "manifest_path": path
        }
        
        log.info(f"  {mod['name']} v{mod['version']}  [{mod_type}]")
        return mod

    except (ValueError, IOError) as e:
        log.error(f"读取失败: {path} - {e}")
        return None