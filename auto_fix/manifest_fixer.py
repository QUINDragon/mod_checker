import os, json, re
import json5
from logger import log
from auto_fix.backup import backup_file


def fix_manifest_issues(manifest_path):
    """检查并修复 manifest.json 的小问题"""
    if not os.path.isfile(manifest_path):
        return {"status": "error", "message": "文件不存在"}
    
    # 读取原始内容
    with open(manifest_path, "r", encoding="utf-8") as f:
        raw = f.read()
    
    fixed = raw
    changes = []
    
    # 1. 用 json5 读取（能处理尾部逗号）
    try:
        data = json5.loads(raw)
    except Exception:
        return {"status": "error", "message": "JSON格式无法解析"}
    
    # 2. 检查是否能被标准 json 解析
    has_trailing_comma = False
    try:
        json.loads(raw)
    except json.JSONDecodeError:
        has_trailing_comma = True
    
    if has_trailing_comma:
        changes.append("修复尾部逗号")
    
    # 3. 标准化 UpdateKeys
    keys = data.get("UpdateKeys", [])
    new_keys = []
    key_changed = False
    for k in keys:
        k = k.strip()
        if k.lower().startswith("nexus:"):
            parts = k.split(":")
            nexus_id = parts[-1].strip()
            normalized = f"Nexus:{nexus_id}"
            if normalized != k:
                key_changed = True
            new_keys.append(normalized)
        else:
            new_keys.append(k)
    if key_changed:
        data["UpdateKeys"] = new_keys
        changes.append("标准化UpdateKeys格式")
    
    # 4. 标准化 Version 格式（去掉多余的零）
    ver = data.get("Version", "")
    if ver:
        normalized_ver = re.sub(r"\.0+$", "", ver)  # 去尾部多余的 .0
        if normalized_ver != ver and re.match(r"^\d[\d.]*$", normalized_ver):
            data["Version"] = normalized_ver
            changes.append(f"标准化版本号: {ver} → {normalized_ver}")
    
    if not changes:
        return {"status": "no_change", "message": "无需修复"}
    
    # 备份并写回
    backup_file(manifest_path)
    
    output = json.dumps(data, ensure_ascii=False, indent=4)
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(output)
    
    log.info(f"已修复 {len(changes)} 个问题: {', '.join(changes)}")
    return {"status": "fixed", "changes": changes}


def fix_all_mods(mods):
    """检查所有MOD的manifest.json"""
    results = []
    for m in mods:
        path = m.get("manifest_path", "")
        if path:
            result = fix_manifest_issues(path)
            if result["status"] == "fixed":
                results.append({"name": m["name"], "changes": result["changes"]})
    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scanner import scan_mods
    
    print("轻度修复 - 检查所有MOD的manifest.json")
    print("=" * 50)
    
    mods = scan_mods()
    results = fix_all_mods(mods)
    
    if not results:
        print("所有MOD的manifest.json没有可修复的问题")