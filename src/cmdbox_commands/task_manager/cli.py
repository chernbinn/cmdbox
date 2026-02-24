import click
from pathlib import Path
from cmdbox_commands.task_manager.manager import TaskManager

@click.group(
    invoke_without_command=True,
    epilog='taskbm COMMAND --help，查看子命令帮助',
)
@click.option('-v', '--version', 'show_version', is_flag=True, help='显示版本号')
@click.option('--path', 'show_path', is_flag=True, help='获取配置文件路径')
def cli(show_version, show_path):
    """任务管理命令行工具"""
    if show_version:
        from cmdbox.cmdbox import _version
        _version()
    if show_path:
        manager = TaskManager()
        click.echo(Path(manager.db_file).parent)
        return

@cli.command()
@click.argument('command')
@click.option('-n', '--name', help='任务名称，未指定默认为命令')
@click.option('-s', '--until-succeed', is_flag=True, help='直到成功才退出')
@click.option('-i', '--interval', type=int, default=30, show_default=True, help='失败后重试间隔（秒）')
@click.option('-e', '--tee_error', is_flag=True, help='将错误日志同步输出到终端')
def submit(command, name, until_succeed, interval, tee_error):
    """提交新任务"""
    manager = TaskManager()
    task_id, task = manager.submit_task(command, name, until_succeed, interval, tee_error)

    click.echo(f"Task submitted! ID: {task_id}")
    show_task(manager, task_id, task)

def show_task(manager, task_id, task):
    # 细化任务内容：状态、名称、PID、日志文件
    # 状态颜色区分：绿色表示运行中，红色表示已完成或失败
    # 显示任务ID、状态、名称、PID、日志文件
    # 示例：
    # 123456 [running] My Task (PID: 12345) /path/to/logfile.log
    # 123457 [finished] Another Task (PID: 12346) /path/to/another.log
    if task is None:
        return
    if any([
        task["status"] == "running",
        task["status"] == "completed"
    ]):
        status_color = "green"
    else:
        status_color = "red"

    if manager._is_process_running(task['pid']):
        pid_status = "running"
        pid_color = "green"
    else:
        if task["status"] == "running":
            task["status"] = "terminated"
        pid_status = "terminated"
        pid_color = "red"
    status_text = click.style(task['status'], fg=status_color)
    pid_text = click.style(f'{task["pid"]} {pid_status}', fg=pid_color)
    # 多行显示内容
    click.echo(f"{task_id}")
    click.echo(f"  Start Time: {task['start_time']}")
    click.echo(f"  Status: {status_text}")
    click.echo(f"  Name: {task['name']}")
    click.echo(f"  PID: {pid_text}")
    click.echo(f"  Log File: {task['log_file']}")
    click.echo(f"  Command: {task['command']}")
    click.echo()

def _list(manager):
    if manager:
        tasks = manager.list_tasks()
        if not tasks:
            click.echo("当前没有任务")
        for task_id, task in tasks.items():
            show_task(manager, task_id, task)

@cli.command()
def list():
    """列出所有任务"""
    manager = TaskManager()
    _list(manager)

@cli.command()
def clean():
    """清理已完成任务"""
    manager = TaskManager()
    manager.clean_tasks()
    click.echo()
    click.echo("清理完成，存在任务：")
    _list(manager)


@cli.command()
@click.argument('task_id')
def kill(task_id):
    """终止任务"""
    manager = TaskManager()
    try:
        if manager.kill_task(task_id):
            click.echo(f"Task {task_id} killed")
        else:
            click.echo("Task not found or already dead", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

if __name__ == '__main__':
    cli()