# file_watcher.py
# 使用 watchdog 监控 Vortex MOD 目录中的 manifest.json / content.json 变化
# 一旦检测到变化，自动调用 scanner.clear_scan_cache() 清除缓存

import os, sys, threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logger import log

# 需要监控的文件名
_WATCHED_FILES = {"manifest.json", "content.json", "Content.json"}

_observer = None
_watch_thread = None


class ModFileHandler(FileSystemEventHandler):
    """检测到 MOD 相关 JSON 文件变化时清除扫描缓存"""

    def __init__(self):
        super().__init__()
        self._debounce_timer = None

    def _clear_cache(self):
        """清除 scanner 缓存"""
        try:
            import scanner
            scanner.clear_scan_cache()
            log.debug("检测到MOD文件变化，扫描缓存已清除")
        except Exception:
            pass

    def _debounced_clear(self):
        """防抖：500ms 内多条事件合并为一次清除"""
        if self._debounce_timer and self._debounce_timer.is_alive():
            return  # 已有定时器在跑，跳过
        self._debounce_timer = threading.Timer(0.5, self._clear_cache)
        self._debounce_timer.daemon = True
        self._debounce_timer.start()

    def _check_and_clear(self, event):
        if event.is_directory:
            return
        filename = os.path.basename(event.src_path)
        if filename in _WATCHED_FILES:
            self._debounced_clear()

    def on_created(self, event):
        self._check_and_clear(event)

    def on_modified(self, event):
        self._check_and_clear(event)

    def on_deleted(self, event):
        self._check_and_clear(event)

    def on_moved(self, event):
        # 移动也可能涉及目标文件
        if not event.is_directory:
            filename = os.path.basename(event.dest_path)
            if filename in _WATCHED_FILES:
                self._debounced_clear()


def start_watching(path=None):
    """
    启动文件监听
    path: 要监听的目录，默认为 config.VORTEX_MODS
    返回 Observer 对象
    """
    global _observer

    if _observer is not None:
        log.debug("文件监听已在运行中")
        return

    if path is None:
        try:
            from config import VORTEX_MODS
            path = VORTEX_MODS
        except ImportError:
            print("  [WATCH] 无法导入 config.VORTEX_MODS，请指定 path")
            return None

    if not os.path.isdir(path):
        print(f"  [WATCH] 目录不存在: {path}")
        return None

    event_handler = ModFileHandler()
    _observer = Observer()
    _observer.schedule(event_handler, path, recursive=True)
    _observer.start()

    print(f"  [WATCH] 已开始监控: {path}")
    print(f"  [WATCH] 监控文件: {', '.join(sorted(_WATCHED_FILES))}")
    return _observer


def stop_watching(observer=None):
    """
    停止文件监听
    """
    global _observer
    target = observer or _observer

    if target is None:
        return

    try:
        target.stop()
        target.join(timeout=2)
    except Exception:
        pass

    if target is _observer:
        _observer = None

    print("  [WATCH] 文件监听已停止")


def is_watching():
    """检查监听是否正在运行"""
    return _observer is not None and _observer.is_alive()


if __name__ == "__main__":
    # 测试：启动监听，等待用户按回车停止
    print("文件监听测试")
    print("=" * 40)
    print(f"监控文件: {', '.join(sorted(_WATCHED_FILES))}")
    print("请尝试修改 Vortex MOD 目录中的 manifest.json 或 content.json")
    print("按回车停止监听...\n")

    obs = start_watching()
    if obs:
        try:
            input()
        finally:
            stop_watching(obs)

