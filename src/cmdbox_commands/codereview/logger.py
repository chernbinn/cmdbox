"""代码审查工具 - 同步上游分支到 Gerrit 审核分支"""

import logging
import os

def setup_logger(name='codereview'):
    """配置 logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = os.environ.get('CODEREVIEW_LOG_LEVEL', 'INFO')    
    logger.setLevel(level)
    
    # 创建控制台处理器
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

logger = setup_logger()
