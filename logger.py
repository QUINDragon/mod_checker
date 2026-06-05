"""
统一日志模块
用法:
    from logger import log
    log.info("普通信息")
    log.warning("警告")
    log.error("错误")
    log.debug("调试信息，仅 MOD_CHECK_LOG_LEVEL=DEBUG 时显示")

通过环境变量控制级别:
    MOD_CHECK_LOG_LEVEL=DEBUG   → 显示所有
    MOD_CHECK_LOG_LEVEL=INFO    → 默认，显示 info/warning/error
    MOD_CHECK_LOG_LEVEL=WARNING → 仅显示 warning/error
    MOD_CHECK_LOG_LEVEL=ERROR   → 仅显示 error
"""
import logging
import os

_level_name = os.environ.get("MOD_CHECK_LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)

_logger = logging.getLogger("mod_check")
_logger.setLevel(_level)

# 避免重复添加 handler
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(_level)
    _handler.setFormatter(logging.Formatter(
        "%(levelname)-7s %(message)s" if _level == logging.DEBUG else "%(message)s"
    ))
    _logger.addHandler(_handler)

log = _logger
