from scanner import scan_mods
from nexus_api import check_nexus_latest_version
from compatibility import check_version

def main():
    print("星露谷物语 MOD 检查工具")
    print("=" * 60)
    
    print("\n[1/3] 扫描本地MOD...")
    mods = scan_mods()
    print(f"共找到 {len(mods)} 个MOD\n")
    
    print("[2/3] 查询N网最新版本...")
    for i, m in enumerate(mods):
        print(f"  ({i+1}/{len(mods)}) {m['name']} (N网ID={m['nexus_id'] or '无'})")
        if m['nexus_id']:
            latest = check_nexus_latest_version(m['nexus_id'])
            m['latest_version'] = latest
            if latest:
                print(f"    → 本地 v{m['version']}  vs  N网 v{latest}")
            else:
                print(f"    → 查询失败")
        else:
            m['latest_version'] = None
            print(f"    → 无N网ID，跳过")
    
    print("\n[3/3] 版本检查结果")
    print("=" * 60)
    
    results = check_version(mods)
    
    for r in results:
        print(f"\n📦 {r['name']}")
        print(f"   本地版本: v{r['local_version']}")
        if r['latest_version']:
            print(f"   N网最新: v{r['latest_version']}")
        print(f"   状态: {'✅' if r['status']=='已是最新版本' else '⚠️' if r['status']=='有可用更新' else 'ℹ️'} {r['status']}")

if __name__ == "__main__":
    main()