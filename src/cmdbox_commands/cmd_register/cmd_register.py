
import click
from pathlib import Path
from toml import load, dump
from cmdbox_commands.cmd_register.py_project.py_project import PyProject, Command
from cmdbox_commands.cmd_register.config import is_debug

class CmdResiter:
    def __init__(self, cmd_register_toml: Path):
        self.cmd_register = {}
        self.cmd_register_toml = cmd_register_toml
        if self.cmd_register_toml.exists():
            try:
                self._load()
            except Exception as e:
                click.echo(f"load cmd_register_toml failed: {e}")

                if not "get_empty_table" in str(e):
                    click.echo(f"load cmd_register_toml failed: {e}")
                    raise e
                self.cmd_register = {}

    def _update_project(self, project_name: str) -> bool:
        commands = []
        try:
            for alias, cmd in self.cmd_register.items():
                if cmd['project_name'] != project_name:
                    continue
                commands.append(
                    Command(
                        cmd_name = alias,
                        command = cmd['command'],
                        is_gui = cmd['is_gui'],
                        description = cmd['description']
                    )
                )
            project = PyProject(
                project_path = self.cmd_register_toml.parent / project_name,
                project_name = project_name
            )
        
            project.init(commands)
            project.install()
            # 提示是否删除临时项目
            if click.confirm(f"是否删除临时目录 '{project.project_path}'"):
                project.clean()
            return True
        except Exception as e:
            click.echo(f"注册命令失败: {e}")
            if is_debug():
                import traceback
                traceback.print_exc()
            return False

    def registe(self, alias: str, command: str, is_gui: bool = False, description: str = '', project_name = 'default'):

        if alias in self.cmd_register:
            raise ValueError(f'alias {alias} already exist')
        self.cmd_register[alias] = {
            'project_name': project_name,
            'command': command,
            'is_gui': is_gui,
            'description': description
        }
        if self._update_project(project_name):
            self._save()
            click.echo(f"register command '{alias}' success")
    
    def remove(self, alias: str = None, project_name:str = None):
        if alias == None and project_name == None:
            raise ValueError('alias or project_name must be specified')
        res = False
        if alias != None:
            if project_name:
                if self.cmd_register[alias]['project_name'] != project_name:
                    raise ValueError(f'alias {alias} not in project {project_name}')
            del self.cmd_register[alias]
            res = self._update_project(project_name)

        else:
            exist = False
            for alias, cmd in self.cmd_register.items():
                if cmd['project_name'] != project_name:
                    continue
                exist = True
                del self.cmd_register[alias]
            if not exist:
                raise ValueError(f'project {project_name} not exist')
            res = PyProject.uninstall(project_name)

        if res:
            self._save()
    
    def list(self, show_project_name = None)->None:
        # 按照project_name为一组显示
        project_name_list = sorted(set([cmd['project_name'] for cmd in self.cmd_register.values()]))
        if show_project_name != None:
            if show_project_name not in project_name_list:
                click.echo(f'project {show_project_name} not exist')
                return
            project_name_list = [show_project_name]        

        for project_name in project_name_list:
            click.echo(f'命令组: {project_name}')
            for alias, cmd in self.cmd_register.items():
                if cmd['project_name'] != project_name:
                    continue
                click.echo(f'  {alias}: {cmd["command"]}')
    
    def _save(self):
        with open(self.cmd_register_toml, 'w', encoding='utf-8') as f:
            dump(self.cmd_register, f)

    def _load(self):
        with open(self.cmd_register_toml, 'r', encoding='utf-8') as f:
            self.cmd_register = load(f)
