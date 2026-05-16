"""命令注册模块"""

import click
import shutil
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any, List
from toml import load, dump
from cmdbox_commands.cmd_register.py_project.utils import check_command_exists, safe_join_path
from cmdbox_commands.cmd_register.py_project.py_project import PyProject, Command
from cmdbox_commands.cmd_register.config import is_debug

# 默认项目名称
DEFAULT_PROJECT_NAME = "default"
# 空字符串占位符
NONE_PLACEHOLDER = "None"

class AliasCMD(Command):
    """命令别名模型"""

    def __init__(self, alias: str,
            command: str,
            is_gui: bool = False,
            description: str = "",
            project_name: str = DEFAULT_PROJECT_NAME):
        """初始化命令别名"""
        super().__init__(
            alias=alias,
            command=command,
            is_gui=is_gui,
            description=description
        )
        self.project_name = project_name.lower()

    def __eq__(self, value: object, /) -> bool:
        """比较两个 AliasCMD 是否相等"""
        if not isinstance(value, AliasCMD):
            return False
        return all([
            value.alias == self.alias,
            value.command == self.command,
            value.project_name == self.project_name
        ])

class CmdRegister:
    """命令注册器"""

    def __init__(self, cmd_register_toml: Path):
        """初始化命令注册器"""
        self.cmd_register: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.cmd_register_toml = cmd_register_toml
        if self.cmd_register_toml.exists():
            try:
                self._load()
            except Exception as e:
                click.echo(f"加载配置文件失败: {e}")

                if "get_empty_table" not in str(e):
                    click.echo(f"加载配置文件失败: {e}")
                    raise e
                self.cmd_register = defaultdict(dict)

    def _update_project(self, project_name: str) -> bool:
        """更新项目配置"""
        if not project_name or project_name == NONE_PLACEHOLDER:
            click.echo(f"项目名称不能为空")
            return False

        commands = []
        try:
            for alias, cmd in self.cmd_register.items():
                if cmd["project_name"] != project_name:
                    continue
                commands.append(
                    Command(
                        alias=alias,
                        command=cmd["command"],
                        is_gui=cmd["is_gui"],
                        description=cmd["description"]
                    )
                )
            if not commands:
                PyProject.uninstall(project_name)
                PyProject.clean_by_path(self.cmd_register_toml.parent / project_name)
                return True
            project = PyProject(
                project_path=self.cmd_register_toml.parent / project_name,
                project_name=project_name
            )

            project.init(commands)
            project.install()
            return True
        except Exception as e:
            click.echo(f"注册命令失败: {e}")
            if is_debug():
                import traceback
                traceback.print_exc()
            return False

    def register(self, alias: str, command: str, is_gui: bool = False,
                description: str = "", project_name: str = DEFAULT_PROJECT_NAME,
                save_temp: bool = False, force_install: bool = False) -> bool:
        """注册自定义命令"""

        alias_cmd = AliasCMD(alias, command, is_gui, description, project_name)
        if not self._pre_check_register(alias_cmd) and not force_install:
            return False
        if force_install:
            click.echo(f"Warning: force install alias \"{alias_cmd.alias}\"")

        self.cmd_register[alias] = {
            "project_name": project_name,
            "command": command,
            "is_gui": is_gui,
            "description": description
        }
        self._clear_cache()
        res = False
        if self._update_project(project_name):
            self._save()
            res = True

        temp_path = safe_join_path(self.cmd_register_toml.parent, project_name)
        if not save_temp and temp_path.exists():
            shutil.rmtree(temp_path)

        return res

    def remove(self, alias: Optional[str] = None, project_name: Optional[str] = None) -> bool:
        """删除自定义命令"""
        if not alias and not project_name:
            raise ValueError("alias or project_name must be specified")

        res = False
        if not alias and project_name:
            return self._remove_project(project_name)

        if alias not in self.cmd_register:
            if not check_command_exists(alias):
                click.echo(f'Alias "{alias}" does not exist {f"in {project_name}" if project_name else ""}')
                return True
            _, installed_project_name = PyProject.is_installed(alias)
            if not installed_project_name:
                click.echo(f"Alias \"{alias}\" is not alias command, cannot be removed")
                return True

            if not project_name and project_name != installed_project_name:
                click.echo(f"Alias \"{alias}\" is installed in project \"{installed_project_name}\", cannot be removed")
                return False
            return self._update_project(installed_project_name)

        if project_name:
            if self._get_project_by_alias(alias) != project_name:
                click.echo(f"Alias \"{alias}\" does not exist in {project_name}")
                return False
        else:
            project_name = self._get_project_by_alias(alias)
            if not project_name:
                click.echo(f"Alias \"{alias}\" does not exist in any project")
                return False
        self.cmd_register.pop(alias, None)
        self._clear_cache()
        if self._check_exist(project_name):
            res = self._update_project(project_name)
        else:
            res = PyProject.uninstall(project_name)
            PyProject.clean_by_path(safe_join_path(self.cmd_register_toml.parent, project_name))

        if res:
            self._save()
        return res

    def list(self, show_project_name: Optional[str] = None) -> None:
        """列出所有自定义命令"""

        # 按照project_name为一组显示
        project_name_list: List[str] = []
        real_projects = PyProject.get_installed_projects()
        if not real_projects and not self.cmd_register:
            click.echo("No project installed")
            return
        if show_project_name:
            if not self._check_exist(show_project_name) and show_project_name not in real_projects:
                click.echo(f"Project \"{show_project_name}\" does not exist")
                return
            project_name_list = [show_project_name]
            real_projects = [show_project_name] if show_project_name in real_projects else []
        else:
            project_name_list = self._get_projects()
            project_name_list = list(set(project_name_list + real_projects))

        only_conf_projects: set = set()
        only_conf_alias: Dict[str, List[str]] = defaultdict(list)
        only_installed_alias: Dict[str, List[str]] = defaultdict(list)
        for project_name in project_name_list:
            real_installed: List[str] = []
            if project_name in real_projects:
                click.echo(f"命令组: {project_name}")
                if self._check_exist(project_name):
                    real_projects.remove(project_name)
                real_installed = PyProject.get_project_commands(project_name)
                click.echo("已安装命令: ")
            else:
                only_conf_projects.add(project_name)

            for alias in set(self.cmd_register.keys()) | set(real_installed):
                if real_installed and self._check_installed_by_installedlist(alias, real_installed):
                    command = None
                    if self._check_configured(alias):
                        real_installed.remove(alias)
                        command = self.cmd_register[alias]["command"]
                    else:
                        command = PyProject.get_actual_command(alias)
                    cmd_suffix = f": {command}" if command else ""
                    click.echo(f"  {alias}{cmd_suffix}")
                elif alias in self.cmd_register and self.cmd_register[alias]["project_name"] == project_name:
                    only_conf_alias[project_name].append(alias)
            if real_installed:
                only_installed_alias[project_name] = real_installed

        exist_diff = any([
            len(only_installed_alias) > 0 or len(real_projects) > 0,
            len(only_conf_projects) > 0 or len(only_conf_alias) > 0
        ])
        if exist_diff:
            if real_projects or only_installed_alias:
                click.echo("\nOnly installed - installed but not configured")
            if real_projects:
                click.echo(f"  Project:{real_projects}")
            if only_installed_alias:
                for project, alias_list in only_installed_alias.items():
                    click.echo(f"  Project-alias:{project} - {alias_list}")

            if only_conf_projects or only_conf_alias:
                click.echo("\nOnly configured - configured but not installed")
            if only_conf_projects:
                click.echo(f"  Project:{only_conf_projects}")
            if only_conf_alias:
                for project, alias_list in only_conf_alias.items():
                    click.echo(f"  Project-alias:{project} - {alias_list}")
            click.echo()
        if exist_diff:
            click.echo("运行 \"cmdr sync --help\" 了解同步配置、安装的命令")

    def show(self, project_name: Optional[str] = None, alias: Optional[str] = None) -> None:
        """显示指定命令组或命令的详细信息"""
        if not project_name and not alias:
            for _alias in self.cmd_register.keys():
                self._print_cmd_register(self.cmd_register[_alias]["project_name"], _alias)
            return

        if project_name:
            try:
                if not self._check_exist(project_name):
                    raise ValueError(f"Project \"{project_name}\" does not exist")
                for _alias in self.cmd_register.keys():
                    if self.cmd_register[_alias]["project_name"] == project_name:
                        self._print_cmd_register(project_name, _alias)
            except ValueError as e:
                click.echo(f"显示命令组{project_name}详细信息失败: {str(e)}")
                if is_debug():
                    import traceback
                    traceback.print_exc()
                return
        if alias:
            try:
                project_name = self._get_project_by_alias(alias)
                if not project_name:
                    raise ValueError(f"命令\"{alias}\"未配置")
                self._print_cmd_register(project_name, alias)
            except ValueError as e:
                click.echo(f"显示自定义命令{alias}详细信息失败: {str(e)}")
                if is_debug():
                    import traceback
                    traceback.print_exc()
                return

    def sync(self, strategy: str, project_name: Optional[str] = None) -> None:
        """同步配置的自定义命令和安装的自定义命令"""
        if strategy == "installed":
            self._sync_installed(project_name)
        elif strategy == "configure":
            self._sync_configure(project_name)
        elif strategy == "mix":
            self._sync_mix(project_name)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _pre_check_register(self, alias_cmd: AliasCMD) -> bool:
        """执行安装自定义命令前的检查"""
        b_equal = False
        if alias_cmd.alias in self.cmd_register:
            old_alias_cmd = AliasCMD(
                    alias_cmd.alias,
                    self.cmd_register[alias_cmd.alias]["command"],
                    self.cmd_register[alias_cmd.alias]["is_gui"],
                    self.cmd_register[alias_cmd.alias]["description"],
                    self.cmd_register[alias_cmd.alias]["project_name"]
                )
            if alias_cmd != old_alias_cmd:
                click.echo(f"Alias \"{alias_cmd.alias}\" already configured")
                alias_info = self.cmd_register[alias_cmd.alias]
                click.echo("\nConfigured info:")
                click.echo(f"   project_name: {alias_info['project_name']}")
                click.echo(f"   command: {alias_info['command']}")
                click.echo(f"   description: {alias_info['description']}\n")

                return False
            b_equal = True
        b_installed = check_command_exists(alias_cmd.alias)

        installed_project = None
        if b_installed:
            installed_project = self._get_project_by_alias(alias_cmd.alias)
        if b_installed and not installed_project:
            raise ValueError(f"Alias \"{alias_cmd.alias}\" exist in non-alias commands, cannot be registered")
        if b_installed:
            actual_comman = PyProject.get_actual_command(alias_cmd.alias)

            if b_equal and installed_project == alias_cmd.project_name and actual_comman == alias_cmd.command:
                click.echo(f"The same alias \"{alias_cmd.alias}\" already installed")
                return False

            if actual_comman == alias_cmd.command and installed_project == alias_cmd.project_name:
                click.echo(f"The same alias \"{alias_cmd.alias}\" already installed")
                self._add_miss_configure(alias_cmd.alias, installed_project, actual_comman,
                        alias_cmd.is_gui, alias_cmd.description)
            else:
                click.echo(f"The same alias \"{alias_cmd.alias}\" already installed, but configure is not equal")
                click.echo(f"\nInstalled info")
                click.echo(f"   installed_project: {installed_project}")
                click.echo(f"   command: {actual_comman}\n")
                self._add_miss_configure(alias_cmd.alias, installed_project, actual_comman)

            self._save()
            return False
        return True

    def _remove_project(self, project_name: str) -> bool:
        """删除整个项目"""
        if not self._check_exist(project_name):
            b_installed, _ = PyProject.is_installed(None, project_name)
            if not b_installed:
                click.echo(f"project {project_name} not exist")
                return True

        if click.confirm(f"确定删除整个组 \"{project_name}\"的命令吗？"):
            res = PyProject.uninstall(project_name)
            if res:
                self._del_project(project_name)
                self._save()
            PyProject.clean_by_path(safe_join_path(self.cmd_register_toml.parent, project_name))
            return res
        click.echo("取消删除")
        return False

    def _get_project_by_alias(self, alias: str) -> Optional[str]:
        """根据别名获取项目名称"""
        if not alias:
            raise ValueError("alias must be specified")
        if alias in self.cmd_register:
            return self.cmd_register[alias]["project_name"]
        return None

    def _check_installed_by_installedlist(self, alias: str, installed: List[str]) -> bool:
        """检查别名是否在已安装列表中"""
        if not alias:
            raise ValueError("alias must be specified")
        if not installed:
            raise ValueError("installed must be specified")

        return alias in installed

    def _check_configured(self, command: str) -> bool:
        """检查命令是否已配置"""
        if not command:
            raise ValueError("command must be specified")
        install_alias = command.rsplit(".", 1)[0]

        return install_alias in self.cmd_register

    @lru_cache
    def _check_exist(self, project_name: str) -> bool:
        """检查项目是否存在"""
        if not project_name:
            raise ValueError("project_name must be specified")
        project_name_list = sorted(set([cmd["project_name"] for cmd in self.cmd_register.values()]))
        return project_name in project_name_list

    @lru_cache
    def _get_projects(self) -> List[str]:
        """获取所有项目名称"""
        return sorted(set([cmd["project_name"] for cmd in self.cmd_register.values()]))

    def _clear_cache(self) -> None:
        """清除缓存，在配置变更后调用"""
        self._check_exist.cache_clear()
        self._get_projects.cache_clear()

    def _del_project(self, project_name: str) -> None:
        """删除项目中的所有别名"""
        to_delete = [
            alias for alias, cmd in self.cmd_register.items()
            if cmd.get("project_name") == project_name
        ]
        for alias in to_delete:
            del self.cmd_register[alias]
        self._clear_cache()

    def _save(self) -> None:
        """保存配置到文件"""
        with open(self.cmd_register_toml, "w", encoding="utf-8") as f:
            dump(self.cmd_register, f)

    def _load(self) -> None:
        """从文件加载配置"""
        with open(self.cmd_register_toml, "r", encoding="utf-8") as f:
            self.cmd_register = load(f)
        self._clear_cache()

    def _sync_installed(self, project_name: Optional[str] = None) -> None:
        """同步已安装的自定义命令"""
        if project_name:
            self._sync_installed_project(project_name)
        else:
            for installed_project in PyProject.get_installed_projects():
                self._sync_installed_project(installed_project)

    def _sync_installed_project(self, project_name: str) -> None:
        """同步已安装项目的自定义命令"""
        installed_commands = PyProject.get_project_commands(project_name)
        for alias in installed_commands:
            if self._check_configured(alias):
                continue
            self._add_miss_configure(alias, project_name, PyProject.get_actual_command(alias))
        self._save()

    def _sync_configure(self, project_name: Optional[str] = None) -> None:
        """同步配置的自定义命令"""
        if project_name:
            self._sync_configure_project(project_name)
        else:
            for configured_project in self._get_projects():
                self._sync_configure_project(configured_project)

    def _sync_configure_project(self, project_name: str) -> None:
        """同步配置项目的自定义命令"""
        for alias in self.cmd_register:
            if self._check_installed(alias):
                continue
            else:
                b_installed, _ = PyProject.is_installed(alias, project_name)
                if not b_installed:
                    break

        if not self._update_project(project_name):
            click.echo(f"Sync project \"{project_name}\" failed")
            raise ValueError(f"Sync project \"{project_name}\" failed")

    def _check_installed(self, alias: str) -> bool:
        """检查自定义命令是否已安装"""
        return bool(self._get_project_by_alias(alias) or PyProject.is_installed(alias)[0])

    def _check_non_alias_installed(self, alias: str) -> bool:
        """检查自定义命令是否为系统命令"""
        return check_command_exists(alias) and not self._check_installed(alias)

    def _sync_mix(self, project_name: Optional[str] = None) -> None:
        """同步配置和已安装的自定义命令"""
        if project_name:
            self._sync_mix_project(project_name)
        else:
            projects = set(self._get_projects() + PyProject.get_installed_projects())
            for sync_project in projects:
                self._sync_mix_project(sync_project)

    def _sync_mix_project(self, project_name: str) -> None:
        """同步配置项目和已安装项目的自定义命令"""
        self._sync_installed_project(project_name)
        self._sync_configure_project(project_name)

    def _add_miss_configure(self, alias: str, project_name: str, command: str,
                is_gui: bool = False, description: str = "") -> None:
        """添加缺失的配置"""
        self.cmd_register[alias] = {
            "project_name": project_name,
            "command": command,
            "is_gui": is_gui,
            "description": description
        }
        self._clear_cache()

    def _print_cmd_register(self, project_name: str, alias: str) -> None:
        """打印自定义命令的详细信息"""
        if not project_name or not alias:
            return
        click.echo(f"命令组: {project_name}")
        click.echo(f"命令别名: {alias}")
        click.echo(f"命令: {self.cmd_register[alias]['command']}")
        click.echo(f"是否为GUI命令: {self.cmd_register[alias]['is_gui']}")
        click.echo(f"描述: {self.cmd_register[alias]['description']}")
        click.echo("")
        