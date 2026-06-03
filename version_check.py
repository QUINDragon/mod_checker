def compare_versions(local_ver, latest_ver):
    """对比两个版本号，返回状态"""
    if not local_ver or not latest_ver:
        return "无法判断"
    
    # 去掉v前缀
    lv = local_ver.lower().lstrip("v")
    nv = latest_ver.lower().lstrip("v")
    
    if lv == nv:
        return "已是最新版本"
    
    # 简单比较（按.分割逐段比较）
    try:
        l_parts = [int(x) for x in lv.split(".")]
        n_parts = [int(x) for x in nv.split(".")]
        
        # 补齐长度
        max_len = max(len(l_parts), len(n_parts))
        l_parts += [0] * (max_len - len(l_parts))
        n_parts += [0] * (max_len - len(n_parts))
        
        for i in range(max_len):
            if l_parts[i] < n_parts[i]:
                return "有可用更新"
            elif l_parts[i] > n_parts[i]:
                return "本地版本高于N网"
        
        return "已是最新版本"
    except ValueError:
        # 如果转数字失败，直接字符串比较
        if lv < nv:
            return "有可用更新"
        elif lv > nv:
            return "本地版本高于N网"
        return "已是最新版本"


def check_version(mods):
    """对每个MOD进行版本对比，返回结果列表"""
    results = []
    
    for m in mods:
        local_ver = m.get("version", "")
        latest_ver = m.get("latest_version")
        
        if latest_ver is None:
            status = "无法获取最新版本"
        else:
            status = compare_versions(local_ver, latest_ver)
        
        results.append({
            "name": m["name"],
            "local_version": local_ver,
            "latest_version": latest_ver,
            "status": status
        })
    
    return results


if __name__ == "__main__":
    # 简单测试
    print("版本对比测试:")
    test_cases = [
        ("2.9.1", "2.9.1"),
        ("2.8.1", "2.9.1"),
        ("3.0.0", "2.9.1"),
        ("v2.9.1", "2.9.1"),
        ("1.0.0-alpha", "1.0.0"),
    ]
    
    for local, latest in test_cases:
        status = compare_versions(local, latest)
        print(f"  {local:15} vs {latest:15} → {status}")