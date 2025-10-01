import os
import click
from pathlib import Path
from cmdbox_commands.cmd_register.cmd_register import CmdResiter
from cmdbox_commands.cmd_register.config import is_debug

CMD_REGISTER_DB = os.environ.get("CMD_REGISTER_DB", os.fspath(Path.home() / '.cmdbox' / 'cmd_register'))
cmd_register = CmdResiter(Path(CMD_REGISTER_DB) / 'cmd_register.toml')

@click.group(
    invoke_without_command=True,
    epilog='cmdr COMMAND --help，查看子命令更多帮助',
)
@click.option('-v', '--version', 'show_version', is_flag=True, help='显示版本号')
@click.option('--debug', 'debug', is_flag=True, help='调试模式')
@click.option('--path', 'show_path', is_flag=True, help='获取配置文件路径')
@click.pass_context
def main(ctx, show_version, debug, show_path):

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
    if show_path:
        click.echo(cmd_register.cmd_register_toml.parent)
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
@click.option('-g', '--gui', 'is_gui', is_flag=True, help='有图形界面工具')
@click.option('--save-temp', 'save_temp', is_flag=True, help='保存中间临时文件')
#@click.option('--force', 'force_install', is_flag=True, help='强制安装命令，如果命令存在则被覆盖')
@click.option('-d', '--description', 'description', default='', help='命令描述')
@click.option('-p', '--project', 'project_name', default='default', help='分组名称')
def register(alias: str, command: str, is_gui: bool = False, 
            description: str = '', project_name = 'default', 
            save_temp: bool = False, force_install: bool = False):
    """
    注册自定义命令

    \b
    alias    自定义命令名称，忽略大小写
    command  实际命令
    """
    try:
        if cmd_register.register(alias, command, is_gui, description, project_name, save_temp, force_install):
            click.echo(f"Register command '{alias}' success")
            if save_temp:
                click.echo(f"中间临时文件路径：{cmd_register.cmd_register_toml.parent / project_name}")
        else:
            click.echo(f"Register command '{alias}' failed")
    except ValueError as e:
        click.echo(f"注册自定义命令失败: {str(e)}")
        if is_debug():
            import traceback
            traceback.print_exc()

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
        res = cmd_register.remove(alias, project_name)
        if res:
            click.echo(f"删除自定义命令或命令集成功: {alias if alias else project_name}")
        else:
            click.echo(f"删除自定义命令或命令集失败。")
    except ValueError as e:
        click.echo(f"删除自定义命令或命令集失败: {str(e)}")
        if is_debug():
            import traceback
            traceback.print_exc()

@main.command()
@click.option('-p', '--project', 'project_name', default=None, help='分组名称')
def list(project_name):
    """
    列出所有自定义命令。
    """
    try:
        cmd_register.list(project_name)
    except ValueError as e:
        click.echo(f"列出自定义命令失败: {str(e)}")
        if is_debug():
            import traceback
            traceback.print_exc()

@main.command()
@click.option('-p', '--project', 'project_name', default=None, help='分组名称')
@click.option('-s', '--strategy', 'strategy', type=click.Choice(['configure', 'installed', 'mix'], 
    case_sensitive=False), 
    prompt=True,
    prompt_required=False,
    default='mix',
    help="""
    \b
    同步策略。
    configure: 仅同步配置文件中的自定义命令，安装未安装的。
    installed: 仅同步已安装的自定义命令，配置未配置的。
    mix:       双向同步，安装未安装的配置，并配置已安装的自定义命令（默认）
    """)
def sync(strategy, project_name = None):
    """
    同步配置的自定义命令和安装的自定义命令，使配置和安装保持一致。"""
    try:
        click.echo(f"同步策略: {strategy}")
        cmd_register.sync(strategy, project_name)
    except ValueError as e:
        click.echo(f"同步自定义命令失败: {str(e)}")
        if is_debug():
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        #cleanup()
        sys.exit(0)