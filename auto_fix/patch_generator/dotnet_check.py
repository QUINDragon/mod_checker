# auto_fix/patch_generator/dotnet_check.py

import subprocess

DOTNET_URL = "https://dotnet.microsoft.com/zh-cn/download"


def check_dotnet_sdk():
    """检查 .NET SDK 是否安装，返回版本号或 None"""
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def ensure_dotnet():
    """检查 .NET SDK，如果不存在则提示"""
    ver = check_dotnet_sdk()
    if ver:
        print(f"✅ .NET SDK 已安装 (v{ver})")
        return True
    
    print(f"❌ 未检测到 .NET SDK")
    print(f"   生成 Harmony 补丁需要 .NET SDK")
    print(f"   请前往 {DOTNET_URL} 下载安装")
    return False


if __name__ == "__main__":
    ensure_dotnet()