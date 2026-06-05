"""
测试 mod_status.py 中的 SMAPI 日志解析
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mock_log(content: str) -> dict:
    """用临时文件模拟 SMAPI 日志，调用 parse_smapi_log"""
    import mod_status
    # 保存原始路径
    original = mod_status.SMAPI_LOG
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()
    mod_status.SMAPI_LOG = tmp.name
    try:
        return mod_status.parse_smapi_log()
    finally:
        os.unlink(tmp.name)
        mod_status.SMAPI_LOG = original


SAMPLE_LOG = """SMAPI 4.1.10 with Stardew Valley 1.6.15 on Windows

[SMAPI] Loaded 3 mods:
[SMAPI]    Content Patcher 2.5.3 by Pathoschild
[SMAPI]    Lookup Anything 1.46.0 by Pathoschild

[SMAPI] Loaded 2 content packs:
[SMAPI]    Some CP Pack 1.2.0 by AuthorName|for Content Patcher
[SMAPI]    Another Pack 3.0.0 by OtherName|for Content Patcher

Skipped mods
--------------------------------------------------
   - Skipped Old Mod 1.0.0 because its DLL 'OldMod.dll' couldn't be loaded.

[SMAPI]    - Broken Mod 1.0.0 because it requires mods which aren't installed (Missing.Dependency)
"""


def test_parse_smapi_log_no_file():
    """日志文件不存在返回 None"""
    import mod_status
    original = mod_status.SMAPI_LOG
    mod_status.SMAPI_LOG = "/nonexistent/log.txt"
    try:
        assert mod_status.parse_smapi_log() is None
    finally:
        mod_status.SMAPI_LOG = original


def test_parse_loaded_mods():
    result = _mock_log(SAMPLE_LOG)
    assert result is not None
    names = [m["name"] for m in result["loaded_mods"]]
    assert "Content Patcher" in names
    assert "Lookup Anything" in names


def test_parse_loaded_packs():
    result = _mock_log(SAMPLE_LOG)
    packs = {m["name"]: m["version"] for m in result["loaded_packs"]}
    assert "Some CP Pack" in packs
    assert packs["Some CP Pack"] == "1.2.0"


def test_parse_failed_mods():
    result = _mock_log(SAMPLE_LOG)
    assert len(result["failed"]) >= 1
    failed = result["failed"][0]
    assert failed["name"] == "Broken Mod"
    assert "Missing.Dependency" in failed["reason"]


def test_parse_skipped_mods():
    result = _mock_log(SAMPLE_LOG)
    assert len(result["skipped"]) >= 1
    skipped = result["skipped"][0]
    assert skipped["name"] == "Skipped Old Mod"
    assert "couldn't be loaded" in skipped["reason"]


def test_parse_empty_log():
    result = _mock_log("just some random text\nnothing to parse here\n")
    assert result is not None
    assert result["loaded_mods"] == []
    assert result["loaded_packs"] == []
    assert result["failed"] == []
    assert result["skipped"] == []
