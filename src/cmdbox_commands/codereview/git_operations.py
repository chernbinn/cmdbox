"""Git 操作模块"""

import subprocess
from .logger import logger

def run_cmd(cmd, capture_output=True, text=True):
    """运行命令"""
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=text)
    return result

def get_parent_count(commit):
    """获取提交的父节点数量"""
    result = run_cmd(f"git rev-list --parents -n 1 {commit}")
    if result.returncode != 0:
        return 0
    output = result.stdout.strip()
    parts = output.split()
    return len(parts) - 1

def get_first_parent(commit):
    """获取第一个父节点"""
    result = run_cmd(f"git rev-parse {commit}^1")
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def get_second_parent(commit):
    """获取第二个父节点"""
    result = run_cmd(f"git rev-parse {commit}^2")
    if result.returncode == 0:
        return result.stdout.strip()
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

def get_sub_commits(parent1, parent2):
    """获取子分支提交列表（正向顺序）"""
    result = run_cmd(f"git rev-list --reverse {parent1}..{parent2}")
    if result.returncode == 0:
        return [c for c in result.stdout.strip().split('\n') if c]
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
        return result.stdout.strip()
    return None

def cherry_pick_commit(commit):
    """cherry-pick 提交（不提交）"""
    result = run_cmd(f"git cherry-pick -n {commit}")
    return result.returncode == 0

def commit_with_message(message):
    """用指定消息提交"""
    result = run_cmd(f"git commit -F -", input=message)
    return result.returncode == 0

def squash_merge_commit(commit):
    """squash merge commit"""
    result = run_cmd(f"git read-tree --reset -u {commit}")
    if result.returncode != 0:
        return False
    message = get_commit_message(commit)
    return commit_with_message(message)

def get_current_branch():
    """获取当前分支"""
    result = run_cmd("git branch --show-current")
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def is_workdir_clean():
    """检查工作目录是否干净"""
    result = run_cmd("git status --porcelain")
    return result.returncode == 0 and result.stdout.strip() == ""

def get_merge_base(branch1, branch2):
    """获取两个分支的共同祖先"""
    result = run_cmd(f"git merge-base {branch1} {branch2}")
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def get_last_synced_commit(target_branch):
    """从提交消息中获取上次同步的commit"""
    result = run_cmd(f"git log -1 --format=%B {target_branch}")
    if result.returncode != 0:
        return None
    
    msg = result.stdout
    for line in msg.split('\n'):
        if "cherry picked from commit" in line:
            parts = line.split()
            if len(parts) >= 5:
                return parts[4]
    return None

def get_new_commits(from_commit, to_branch):
    """获取从from_commit到to_branch的新提交（正向顺序）"""
    result = run_cmd(f"git rev-list --reverse --first-parent {from_commit}..{to_branch}")
    if result.returncode == 0:
        return [c for c in result.stdout.strip().split('\n') if c]
    return []

def checkout_branch(branch):
    """切换到指定分支"""
    result = run_cmd(f"git checkout {branch}")
    return result.returncode == 0

def pull_branch(remote, branch):
    """拉取远程分支"""
    result = run_cmd(f"git pull {remote} {branch}")
    return result.returncode == 0

def is_git_available():
    """检查 git 是否可用"""
    result = run_cmd("git --version")
    return result.returncode == 0