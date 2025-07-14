import shutil
import subprocess
import click
from functools import lru_cache
from typing import Union, Optional
from pydantic import BaseModel, field_validator
from cmdbox_commands.cmd_register.py_project.pyproject_toml import ScriptEntry, PyprojectToml
from cmdbox_commands.cmd_register.config import is_debug
from .utils import child_run, Base32V, check_command_exists

class Command(BaseModel):
    alias: str
    command: str
    is_gui: bool = False
    description: str = ''    

    def src_file_name(self):
        return f'{self.alias}_{"gui_" if self.is_gui else ""}cli.py'

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
                cmd_name=command.alias,
                cmd_type='gui-scripts' if command.is_gui else 'scripts',
                cmd_entry=f'{self.project_name}.{command.src_file_name()[:-3]}:main'
            ))

        self.pyproject_toml = PyprojectToml(
            project_name=self.project_name,
            projec_version=Base32V.encrypt_version('0.1.0', f"cmdr_{self.project_name}"),
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
        """
        result = subprocess.run(f'pipx install -f {self.project_path}', 
                    shell=True, 
                    encoding='utf-8',
                    capture_output=True, 
                    text=True)
        if result.returncode != 0:
            raise ValueError(f"install '{self.project_path}' failed")
        else:
            click.echo(f"install '{self.project_path}' success")
        """
        result = child_run(f'pipx install -f {self.project_path}', 2)
        if result.return_code != 0:
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

    @staticmethod
    def is_installed(alias: str, project_name: str = None) -> Union[bool, Optional[str]]:
        """ 检查自定义命令是否被安装 """
        # pipx runpip cmdbox show -f cmdbox，当project不为None时
        # pipx list,当project为None时
        if not alias:
            raise ValueError(f"is_installed, alias can't be empty or None")
        command = None
        if project_name:
            command = f'pipx runpip {project_name} show -f {project_name}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                return False, None
            if alias:
                if result.stdout and alias in result.stdout:
                    return True, project_name                
            else:
                return True, project_name
            return False, None
        else:
            command = f'pipx list --short'
            result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
            result.check_returncode()
            for line in result.stdout.splitlines():
                project = line.split()[0]
                is_installed, project_name = PyProject.is_installed(alias, project)
                if is_installed:
                    return True, project_name
            
            if check_command_exists(alias):
            # if shutil.which(alias):
                return True, "__sys_system__"
            return False, None

    @staticmethod
    @lru_cache
    def get_project_commands(project_name: str):
        command = f'pipx runpip {project_name} show -f {project_name}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            return []
        commands = []
        if is_debug():
            click.echo(f"get_project_commands-result.stdout: {result.stdout}")
        for line in result.stdout.splitlines():
            if  line.count("Scripts\\") > 0:
                if is_debug():
                    click.echo(f"line: {line}")
                commands.append(line.split("Scripts\\")[1].rsplit('.', 1)[0])
        return commands

    @staticmethod
    def get_installed_projects():
        command = f'pipx list --short'
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        result.check_returncode()
        #click.echo(f"result.stdout: {result.stdout}")
        projects = []
        for project in result.stdout.splitlines():
            _version = project.split()[1]
            _, scrt_name = Base32V.decrypt_version(_version)
            if is_debug():
                click.echo(f"+++++project: {project}")
                click.echo(f"+++++scrt_name: {scrt_name}")
            if not scrt_name:
                continue
            sps = scrt_name.split('_')
            if sps[0] == "cmdr" and sps[1]:
                projects.append(sps[1])
        return projects

    @staticmethod
    def get_actual_command(alias: str):
        command = fr'{alias} --command'
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        if is_debug():
            click.echo(f"get_actual_command-command: {command}")
            click.echo(f"get_actual_command-result.stdout: {result.stdout}")
        if result.returncode != 0:
            return None
        return PyProject._handle_result_out(result.stdout)

    @staticmethod
    def get_project_name(alias: str):
        command = fr'{alias} --project-name'
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        if is_debug():
            click.echo(f"get_project_name-command: {command}")
            click.echo(f"get_project_name-result.stdout: {result.stdout}")
        if result.returncode != 0:
            return None
        return PyProject._handle_result_out(result.stdout)
    
    def _file_content(self, command: Command):
        from cmdbox_commands.cmd_register.py_project.generator import generator_src

        return generator_src(command.command, command.description)

    @staticmethod
    def _handle_result_out(str):
        if str:
            return str.strip()
        return None

