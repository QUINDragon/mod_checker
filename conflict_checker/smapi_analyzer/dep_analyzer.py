def check_dependencies(mods):
    """检查所有MOD的依赖是否满足"""
    # 建立 MOD 索引
    mod_index = {}
    for m in mods:
        uid = m.get("unique_id", "")
        if uid:
            mod_index[uid] = m
    
    results = []
    
    for m in mods:
        deps = []
        
        # 检查旧格式 RequiredMods
        for req_id in m.get("requires", []):
            if req_id in mod_index:
                deps.append({"id": req_id, "exists": True, "version_ok": True})
            else:
                deps.append({"id": req_id, "exists": False, "version_ok": False})
        
        # 检查新格式 Dependencies
        for dep in m.get("dependencies", []):
            dep_id = dep.get("UniqueID", "")
            min_ver = dep.get("MinimumVersion", "")
            
            if dep_id in mod_index:
                dep_mod = mod_index[dep_id]
                actual_ver = dep_mod.get("version", "")
                version_ok = True
                # 如果有最低版本要求，对比一下
                if min_ver:
                    from compatibility import compare_versions
                    version_ok = compare_versions(actual_ver, min_ver) == "已是最新版本" or compare_versions(actual_ver, min_ver) == "本地版本高于N网"
                
                deps.append({"id": dep_id, "exists": True, "version_ok": version_ok, "required": min_ver, "actual": actual_ver})
            else:
                deps.append({"id": dep_id, "exists": False, "version_ok": False, "required": min_ver, "actual": ""})
        
        # 判断状态
        missing = [d for d in deps if not d["exists"]]
        version_bad = [d for d in deps if d["exists"] and not d["version_ok"]]
        
        if not deps:
            status = "无依赖"
        elif missing:
            status = f"缺少 {len(missing)} 个依赖"
        elif version_bad:
            status = f"{len(version_bad)} 个依赖版本过低"
        else:
            status = "依赖满足"
        
        results.append({"name": m["name"], "deps": deps, "status": status})
    
    return results


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from scanner import scan_mods
    
    print("依赖检查")
    print("=" * 40)
    
    mods = scan_mods()
    print()
    
    results = check_dependencies(mods)
    
    for r in results:
        emoji = "✅" if r["status"] in ("无依赖", "依赖满足") else "⚠️" if "缺少" in r["status"] else "❌"
        print(f"\n{emoji} {r['name']}: {r['status']}")
        for d in r["deps"]:
            sym = "✅" if d["exists"] and d["version_ok"] else "❌" if not d["exists"] else "⚠️"
            ver_info = ""
            if d.get("required"):
                ver_info = f" (需要 v{d['required']}, 本地 v{d['actual']})"
            print(f"    {sym} {d['id']}{ver_info}")