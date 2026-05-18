"""同步操作模块"""

import os
import click
from typing import Optional, List, Dict
from .logger import logger
from . import git_operations as git_ops
from .config import DEFAULT_MAX_MERGE_DEPTH, show_config

linear_merge_depth = 0
MAX_MERGE_DEPTH = -1
TRACK_BRANCH = None

def sync_project(project_config: Dict[str, str]) -> bool:
    """执行完整的同步流程"""
    repo_path = project_config['repo_path']
    upstream_remote = project_config['upstream_remote']
    remote_branch = project_config['remote_branch']
    track_branch = project_config['track_branch']
    target_branch = project_config['target_branch']
    gerrit_remote = project_config['gerrit_remote']
    gerrit_branch = project_config['gerrit_branch']

    global linear_merge_depth, MAX_MERGE_DEPTH, TRACK_BRANCH
    linear_merge_depth = 0
    MAX_MERGE_DEPTH = project_config.get('max_merge_depth', DEFAULT_MAX_MERGE_DEPTH)
    TRACK_BRANCH = track_branch
    
    # 切换到仓库目录
    original_dir = os.getcwd()
    os.chdir(repo_path)
    
    try:
        # 检查 git 是否可用
        if not git_ops.is_git_available():
            logger.error("错误: git 命令不可用")
            return False

        # 检查根目录是否存在.git目录
        if not os.path.exists(".git"):
            logger.error(f"错误: 项目根目录 {repo_path} 下不存在.git目录，非git仓库")
            return False

        last_synced = _parse_last_synced_commit(project_config)
        if not last_synced:
            raise Exception("无法获取上一次同步位置")

        parent_merge_commit: List[str] = []
        if not git_ops.in_parent_chain(track_branch, last_synced):
            parent_merge_commit = git_ops.get_parent_merge_commit(target_branch)
            if parent_merge_commit:            
                logger.info(f"上一次最后同步的是merge commit，相关主链commit: {parent_merge_commit}")            
                parent_merge_commit.append(last_synced)
                last_synced = parent_merge_commit[0]
            else:
                logger.info(f"sync commit记录异常，无法正确获取上一次的同步位置")
                return False
        
        # 询问是否更新本地追踪分支
        if _is_github_repo(upstream_remote):            
            logger.info(f"注意: GitHub 仓库实时网络较差，跳过执行 pull 命令。手动更新 {track_branch} 分支\n")
        else:
            pull_choice = click.prompt(f"更新本地 {track_branch} 分支 (git pull)?", default="Y")
            if pull_choice.upper() != "N":
                logger.info(f"正在从 {upstream_remote}/{remote_branch} 更新 {track_branch}...")
                if git_ops.checkout_branch(track_branch):
                    # 检查当前分支                
                    if not _handle_ensure_branch(track_branch):
                        return False
                    
                    if not git_ops.pull_branch(upstream_remote, remote_branch):
                        logger.warning(f"警告: git pull 失败，本地分支可能已过时")
                else:
                    logger.warning(f"警告: 切换到 {track_branch} 失败")
            
        if not _handle_ensure_branch(target_branch):
            return False

        if not _linearize_branch_chain(last_synced, track_branch, parent_merge_commit):
            logger.info("\n没有新提交需要同步。")
            return True
        logger.info(f"\n提示: 现在可以运行 'git push {gerrit_remote} HEAD:refs/for/{gerrit_branch}' 推送到 Gerrit 进行审核")
    
    finally:
        os.chdir(original_dir)

def _parse_last_synced_commit(project_config) -> Optional[str]:
    """解析上次同步的commit"""
    track_branch = project_config['track_branch']
    target_branch = project_config['target_branch']
    
    # 获取上次同步的commit
    last_synced = git_ops.get_last_synced_commit(target_branch)
    if not last_synced:
        # 首次同步，使用 merge-base
        logger.info(f"\n首次同步，使用 merge-base...")
        last_synced = git_ops.get_merge_base(track_branch, target_branch)
        if not last_synced:
            logger.error(f"\n错误: 无法找到 {track_branch} 和 {target_branch} 的共同祖先")
            return None
    else:
        logger.info(f"\n上次同步的commit: {last_synced}")
    return last_synced

