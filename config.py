import os

# ─── 路径配置 ───────────────────────────────────────────────────
# Vortex MOD 存放路径
VORTEX_MODS = os.path.join(os.environ.get("APPDATA", ""), "Vortex", "stardewvalley", "mods")

# 星露谷物语游戏路径（自动检测常用位置）
_GAME_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Stardew Valley",
    r"C:\Program Files\Steam\steamapps\common\Stardew Valley",
    r"D:\Steam\steamapps\common\Stardew Valley",
    r"E:\Steam\steamapps\common\Stardew Valley",
]

GAME_PATH = ""
for p in _GAME_PATHS:
    if os.path.isdir(p):
        GAME_PATH = p
        break

# SMAPI 路径
SMAPI_PATH = os.path.join(GAME_PATH, "Mods", "SMAPI") if GAME_PATH else ""


# ─── N网 API 配置 ───────────────────────────────────────────────
NEXUS_API_KEY = "Fenw8ZiSyY1z92B0NFYEHvzJSDu9HBEz7HDRYmaKlBq0EkKul17gfl/1--FXAYDGeYvBNz+zIs--I9DeGmW/pRaCe+mARTGeZg=="
NEXUS_USER_AGENT = "Stardew-MOD-Checker/1.0"


# ─── 服务器配置（Web界面用） ────────────────────────────────────
PORT = 8090