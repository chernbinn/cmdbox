
import click
import shutil
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from toml import load, dump
from cmdbox_commands.cmd_register.py_project.utils import check_command_exists
from cmdbox_commands.cmd_register.py_project.py_project import PyProject, Command
from cmdbox_commands.cmd_register.config import is_debug

class AliasCMD(Command):
    project_name: str = 'default' 
    # 继承了BaseModel，project_name不再是类属性，是BaseModel的模型字段
    # 类属性必须声明模型字段，不再具备类属性，比如这里注释掉project_name，__init__中初始化project_name会报错

    def __init__(self, alias: str, 
            command: str, 
            is_gui: bool = False, 
            description: str = '', 
            project_name: str = 'default'):
        super().__init__(
            alias=alias,
            command=command,
            is_gui=is_gui,
            description=description
        )
        self.project_name = project_name.lower()

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, AliasCMD):
            return False
        if all([
            value.alias == self.alias,
            value.command == self.command,
            value.project_name == self.project_name
        ]):
            return True
        return False

class CmdResiter:
    def __init__(self, cmd_register_toml: Path):
        self.cmd_register = defaultdict(dict)
        self.cmd_register_toml = cmd_register_toml
        if self.cmd_register_toml.exists():
            try:
                self._load()
            except Exception as e:
                click.echo(f"load cmd_register_toml failed: {e}")

                if not "get_empty_table" in str(e):
                    click.echo(f"load cmd_register_toml failed: {e}")
                    raise e
                self.cmd_register = defaultdict(dict)

    def _update_project(self, project_name: str) -> bool:
        commands = []
        try:
            for alias, cmd in self.cmd_register.items():
                if cmd['project_name'] != project_name:
                    continue
                commands.append(
                    Command(
                        alias = alias,
                        command = cmd['command'],
                        is_gui = cmd['is_gui'],
                        description = cmd['description']
                    )
                )
            if not commands:
                PyProject.uninstall(project_name)
                PyProject.clean_by_path(self.cmd_register_toml.parent / project_name)
                return True
            project = PyProject(
                project_path = self.cmd_register_toml.parent / project_name,
                project_name = project_name
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
                description: str = '', project_name = 'default',
                save_temp: bool = False, force_install: bool = False)->bool:

        alias_cmd = AliasCMD(alias, command, is_gui, description, project_name)
        if not self._pre_check_register(alias_cmd) and not force_install:
            return False
        if force_install:
            click.echo(f'Warning: force install alias "{alias_cmd.alias}"')

        self.cmd_register[alias] = {
            'project_name': project_name,
            'command': command,
            'is_gui': is_gui,
            'description': description
        }
        res = False
        if self._update_project(project_name):
            self._save()
            res = True

        temp_path = self.cmd_register_toml.parent / project_name
        if not save_temp and temp_path.exists():
            shutil.rmtree(temp_path)

        return res    
    
    def remove(self, alias: str = None, project_name:str = None)->bool:
        if not alias and not project_name:
            raise ValueError('alias or project_name must be specified')

        res = False
        if not alias and project_name:
            return self._remove_proejct(project_name)

        if alias not in self.cmd_register:
            if not check_command_exists(alias):
                click.echo(f'Alias "{alias}" dose not exist {f"in {project_name}" if project_name else ""}')
                return True
            _, installed_project_name = PyProject.is_installed(alias)
            if not installed_project_name :
                click.echo(f'Alias "{alias}" is not alias command, can not be removed')
                return True
            
            if not project_name and project_name != installed_project_name:
                click.echo(f'Alias "{alias}" is installed in project "{installed_project_name}", can not be removed')
                return False
            return self._update_project(installed_project_name)

        if project_name:
            if self._get_project_by_alias(alias) != project_name:
                click.echo(f'Alias "{alias}" dose not exist in {project_name}')
                return False
        else:
            project_name = self._get_project_by_alias(alias)
            if not project_name:
                click.echo(f'Alias "{alias}" dose not exist in any project')
                return False
        self.cmd_register.pop(alias, None)
        if self._check_exist(project_name):
            res = self._update_project(project_name)
        else:
            res = PyProject.uninstall(project_name)
            PyProject.clean_by_path(self.cmd_register_toml.parent / project_name)
        self._save()
        return res
    
    def list(self, show_project_name = None)->None:
        # 按照project_name为一组显示
        project_name_list = []
        real_projects = PyProject.get_installed_projects()
        if not real_projects and not self.cmd_register:
            click.echo(f'No project installed')
            return
        if show_project_name:
            if not self._check_exist(show_project_name) and show_project_name not in real_projects:
                click.echo(f'Project "{show_project_name}" dose not exist')
                return
            project_name_list = [show_project_name]
            real_projects = [show_project_name] if show_project_name in real_projects else []
        else:
            project_name_list = self._get_projects()
            project_name_list = set(project_name_list + real_projects)
        
        only_conf_projects: set[str] = set()
        only_conf_alias: dict[str, list[str]] = defaultdict(list)
        only_installed_alias: dict[str, list[str]] = defaultdict(list)
        for project_name in project_name_list:   
            real_installed = []
            if project_name in real_projects:
                click.echo(f'命令组: {project_name}')
                if self._check_exist(project_name):
                    real_projects.remove(project_name)
                real_installed = PyProject.get_project_commands(project_name)
                click.echo(f'已安装命令: ')
            else:
                only_conf_projects.add(project_name)
            
            for alias in (set(self.cmd_register.keys()) | set(real_installed)):
                if real_installed and self._check_installed_by_installedlist(alias, real_installed):
                    command = None
                    if self._check_configured(alias):
                        real_installed.remove(alias)
                        command = self.cmd_register[alias]['command']
                    else:
                        command = PyProject.get_actual_command(alias)
                    click.echo(f'  {alias}{f": {command}" if command else ""}')
                elif alias in self.cmd_register and self.cmd_register[alias]['project_name'] == project_name:
                    only_conf_alias[project_name].append(alias)
            if real_installed:
                only_installed_alias[project_name] = real_installed
                    
        exist_diff = any([
            len(only_installed_alias)>0 or len(real_projects)>0,
            len(only_conf_projects)>0 or len(only_conf_alias)>0
        ])
        if exist_diff:
            if real_projects or only_installed_alias:
                click.echo("\nOnly installed - installed but not configured")
            if real_projects:                    
                click.echo(f'  Project:{real_projects}')
            if only_installed_alias:
                for project, alias_list in only_installed_alias.items():
                    click.echo(f'  Project-alias:{project} - {alias_list}')

            if only_conf_projects or only_conf_alias:
                click.echo("\nOnly configured - configured but not installed")
            if only_conf_projects:
                click.echo(f'  Project:{only_conf_projects}')
            if only_conf_alias:
                for project, alias_list in only_conf_alias.items():
                    click.echo(f'  Project-alias:{project} - {alias_list}')
            click.echo()
        if exist_diff:
            click.echo(f'运行 "cmdr sync --help" 了解同步配置、安装的命令')

    def sync(self, strategy: str, project_name: str = None):
        """
        同步配置的自定义命令和安装的自定义命令，使配置和安装保持一致。"""
        if strategy == 'installed':
            self._sync_installed(project_name)
        elif strategy == 'configure':
            self._sync_configure(project_name)
        elif strategy == 'mix':
            self._sync_mix(project_name)
        else:
            raise ValueError(f'Unknown strategy: {strategy}')

    def _pre_check_register(self, alias_cmd: AliasCMD)->bool:
        b_equal = False
        if alias_cmd.alias in self.cmd_register:
            old_alias_cmd = AliasCMD(
                    alias_cmd.alias, 
                    self.cmd_register[alias_cmd.alias]['command'], 
                    self.cmd_register[alias_cmd.alias]['is_gui'], 
                    self.cmd_register[alias_cmd.alias]['description'], 
                    self.cmd_register[alias_cmd.alias]['project_name']
                )
            if alias_cmd != old_alias_cmd:
                click.echo(f'Alias "{alias_cmd.alias}" already configured')
                alias_info = self.cmd_register[alias_cmd.alias]
                click.echo("\nConfigured info:")
                click.echo(f'   project_name: {alias_info["project_name"]}')
                click.echo(f'   command: {alias_info["command"]}')
                click.echo(f'   description: {alias_info["description"]}\n')

                return False
            b_equal = True
        # to do: equal or not configured
        b_installed = check_command_exists(alias_cmd.alias)

        installed_project = None
        if b_installed:
            #installed_project = PyProject.get_project_name(alias_cmd.alias)
            installed_project = self._get_project_by_alias(alias_cmd.alias)
        if b_installed and not installed_project:
            #click.echo(f'Warning: alias "{alias_cmd.alias}" is system command, can not be registered')
            raise ValueError(f'Alias "{alias_cmd.alias}" exist in non-alias commands, can not be registered')
        if b_installed:
            actual_comman = PyProject.get_actual_command(alias_cmd.alias)

            if b_equal and installed_project == alias_cmd.project_name and actual_comman == alias_cmd.command:
                click.echo(f'The same alias "{alias_cmd.alias}" already installed')
                return False            
            
            #b_installed, installed_project = PyProject.is_installed(alias_cmd.alias)
            if actual_comman == alias_cmd.command and installed_project == alias_cmd.project_name:
                click.echo(f'The same alias "{alias_cmd.alias}" already installed')
                self._add_miss_configure(alias_cmd.alias, installed_project, actual_comman, 
                        alias_cmd.is_gui, alias_cmd.description)                
            else:
                click.echo(f'The same alias "{alias_cmd.alias}" already installed, but configure is not equal')
                click.echo(f'\nInstalled nnfo')
                click.echo(f'   installed_project: {installed_project}')
                click.echo(f'   command: {actual_comman}\n')
                self._add_miss_configure(alias_cmd.alias, installed_project, actual_comman)

            self._save()
            return False
        return True
    
    def _remove_proejct(self, project_name: str):
        if not self._check_exist(project_name):
            b_installed, project = PyProject.is_installed(None, project_name)
            if not b_installed:
                click.echo(f'project {project_name} not exist')
                return True            

        if click.confirm(f"确定删除整个组 '{project_name}'的命令吗？"):
            res = PyProject.uninstall(project_name)
            if res:
                self._del_project(project_name)
                self._save()
            PyProject.clean_by_path(self.cmd_register_toml.parent / project_name)
            return res
        click.echo("取消删除")
        return False
    
    def _get_project_by_alias(self, alias: str)->str:
        if not alias:
            raise ValueError('alias must be specified')
        #print(f'get_project_by_alias {alias}')
        if alias in self.cmd_register:
            #print(f'alias {alias} in cmd_register')
            return self.cmd_register[alias]['project_name']
        return None
                
    def _check_installed_by_installedlist(self, alias: str, installed: list)->bool:
        if not alias:
            raise ValueError('alias must be specified')
        if not installed:
            raise ValueError('installed must be specified')

        if alias in installed:
            return True
        """
        subfix = installed[0].rsplit('.', 1)[1]
        command = f"{alias}.{subfix}"
        if command in installed:
            installed.remove(command)
            return True
        """
        return False

    def _check_configured(self, command: str)->bool:
        if not command:
            raise ValueError('command must be specified')
        install_alias = command.rsplit('.', 1)[0]

        if install_alias not in self.cmd_register:
            return False
        return True
    
    @lru_cache
    def _check_exist(self, project_name: str):
        if not project_name:
            raise ValueError('project_name must be specified')
        project_name_list = sorted(set([cmd['project_name'] for cmd in self.cmd_register.values()]))
        return project_name in project_name_list

    @lru_cache
    def _get_projects(self):
        return sorted(set([cmd['project_name'] for cmd in self.cmd_register.values()]))

    def _del_project(self, project_name: str):
        to_delete = [
            alias for alias, cmd in self.cmd_register.items()
            if cmd.get('project_name') == project_name
        ]
        for alias in to_delete:
            del self.cmd_register[alias]
    
    def _save(self):
        with open(self.cmd_register_toml, 'w', encoding='utf-8') as f:
            dump(self.cmd_register, f)

    def _load(self):
        with open(self.cmd_register_toml, 'r', encoding='utf-8') as f:
            self.cmd_register = load(f)    

    def _sync_installed(self, project_name: str = None):
        """
        同步已安装的自定义命令，使配置和安装保持一致。"""
        if project_name:
            self._sync_installed_project(project_name)
        else:
            for project_name in PyProject.get_installed_projects():
                self._sync_installed_project(project_name)

    def _sync_installed_project(self, project_name: str):
        """
        同步已安装项目的自定义命令，使配置和安装保持一致。"""
        installed_commands = PyProject.get_project_commands(project_name)
        for alias in installed_commands:
            if self._check_configured(alias):
                continue
            self._add_miss_configure(alias, project_name, PyProject.get_actual_command(alias))
        self._save()

    def _sync_configure(self, project_name: str = None):
        """
        同步配置的自定义命令，使配置和安装保持一致。"""
        if project_name:
            self._sync_configure_project(project_name)
        else:
            for project_name in self._get_projects():
                self._sync_configure_project(project_name)

    def _sync_configure_project(self, project_name: str):
        """
        同步配置项目的自定义命令，使配置和安装保持一致。"""
        for alias in self.cmd_register:
            if self._check_installed(alias):
                continue
            else:
                b_installed, _ = PyProject.is_installed(alias, project_name)
                if not b_installed:
                    break
            
        if not self._update_project(project_name):
            click.echo(f"Sync project '{project_name}' failed")
            raise ValueError(f"Sync project '{project_name}' failed")            

    def _check_installed(self, alias: str)->bool:
        """
        检查自定义命令是否已安装。"""
        if self._get_project_by_alias(alias) or PyProject.is_installed(alias)[0]:
            return True
        return False

    def _check_non_alias_installed(self, alias: str)->bool:
        """
        检查自定义命令是否为系统命令。"""
        if (check_command_exists(alias) and 
            not self._check_installed(alias)):
            return True
        return False
    
    def _sync_mix(self, project_name: str = None):
        """
        同步配置和已安装的自定义命令，使配置和安装保持一致。"""
        if project_name:
            self._sync_mix_project(project_name)
        else:
            projects = set(self._get_projects() + PyProject.get_installed_projects())
            for project_name in projects:
                self._sync_mix_project(project_name)
        
    def _sync_mix_project(self, project_name: str):
        """
        同步配置项目和已安装项目的自定义命令，使配置和安装保持一致。"""
        self._sync_installed_project(project_name)
        self._sync_configure_project(project_name)

    def _add_miss_configure(self, alias: str, project_name: str, command: str, 
                is_gui: bool=False, description:str = ""):
        """
        同步配置项目的自定义命令，使配置和安装保持一致。"""
        self.cmd_register[alias] = {
            'project_name': project_name,
            'command': command,
            'is_gui': is_gui,
            'description': description
        }

