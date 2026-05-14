#!/usr/bin/env python
"""代码审查工具 - 同步上游分支到 Gerrit 审核分支"""

import click
from logger import logger
import config as config_module
import sync as sync_module
import analyze as analyze_module

@click.group()
def cli():
    """代码审查工具 - 同步上游分支到 Gerrit 审核分支"""
    pass

@cli.command()
@click.argument('project')
@click.option('--show-config', is_flag=True, help='显示当前配置')
@click.option('--set-config', is_flag=True, help='交互式修改配置')
@click.option('--reset-config', is_flag=True, help='重置配置')
@click.option('--show-state', is_flag=True, help='显示当前追踪的 commit')
def sync(project, show_config, set_config, reset_config, show_state):
    """同步上游分支到 Gerrit 审核分支"""
    # 处理配置命令
    if reset_config:
        config_module.reset_config(project)
        return
    
    if show_config:
        config_module.show_config(project)
        return
    
    if show_state:
        _show_state(project)
        return
    
    if set_config:
        config_module.set_config(project)
        return
    
    # 如果没有配置，运行向导
    config = config_module.load_config(project)
    if not config:
        logger.info(f"项目 {project} 未配置，运行向导...")
        config = config_module.run_wizard(project)
        if not config:
            return
    
    # 执行同步
    try:
        sync_module.sync_project(config)
    except Exception as e:
        logger.error(f"同步失败: {e}")

def _show_state(project):
    """显示同步状态"""
    config = config_module.load_config(project)
    if not config:
        logger.info(f"项目 {project} 没有配置")
        return
    
    import os
    import git_operations as git
    
    os.chdir(config['repo_path'])
    last_commit = git.get_last_synced_commit(config['target_branch'])
    if last_commit:
        logger.info(f"上次同步的 commit: {last_commit}")
    else:
        logger.info(f"没有找到同步状态")

@cli.command()
@click.argument('commit')
def analyze(commit):
    """分析单个 commit 的类型"""
    analyze_module.analyze_commit(commit)

if __name__ == '__main__':
    cli()