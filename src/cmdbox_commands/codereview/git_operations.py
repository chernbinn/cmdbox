"""Git 操作模块"""

import subprocess
from .logger import logger

# 完整长度的 commit hash 长度
# COMMIT_HASH_LEN = None
# 短长度的 commit hash 长度
COMMIT_HASH_LEN = 12

CHERRY_PICK_PREFIX = "cherry picked from commit "
CHERRY_PICK_PREFIX_LEN = len(CHERRY_PICK_PREFIX.split())
SQUASHED_PREFIX = "squashed from commit "
SQUASHED_PREFIX_LEN = len(SQUASHED_PREFIX.split())
MERGE_COMMIT_PREFIX = "chain merge commit: "
MERGE_COMMIT_PREFIX_LEN = len(MERGE_COMMIT_PREFIX.split())

def run_cmd(cmd, capture_output=True, text=True, input=None):
    """运行命令"""
    logger.debug(f"git COMMAND: {cmd}")
    if input:
        logger.debug(f"input: {input}")
    result = subprocess.run(cmd, 
                    shell=True, 
                    capture_output=capture_output, 
                    text=text, 
                    encoding='utf-8', 
                    input=input
                )
    return result

def get_parent_count(commit):
    """获取提交的父节点数量"""
    result = run_cmd(f"git rev-list --parents -n 1 {commit}")
    if result.returncode != 0:
        return 0
    output = result.stdout.strip()
    parts = output.split()
    return len(parts) - 1

def get_parents(commit):
    """返回 (first_parent, second_parent) 元组，非 merge commit 的 second_parent 为 None"""
    result = run_cmd(f"git log -1 --pretty=%P {commit}")
    if result.returncode != 0:
        return None, None
    parts = result.stdout.strip().split()
    if len(parts) == 0:
        return None, None
    first = parts[0]
    second = parts[1] if len(parts) > 1 else None
    return first[:COMMIT_HASH_LEN], second and second[:COMMIT_HASH_LEN]

def get_first_parent(commit):
    """获取第一个父节点
    deprecated: 请使用 get_parents 获取 commit 的所有父节点
    """
    logger.warning(f"deprecated: 请使用 get_parents 获取 commit 的所有父节点\n在windows环境下把^1解析错误导致返回结果错误情况")
    result = run_cmd(f"git rev-parse {commit}^1")
    logger.debug(f"result: {result}")
    if result.returncode == 0:
        return result.stdout.strip()[:COMMIT_HASH_LEN]
    return None

def get_second_parent(commit):
    """获取第二个父节点"""
    result = run_cmd(f"git rev-parse {commit}^2")
    if result.returncode == 0:
        return result.stdout.strip()[:COMMIT_HASH_LEN]
    return None

def is_empty_merge(commit, parent1):
    """检查是否为空合并"""
    result = run_cmd(f"git diff --quiet {parent1} {commit}")
    return result.returncode == 0

def has_conflict_resolution(commit, parent1, parent2):
    """检查 merge commit 是否有冲突解决"""
    base = run_cmd(f"git merge-base {parent1} {parent2}").stdout.strip()
    auto_tree = run_cmd(f"git merge-tree --write-tree {base} {parent1} {parent2}").stdout.strip()
    real_tree = run_cmd(f"git rev-parse {commit}^{{tree}}").stdout.strip()
    return auto_tree != real_tree

def get_parent_sub_commits(start_point, end_point):
    """获取分支提交列表（正向顺序）"""
    # 只获取主链上的提交
    # git rev-list --reverse --first-parent $P1..$P2
    # 从 $P1 到 $P2 的所有提交，包含merge引入的提交记录
    # git rev-list --reverse {parent1}..{parent2}
    result = run_cmd(f"git rev-list --reverse --first-parent {start_point}..{end_point}")
    if result.returncode == 0:
        return [c[:COMMIT_HASH_LEN] for c in result.stdout.strip().split('\n') if c]
    return []

def get_commit_message(commit):
    """获取提交消息"""
    result = run_cmd(f"git log -1 --format=%B {commit}")
    if result.returncode == 0:
        return result.stdout.strip()
    return ""

def get_latest_commit(branch):
    """获取分支的最新提交"""
    result = run_cmd(f"git rev-parse {branch}")
    if result.returncode == 0:
        return result.stdout.strip()[:COMMIT_HASH_LEN]
    return None

def cherry_pick_commit(commit):
    """cherry-pick 提交（不提交）"""
    result = run_cmd(f"git cherry-pick -n {commit}")
    return result.returncode == 0

def is_commit_exists(commit):
    """检查提交是否存在"""
    result = run_cmd(f"git rev-parse --verify {commit}")
    return result.returncode == 0

def is_ancestor(ancestor, descendant):
    """检查是否为祖先"""
    result = run_cmd(f"git merge-base --is-ancestor {ancestor} {descendant}")
    return result.returncode == 0

def commit_with_message(message):
    """用指定消息提交"""
    result = run_cmd(f"git commit -F -", input=message)
    if result.returncode != 0:
        logger.error(f"git commit 失败，返回码: {result.returncode}, stderr: {result.stderr or 'N/A'}")
        return False
    return result.returncode == 0

