import click
import subprocess

def check_command_exist(command: str) -> bool:
    """检查命令是否存在"""
    # command不可以是已经存在的命令。执行“which cmd_name”，如果返回值不是空，则说明已经存在。
    click.echo(f"check '{command}' exist?")
    result = subprocess.run(f'which {command}', 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8')
    if result.stdout.strip():
        click.echo(f"'{command}' already exist")
        return True
    click.echo(f"'{command}' not exist")
    return False
