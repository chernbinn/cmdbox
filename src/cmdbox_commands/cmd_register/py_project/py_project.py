"""Python项目管理模块"""

import os
import re
import shutil
import subprocess
import click
from pathlib import Path
from functools import lru_cache
from typing import Union, Optional, Tuple, List
from pydantic import BaseModel, field_validator
from cmdbox_commands.cmd_register.py_project.pyproject_toml import ScriptEntry, PyprojectToml
from cmdbox_commands.cmd_register.config import is_debug
from .utils import child_run, Base32V, check_command_exists

# 项目名称安全模式（仅允许字母、数字、下划线和连字符）
SAFE_PROJECT_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# 排除的项目名称集合（这些项目不会被同步）
EXCLUDED_PROJECTS = frozenset(["cmdbox"])

# 命令别名安全模式（符合Python模块命名规范）
# - 只能包含字母、数字和下划线
# - 不能以数字开头
# - 不能以下划线开头（按Python惯例，下划线开头表示私有）
ALIAS_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def validate_project_name(project_name: str) -> bool:
    """验证项目名称是否安全

    Args:
        project_name: 项目名称

    Returns:
        bool: 项目名称是否只包含安全字符

    Note:
        安全的项目名称只能包含字母、数字、下划线和连字符。
        这符合 pipx 的包名规范，也是防止 shell 注入的基本保障。
    """
    return bool(SAFE_PROJECT_PATTERN.match(project_name))


def validate_alias_name(alias: str) -> bool:
    """验证命令别名是否符合Python模块命名规范

    Args:
        alias: 命令别名

    Returns:
        bool: 别名是否有效

    Note:
        有效的命令别名必须符合Python模块命名规范：
        - 只能包含字母、数字和下划线
        - 不能以数字开头
        - 不能以下划线开头（按Python惯例，下划线开头表示私有）
        - 不能包含连字符（Python模块名不允许）

        这是因为命令别名会被用作生成Python模块文件名和entry point。
    """
    if not alias:
        return False
    return bool(ALIAS_PATTERN.match(alias))


class Command(BaseModel):
    """命令模型"""
    alias: str
    command: str
    is_gui: bool = False
    description: str = ""

    @field_validator('alias')
    def validate_alias(cls, v):
        """验证命令别名是否符合Python模块命名规范"""
        if not validate_alias_name(v):
            raise ValueError(
                f"Invalid command alias '{v}'. "
                f"Alias must comply with Python module naming rules:\n"
                f"  - Can only contain letters, numbers, and underscores\n"
                f"  - Cannot start with a number\n"
                f"  - Cannot start with an underscore\n"
                f"  - Cannot contain hyphens (use underscores instead)"
            )
        return v

    def src_file_name(self) -> str:
        """获取源代码文件名"""
        gui_prefix = "gui_" if self.is_gui else ""
        # 将连字符替换为下划线，因为Python模块名不允许包含连字符
        safe_alias = self.alias.replace("-", "_")
        return f"{safe_alias}_{gui_prefix}cli.py"