def squash_merge_commit(commit):
    """squash merge commit"""
    result = run_cmd(f"git read-tree --reset -u {commit}")
    if result.returncode != 0:        
        logger.error(f"git read-tree 失败，返回码: {result.returncode}, stderr: {result.stderr or 'N/A'}")
        return False
    message = get_commit_message(commit)
    return commit_with_message(message)

def get_current_branch():
    """获取当前分支"""
    result = run_cmd("git branch --show-current")
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def get_merge_base(branch1, branch2):
    """获取两个分支主链的共同祖先"""
    # 不限制主链上的提交
    # result = run_cmd(f"git merge-base {branch1} {branch2}")
    # 只从主链上计算共同祖先
    # shell command: git merge-base $(git rev-list --first-parent -1 {branch1}) {branch2}
    result = run_cmd(f"git rev-list --first-parent -1 {branch1}")
    if result.returncode != 0:
        logger.error(f"git rev-list 失败，返回码: {result.returncode}, stderr: {result.stderr or 'N/A'}")
        return None
    branch1_latest_commit = result.stdout.strip()[:COMMIT_HASH_LEN]
    result = run_cmd(f"git merge-base {branch1_latest_commit} {branch2}")
    if result.returncode == 0:
        return result.stdout.strip()[:COMMIT_HASH_LEN]
    logger.error(f"git merge-base 失败，返回码: {result.returncode}, stderr: {result.stderr or 'N/A'}")
    return None

def get_last_synced_commit(target_branch):
    """从提交消息中获取上次同步的commit"""
    result = run_cmd(f"git log -1 --format=%B {target_branch}")
    if result.returncode != 0:
        return None
    
    msg = result.stdout
    for line in msg.split('\n'):
        parts = line.split()
        if CHERRY_PICK_PREFIX in line:            
            if len(parts) > CHERRY_PICK_PREFIX_LEN:
                return parts[CHERRY_PICK_PREFIX_LEN]
        elif SQUASHED_PREFIX in line:
            if len(parts) > SQUASHED_PREFIX_LEN:
                return parts[SQUASHED_PREFIX_LEN]
    return None

def get_parent_merge_commit(branch) -> list:
    """获取最新提交的父合并提交"""
    result = run_cmd(f"git log -1 --format=%B {branch}")
    if result.returncode != 0:
        return []

    msg = result.stdout
    for line in msg.split('\n'):
        if MERGE_COMMIT_PREFIX in line:
            parts = line.split()
            if len(parts) > MERGE_COMMIT_PREFIX_LEN:
                return parts[MERGE_COMMIT_PREFIX_LEN:]
    return []

def get_new_commits(from_commit, to_branch):
    """获取从from_commit到to_branch的新提交（正向顺序）"""
    result = run_cmd(f"git rev-list --reverse --first-parent {from_commit}..{to_branch}")
    if result.returncode == 0:
        return [c[:COMMIT_HASH_LEN] for c in result.stdout.strip().split('\n') if c]
    return []

def checkout_branch(branch):
    """切换到指定分支"""
    result = run_cmd(f"git checkout {branch}")
    return result.returncode == 0

def pull_branch(remote, branch):
    """拉取远程分支"""
    result = run_cmd(f"git pull {remote} {branch}")    
    logger.info(f"{result.stdout.strip()}")
    logger.info("拉取完成")
    return result.returncode == 0

def is_git_available():
    """检查 git 是否可用"""
    result = run_cmd("git --version")
    logger.info(f"{result.stdout.strip()}")
    return result.returncode == 0

def get_upstream_remote(upstream):
    """获取上游远程"""
    result = run_cmd(f"git remote get-url {upstream}")
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def in_parent_chain(branch, commit):
    """检查是否在父链上"""
    result = run_cmd(f"git merge-base --is-ancestor {commit} {branch}")
    return result.returncode == 0

def is_exists_conflict():
    """检查是否存在冲突"""
    return not is_workdir_clean()

def is_workdir_clean() -> bool:
    """检查工作目录是否干净"""
    """
    代码	描述	说明与示例
    UU	双方修改 (both modified)	最常见的冲突。你和对方修改了同一文件的同一区域，Git 无法自动合并。
    AU	我们添加 (added by us)	在Git“我们”这边是一个“添加”了新文件的操作，而“他们”那边则是“修改”了这个文件。
    UA	他们添加 (added by them)	对方添加了一个文件，但我们这边也修改了它。
    DU	我们删除 (deleted by us)	我们删除了一个文件，但对方对此文件做了修改。
    UD	他们删除 (deleted by them)	对方删除了一个文件，但我们对此文件做了修改。
    """
    result = run_cmd("git status --porcelain")
    if result.returncode != 0:
        logger.error(f"git status --porcelain 失败，返回码: {result.returncode}, stderr: {result.stderr or 'N/A'}")
        return False

    conflicts = [line for line in result.stdout.split('\n') 
             if line.startswith(('UU', 'AU', 'UA', 'DU', 'UD'))]
    if conflicts:
        logger.info(f"工作目录有冲突: {conflicts}")
        return False
    return True