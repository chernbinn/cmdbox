        
import sys,os
import click
import subprocess
import threading
import signal
import time
from pathlib import Path

_child_process = None
_should_exit = False

def stderr_print(line):
    """
    if os.name == 'nt':
        try:
            line_str = line.decode('gbk', errors='replace').rstrip('\n')
        except UnicodeDecodeError:
            line_str = line.decode('utf-8', errors='replace').rstrip('\n')
    else:
        line_str = line.decode('utf-8', errors='replace').rstrip('\n')
    print(line_str, file=sys.stderr)
    """
    print(line, file=sys.stderr)

def read_stream(stream, output_file, is_stderr=False):
    for line in iter(stream.readline, ''):
        if not line:
            break
        if output_file:
            output_file.write(line)
            output_file.flush()
        if is_stderr:
            stderr_print(line)

def get_package_name():
    # 获取当前代码的包名
    return Path(__file__).parent.name

def sigint_handler(sig, frame):
    click.echo("\nCtrl+C pressed, exiting...")
    global _child_process, _should_exit

    _should_exit = True
    if _child_process:
        # Terminate the process group on Unix-like systems
        if os.name == 'posix':
            os.killpg(os.getpgid(_child_process.pid), signal.SIGTERM)
        else:
            click.echo(f"----Child process id: {_child_process.pid}")
            # On Windows, use taskkill to ensure the process tree is terminated
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(_child_process.pid)])
    sys.exit(0)

@click.command(context_settings={"ignore_unknown_options": True}, help="Alias command")
@click.pass_context
@click.option("-v", 'verbose', count=True, show_default=True, help="Enable debug mode, more log use -vv, max count 2")
@click.option("--log-file ", 'log_file', type=click.Path(), help="Log file")
@click.option('--help', 'help', is_flag=True, help="Show help message")
@click.option('--run-sync', 'run_sync', is_flag=True, help="同步运行命令，可能会阻塞命令行直到命令执行完成，比较耗资源。默认后台执行命令")
@click.option("--command", 'act_command', is_flag=True, help="获取alias对应的真实命令")
@click.option("--project-name", '_project_name', is_flag=True, help="获取命令所在组名")
@click.argument("args", nargs=-1)
def main(ctx, args, verbose, log_file, help, act_command, run_sync, _project_name):
    signal.signal(signal.SIGINT, sigint_handler)

    command = r"C:\\Program Files\\Notepad++\\notepad++.exe"
    if act_command:
        click.echo(command)
        return 
    if _project_name:
        click.echo(get_package_name())
        return
    if verbose > 0:
        click.echo(f"command: {command}")
        click.echo(f"verbose: {verbose}")
        click.echo(f"log_file: {log_file}")
    _args = [item for item in args]
    if help and ("--help" not in _args):
        #click.echo(f"help: {help}")
        _args.extend(['--help'])
    command = " ".join([command] + _args)
    if verbose > 0:
        click.echo(f"Excute command: {command}")

    if os.name == 'nt':
        creation_flags = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
                ["C:\\Program Files\\Notepad++\\notepad++.exe"] + _args,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags if os.name == 'nt' else 0
            )
        stderr_thread = None
        stdout_thread = None

        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        if verbose > 0:
            stderr_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stderr, f, True), daemon=True)
            stderr_thread.start()
        if verbose > 1 or help:
            stdout_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stdout, f, True), daemon=True)
            stdout_thread.start()
        if run_sync:
            global _child_process
            _child_process = proc
            click.echo(f"Child process id: {proc.pid}")
            # proc.wait()
            if os.name == 'nt':
                try:
                    while True:
                        if _child_process.poll() is not None:
                            break
                        if _should_exit:
                            break
                        time.sleep(1)
                except KeyboardInterrupt:
                    sigint_handler(signal.SIGINT, None)
            else:
                proc.wait()
            if stderr_thread:
                stderr_thread.join()
            if stdout_thread:
                stdout_thread.join()
        if f:
            f.close()
        click.echo("\nCommand success")
    except Exception as e:
        click.echo(f"Excute command '{command}' failed: {e}", file=sys.stderr)
        click.echo(ctx.get_help())
        sys.exit(1)
    
if __name__ == "__main__":
    main()
        