"""代码审查工具 - 同步上游分支到 Gerrit 审核分支"""

import logging

def setup_logger(name='codereview'):
    """配置 logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

logger = setup_logger()
