import os, json5 as json
from collections import defaultdict

def get_cp_content_path(mod):
    """获取CP包的content.json路径"""
    manifest_path = mod.get("manifest_path", "")
    if not manifest_path:
        return None
    mod_dir = os.path.dirname(manifest_path)
    for name in ["content.json", "Content.json"]:
        path = os.path.join(mod_dir, name)
        if os.path.isfile(path):
            return path
    return None

def _load_json(path):
    """安全加载JSON文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _extract_from_list(data_list, base_dir, visited):
    """从Changes列表中提取所有Target详细信息，并递归处理Include"""
    targets = []
    
    for item in data_list:
        target = item.get("Target", "")
        if target:
            targets.append({
                "target": target,
                "from_file": item.get("FromFile", ""),
                "action": item.get("Action", "Edit"),
                "priority": item.get("Priority", "Default")
            })
    
    # 处理Include
    for item in data_list:
        inc_from = item.get("From", "")
        if inc_from:
            inc_path = os.path.join(base_dir, inc_from)
            if inc_path in visited:
                continue
            visited.add(inc_path)
            
            inc_data = _load_json(inc_path)
            if inc_data:
                changes = inc_data.get("Changes", [])
                if changes:
                    sub_targets = _extract_from_list(changes, os.path.dirname(inc_path), visited)
                    targets.extend(sub_targets)
                
                sub_includes = inc_data.get("Includes", [])
                if sub_includes:
                    for sub_inc in sub_includes:
                        sub_from = sub_inc.get("From", "")
                        if sub_from:
                            sub_path = os.path.join(os.path.dirname(inc_path), sub_from)
                            if sub_path in visited:
                                continue
                            visited.add(sub_path)
                            sub_data = _load_json(sub_path)
                            if sub_data and "Changes" in sub_data:
                                sub_targets = _extract_from_list(sub_data["Changes"], os.path.dirname(sub_path), visited)
                                targets.extend(sub_targets)
    
    return targets


def extract_changes(content_path):
    """从content.json提取所有Changes中的Target（含递归Include）"""
    if not content_path:
        return []
    
    data = _load_json(content_path)
    if not data:
        print(f"  [ERR] 读取content.json失败: {content_path}")
        return []
    
    targets = []
    visited = {content_path}  # 防止循环引用
    
    # 直接从Changes提取
    changes = data.get("Changes", [])
    if changes:
        targets = _extract_from_list(changes, os.path.dirname(content_path), visited)
    
    # 处理根级别的Include
    for inc in data.get("Includes", []):
        inc_from = inc.get("From", "")
        if inc_from:
            inc_path = os.path.join(os.path.dirname(content_path), inc_from)
            if inc_path in visited:
                continue
            visited.add(inc_path)
            inc_data = _load_json(inc_path)
            if inc_data and "Changes" in inc_data:
                sub_targets = _extract_from_list(inc_data["Changes"], os.path.dirname(inc_path), visited)
                targets.extend(sub_targets)
    
    # 按target去重
    seen = set()
    unique = []
    for t in targets:
        if t["target"] not in seen:
            seen.add(t["target"])
            unique.append(t)
    return unique


def analyze_cp_mods(mods):
    """分析所有CP包，提取它们修改的文件列表"""
    cp_mods = [m for m in mods if m.get("mod_type") == "ContentPatcher包"]
    
    if not cp_mods:
        print("没有找到ContentPatcher包")
        return {}
    
    results = {}
    for m in cp_mods:
        content_path = get_cp_content_path(m)
        changes = extract_changes(content_path)
        results[m["name"]] = {
            "content_path": content_path,
            "manifest_path": m.get("manifest_path", ""),
            "changes": changes,
            "change_count": len(changes)
        }
        print(f"  {m['name']}: {len(changes)} 个修改")
        for t in changes[:5]:
            print(f"    - {t['target']} ({t['action']})")
        if len(changes) > 5:
            print(f"    ... 还有 {len(changes)-5} 个")
    
    return results


def find_conflicts(analysis_results):
    """对比各个CP包的修改，找出冲突（含详细信息）"
    过滤条件：同一个Vortex压缩包内的MOD之间的冲突不计入"""
    if not analysis_results:
        return []
    
    # 获取每个MOD的Vortex父目录（用于判断是否同压缩包）
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scanner import scan_mods
    all_mods = scan_mods()
    mod_parents = {}
    for m in all_mods:
        name = m["name"]
        mp = m.get("manifest_path", "")
        if mp:
            # Vortex 父目录名字
            parent = os.path.basename(os.path.dirname(os.path.dirname(mp)))
            mod_parents[name] = parent
    
    # 按target聚合，含详细信息
    target_map = {}
    for mod_name, info in analysis_results.items():
        content_path = info.get("content_path", "")
        content_dir = os.path.dirname(content_path) if content_path else ""
        for change in info.get("changes", []):
            target_name = change["target"]
            if target_name not in target_map:
                target_map[target_name] = []
            
            from_file = change.get("from_file", "")
            from_file_abs = ""
            from_file_exists = False
            if from_file and content_dir:
                abs_path = os.path.normpath(os.path.join(content_dir, from_file))
                from_file_abs = abs_path
                from_file_exists = os.path.isfile(abs_path)
            
            target_map[target_name].append({
                "name": mod_name,
                "from_file": from_file,
                "from_file_abs": from_file_abs,
                "from_file_exists": from_file_exists,
                "action": change.get("action", "Edit"),
                "priority": change.get("priority", "Default")
            })
    
    conflicts = []
    for target, mod_list in target_map.items():
        if len(mod_list) >= 2:
            # 检查这些MOD是否都在同一个Vortex父目录下
            parents = set()
            for m in mod_list:
                p = mod_parents.get(m["name"], "")
                if p:
                    parents.add(p)
            # 如果只有一个父目录，说明是同压缩包，跳过
            if len(parents) == 1 and len(mod_list) == len([m for m in mod_list if mod_parents.get(m["name"], "") == list(parents)[0]]):
                continue
            conflicts.append({
                "target": target,
                "mods": mod_list,
                "mod_count": len(mod_list)
            })
    
    return sorted(conflicts, key=lambda x: x["mod_count"], reverse=True)
def analyze_cp_conflicts_for_mod(mod_name):
    """对单个MOD分析CP包冲突"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scanner import scan_mods
    
    mods = scan_mods()
    results = analyze_cp_mods(mods)
    conflicts = find_conflicts(results)
    
    # 找出这个MOD涉及的冲突
    mod_conflicts = []
    for c in conflicts:
        if mod_name in c["mods"]:
            mod_conflicts.append(c)
    
    return mod_conflicts


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scanner import scan_mods
    
    print("CP包冲突分析（含递归Include）")
    print("=" * 40)
    
    mods = scan_mods()
    print()
    
    results = analyze_cp_mods(mods)
    
    print("\n" + "=" * 40)
    print("冲突检测结果")
    print("=" * 40)
    
    conflicts = find_conflicts(results)
    
    if not conflicts:
        print("✅ 没有发现冲突")
    else:
        # 按冲突数量排序
        target_conflict_count = {}
        for c in conflicts:
            for m in c["mods"]:
                mn = m["name"]
                target_conflict_count[mn] = target_conflict_count.get(mn, 0) + 1
        
        print(f"\n共发现 {len(conflicts)} 个冲突目标\n")
        print("各MOD涉及冲突数量:")
        for mn, cnt in sorted(target_conflict_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {mn}: {cnt} 处冲突")
        
        print("\n冲突详情（前20条）:")
        for c in conflicts[:20]:
            print(f"\n⚠️  {c['target']}")
            for m in c['mods']:
                print(f"     - {m['name']} ({m['action']}, {m['from_file'] or '无文件'})")
        if len(conflicts) > 20:
            print(f"\n  ... 还有 {len(conflicts)-20} 条冲突")