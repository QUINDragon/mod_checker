import os
import re

# ─── 路径配置 ───────────────────────────────────────────────────
# Vortex MOD 存放路径
VORTEX_MODS = os.path.join(os.environ.get("APPDATA", ""), "Vortex", "stardewvalley", "mods")


def _detect_game_path():
    """智能检测星露谷物语游戏路径"""
    game_dir_name = os.path.join("steamapps", "common", "Stardew Valley")
    steam_paths = []

    # 1. 尝试从 Windows 注册表读取 Steam 安装路径
    try:
        import winreg
        for hive, key_path in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Valve\Steam"),
        ]:
            try:
                key = winreg.OpenKey(hive, key_path)
                steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                if steam_path and os.path.isdir(steam_path):
                    steam_paths.append(steam_path)
            except (OSError, FileNotFoundError):
                pass
    except ImportError:
        pass

    # 2. 解析 libraryfolders.vdf 获取所有 Steam 库目录
    for steam_root in list(steam_paths):
        vdf_path = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf_path):
            try:
                with open(vdf_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 匹配 "path" 字段中的库路径
                for m in re.finditer(r'"path"\s+"([^"]+)"', content):
                    lib_path = m.group(1).replace("\\\\", "\\")
                    if lib_path not in steam_paths:
                        steam_paths.append(lib_path)
            except Exception:
                pass

    # 3. 遍历所有 Steam 库路径查找游戏
    for lib_path in steam_paths:
        candidate = os.path.join(lib_path, game_dir_name)
        if os.path.isdir(candidate):
            return candidate

    # 4. 回退：尝试常见路径
    fallback_paths = [
        r"C:\Program Files (x86)\Steam\steamapps\common\Stardew Valley",
        r"C:\Program Files\Steam\steamapps\common\Stardew Valley",
    ]
    for p in fallback_paths:
        if os.path.isdir(p):
            return p

    # 5. 遍历所有盘符查找
    try:
        import string
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1
    except Exception:
        drives = [f"{d}:\\" for d in "CDEFGH"]

    for drive in drives:
        candidate = os.path.join(drive, "Steam", game_dir_name)
        if os.path.isdir(candidate):
            return candidate

    return ""


# 星露谷物语游戏路径
GAME_PATH = _detect_game_path()

GAME_VERSION_HISTORY = {
    "1.6.15": "2024-12-20",
    "1.6.14": "2024-11-12",
    "1.6.13": "2024-11-08",
    "1.6.12": "2024-11-07",
    "1.6.11": "2024-11-06",
    "1.6.10": "2024-11-04",
    "1.6.9":  "2024-11-04",
    "1.6.8":  "2024-04-28",
    "1.6.7":  "2024-04-27",
    "1.6.6":  "2024-04-26",
    "1.6.5":  "2024-04-20",
    "1.6.4":  "2024-04-18",
    "1.6.3":  "2024-03-27",
    "1.6.2":  "2024-03-21",
    "1.6.1":  "2024-03-19",
    "1.6.0":  "2024-03-19",
}

# 最新已知游戏版本（获取不到SMAPI日志时的回退值）
DEFAULT_GAME_VERSION = "1.6.15"

# SMAPI 路径
SMAPI_PATH = os.path.join(GAME_PATH, "Mods", "SMAPI") if GAME_PATH else ""

# SMAPI 日志路径
SMAPI_LOG = os.path.join(os.environ.get("APPDATA", ""), "StardewValley", "ErrorLogs", "SMAPI-latest.txt")


# ─── N网 API 配置 ───────────────────────────────────────────────
# 优先级：环境变量 > 本地配置文件 > 空

# 配置文件路径：开发模式用项目目录，exe 模式用 exe 所在目录
def _get_config_path() -> str:
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe
        return os.path.join(os.path.dirname(sys.executable), "config.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

_CONFIG_FILE = _get_config_path()

def _load_local_config() -> dict:
    if os.path.isfile(_CONFIG_FILE):
        try:
            import json
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_api_key(key: str) -> None:
    """保存 API Key 到本地配置文件"""
    import json
    cfg = _load_local_config()
    cfg["NEXUS_API_KEY"] = key.strip()
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    # 更新缓存的模块级变量
    global NEXUS_API_KEY
    NEXUS_API_KEY = key.strip()

def get_api_key() -> str:
    return os.environ.get("NEXUS_API_KEY") or _load_local_config().get("NEXUS_API_KEY", "")

NEXUS_API_KEY = get_api_key()
NEXUS_USER_AGENT = "Stardew-MOD-Checker/1.0"


# ─── 服务器配置（Web界面用） ────────────────────────────────────
PORT = 8090