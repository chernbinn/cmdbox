"""配置管理模块"""

import json
from pathlib import Path
from .logger import logger

CONFIG_BASE = Path.home() / ".gerrit_review"
# 开关：是否线性化展开 merge commit
# True: 可配置展开深度
# False: 默认 squash方式 合入 merge commit
LINEARIZE_MERGE_FEATURE = True
DEFAULT_MAX_MERGE_DEPTH = 0

def get_config_dir():
    """获取配置目录"""
    return CONFIG_BASE.resolve()

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

def _get_default_config(project_name):
    """获取默认配置"""
    import os
    return {
        "project_name": project_name,
        "repo_path": os.getcwd(),
        "upstream_remote": "origin",
        "remote_branch": "main",
        "track_branch": "main",
        "target_branch": f"gerrit-main",
        "gerrit_remote": "gerrit",
        "gerrit_branch": f"custom",
        "max_merge_depth": DEFAULT_MAX_MERGE_DEPTH
    }

def _merge_depth_prompt():
    prompt_text = (
            f"max_merge_depth-展开子链 merge commit 的最大深度\n"
            "  -1: 全部线性化展开 merge commit\n"
            "   0: 全部 squash方式 合入 merge commit\n"
            "  其他值: 展开深度超过最大深度时, squash方式 合入 merge commit。"
        )
    return prompt_text

def run_wizard(project_name):
    """配置向导"""
    import click

    logger.info(f"\n向导: 创建新项目 {project_name} 的配置，按Enter键使用默认值")
    logger.info("-" * 40)

    config = _get_default_config(project_name)

    repo_path = click.prompt(f"repo_path-项目根路径，当前默认值:", default=config['repo_path'])
    if not repo_path:
        logger.error("错误: 仓库路径不能为空")
        return None
    config['repo_path'] = repo_path

    config['upstream_remote'] = click.prompt(f"upstream_remote-上游远程仓库，当前默认值", default=config['upstream_remote'])
    config['remote_branch'] = click.prompt(f"remote_branch-上游分支，当前默认值", default=config['remote_branch'])
    config['track_branch'] = click.prompt(f"track_branch-本地追踪分支，当前默认值", default=config['track_branch'])
    config['target_branch'] = click.prompt(f"target_branch-目标分支，当前默认值", default=config['target_branch'])
    config['gerrit_remote'] = click.prompt(f"gerrit_remote-Gerrit-远程仓库，当前默认值", default=config['gerrit_remote'])
    config['gerrit_branch'] = click.prompt(f"gerrit_branch-Gerrit-分支，当前默认值", default=config['gerrit_branch'])
    if LINEARIZE_MERGE_FEATURE:
        prompt_text = _merge_depth_prompt()
        config['max_merge_depth'] = click.prompt(f"{prompt_text}当前默认值", default=config['max_merge_depth'])

    save_config(project_name, config)
    logger.info(f"\n配置已保存到 {get_config_file(project_name)}")
    return config

def show_config(project_name):
    """显示配置"""
    config = load_config(project_name)
    if config:
        logger.info(f"Tip: {_merge_depth_prompt()}")
        logger.info(f"Tip: 项目配置中未配置的项使用默认值，如果需要修改默认值，请使用 codereview config set {project_name} 修改")
        logger.info(f"项目 {project_name} 的当前配置:")
        default_config = _get_default_config(project_name)
        default_tag = "（默认值）"
        config_keys = set(config.keys())
        for key, value in default_config.items():
            logger.info(f"  {key}: {config.get(key, value)}{default_tag if key not in config_keys else ''}")
    else:
        logger.info(f"项目 {project_name} 没有配置")

def set_config(project_name):
    """交互式修改配置"""
    import click

    config = load_config(project_name)
    if not config:
        logger.info(f"项目 {project_name} 没有配置，请先运行向导")
        return    
    show_config(project_name)

    logger.info("\n输入新值（按回车保持当前值）:")
    new_config = config.copy()
    default_config = _get_default_config(project_name)
    for key in default_config.keys():
        value = click.prompt(key, default=config.get(key, default_config[key]))
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

def add_config(project_name):
    """添加新项目配置（交互式向导）"""
    config_file = get_config_file(project_name)
    if config_file.exists():
        logger.info(f"项目 {project_name} 已存在配置，请使用 'codereview config set {project_name}' 修改")
        return None

    return run_wizard(project_name)

def del_config(project_name):
    """删除项目配置"""
    config_file = get_config_file(project_name)
    if config_file.exists():
        config_file.unlink()
        logger.info(f"已删除项目 {project_name} 的配置")
    else:
        logger.info(f"项目 {project_name} 没有配置可删除")

def list_projects():
    """列出所有项目"""
    for json_file in CONFIG_BASE.glob("*.json"):
        if json_file.is_file():          # 确保是文件，而非同名目录
            project_name = json_file.stem  # 自动去除最后一个后缀
            logger.info(project_name)