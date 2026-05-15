"""分析操作模块"""

from .logger import logger
from . import git_operations as git_ops

def analyze_commit(commit_hash):
    """分析单个 commit 的类型"""
    parent_count = git_ops.get_parent_count(commit_hash)
    logger.info(f"提交: {commit_hash}")
    logger.info(f"父节点数量: {parent_count}")
    
    if parent_count == 1:
        logger.info("类型: 普通提交")
    elif parent_count >= 2:
        logger.info("类型: Merge commit")
        p1, p2 = git_ops.get_parents(commit_hash)
        # p1 = git_ops.get_first_parent(commit_hash)
        # p2 = git_ops.get_second_parent(commit_hash)
        logger.info(f"父节点1: {p1}")
        logger.info(f"父节点2: {p2}")
        
        if git_ops.is_empty_merge(commit_hash, p1):
            logger.info("状态: 空合并")
        elif git_ops.has_conflict_resolution(commit_hash, p1, p2):
            logger.info("状态: 有冲突解决")
        else:
            logger.info("状态: 无冲突合并")
            subs = git_ops.get_sub_commits(p1, p2)
            logger.info(f"子分支提交数量: {len(subs)}")