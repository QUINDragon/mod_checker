import os, shutil, datetime, glob

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_fix", "backup")


def backup_file(filepath):
    """备份单个文件，返回备份路径"""
    if not os.path.isfile(filepath):
        print(f"  [ERR] 文件不存在: {filepath}")
        return None
    
    # 生成备份文件名：时间_路径（去掉非法字符）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rel_path = filepath.replace(":", "").replace("\\", "_").replace("/", "_")
    backup_path = os.path.join(BACKUP_DIR, f"{timestamp}_{rel_path}")
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    
    print(f"  [OK] 已备份: {backup_path}")
    return backup_path


def list_backups():
    """列出所有备份"""
    if not os.path.isdir(BACKUP_DIR):
        print("没有备份")
        return []
    
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "*")))
    for b in backups:
        name = os.path.basename(b)
        size = os.path.getsize(b)
        print(f"  {name} ({size} 字节)")
    
    return backups


def restore_backup(backup_path):
    """还原备份（需要用户指定目标路径）"""
    if not os.path.isfile(backup_path):
        print(f"  [ERR] 备份文件不存在: {backup_path}")
        return False
    
    print(f"  备份文件: {backup_path}")
    print(f"  大小: {os.path.getsize(backup_path)} 字节")
    print(f"  创建时间: {datetime.datetime.fromtimestamp(os.path.getmtime(backup_path))}")
    
    confirm = input("  要还原到这个文件原来的位置吗？(y/n): ").strip().lower()
    if confirm != "y":
        print("  已取消")
        return False
    
    # 从备份文件名推断原路径
    # 格式：时间_路径
    name = os.path.basename(backup_path)
    parts = name.split("_", 1)
    if len(parts) < 2:
        print("  [ERR] 无法识别备份文件")
        return False
    
    original_path = parts[1].replace("_", "\\")
    # 还原
    os.makedirs(os.path.dirname(original_path), exist_ok=True)
    shutil.copy2(backup_path, original_path)
    print(f"  [OK] 已还原: {original_path}")
    return True


if __name__ == "__main__":
    print("备份管理")
    print("=" * 40)
    list_backups()