"""统一的日志配置模块"""
import logging
import sys
from pathlib import Path

# 默认日志格式
DEFAULT_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 全局 logger 缓存
_loggers = {}


def get_logger(name: str = 'music_tagger', level: int = logging.INFO) -> logging.Logger:
    """
    获取或创建 logger 实例。

    Args:
        name: logger 名称
        level: 日志级别

    Returns:
        配置好的 Logger 实例
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加 handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger


def set_log_level(level: int):
    """设置所有 logger 的日志级别"""
    for logger in _loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def add_file_handler(log_file: str, level: int = logging.DEBUG):
    """
    添加文件日志处理器。

    Args:
        log_file: 日志文件路径
        level: 文件日志级别
    """
    logger = get_logger()

    # 确保目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT))
    logger.addHandler(file_handler)