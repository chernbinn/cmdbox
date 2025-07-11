import os
import click
from pathlib import Path
from cmdbox_commands.cmd_register.cmd_register import CmdResiter
from cmdbox_commands.cmd_register.config import is_debug

cmd_register = CmdResiter(Path.home() / '.cmdbox' / 'cmd_register' / 'cmd_register.toml')

@click.group(
    invoke_without_command=True,
    epilog='cmdr COMMAND --help，查看子命令更多帮助',
)
@click.option('-v', '--version', 'show_version', is_flag=True, help='显示版本号')
@click.option('--debug', 'debug', is_flag=True, help='调试模式')
@click.pass_context
def main(ctx, show_version, debug):

    # hele文档按照原格式显示
    """
    命令注册工具，用于注册自定义命令。

    \b
    把不能通过命令行打开的工具注册为命令行打开的工具，通过命令行打开。
    把复杂的命令注册为简单的命令。
    """
    if show_version:
        from cmdbox.cmdbox import _version
        _version()
        return
    if debug:
        click.echo('调试模式')
        os.environ['CMD_REGISTER_DEBUG'] = '1'
    # 输出help内容
    if ctx.invoked_subcommand == None:
        click.echo(main.get_help(ctx))
        return

@main.command("add")
@click.argument('alias')
@click.argument('command')
#@click.option('-g', '--gui', 'is_gui', is_flag=True, help='有图形界面工具')
@click.option('-d', '--description', 'description', default='', help='命令描述')
@click.option('-p', '--project', 'project_name', default='default', help='分组名称')
def registe(alias: str, command: str, is_gui: bool = False, description: str = '', project_name = 'default'):
    """注册自定义命令

    \b
    alias    自定义命令名称
    command  实际命令
    """
    try:
        cmd_register.registe(alias, command, is_gui, description, project_name)
    except ValueError as e:
        if is_debug():
            import traceback
            traceback.print_exc()
        #click.echo(e)
        return

@main.command()
@click.option('-a', '--alias', 'alias', default=None, help='自定义命令名称')
@click.option('-p', '--project', 'project_name', default=None, help='分组名称')
def remove(alias: str = None, project_name:str = None):
    """
    删除自定义命令。
    """
    if alias == None and project_name == None:
        click.echo('alias or project_name must be specified')
        return
    try:
        cmd_register.remove(alias, project_name)
        click.echo(f"删除自定义命令成功: {alias}")
    except ValueError as e:
        click.echo(f"删除自定义命令失败: {e}")
        if is_debug():
            import traceback
            traceback.print_exc()

@main.command()
@click.option('-p', '--project', 'project_name', default=None, help='分组名称')
def list(project_name):
    """
    列出所有自定义命令。
    """
    cmd_register.list(project_name)

if __name__ == '__main__':
    main()