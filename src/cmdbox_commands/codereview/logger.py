import logging
import os

_logger = None  # 保存全局 logger 实例

def setup_logger(name='codereview'):
    """配置 logger（仅首次调用时创建）"""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(name)
    if logger.handlers:
        _logger = logger
        return logger

    level = os.environ.get('CODEREVIEW_LOG_LEVEL', 'INFO')
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)

    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    _logger = logger
    return logger

def set_log_level(level: str):
    """动态修改全局 logger 及其 handler 的日志级别"""
    global _logger
    if _logger is None:
        # 如果尚未初始化，先初始化（但通常会先调用 setup_logger）
        setup_logger()
    
    # 数值化级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    _logger.setLevel(numeric_level)
    for handler in _logger.handlers:
        handler.setLevel(numeric_level)
    
    # 可选：同时设置根 logger 的级别（如果需要）
    # logging.getLogger().setLevel(numeric_level)

# 为保持向后兼容，仍然提供一个 logger 实例
logger = setup_logger()