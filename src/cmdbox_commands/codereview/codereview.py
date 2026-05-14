#!/usr/bin/env python
import click
import subprocess
import os

def run_cmd(cmd, capture_output=True, text=True):
    """运行 git 命令"""
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
    result = run_cmd(f"git commit -m {repr(message)}")
    return result.returncode == 0

def squash_merge_commit(commit):
    """squash merge commit"""
    result = run_cmd(f"git read-tree --reset -u {commit}")
    if result.returncode != 0:
        return False
    message = get_commit_message(commit)
    return commit_with_message(message)

def sync_branch(upstream_branch, last_sync_commit):
    """同步上游分支到当前分支"""
    click.echo(f"开始同步上游分支 {upstream_branch}")
    click.echo(f"上次同步位置: {last_sync_commit}")
    
    # 获取主干上的所有提交
    if last_sync_commit:
        cmd = f"git rev-list --reverse --first-parent {upstream_branch} ^{last_sync_commit}"
    else:
        cmd = f"git rev-list --reverse --first-parent {upstream_branch}"
    
    result = run_cmd(cmd)
    if result.returncode != 0:
        click.echo(f"获取提交列表失败: {result.stderr}", err=True)
        return None
    
    commits = [c for c in result.stdout.strip().split('\n') if c]
    click.echo(f"待处理提交数量: {len(commits)}")
    
    for commit in commits:
        click.echo(f"\n处理提交: {commit}")
        
        parent_count = get_parent_count(commit)
        
        # 1. 普通提交
        if parent_count == 1:
            click.echo(f"普通提交，直接 cherry-pick")
            if cherry_pick_commit(commit):
                message = get_commit_message(commit)
                commit_with_message(message)
                click.echo(f"成功应用提交 {commit}")
            else:
                click.echo(f"cherry-pick 失败，跳过 {commit}", err=True)
            continue
        
        # 2. 处理 merge commit
        if parent_count >= 2:
            p1 = get_first_parent(commit)
            p2 = get_second_parent(commit)
            
            # 2.1 检查是否为空合并
            if is_empty_merge(commit, p1):
                click.echo(f"空合并，跳过: {commit}")
                continue
            
            # 2.2 判断是否有冲突解决
            if has_conflict_resolution(commit, p1, p2):
                click.echo(f"有冲突合并，直接 squash: {commit}")
                if squash_merge_commit(commit):
                    click.echo(f"成功 squash 合并 {commit}")
                else:
                    click.echo(f"squash 失败，跳过 {commit}", err=True)
                continue
            
            # 2.3 无冲突合并：获取子分支提交列表
            subs = get_sub_commits(p1, p2)
            
            # 2.4 检查子分支中是否包含 merge commit
            need_squash = False
            for sub in subs:
                sub_parents = get_parent_count(sub)
                if sub_parents != 1:
                    need_squash = True
                    break
            
            if need_squash:
                click.echo(f"子分支内含有 merge commit，整体 squash: {commit}")
                if squash_merge_commit(commit):
                    click.echo(f"成功 squash 合并 {commit}")
                else:
                    click.echo(f"squash 失败，跳过 {commit}", err=True)
            else:
                click.echo(f"无冲突且子分支线性，逐个 cherry-pick 子提交")
                for sub in subs:
                    click.echo(f"  cherry-pick: {sub}")
                    if cherry_pick_commit(sub):
                        message = get_commit_message(sub)
                        commit_with_message(message)
                        click.echo(f"    成功应用")
                    else:
                        click.echo(f"    cherry-pick 失败，跳过", err=True)
    
    # 返回最新的 upstream commit
    return get_latest_commit(upstream_branch)

@click.group()
def cli():
    """代码审查工具 - 用于同步上游分支并处理 merge commit"""
    pass

@cli.command()
@click.argument('upstream', default='upstream/main')
@click.option('--last-sync', '-l', help='上次同步的 commit ID')
def sync(upstream, last_sync):
    """同步上游分支到当前分支，处理 merge commit"""
    # 检查是否在 git 仓库中
    result = run_cmd("git rev-parse --is-inside-work-tree")
    if result.returncode != 0:
        click.echo("错误：当前目录不是 git 仓库", err=True)
        return
    
    # 获取当前分支
    current_branch = run_cmd("git branch --show-current").stdout.strip()
    click.echo(f"当前分支: {current_branch}")
    
    # 同步分支
    new_last_sync = sync_branch(upstream, last_sync)
    
    if new_last_sync:
        click.echo(f"\n同步完成！")
        click.echo(f"新的同步位置: {new_last_sync}")
        click.echo(f"下次同步时使用: --last-sync {new_last_sync}")

@cli.command()
@click.argument('commit')
def analyze(commit):
    """分析单个 commit 的类型"""
    parent_count = get_parent_count(commit)
    click.echo(f"提交: {commit}")
    click.echo(f"父节点数量: {parent_count}")
    
    if parent_count == 1:
        click.echo("类型: 普通提交")
    elif parent_count >= 2:
        click.echo("类型: Merge commit")
        p1 = get_first_parent(commit)
        p2 = get_second_parent(commit)
        click.echo(f"父节点1: {p1}")
        click.echo(f"父节点2: {p2}")
        
        if is_empty_merge(commit, p1):
            click.echo("状态: 空合并")
        elif has_conflict_resolution(commit, p1, p2):
            click.echo("状态: 有冲突解决")
        else:
            click.echo("状态: 无冲突合并")
            subs = get_sub_commits(p1, p2)
            click.echo(f"子分支提交数量: {len(subs)}")

if __name__ == '__main__':
    cli()