"""
测试 scanner.py 中的 manifest 解析与扫描功能
"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scanner


# ─── clear_scan_cache ───────────────────────────────────────────
def test_clear_cache():
    scanner._SCAN_CACHE = {"test": "data"}
    scanner.clear_scan_cache()
    assert scanner._SCAN_CACHE is None


# ─── _read_manifest ─────────────────────────────────────────────
def test_read_manifest_basic():
    """解析一个正常的 manifest.json"""
    content = json.dumps({
        "Name": "Test Mod",
        "Author": "Tester",
        "Version": "1.0.0",
        "UniqueID": "Test.Mod",
        "UpdateKeys": ["Nexus:12345"],
        "ContentPackFor": {"UniqueID": "Pathoschild.ContentPatcher"},
    })
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    try:
        result = scanner._read_manifest(tmp_path)
        assert result is not None
        assert result["name"] == "Test Mod"
        assert result["version"] == "1.0.0"
        assert result["nexus_id"] == "12345"
        assert result["mod_type"] == "ContentPatcher包"
    finally:
        os.unlink(tmp_path)


def test_read_manifest_smapi_plugin():
    """解析 SMAPI 插件类型"""
    content = json.dumps({
        "Name": "SMAPI Mod",
        "Version": "2.0.0",
        "UniqueID": "Smapi.Mod",
        "EntryDll": "Mod.dll",
    })
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    try:
        result = scanner._read_manifest(tmp_path)
        assert result is not None
        assert result["mod_type"] == "SMAPI插件"
        assert result["name"] == "SMAPI Mod"
    finally:
        os.unlink(tmp_path)


def test_read_manifest_other_type():
    """解析其他类型的 MOD"""
    content = json.dumps({
        "Name": "Other Mod",
        "Version": "1.0",
    })
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    try:
        result = scanner._read_manifest(tmp_path)
        assert result is not None
        assert result["mod_type"] == "其他"
    finally:
        os.unlink(tmp_path)


def test_read_manifest_no_update_keys():
    """解析没有 UpdateKeys 的 manifest"""
    content = json.dumps({
        "Name": "NoNexus Mod",
        "Version": "1.0",
    })
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    try:
        result = scanner._read_manifest(tmp_path)
        assert result is not None
        assert result["nexus_id"] == ""
    finally:
        os.unlink(tmp_path)


def test_read_manifest_invalid_json():
    """解析无效 JSON 应返回 None"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{not valid json")
        tmp_path = f.name

    try:
        result = scanner._read_manifest(tmp_path)
        assert result is None
    finally:
        os.unlink(tmp_path)


def test_read_manifest_not_found():
    """解析不存在的文件应返回 None"""
    result = scanner._read_manifest("/nonexistent/path.json")
    assert result is None
