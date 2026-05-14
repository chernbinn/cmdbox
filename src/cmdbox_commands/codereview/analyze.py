#!/usr/bin/env python
"""分析操作模块"""

from logger import logger
import git_operations as git

def analyze_commit(commit):
    """分析单个 commit 的类型"""
    parent_count = git.get_parent_count(commit)
    logger.info(f"提交: {commit}")
    logger.info(f"父节点数量: {parent_count}")
    
    if parent_count == 1:
        logger.info("类型: 普通提交")
    elif parent_count >= 2:
        logger.info("类型: Merge commit")
        p1 = git.get_first_parent(commit)
        p2 = git.get_second_parent(commit)
        logger.info(f"父节点1: {p1}")
        logger.info(f"父节点2: {p2}")
        
        if git.is_empty_merge(commit, p1):
            logger.info("状态: 空合并")
        elif git.has_conflict_resolution(commit, p1, p2):
            logger.info("状态: 有冲突解决")
        else:
            logger.info("状态: 无冲突合并")
            subs = git.get_sub_commits(p1, p2)
            logger.info(f"子分支提交数量: {len(subs)}")