
try:
    from cmdbox._version import __version__
except:
    __version__ = "0.0.0"

import click
from importlib.metadata import entry_points
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

def get_project_scripts():
    """只获取当前项目注册的命令"""
    project_name = "cmdbox_commands"  # 替换为你的项目名
    scripts = []
    for entry_point in entry_points().get("console_scripts", []):
        if project_name in entry_point.value.split(".", 1)[0]:
            scripts.append({
                "name": entry_point.name,
                "module": entry_point.value
            })
    return scripts

def get_scripts():
    """优先使用 importlib.metadata，回退到其他方法"""
    try:
        return get_project_scripts()
    except:
        return get_scripts_legacy()  # 回退到方法3

@click.command()
@click.version_option(version=__version__, prog_name='cmdbox')
@click.option('-l', '--list', 'show_list', is_flag=True, help='查看支持的命令行工具')
def cli(show_list):
    """任务管理命令行工具"""
    # 实现--list选项功能
    if show_list:
        # 动态从project.scripts中解析
        scripts = get_scripts()
        click.echo("支持的命令行工具:")
        for script in scripts:
            click.echo(f"  {script['name']}")
        click.echo()
        if len(scripts) > 0:
            click.echo(f"命令使用方式，COMMAND --help查看，例如：{scripts[0]['name']} --help")

def _version():
    click.echo(f"cmdbox version: {__version__}")

def main():
    cli()

if __name__ == "__main__":
    main()
