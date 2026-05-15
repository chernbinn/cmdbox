"""代码审查工具 - 同步上游分支到 Gerrit 审核分支"""

import click
from .logger import logger
from .config import (
    load_config,
    show_config as config_show,
    set_config as config_set,
    reset_config as config_reset,
    list_projects as config_list_projects,
    run_wizard,
)
from .sync import sync_project
from .analyze import analyze_commit
from . import git_operations as git_ops

@click.group()
def cli():
    """代码审查工具 - 同步上游分支到 Gerrit 审核分支"""
    pass

@cli.group('config')
def config_group():
    """配置管理命令"""
    pass

@config_group.command('show')
@click.argument('project')
def config_show_cmd(project):
    """显示项目配置"""
    config_show(project)

@config_group.command('set')
@click.argument('project')
def config_set_cmd(project):
    """设置项目配置"""
    config_set(project)

@config_group.command('reset')
@click.argument('project')
def config_reset_cmd(project):
    """重置项目配置"""
    config_reset(project)

@config_group.command('show-state')
@click.argument('project')
def config_show_state_cmd(project):
    """显示项目同步状态"""
    _show_state(project)

def _show_state(project_name):
    """显示同步状态"""
    import os
    
    project_config = load_config(project_name)
    if not project_config:
        logger.info(f"项目 {project_name} 没有配置")
        return
    
    os.chdir(project_config['repo_path'])
    last_synced = git_ops.get_last_synced_commit(project_config['target_branch'])
    if last_synced:
        logger.info(f"上次同步的 commit: {last_synced}")
    else:
        logger.info(f"没有找到同步状态")

@config_group.command('list')
def config_list_cmd():
    """显示所有项目"""
    config_list_projects()

@cli.command('sync')
@click.argument('project')
def sync_cmd(project):
    """同步上游分支到 Gerrit 审核分支"""
    # 如果没有配置，运行向导
    project_config = load_config(project)
    if not project_config:
        logger.info(f"项目 {project} 未配置，运行向导...")
        project_config = run_wizard(project)
        if not project_config:
            return
    
    # 执行同步
    try:
        sync_project(project_config)
    except Exception as e:
        logger.error(f"同步失败: {e}")

@cli.command('analyze')
@click.argument('commit_hash')
def analyze_cmd(commit_hash):
    """分析单个 commit 的类型"""
    analyze_commit(commit_hash)

if __name__ == '__main__':
    cli()