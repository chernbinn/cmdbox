"""同步操作模块"""

import os
import click
from .logger import logger
from . import git_operations as git_ops

linear_merge_depth = 0
MAX_MERGE_DEPTH = -1
TRACK_BRANCH = None

def sync_project(project_config):
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
    MAX_MERGE_DEPTH = project_config.get('max_merge_depth', -1)
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
        
        # 输出项目信息
        logger.info(f"\n项目: {os.path.basename(repo_path)}")
        logger.info(f"仓库: {repo_path}")
        logger.info(f"上游: {upstream_remote}/{remote_branch}")
        logger.info(f"本地追踪分支: {track_branch}")
        logger.info(f"目标分支: {target_branch}")
        logger.info(f"Gerrit远程分支: {gerrit_remote}/{gerrit_branch}")
        logger.info(f"MAX_MERGE_DEPTH: {MAX_MERGE_DEPTH}\n")
        
        # 获取上次同步的commit
        last_synced = git_ops.get_last_synced_commit(target_branch)
        if not last_synced:
            # 首次同步，使用 merge-base
            last_synced = git_ops.get_merge_base(track_branch, target_branch)
            if last_synced:
                logger.info(f"\n首次同步，使用 merge-base: {last_synced}")
            else:
                logger.error(f"\n错误: 无法找到 {track_branch} 和 {target_branch} 的共同祖先")
                return False
        else:
            logger.info(f"\n上次同步的commit: {last_synced}")
        
        # 询问是否更新本地追踪分支
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
        
        if not _linearize_branch_chain(last_synced, track_branch):
            return False
        logger.info(f"\n提示: 现在可以运行 'git push {gerrit_remote} HEAD:refs/for/{gerrit_branch}' 推送到 Gerrit 进行审核")
    
    finally:
        os.chdir(original_dir)

def _linearize_branch_chain(start_point, end_point):
    """将合并提交转换为普通提交"""    
    logger.info(f"\n当前merge深度: {linear_merge_depth}")
    logger.info("-" * ((linear_merge_depth+1) * 2))
    logger.info(f"获取从 {start_point}..{end_point} 的新提交...")        
    new_commits = git_ops.get_parent_sub_commits(start_point, end_point)
    
    if not new_commits:
        logger.info("没有新提交需要同步。")
        return True
    
    logger.info(f"找到 {len(new_commits)} 个新提交:")
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
        
        # 添加 cherry-pick 标记
        full_msg += f"\n\ncherry picked from commit {commit_id}"
        if parent_count == 1:
            # 普通提交
            logger.info("  类型: 普通提交")
            _handle_normal_commit(commit_id, full_msg)
            
        elif parent_count >= 2:
            # Merge commit
            logger.info("  类型: Merge commit")
            _handle_merge_commit(commit_id, full_msg)
    
    logger.info("\n" + "=" * ((linear_merge_depth+1) * 2))
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
    result = git_ops.run_cmd("git status --porcelain")
    if "UU" in result.stdout:
        logger.error("  错误: 检测到合并冲突")
        logger.error("  请手动解决冲突，然后运行:")
        logger.error("    git add .")
        logger.error("    git commit")
        logger.error("  之后重新运行此脚本")
        raise Exception("merge conflict")
    
    # 提交（Change-Id 将由 commit-msg hook 添加）
    if not git_ops.commit_with_message(full_msg):
        logger.error("  错误: 提交失败，可能缺少 commit-msg hook")
        logger.error("  请安装 hook: curl -o .git/hooks/commit-msg http://localhost:8080/tools/hooks/commit-msg")
        raise Exception("commit failed")
    
    logger.info("  成功提交，Change-Id 已添加")

def _handle_merge_commit(commit_id, full_msg):
    """处理 merge commit"""
    global linear_merge_depth

    p1, p2 = git_ops.get_parents(commit_id)
    logger.info(f"  merge提交 {commit_id} 有父节点 {p1} 和 {p2}")
    
    # 检查是否为空合并
    if git_ops.is_empty_merge(commit_id, p1):
        logger.info("  空合并，跳过")
        return
    
    if MAX_MERGE_DEPTH == 0:
        logger.info("  MAX_MERGE_DEPTH 为0，直接 squash")
        _squash_commit(commit_id, full_msg)
        return
    elif git_ops.has_conflict_resolution(commit_id, p1, p2):
        # 检查是否有冲突解决
        logger.info("  有冲突合并，直接 squash")
        _squash_commit(commit_id, full_msg)
        return

    if MAX_MERGE_DEPTH > 0 and linear_merge_depth >= MAX_MERGE_DEPTH:
        logger.info(f"  merge线性化展开超过最大深度{MAX_MERGE_DEPTH}，直接 squash")
        _squash_commit(commit_id, full_msg)
        return

    linear_merge_depth += 1
    _linearize_branch_chain(p1, p2)
    
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