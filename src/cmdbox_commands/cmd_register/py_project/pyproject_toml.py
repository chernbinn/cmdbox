import shutil
import subprocess
import click
from pydantic import BaseModel, field_validator
from typing import Literal
from pathlib import Path
from .utils import check_command_exists

class ScriptEntry(BaseModel):
    cmd_name: str
    cmd_type: Literal['scripts', 'gui-scripts']
    cmd_entry: str

    @field_validator('cmd_type')
    def validate_cmd_type(cls, v):
        if v not in ['scripts', 'gui-scripts']:
            raise ValueError("cmd_type must be 'scripts' or 'gui-scripts'")
        return v
    
    #@field_validator('cmd_name')
    def validate_cmd_name(cls, v):
        # cmd_name不可以是已经存在的命令。执行“which cmd_name”，如果返回值不是空，则说明已经存在。
        """
        click.echo(f"validate cmd_name '{v}'")
        result = subprocess.run(f'which {v}', shell=True, capture_output=True, text=True, encoding='utf-8')
        if result.stdout.strip():
            raise ValueError(f"cmd_name '{v}' already exists")
        click.echo(f"validate cmd_name '{v}' end")
        return v
        """
        if check_command_exists(v):
        #if shutil.which(v):
            raise ValueError(f"自定义命令 '{v}' already exists")
        return v

    @field_validator('cmd_entry')
    def validate_cmd_entry(cls, v):
        """
        # cmd_entry必须是可执行的入口，比如cmdbox_commands.task_manager.cli:cli
        # 执行“cmd_name --test”，如果返回值不是空，则说明是可执行的。
        result = subprocess.run(f'{self.cmd_name} --test', shell=True, capture_output=True, text=True)
        if not result.stdout.strip():
            raise ValueError(f"cmd_entry '{v}' is not executable")
        """
        return v

    def script_entry(self):
        return f'{self.cmd_name} = "{self.cmd_entry}"'

class PyprojectToml(BaseModel):
    project_name: str
    projec_version: str
    scripts: list[ScriptEntry]
    
    def __python_version(self):
        return subprocess.run(
            f'python -V', 
            shell=True, 
            capture_output=True, 
            text=True).stdout.strip().split(' ')[1]

    def __setuptools_version(self):
        return subprocess.run(
            f'pip show setuptools', 
            shell=True, 
            capture_output=True, 
            text=True).stdout.strip().splitlines()[1].split(' ')[1]
    
    def save_pyprojectToml(self, pyproject_toml: Path):
        with open(pyproject_toml, 'w', encoding='utf-8') as f:
            #print("-------", self.generate())
            f.write(self.generate())

    def __generate_entrys(self, type: Literal['scripts', 'gui-scripts']='scripts') -> str:

        entrys = []
        entrys.append(f'[project.{type}]')

        for command in self.scripts:
            if command.cmd_type == type:
                entrys.append(command.script_entry())

        # 返回为多行的字符串
        if len(entrys) <= 1:
            return ''
        return '\n'.join(entrys)
    
    def generate(self):
        # 自动获取python版本
        python_version = self.__python_version()
        # print(python_version)

        # 使用pip获取setuptools版本
        setuptools_version: str = self.__setuptools_version()

        return f"""
[build-system]
requires = [
    "setuptools>={setuptools_version}", 
]
build-backend = "setuptools.build_meta"

[project]
name = "{self.project_name}"
version = "{self.projec_version}"
dependencies = [
    "click>=8.0"
]
requires-python = ">={python_version}"

[tool.setuptools.packages.find]
where = ["src"]
include = ["{self.project_name}"]
{self.__generate_entrys()}
{self.__generate_entrys('gui-scripts')}
        """
"""
[tool.setuptools.package-data]
"{self.cmd_name}" = ["data/*"]
"""