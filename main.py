"""
星露谷物语 MOD 检查工具 — 统一入口
双击运行: 原生桌面窗口
命令行:
    ModChecker.exe web              Web 前端（浏览器）
    ModChecker.exe cli              CLI 交互模式
    ModChecker.exe fix --auto      自动修复
"""
import sys


def run_cli() -> None:
    from scan_cli import main
    main()


def run_fix() -> None:
    from fix_mode import main
    main()


def run_web() -> None:
    """Web 前端 — 浏览器中打开"""
    import webbrowser, threading, time
    def _open():
        time.sleep(0.5)
        webbrowser.open("http://127.0.0.1:8090")
    threading.Thread(target=_open, daemon=True).start()
    from web.app import run_server
    run_server()


def run_gui() -> None:
    """原生桌面窗口"""
    from gui.app import run_gui
    run_gui()


def main() -> None:
    # 无参数 = 双击 → 原生窗口
    if len(sys.argv) < 2:
        run_gui()
        return

    cmd = sys.argv[1].lower()

    if cmd == "web":
        sys.argv.pop(1)
        run_web()
    elif cmd in ("cli", "cmd", "terminal"):
        sys.argv.pop(1)
        run_cli()
    elif cmd in ("fix", "repair"):
        sys.argv.pop(1)
        run_fix()
    elif cmd in ("gui", "window"):
        sys.argv.pop(1)
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