def _is_github_repo(upstream):
    """检查是否为 GitHub 仓库"""
    upstream_url = git_ops.get_upstream_remote(upstream)
    logger.info(f"远端仓库：{upstream_url}")
    return upstream_url.find("github.com") != -1

def _linearize_branch_chain(start_point: str, end_point: str, parent_chain: List[str]):
    """将合并提交转换为普通提交"""
    global linear_merge_depth
    logger.info(f"\n当前merge深度: {linear_merge_depth}")
    if parent_chain:
        logger.info(f"主链相关commit: {parent_chain}") 
    if linear_merge_depth < 0:
        logger.error(f"错误: merge深度 {linear_merge_depth}，无法继续处理")
        raise Exception("merge depth error")
    logger.info("-" * ((linear_merge_depth+1) * 2))

    if parent_chain:
        logger.info(f"{git_ops.MERGE_COMMIT_PREFIX}不为空，上次最后同步的是merge commit，需要先恢复到主链")

    if parent_chain and start_point == parent_chain[linear_merge_depth]:
        logger.info(f"恢复{linear_merge_depth}层merge commit: {parent_chain[linear_merge_depth]}")
        # 从记录而言，start_point是一个merge commit
        if (linear_merge_depth+1) < len(parent_chain):
            depth = linear_merge_depth + 1
            p1, p2 = git_ops.get_parents(start_point)
            next_commit = parent_chain[depth]
            if next_commit in git_ops.get_parent_sub_commits(p1, p2):
                _linearize_branch_chain(next_commit, p2, parent_chain)
                parent_chain.pop()
                linear_merge_depth = linear_merge_depth - 1
                if linear_merge_depth < 0:
                    logger.error(f"错误: merge深度 {linear_merge_depth}，无法继续处理")
                    raise Exception("merge depth error")
            else:
                logger.error(f"merge commit记录异常，无法继续处理，{next_commit} 不是 {start_point} 的子链提交")
                raise Exception("merge commit record error")
        else:
            parent_chain.pop()
            logger.info(f"已恢复所有merge commit，开始处理新提交...")

    logger.info(f"获取从 {start_point}..{end_point} 的新提交...")
    new_commits = git_ops.get_parent_sub_commits(start_point, end_point)
    logger.info(f"找到 {len(new_commits)} 个新提交:")

    if not new_commits:
        logger.info("=" * ((linear_merge_depth+1) * 2))
        logger.info(f"merge深度 {linear_merge_depth}: 所有提交处理完成！")
        return False
    
    for commit in new_commits:
        msg = git_ops.get_commit_message(commit)
        short_msg = msg.split('\n')[0] if msg else ""
        logger.info(f"  {commit}: {short_msg}")
        
    # 处理每个提交
    logger.info("\n开始处理提交...")
    for i, commit_id in enumerate(new_commits, 1):
        logger.info(f"\n[{i}/{len(new_commits)}] 处理提交: {commit_id}")
        
        parent_count = git_ops.get_parent_count(commit_id)
        # 获取完整提交消息
        full_msg = git_ops.get_commit_message(commit_id)        
        if parent_count == 1:
            # 普通提交
            logger.info("  类型: 普通提交")
            # 添加主链merge commit信息
            if parent_chain:
                full_msg += f"\n{git_ops.MERGE_COMMIT_PREFIX}{' '.join(parent_chain)}"
            # 添加 cherry-pick 标记
            full_msg += f"\n{git_ops.CHERRY_PICK_PREFIX}{commit_id}"
            _handle_normal_commit(commit_id, full_msg)
            
        elif parent_count >= 2:
            # Merge commit
            logger.info("  类型: Merge commit")
            _handle_merge_commit(commit_id, full_msg, parent_chain)

    logger.info("=" * ((linear_merge_depth+1) * 2))
    logger.info(f"merge深度 {linear_merge_depth}: 所有提交处理完成！")
    return True

