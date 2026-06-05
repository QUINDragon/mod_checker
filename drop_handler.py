"""
拖拽处理器：将 MOD 文件夹拖到此脚本上自动处理
用法:
    python drop_handler.py "C:\path\to\mod"
    或拖拽文件夹到 drop_scan.bat
"""
import sys, os, subprocess, json

ROOT = os.path.dirname(os.path.abspath(__file__))


def copy_to_clipboard(text: str) -> None:
    """复制文本到剪贴板"""
    try:
        import subprocess
        subprocess.run(["clip"], input=text.encode("utf-16-le"), check=False,
                       creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    except Exception:
        pass


def detect_mod(path: str) -> dict | None:
    """从路径检测 MOD 信息"""
    if not os.path.isdir(path):
        # 可能是直接拖了 manifest.json
        if os.path.isfile(path) and os.path.basename(path).lower() == "manifest.json":
            path = os.path.dirname(path)
        else:
            return None

    manifest = os.path.join(path, "manifest.json")
    if not os.path.isfile(manifest):
        # 可能是子文件夹
        for item in os.listdir(path):
            sub = os.path.join(path, item)
            if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, "manifest.json")):
                path = sub
                manifest = os.path.join(sub, "manifest.json")
                break
        else:
            return None

    try:
        import json5
        with open(manifest, "r", encoding="utf-8") as f:
            data = json5.loads(f.read())
        return {
            "name": data.get("Name", "未知"),
            "version": data.get("Version", "未知"),
            "unique_id": data.get("UniqueID", ""),
            "path": path,
            "manifest": manifest,
        }
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print("用法: 将 MOD 文件夹拖到此脚本上")
        print("  python drop_handler.py \"C:\\path\\to\\mod\"")
        input("按任意键退出...")
        return

    dropped = sys.argv[1]
    info = detect_mod(dropped)

    if not info:
        print(f"❌ 未在路径中找到 manifest.json: {dropped}")
        print("\n支持的拖拽方式:")
        print("  - 直接拖 MOD 文件夹")
        print("  - 拖 manifest.json 文件")
        print("  - 拖 Vortex 解压后的 MOD 父文件夹")
        input("按任意键退出...")
        return

    # 复制路径到剪贴板
    copy_to_clipboard(info["path"])
    print(f"📋 路径已复制: {info['path']}")

    # 显示 MOD 信息
    print(f"\n📦 {info['name']} v{info['version']}")
    if info["unique_id"]:
        print(f"   ID: {info['unique_id']}")

    # 自动快速分析
    print(f"\n🔍 正在快速分析...")
    scan_script = os.path.join(ROOT, "scan_cli.py")
    python = sys.executable
    try:
        result = subprocess.run(
            [python, scan_script, "-d", info["name"]],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.stderr:
            print(result.stderr[:500])
    except Exception as e:
        print(f"分析失败: {e}")

    input("\n按任意键退出...")


if __name__ == "__main__":
    main()
