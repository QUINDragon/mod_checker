import os
from collections import defaultdict

# 地图文件扩展名
MAP_EXTENSIONS = {".tbin", ".xnb"}

def scan_map_files(mods):
    """扫描所有MOD，找出每个MOD中的地图文件"""
    results = {}
    
    for m in mods:
        manifest_path = m.get("manifest_path", "")
        if not manifest_path:
            continue
        
        mod_dir = os.path.dirname(manifest_path)
        map_files = []
        
        for root, dirs, files in os.walk(mod_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in MAP_EXTENSIONS:
                    rel_path = os.path.relpath(os.path.join(root, f), mod_dir)
                    map_files.append(rel_path)
        
        if map_files:
            results[m["name"]] = {
                "map_files": sorted(map_files),
                "count": len(map_files)
            }
            print(f"  {m['name']}: {len(map_files)} 个地图文件")
    
    return results


def find_map_conflicts(scan_results):
    """对比各个MOD的地图文件，找出重叠的文件名"""
    if not scan_results:
        return []
    
    # 收集所有地图文件的基本名（不包含路径）
    file_mods = defaultdict(list)
    for mod_name, info in scan_results.items():
        for f in info["map_files"]:
            basename = os.path.basename(f)
            file_mods[basename].append({
                "mod": mod_name,
                "path": f
            })
    
    # 找被多个MOD使用的文件
    conflicts = []
    for basename, items in file_mods.items():
        if len(items) >= 2:
            conflicts.append({
                "file": basename,
                "details": items,
                "mod_count": len(items)
            })
    
    return sorted(conflicts, key=lambda x: x["mod_count"], reverse=True)


def analyze_map_conflicts(mods):
    """完整分析：扫描+找冲突"""
    print("扫描地图文件...")
    scan_results = scan_map_files(mods)
    
    if not scan_results:
        print("没有找到任何地图文件")
        return
    
    print(f"\n共扫描到 {sum(v['count'] for v in scan_results.values())} 个地图文件")
    
    conflicts = find_map_conflicts(scan_results)
    
    print("\n" + "=" * 40)
    print("地图文件冲突检测结果")
    print("=" * 40)
    
    if not conflicts:
        print("✅ 没有发现地图文件冲突")
    else:
        mod_conflict_count = defaultdict(int)
        for c in conflicts:
            for item in c["details"]:
                mod_conflict_count[item["mod"]] += 1
        
        print(f"\n共发现 {len(conflicts)} 个冲突文件\n")
        print("各MOD涉及冲突数量:")
        for mn, cnt in sorted(mod_conflict_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {mn}: {cnt} 处冲突")
        
        print("\n冲突详情:")
        for c in conflicts:
            print(f"\n⚠️  {c['file']}")
            for item in c["details"]:
                print(f"     - {item['mod']} ({item['path']})")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scanner import scan_mods
    
    print("地图文件冲突分析")
    print("=" * 40)
    
    mods = scan_mods()
    print()
    
    analyze_map_conflicts(mods)