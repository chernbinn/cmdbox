"""配置管理模块"""

import json
from pathlib import Path
from .logger import logger

CONFIG_BASE = Path.home() / ".gerrit_review"

def get_config_file(project_name):
    """获取配置文件路径"""
    CONFIG_BASE.mkdir(parents=True, exist_ok=True)
    return CONFIG_BASE / f"{project_name}.json"

def load_config(project_name):
    """加载项目配置"""
    config_file = get_config_file(project_name)
    if not config_file.exists():
        return None
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(project_name, config):
    """保存项目配置"""
    config_file = get_config_file(project_name)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_default_config(project_name):
    """获取默认配置"""
    import os
    return {
        "repo_path": os.getcwd(),
        "upstream_remote": "origin",
        "remote_branch": "main",
        "track_branch": "main",
        "target_branch": f"gerrit-main",
        "gerrit_remote": "gerrit",
        "gerrit_branch": f"gerrit-main"
    }

def run_wizard(project_name):
    """配置向导"""
    import click
    
    logger.info(f"\n向导: 创建新项目配置")
    logger.info("-" * 40)
    
    config = get_default_config(project_name)
    
    repo_path = click.prompt(f"项目根路径", default=config['repo_path'])
    if not repo_path:
        logger.error("错误: 仓库路径不能为空")
        return None
    config['repo_path'] = repo_path
    
    config['upstream_remote'] = click.prompt(f"上游远程仓库", default=config['upstream_remote'])
    config['remote_branch'] = click.prompt(f"上游分支", default=config['remote_branch'])
    config['track_branch'] = click.prompt(f"本地追踪分支", default=config['track_branch'])
    config['target_branch'] = click.prompt(f"目标分支", default=config['target_branch'])
    config['gerrit_remote'] = click.prompt(f"Gerrit远程仓库", default=config['gerrit_remote'])
    config['gerrit_branch'] = click.prompt(f"Gerrit分支", default=config['gerrit_branch'])
    
    save_config(project_name, config)
    logger.info(f"\n配置已保存到 {get_config_file(project_name)}")
    return config

def show_config(project_name):
    """显示配置"""
    config = load_config(project_name)
    if config:
        logger.info(f"项目 {project_name} 的配置:")
        for key, value in config.items():
            logger.info(f"  {key}: {value}")
    else:
        logger.info(f"项目 {project_name} 没有配置")

def set_config(project_name):
    """交互式修改配置"""
    import click
    
    config = load_config(project_name)
    if not config:
        logger.info(f"项目 {project_name} 没有配置，请先运行向导")
        return
    
    logger.info(f"当前配置:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    logger.info("\n输入新值（按回车保持当前值）:")
    new_config = config.copy()
    for key in ['repo_path', 'upstream_remote', 'remote_branch', 'track_branch', 'target_branch', 'gerrit_remote', 'gerrit_branch']:
        value = click.prompt(key, default=config[key])
        if value:
            new_config[key] = value
    
    save_config(project_name, new_config)
    logger.info(f"配置已更新")

def reset_config(project_name):
    """重置配置"""
    config_file = get_config_file(project_name)
    if config_file.exists():
        config_file.unlink()
        logger.info(f"已重置项目 {project_name} 的配置")
    else:
        logger.info(f"项目 {project_name} 没有配置可重置")

def list_projects():
    """列出所有项目"""
    for json_file in CONFIG_BASE.glob("*.json"):
        if json_file.is_file():          # 确保是文件，而非同名目录
            project_name = json_file.stem  # 自动去除最后一个后缀
            logger.info(project_name)