def _handle_normal_commit(commit_id, full_msg):
    """处理普通提交"""
    if linear_merge_depth > 1:
        if git_ops.is_ancestor(commit_id, TRACK_BRANCH):
            logger.info(f"  子链merge的 {commit_id} 在主链上已存在，跳过")
            return
    # Cherry-pick（不提交）
    if not git_ops.cherry_pick_commit(commit_id):
        logger.error(f"  错误: cherry-pick 失败")
        logger.error("  请手动解决冲突后继续")
        raise Exception("cherry-pick failed")
    
    # 检查是否有冲突
    if git_ops.is_exists_conflict():
        logger.error("  错误: 检测到合并冲突")
        logger.error("  请手动解决冲突，然后运行:")
        logger.error("    git add .")
        logger.error("    git commit")
        logger.error("  之后重新运行此脚本")
        raise Exception("merge conflict")
    
    # 提交（Change-Id 将由 commit-msg hook 添加）
    if not git_ops.commit_with_message(full_msg):
        raise Exception("commit failed")
    
    logger.info("  成功提交，Change-Id 已添加")

def _handle_merge_commit(commit_id: str, full_msg: str, parent_chain: Optional[list[str]] = None):
    """处理 merge commit"""
    global linear_merge_depth
    if parent_chain is None:
        parent_chain = []

    p1, p2 = git_ops.get_parents(commit_id)
    logger.info(f"  merge提交 {commit_id} 有父节点 {p1} 和 {p2}")
    
    # 检查是否为空合并
    if git_ops.is_empty_merge(commit_id, p1):
        logger.info("  空合并，跳过")
        return
    
    if parent_chain:
        full_msg += f"\n{git_ops.MERGE_COMMIT_PREFIX}{' '.join(parent_chain)}"
    
    if MAX_MERGE_DEPTH == 0:
        logger.info("  MAX_MERGE_DEPTH 为0，直接 squash")
        # 添加 squash 标记
        full_msg += f"\n{git_ops.SQUASHED_PREFIX}{commit_id}"
        _squash_commit(commit_id, full_msg)
        return
    elif git_ops.has_conflict_resolution(commit_id, p1, p2):
        # 检查是否有冲突解决
        logger.info("  有冲突合并，直接 squash")
        # 添加 squash 标记
        full_msg += f"\n{git_ops.SQUASHED_PREFIX}{commit_id}"
        _squash_commit(commit_id, full_msg)
        return

    if MAX_MERGE_DEPTH > 0 and linear_merge_depth >= MAX_MERGE_DEPTH:
        logger.info(f"  merge线性化展开超过最大深度{MAX_MERGE_DEPTH}，直接 squash")
        # 添加 squash 标记
        full_msg += f"\n{git_ops.SQUASHED_PREFIX}{commit_id}"
        _squash_commit(commit_id, full_msg)
        return

    linear_merge_depth += 1
    # 递归处理子链
    parent_chain.append(commit_id)
    _linearize_branch_chain(p1, p2, parent_chain)
    parent_chain.pop()
    linear_merge_depth -= 1
    
def _squash_commit(commit_id, full_msg):
    """Squash 提交"""
    if not git_ops.run_cmd(f"git read-tree --reset -u {commit_id}"):
        logger.error("  错误: squash 失败")
        raise Exception("squash failed")
    logger.info("-----")
    logger.info(f"  squash提交 {commit_id} 消息:\n{full_msg}")
    logger.info("-----")
    if not git_ops.commit_with_message(full_msg):
        logger.error("  错误: 提交失败")
        raise Exception("commit failed")
    
    logger.info("  成功 squash")

def _handle_ensure_branch(branch) -> bool:
    """处理 Change-Branch 提交"""
    current_branch = git_ops.get_current_branch()
    logger.info(f"当前分支是 {current_branch}")
    if current_branch != branch:
        logger.info(f"正在切换到 {branch}...")
        if not git_ops.checkout_branch(branch):
            logger.error(f"错误: 切换分支失败")
            return False
    
    # 检查工作目录是否干净
    if not git_ops.is_workdir_clean():
        logger.error("错误: 工作目录有未提交的更改，请提交或暂存它们")
        return False
    
    return True