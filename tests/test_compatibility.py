"""
测试 compatibility.py 中的版本解析与比较函数
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compatibility import (
    _parse_version,
    _compare_version_list,
    compare_versions,
    check_version,
)


# ─── _parse_version ─────────────────────────────────────────────
def test_parse_version_normal():
    assert _parse_version("1.6.15") == [1, 6, 15]
    assert _parse_version("4.1.10") == [4, 1, 10]
    assert _parse_version("0.1.0") == [0, 1, 0]


def test_parse_version_with_v_prefix():
    assert _parse_version("v1.6.15") == [1, 6, 15]
    assert _parse_version("V2.0") == [2, 0]


def test_parse_version_with_prerelease():
    assert _parse_version("1.6.15-beta") == [1, 6, 15]
    assert _parse_version("4.1.0-alpha.2") == [4, 1, 0]


def test_parse_version_empty():
    assert _parse_version("") is None
    assert _parse_version(None) is None


def test_parse_version_invalid():
    assert _parse_version("abc") is None
    assert _parse_version("1.6.x") is None


# ─── _compare_version_list ──────────────────────────────────────
def test_compare_version_list_equal():
    assert _compare_version_list([1, 6, 15], [1, 6, 15]) is True


def test_compare_version_list_greater():
    assert _compare_version_list([2, 0], [1, 9]) is True
    assert _compare_version_list([1, 6, 15], [1, 6, 14]) is True


def test_compare_version_list_less():
    assert _compare_version_list([1, 0], [2, 0]) is False
    assert _compare_version_list([1, 6, 3], [1, 6, 4]) is False


def test_compare_version_list_different_length():
    # 1.6 == 1.6.0
    assert _compare_version_list([1, 6], [1, 6, 0]) is True
    assert _compare_version_list([1, 6, 0], [1, 6]) is True
    # 1.6 < 1.6.1
    assert _compare_version_list([1, 6], [1, 6, 1]) is False


def test_compare_version_list_empty():
    assert _compare_version_list([], [1, 0]) is None
    assert _compare_version_list([1, 0], []) is None
    assert _compare_version_list(None, [1, 0]) is None


# ─── compare_versions ───────────────────────────────────────────
def test_compare_versions_equal():
    assert compare_versions("1.0.0", "1.0.0") == "已是最新版本"
    assert compare_versions("v2.0", "2.0") == "已是最新版本"
    assert compare_versions("v1.6.15", "v1.6.15") == "已是最新版本"
    # 不同长度但等价的版本
    assert compare_versions("1.6", "1.6.0") == "已是最新版本"
    assert compare_versions("1.6.0", "1.6") == "已是最新版本"
    assert compare_versions("2.0", "2.0.0") == "已是最新版本"


def test_compare_versions_has_update():
    assert compare_versions("1.0.0", "1.0.1") == "有可用更新"
    assert compare_versions("1.6", "1.7") == "有可用更新"
    assert compare_versions("v1.6.14", "v1.6.15") == "有可用更新"


def test_compare_versions_local_higher():
    assert compare_versions("3.0", "2.0") == "本地版本高于N网"
    assert compare_versions("1.6.15", "1.6.14") == "本地版本高于N网"


def test_compare_versions_empty():
    assert compare_versions("", "1.0") == "无法判断"
    assert compare_versions("1.0", "") == "无法判断"
    assert compare_versions(None, "1.0") == "无法判断"


def test_compare_versions_invalid_format():
    # 无法解析的版本号回退到字符串比较
    result = compare_versions("abc", "xyz")
    assert result in ("已是最新版本", "有可用更新", "本地版本高于N网", "无法判断")


# ─── check_version ──────────────────────────────────────────────
def test_check_version_basic():
    mods = [
        {"name": "mod_a", "version": "1.0.0", "latest_version": "1.0.1"},
        {"name": "mod_b", "version": "2.0", "latest_version": "2.0"},
        {"name": "mod_c", "version": "3.0", "latest_version": None},
    ]
    results = check_version(mods)
    assert results[0]["status"] == "有可用更新"
    assert results[1]["status"] == "已是最新版本"
    assert results[2]["status"] == "无法获取最新版本"
    assert len(results) == 3