class PyProject:
    def __init__(self, project_path: Union[str, Path], project_name: str):
        """初始化项目"""
        if not validate_project_name(project_name):
            raise ValueError(f"Invalid project name '{project_name}'. "
                           f"Project names can only contain letters, numbers, underscores, and hyphens.")
        self.project_name = project_name
        self.project_path: Path = Path(project_path)
        self.pyproject_toml: Optional[PyprojectToml] = None

    def init(self, commands: List[Command]) -> None:
        """初始化项目结构"""
        self.src_path = self.project_path / f"src/{self.project_name}"
        if not self.src_path.exists():
            click.echo(f"create src path '{self.src_path}'")
            self.src_path.mkdir(parents=True)

        click.echo("init src files")
        self._generate_src(commands)

        click.echo("init pyproject.toml")
        scripts = []
        for command in commands:
            scripts.append(ScriptEntry(
                cmd_name=command.alias,
                cmd_type="scripts",
                cmd_entry=f"{self.project_name}.{command.src_file_name()[:-3]}:main"
            ))

        from cmdbox.cmdbox import _version
        dot_count = _version().count(".")
        if dot_count == 3:
            base_version = _version().rsplit(".", 1)[0]
        else:
            base_version = _version()
        click.echo(f"base_version: {base_version}")
        self.pyproject_toml = PyprojectToml(
            project_name=self.project_name,
            projec_version=Base32V.encrypt_version(base_version, f"cmdr_{self.project_name}"),
            scripts=scripts
        )
        click.echo("save pyproject.toml")
        self.pyproject_toml.save_pyprojectToml(self.project_path / "pyproject.toml")

    def install(self) -> None:
        """安装项目"""
        if not validate_project_name(self.project_name):
            raise ValueError(f"Invalid project name '{self.project_name}'")

        click.echo(f"uninstall old tools:'{self.project_name}'")
        subprocess.run(["pipx", "uninstall", self.project_name])

        click.echo(f"install new tools:'{self.project_name}'")
        result = child_run(f"pipx install -f {self.project_path}", 2)
        if result.returncode != 0:
            raise ValueError(f"install '{self.project_path}' failed")
        click.echo(f"install '{self.project_path}' success")

    @staticmethod
    def uninstall(project_name: str) -> bool:
        """卸载项目"""
        if not validate_project_name(project_name):
            click.echo(f"Invalid project name '{project_name}'")
            return False

        result = child_run(f"pipx runpip {project_name} show -f {project_name}")
        if result.returncode != 0:
            click.echo(f"project '{project_name}' not exists")
            return True

        result = child_run(f"pipx uninstall {project_name}", 1)
        if result.returncode != 0:
            click.echo(f"uninstall '{project_name}' failed")
            return False
        click.echo(f"uninstall '{project_name}' success")
        return True

    def clean(self) -> None:
        """清理项目目录"""
        try:
            if self.project_path.exists():
                shutil.rmtree(self.project_path)
        except Exception:
            pass

    @staticmethod
    def clean_by_path(path: Union[str, Path]) -> None:
        """根据路径清理项目"""
        try:
            if Path(path).exists():
                shutil.rmtree(path)
        except Exception:
            pass

    def _generate_src(self, commands: List[Command]) -> None:
        """生成源代码文件"""
        for command in commands:
            file_name = command.src_file_name()
            (self.src_path / file_name).write_text(self._file_content(command), encoding="utf-8")

    @staticmethod
    def is_installed(alias: str, project_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """检查自定义命令是否被安装"""
        if not alias:
            raise ValueError("is_installed, alias cannot be empty or None")

        if project_name:
            if not validate_project_name(project_name):
                return False, None
            command = f"pipx runpip {project_name} show -f {project_name}"
            result = child_run(command)
            if result.returncode != 0:
                return False, None
            if result.stdout and alias in result.stdout:
                return True, project_name
            return False, None
        else:
            command = "pipx list --short"
            result = child_run(command)
            if result.returncode != 0:
                click.echo(f"is_installed, command '{command}' failed\n{result.stderr}")
                raise ValueError(f"is_installed, command '{command}' failed")
            for line in result.stdout.splitlines():
                project = line.split()[0]
                if project in EXCLUDED_PROJECTS:
                    continue
                is_installed, installed_project = PyProject.is_installed(alias, project)
                if is_installed:
                    return True, installed_project

            if check_command_exists(alias):
                return True, "__sys_system__"
            return False, None

    @staticmethod
    @lru_cache
    def get_project_commands(project_name: str) -> List[str]:
        """获取项目中的所有命令"""
        if not validate_project_name(project_name):
            return []
        command = f"pipx runpip {project_name} show -f {project_name}"
        result = child_run(command)
        if result.returncode != 0:
            return []
        commands: List[str] = []
        if is_debug():
            click.echo(f"get_project_commands-result.stdout: {result.stdout}")

        scripts_dir = f"Scripts{os.sep}" if os.name == "nt" else "bin"
        for line in result.stdout.splitlines():
            if scripts_dir in line:
                if is_debug():
                    click.echo(f"line: {line}")
                commands.append(line.split(scripts_dir)[1].rsplit(".", 1)[0])
        return commands

    @staticmethod
    def get_installed_projects() -> List[str]:
        """获取所有已安装的项目"""
        command = "pipx list --short"
        result = child_run(command)
        if result.returncode != 0:
            click.echo(f"get_installed_projects, command '{command}' failed\n{result.stderr}")
            raise ValueError(f"get_installed_projects, command '{command}' failed")
        if is_debug():
            click.echo(f"get_installed_projects-result.stdout:\n{result.stdout}")
        projects: List[str] = []
        for project in result.stdout.splitlines():
            proj_version = project.split()[1]
            _, scrt_name = Base32V.decrypt_version(proj_version)
            if is_debug():
                click.echo(f"+++++project: {project}")
                click.echo(f"+++++scrt_name: {scrt_name}")
            if not scrt_name:
                continue
            sps = scrt_name.split("_")
            if len(sps) >= 2 and sps[0] == "cmdr" and sps[1]:
                projects.append(sps[1])
        return projects

    @staticmethod
    def get_actual_command(alias: str) -> Optional[str]:
        """获取实际命令"""
        command = fr"{alias} --icommand"
        result = child_run(command, 2)
        if is_debug():
            click.echo(f"get_actual_command-command: {command}")
            click.echo(f"get_actual_command-result.stdout: \n{result.stdout}")
            click.echo(f"get_actual_command-result.stderr: \n{result.stderr}")
        if result.returncode != 0:
            return None
        return PyProject._handle_result_out(f"{result.stdout}\n{result.stderr}", "ActCommand:")

    @staticmethod
    def get_project_name(alias: str) -> Optional[str]:
        """获取项目名称"""
        command = fr"{alias} --oproject-name"
        result = child_run(command, 2)
        if is_debug():
            click.echo(f"get_project_name-command: {command}")
            click.echo(f"get_project_name-result.stdout: \n{result.stdout}")
            click.echo(f"get_project_name-result.stderr: \n{result.stderr}")
        if result.returncode != 0:
            return None
        return PyProject._handle_result_out(f"{result.stdout}\n{result.stderr}", "PackageName:")

    def _file_content(self, command: Command) -> str:
        """生成命令源代码内容"""
        from cmdbox_commands.cmd_register.py_project.generator import generator_src
        return generator_src(command.command, command.description, command.is_gui)

    @staticmethod
    def _handle_result_out(string: str, key: str) -> Optional[str]:
        """处理命令输出结果"""
        if string and key in string:
            return string.split(key)[1].strip()
        return None
