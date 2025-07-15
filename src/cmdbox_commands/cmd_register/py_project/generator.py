def generator_src(command: str, description: str):
    return fr'''      
import sys,os
import click
import subprocess
import threading
import signal
import time
from pathlib import Path

_child_process = None
_should_exit = False

def out_print(*args, file=sys.stdout, flush=True, **kw):
    print(*args, file=file, flush=flush, **kw)

def sigint_handler(sig, frame):
    out_print("\nCtrl+C pressed, exiting...")
    global _child_process, _should_exit

    _should_exit = True
    if _child_process:
        # Terminate the process group on Unix-like systems
        if os.name == 'posix':
            os.killpg(os.getpgid(_child_process.pid), signal.SIGTERM)
        else:
            out_print(f"----Child process id: {{_child_process.pid}}")
            # On Windows, use taskkill to ensure the process tree is terminated
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(_child_process.pid)])
    sys.exit(0)

def read_stream(stream, output_file, is_stderr):
    for line in iter(stream.readline, ''):
        if not line:
            break
        line = line.rstrip()
        if output_file:
            output_file.write(line)
            output_file.flush()
        if is_stderr:
            out_print(f"\033[31merror:\033[0m", line, file=sys.stderr)
        else:
            out_print(line)

def get_package_name():
    # 获取当前代码的包名
    return Path(__file__).parent.name

def _inner_exit(ctx, param, value):
    if value:
        sigint_handler(signal.SIGINT, None)

@click.command(context_settings={{"ignore_unknown_options": True}})
@click.pass_context
@click.option("-ov", 'verbose', is_flag=True, show_default=True, help="同步执行内部命令，输出命令执行信息")
@click.option("--olog-file", 'log_file', type=click.Path(), help="同步执行内部命令，并输出log到文件")
@click.option('--irun-sync', 'run_sync', is_flag=True, help="同步运行内部命令。阻塞命令行直到内部命令执行完成，比较耗资源。未说明同步执行，默认后台执行内部命令")
@click.option("--icommand", 'act_command', is_flag=True, help="获取alias的内部命令")
@click.option("--oproject-name", '_project_name', is_flag=True, help="获取命令所在组名")
@click.option('-h', '--help', 'ohelp', is_flag=True, help="显示帮助信息。不会执行内部命令")
@click.option("--ihelp", "ihelp", is_flag=True, help="查看内部命令帮助信息，内部命令的--help")
#@click.option("--iexit", "iexit", callback=_inner_exit,
#    is_eager=True, expose_value=False, is_flag=True, help="退出正在执行的内部命令，此选项单独使用")
@click.argument("args", nargs=-1, metavar="INNER_ARGS")
def main(ctx, args, verbose, log_file, ohelp, ihelp, act_command, run_sync, _project_name):
    """{description}
    内部命令：{command}

    \b
    INNER_ARGS    内部命令的选项，使用--ihelp查看。如果内部命令不支持任何选项，该参数无效。
    """
    signal.signal(signal.SIGINT, sigint_handler)
    out_print(f"执行目录：{{os.getcwd()}}")

    command = r"{command}"
    if act_command:
        out_print(command)
        return
    if _project_name:
        out_print(get_package_name())
        return
    if ohelp:
        out_print("")
        out_print(ctx.get_help())
        out_print("")
        return

    if verbose:
        out_print(f"log_file: {{log_file}}")

    _args = [item for item in args]
    if ihelp:
        _args.extend(['--help'])
    command = " ".join([command] + _args)
    out_print(f"Excute command: {{command}}\n")    
    
    creation_flags = 0
    if os.name == 'nt':
        creation_flags = 0# subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
                " ".join([r"{command}"] + _args),
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags,
                cwd=os.getcwd()
            )
        stderr_thread = None
        stdout_thread = None

        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        stderr_thread = threading.Thread(
                target=read_stream, 
                args=(proc.stderr, f, True), daemon=True)
        stderr_thread.start()
        if verbose or ihelp:
            stdout_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stdout, f, False), daemon=True)
            stdout_thread.start()
        
        if run_sync or ihelp or verbose or log_file:
            global _child_process
            _child_process = proc            
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
        else:
            out_print(f"Backend child process id: {{proc.pid}}")

        if f:
            f.close()
    except Exception as e:
        out_print(f"Excute command '{{command}}' failed: {{e}}")
        out_print(ctx.get_help())
        sys.exit(1)

if __name__ == "__main__":
    main()
        '''