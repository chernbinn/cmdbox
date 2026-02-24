
try:
    from cmdbox._version import __version__
except:
    __version__ = "0.0.0"

import click
from importlib.metadata import entry_points
from pathlib import Path
"""
try:
    from pkg_resources import iter_entry_points
except ImportError:
    iter_entry_points = None

def get_scripts_legacy():
    if not iter_entry_points:
        return []
    project_name = "cmdbox_commands"  # 替换为你的项目名
    return [
        {"name": ep.name, "module": ep.module_name}
        for ep in iter_entry_points("console_scripts") 
        if project_name in ep.module_name.split(".", 1)[0]
    ]
"""
def get_project_scripts(script_tag: str):
    """只获取当前项目注册的命令"""
    project_name = "cmdbox_commands"  # 替换为你的项目名
    scripts = []
    entry_points_result = entry_points()
    # Handle both dict-like and EntryPoints object formats
    if hasattr(entry_points_result, 'get'):
        # Dict-like format (older Python versions)
        entry_points_list = entry_points_result.get(f"{script_tag}", [])
    else:
        # EntryPoints object format (newer Python versions)
        entry_points_list = entry_points_result.select(group=f"{script_tag}")
    
    for entry_point in entry_points_list:
        if project_name in entry_point.value.split(".", 1)[0]:
            scripts.append({
                "name": entry_point.name,
                "module": entry_point.value
            })
    return scripts

def get_scripts():
    """优先使用 importlib.metadata，回退到其他方法"""
    try:
        return get_project_scripts("console_scripts")
    except:
        pass
        #return get_scripts_legacy()

def get_gui_scripts():
    """获取GUI工具"""
    return get_project_scripts("gui_scripts")

@click.command()
@click.version_option(version=__version__, prog_name='cmdbox')
@click.option('-l', '--list', 'show_list', is_flag=True, help='查看支持的命令行工具')
@click.option('-p', '--path', 'show_path', is_flag=True, help='查看命令行工具的文件存储路径')
def cli(show_list, show_path):
    """任务管理命令行工具"""
    # 实现--list选项功能
    if show_list:
        # 动态从project.scripts中解析
        scripts = get_scripts() or []
        click.echo("支持的命令行工具:")
        for script in scripts:
            click.echo(f"  {script['name']}")
        click.echo()
        click.echo("支持的GUI工具:")
        gui_scripts = get_gui_scripts() or []
        for script in gui_scripts:
            click.echo(f"  {script['name']}")
        click.echo()    

        if len(scripts) > 0 or len(gui_scripts) > 0:
            click.echo(f"命令使用方式，COMMAND --help查看，例如：{scripts[0]['name']} --help")

    if show_path:
        click.echo(Path.home() / ".cmdbox")
        return

def _version():
    click.echo(f"cmdbox version: {__version__}")
    return __version__


def main():
    cli()

if __name__ == "__main__":
    main()
