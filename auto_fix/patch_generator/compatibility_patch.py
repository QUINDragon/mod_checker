import os, json, shutil, datetime, zipfile

from data.patch_record import add_patch, patch_exists


PATCHES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "patches")


def _get_patch_name(conflict, selected_mod_name):
    """生成补丁名称"""
    conflict_target = conflict["target"].replace("/", "_").replace(" ", "_")
    short_name = selected_mod_name[:10]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{short_name}_{conflict_target}"


def _ensure_patches_dir():
    """确保 patches 目录存在"""
    os.makedirs(PATCHES_DIR, exist_ok=True)


def _build_package(patch_name, conflict, selected_mod_name, selected_info):
    """构建补丁包目录结构，返回路径"""
    patch_dir = os.path.join(PATCHES_DIR, patch_name)
    assets_dir = os.path.join(patch_dir, "assets")
    
    # 清空并重建
    if os.path.isdir(patch_dir):
        shutil.rmtree(patch_dir)
    
    # 复制资源文件
    from_file = selected_info.get("from_file", "")
    from_file_abs = selected_info.get("from_file_abs", "")
    if from_file and from_file_abs and os.path.isfile(from_file_abs):
        # 保持相对路径结构
        rel_path = from_file.replace("\\", "/")
        dest = os.path.join(assets_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(from_file_abs, dest)
    
    # 生成 manifest.json
    other_mods = [m.get("name", "?") for m in conflict.get("mods", []) if isinstance(m, dict) and m.get("name") != selected_mod_name]
    target_name = (conflict.get("target", "unknown").split("/")[-1]) if conflict.get("target") else "unknown"
    manifest = {
        "Name": f"[ModChecker] {selected_mod_name} - {target_name}",
        "Author": "ModChecker AutoFix",
        "Version": "1.0.0",
        "Description": f"自动生成的兼容补丁：解决 {selected_mod_name} 与 {', '.join(other_mods)} 在 {conflict['target']} 上的冲突",
        "UniqueID": f"ModChecker.AutoFix.{patch_name}",
        "ContentPackFor": {
            "UniqueID": "Pathoschild.ContentPatcher",
            "MinimumVersion": "2.0.0"
        }
    }
    with open(os.path.join(patch_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)
    
    # 生成 content.json
    target = conflict["target"]
    from_file_rel = from_file.replace("\\", "/") if from_file else ""
    changes = []
    if from_file_rel and from_file_abs and os.path.isfile(from_file_abs):
        changes.append({
            "Action": "Load",
            "Target": target,
            "FromFile": f"assets/{from_file_rel}",
            "Priority": "Exclusive"
        })
    
    content = {
        "Format": "1.30.0",
        "Changes": changes
    }
    with open(os.path.join(patch_dir, "content.json"), "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=4)
    
    # 生成 README.txt
    readme = (
        f"ModChecker 兼容补丁\n"
        f"{'=' * 40}\n\n"
        f"补丁名称: {patch_name}\n"
        f"冲突目标: {conflict['target']}\n"
        f"涉及的MOD: {', '.join([m['name'] for m in conflict['mods']])}\n"
        f"保留MOD: {selected_mod_name}\n"
        f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"⚠️ 版权声明\n"
        f"本补丁包含的MOD资源文件版权归原作者所有，仅供本地个人使用，请勿传播。\n"
    )
    with open(os.path.join(patch_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme)
    
    return patch_dir


def _zip_package(patch_dir, patch_name):
    """打包为 zip"""
    zip_path = os.path.join(PATCHES_DIR, f"{patch_name}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(patch_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, patch_dir)
                zf.write(file_path, arcname)
    return zip_path


def generate_compatibility_patch(conflict, selected_mod_name):
    """生成兼容补丁包"""
    # 防御：检查 conflict 结构完整性
    if not isinstance(conflict, dict) or "mods" not in conflict or "target" not in conflict:
        return {"status": "error", "message": "冲突数据不完整，缺少 mods 或 target"}
    if not isinstance(conflict["mods"], list) or not conflict["mods"]:
        return {"status": "error", "message": "冲突数据中 mods 为空"}
    if not conflict.get("target"):
        return {"status": "error", "message": "冲突目标为空"}

    # 检查资源文件是否存在
    selected_info = None
    for m in conflict["mods"]:
        if not isinstance(m, dict):
            continue
        if m.get("name") == selected_mod_name:
            selected_info = m
            break

    if not selected_info:
        return {"status": "error", "message": f"未找到MOD: {selected_mod_name}"}

    if not selected_info.get("from_file_abs") or not os.path.isfile(selected_info.get("from_file_abs", "")):
        return {"status": "error", "message": f"所选MOD ({selected_mod_name}) 的资源文件不存在，无法生成兼容补丁"}

    # 检查是否已存在相同补丁
    mod_names = sorted([m.get("name", "?") for m in conflict["mods"] if isinstance(m, dict)])
    if patch_exists(mod_names, conflict["target"], "compatibility"):
        return {"status": "exists", "message": "该补丁已存在"}
    
    _ensure_patches_dir()
    
    # 构建补丁包
    patch_name = _get_patch_name(conflict, selected_mod_name)
    patch_dir = _build_package(patch_name, conflict, selected_mod_name, selected_info)
    
    # 打包
    zip_path = _zip_package(patch_dir, patch_name)
    
    # 清理临时目录
    shutil.rmtree(patch_dir)
    
    # 记录到数据库
    description = f"解决 {selected_mod_name} 与 {', '.join([m['name'] for m in conflict['mods'] if m['name'] != selected_mod_name])} 在 {conflict['target']} 上的冲突"
    patch_id = add_patch(
        name=patch_name,
        description=description,
        patch_type="compatibility",
        mod_names=[m["name"] for m in conflict["mods"]],
        target_nexus_ids="",
        conflict_target=conflict["target"],
        zip_path=zip_path
    )
    
    return {
        "status": "success",
        "patch_id": patch_id,
        "zip_path": zip_path,
        "message": f"兼容补丁已生成: {zip_path}\n  请将补丁拖入 Vortex 安装"
    }


def batch_generate(conflicts, selected_map):
    """
    批量生成补丁
    conflicts: 冲突列表
    selected_map: {目标: 选中的MOD名}
    """
    results = []
    for c in conflicts:
        target = c["target"]
        if target in selected_map:
            result = generate_compatibility_patch(c, selected_map[target])
            results.append(result)
    return results