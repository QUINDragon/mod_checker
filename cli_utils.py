"""
CLI 工具：彩色输出、模糊匹配、进度条
无外部依赖，纯 ANSI + 标准库
"""
import sys, os


# ═══════════════════════════════════════════════════════════════
#  颜色
# ═══════════════════════════════════════════════════════════════

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def setup():
        """启用 Windows 控制台 ANSI 支持"""
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass


def red(text: str) -> str:
    return f"{Colors.RED}{text}{Colors.RESET}"

def green(text: str) -> str:
    return f"{Colors.GREEN}{text}{Colors.RESET}"

def yellow(text: str) -> str:
    return f"{Colors.YELLOW}{text}{Colors.RESET}"

def blue(text: str) -> str:
    return f"{Colors.BLUE}{text}{Colors.RESET}"

def cyan(text: str) -> str:
    return f"{Colors.CYAN}{text}{Colors.RESET}"

def bold(text: str) -> str:
    return f"{Colors.BOLD}{text}{Colors.RESET}"


# ═══════════════════════════════════════════════════════════════
#  模糊匹配
# ═══════════════════════════════════════════════════════════════

def fuzzy_match(query: str, candidates: list[str], threshold: float = 0.3) -> list[tuple[str, float]]:
    """模糊匹配，返回 (候选名, 得分) 列表，按得分降序"""
    q = query.lower().strip()
    if not q:
        return [(c, 1.0) for c in candidates]

    scored = []
    for c in candidates:
        cl = c.lower()
        # 完全匹配
        if q == cl:
            scored.append((c, 2.0))
            continue
        # 前缀匹配
        if cl.startswith(q):
            scored.append((c, 1.5))
            continue
        # 子串匹配
        if q in cl:
            scored.append((c, 1.0))
            continue
        # 字符级模糊（每个查询字符按顺序出现）
        score = _seq_match(q, cl)
        if score >= threshold:
            scored.append((c, score))

    scored.sort(key=lambda x: -x[1])
    return scored


def _seq_match(query: str, target: str) -> float:
    """查询字符在目标中按顺序出现的得分"""
    qi = 0
    for ch in target:
        if qi < len(query) and ch == query[qi]:
            qi += 1
    if qi == 0:
        return 0.0
    return qi / len(query) * 0.5  # 子序列匹配最多 0.5 分


# ═══════════════════════════════════════════════════════════════
#  进度条
# ═══════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, width: int = 30, label: str = "") -> str:
    """返回进度条字符串"""
    if total <= 0:
        return ""
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"\r  {label}[{bar}] {current}/{total} ({pct*100:.0f}%)"
