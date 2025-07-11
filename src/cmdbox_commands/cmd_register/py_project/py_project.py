import shutil
import subprocess
import click
from dataclasses import dataclass
from pydantic import BaseModel, field_validator
from cmdbox_commands.cmd_register.py_project.pyproject_toml import ScriptEntry, PyprojectToml
from .utils import check_command_exist


#@dataclass
class Command(BaseModel):
    cmd_name: str
    is_gui: bool
    command: str
    description: str = ""

    def src_file_name(self):
        return f'{self.cmd_name}_{"gui_" if self.is_gui else ""}cli.py'

    @field_validator('cmd_name')
    def validate_command(cls, v):
        if check_command_exist(v):
            raise ValueError(f"cmd_name '{v}' already exists")
        return v

class PyProject:    
    def __init__(self, project_path: str, project_name: str):        
        self.project_name = project_name
        self.project_path: str = project_path
        self.pyproject_toml: PyprojectToml = None

    def init(self, commands: list[Command]):
        self.src_path = (self.project_path/ f'src/{self.project_name}')
        if not self.src_path.exists():
            click.echo(f"create src path '{self.src_path}'")
            self.src_path.mkdir(parents=True)

        click.echo(f"init src files")
        self._gernerate_src(commands)
        """
        self.pyproject_toml = PyprojectToml(
            project_name=self.project_name,
            scripts=[]
        )
        self.pyproject_toml.save_pyprojectToml(self.project_path/ 'pyproject.toml')
        self._install_dev()
        """
        click.echo(f"init pyproject.toml")
        scripts = []
        for command in commands:
            scripts.append(ScriptEntry(
                cmd_name=command.cmd_name,
                cmd_type='gui-scripts' if command.is_gui else 'scripts',
                cmd_entry=f'{self.project_name}.{command.src_file_name()[:-3]}:main'
            ))

        self.pyproject_toml = PyprojectToml(
            project_name=self.project_name,
            scripts=scripts
        )
        click.echo(f"save pyproject.toml")
        self.pyproject_toml.save_pyprojectToml(self.project_path/ 'pyproject.toml')    

    def install(self):
        # 先卸载旧版本
        click.echo(f"uninstall old tools:'{self.project_name}'")
        subprocess.run(f'pipx uninstall {self.project_name}', 
                    shell=True, 
                    encoding='utf-8',
                    capture_output=True, 
                    text=True)
        # 安装新版本
        click.echo(f"install new tools:'{self.project_name}'")
        result = subprocess.run(f'pipx install -f {self.project_path}', 
                    shell=True, 
                    encoding='utf-8',
                    capture_output=True, 
                    text=True)
        if result.returncode != 0:
            raise ValueError(f"install '{self.project_path}' failed")
        else:
            click.echo(f"install '{self.project_path}' success")

    @staticmethod
    def uninstall(project_name: str)->bool:
        # 检查是否存在
        result = subprocess.run(f'pipx runpip {project_name}', shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"project '{project_name}' not exists")
            return False

        result = subprocess.run(f'pipx uninstall {project_name}', shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            #raise ValueError(f"uninstall '{project_name}' failed")
            click.echo(f"uninstall '{project_name}' failed")
            return False
        else:
            click.echo(f"uninstall '{project_name}' success")
        return True

    def clean(self):
        # 删除项目目录
        shutil.rmtree(self.project_path)

    def _gernerate_src(self, commands: list[Command]):
        for command in commands:
            file_name = command.src_file_name()
            (self.src_path/ file_name).write_text(self._file_content(command), encoding='utf-8')
        
    def _install_dev(self):
        # 如果虚拟环境不存在，创建虚拟环境
        virtual_env = self.project_path/ '.venv'
        if not virtual_env.exists():
            subprocess.run(f'python -m venv {virtual_env}', shell=True, capture_output=True, text=True)
        # 激活虚拟环境及安装
        activate_cmd = f'{virtual_env}/Scripts/activate'
        result = subprocess.run(activate_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError(f"activate virtual env '{virtual_env}' failed")

        # 安装开发版本
        click.echo(f'pip install -e --force-reinstall {self.project_path}')
        result = subprocess.run(f'pip install -e --force-reinstall {self.project_path}', shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError(f"install dev '{self.project_path}' failed")
        else:
            click.echo(f"install dev '{self.project_path}' success")
    
    def _file_content(self, command: Command):
        from cmdbox_commands.cmd_register.py_project.generator import generator_src

        return generator_src(command.command, command.description)

