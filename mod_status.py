import os, re
from scanner import scan_mods
from config import GAME_PATH, SMAPI_LOG



def parse_smapi_log():
    if not os.path.isfile(SMAPI_LOG):
        return None
    try:
        content = open(SMAPI_LOG, "r", encoding="utf-8").read()
    except Exception:
        return None
    
    result = {"loaded_mods": [], "loaded_packs": [], "skipped": [], "failed": []}
    
    # 匹配所有 "   Name Version by Author"
    for m in re.finditer(r"   (.+?)\s+(\d[\d.]+\d)\s+by\s+", content):
        name = m.group(1).strip()
        version = m.group(2).strip()
        # 判断前面的行是 mods 还是 content packs
        before = content[max(0, m.start()-200):m.start()]
        if "content pack" in before.lower():
            result["loaded_packs"].append({"name": name, "version": version})
        else:
            result["loaded_mods"].append({"name": name, "version": version})
    
        # Failed
    for m in re.finditer(r"-\s+(.+?)\s+(\d[\d.]+\d)\s+because\s+it requires mods which aren't installed\s+\(([^)]+)\)", content):
        result["failed"].append({"name": m.group(1).strip(), "version": m.group(2).strip(), "reason": f"缺少 {m.group(3)}"})
    
    # Skipped
    ms = re.search(r"Skipped mods\n(.+?)(?:\n\n|\n\[|\n$)", content, re.DOTALL)
    if ms:
        for line in ms.group(1).split("\n"):
            line = line.strip().lstrip("- ")
            if not line or "---" in line:
                continue
            rm = re.match(r"(.+?)\s+(\d[\d.]+\d)\s+because\s+(.+)", line)
            if rm:
                result["skipped"].append({"name": rm.group(1).strip(), "version": rm.group(2).strip(), "reason": rm.group(3).rstrip(".")})
    
    return result

def check_mod_status():
    """对比scanner和SMAPI日志，判断每个MOD的生效状态"""
    mods = scan_mods()
    log = parse_smapi_log()
    
    if not log:
        print("未找到SMAPI日志，请先运行游戏")
        return
    
    # 建立日志中的MOD名称索引
    log_names = set()
    for m in log["loaded_mods"]:
        log_names.add(m["name"].lower())
    for m in log["loaded_packs"]:
        log_names.add(m["name"].lower())
    for m in log["skipped"]:
        log_names.add(m["name"].lower())
    for m in log["failed"]:
        log_names.add(m["name"].lower())
    
    print("\nMOD生效状态检查")
    print("=" * 50)
    
    for m in mods:
        name = m["name"]
        name_lower = name.lower()
        
        # 检查在哪个列表里
        in_loaded = any(m2["name"].lower() == name_lower for m2 in log["loaded_mods"] + log["loaded_packs"])
        in_skipped = any(m2["name"].lower() == name_lower for m2 in log["skipped"])
        in_failed = any(m2["name"].lower() == name_lower for m2 in log["failed"])
        
        if in_loaded:
            status = "✅ 已加载"
        elif in_skipped:
            reason = next((m2["reason"] for m2 in log["skipped"] if m2["name"].lower() == name_lower), "")
            status = f"⏭️ 被跳过 ({reason})"
        elif in_failed:
            reason = next((m2["reason"] for m2 in log["failed"] if m2["name"].lower() == name_lower), "")
            status = f"❌ 加载失败 ({reason})"
        else:
            status = "❓ 日志中未出现"
        
        print(f"  {status}")
        print(f"     {name} v{m['version']}  [{m['mod_type']}]")


def _find_mod_before(content, pos):
    """在pos位置之前找MOD名称"""
    lines = content[:pos].split("\n")
    for line in reversed(lines):
        if "content pack:" in line.lower() or "mod:" in line.lower():
            parts = line.split(":", 2)
            if len(parts) >= 3:
                return parts[-1].strip()[:50]
    return ""


def parse_smapi_issues():
    """解析SMAPI日志，提取问题列表（供修复模式使用）"""
    if not os.path.isfile(SMAPI_LOG):
        print(f"  [WARN] 找不到SMAPI日志: {SMAPI_LOG}")
        return []

    try:
        with open(SMAPI_LOG, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERR] 读取日志失败: {e}")
        return []

    issues = []

    # 提取 "Failed: it requires mods which aren't installed (xxx)"
    for match in re.finditer(r"Failed:\s*it requires mods which aren't installed\s*\(([^)]+)\)", content):
        mod_line = _find_mod_before(content, match.start())
        issues.append({
            "type": "缺少依赖",
            "mod": mod_line,
            "detail": f"缺少 {match.group(1)}",
            "raw": match.group(0)
        })

    # 提取 "Failed to load xxx"
    for match in re.finditer(r"Failed to load\s+(.+?)(?:\.|:)", content):
        issues.append({
            "type": "加载失败",
            "mod": match.group(1).strip(),
            "detail": "MOD加载失败",
            "raw": match.group(0)
        })

    # 提取冲突相关
    for match in re.finditer(r"(conflict|conflicts|already loaded|duplicate)", content, re.IGNORECASE):
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.start())
        line = content[line_start:line_end].strip()
        issues.append({
            "type": "冲突警告",
            "mod": "",
            "detail": line[:100],
            "raw": line
        })

    return issues


if __name__ == "__main__":
    check_mod_status()