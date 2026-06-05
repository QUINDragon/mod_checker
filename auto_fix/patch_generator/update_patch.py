import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nexus_api import check_nexus_latest_version
from data.patch_record import add_patch


def create_update_patch(mod):
    nexus_id = mod.get("nexus_id", "")
    if not nexus_id:
        return {"status": "error", "message": "该MOD没有N网ID，无法找到更新"}
    
    latest_ver = check_nexus_latest_version(nexus_id)
    current_ver = mod.get("version", "")
    
    if not latest_ver or latest_ver == current_ver:
        return {"status": "no_update", "message": f"{mod['name']} 已是最新版本 (v{current_ver})"}
    
    nexus_url = f"https://www.nexusmods.com/stardewvalley/mods/{nexus_id}"
    
    patch_id = add_patch(
        name=f"update_{mod['name']}_{latest_ver}",
        description=f"引导更新 {mod['name']} 从 v{current_ver} 到 v{latest_ver}",
        patch_type="update",
        mod_names=[mod["name"]],
        target_nexus_ids=nexus_id
    )
    
    return {
        "status": "success",
        "patch_id": patch_id,
        "message": f"N网链接: {nexus_url} (v{current_ver} -> v{latest_ver})"
    }
