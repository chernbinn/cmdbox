def __gernerate_syncrun_option(is_gui: bool) -> str:
    if is_gui:
        return """@click.option('--irun-sync', 'run_sync', is_flag=True, 
            help="同步运行内部命令。阻塞命令行直到内部命令执行完成，比较耗资源。未说明同步执行，默认后台执行内部命令")"""
    return ""

def generator_src(command: str, description: str, is_gui: bool):
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

def sigint_handler(sig, frame, ctrl_c: bool=True):    
    global _child_process, _should_exit

    _should_exit = True
    if _child_process:
        # Terminate the process group on Unix-like systems
        if os.name == 'posix':
            os.killpg(os.getpgid(_child_process.pid), signal.SIGTERM)
        else:
            # out_print(f"Child process id: {{_child_process.pid}}")
            # On Windows, use taskkill to ensure the process tree is terminated
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(_child_process.pid)])
    if ctrl_c:
        out_print("\nCtrl+C pressed, exiting...")
        sys.exit(0)

def str_decode(line_bytes):
    # 优先尝试系统默认编码（Windows为gbk，Linux为utf-8）
    default_encoding = 'gbk' if os.name == 'nt' else 'utf-8'
    encodings_to_try = [
        default_encoding,
        'utf-8',
        'utf-8-sig',
        'ascii',
        'gb18030',  # 兼容gbk的更广编码
        'latin1'    # 不会报错的最后兜底
    ]
    
    for encoding in encodings_to_try:
        try:
            line_str = line_bytes.decode(encoding).rstrip()
            if line_str: 
                return line_str
        except Exception:
            continue
    
    # 最终兜底方案：替换不可解码字符
    return line_bytes.decode('utf-8', errors='replace').rstrip()

def read_stream(stream, output_file, is_stderr):
    def record_line(line: str):
        if is_stderr:
            #out_print(f"\033[31merror:\033[0m", line, file=sys.stderr)
            out_print(line, file=sys.stderr)
        else:
            out_print(line)

        if output_file:
            newline = (line + "\n") if line.endswith("\n") else line
            output_file.write(f"{{newline}}")
            output_file.flush()

    for line_bytes in iter(stream.readline, b''):
        if not line_bytes:
            break
        line = str_decode(line_bytes)        
        record_line(line)
        
    remaining = stream.read()
    if remaining:
        last_line = str_decode(remaining)
        record_line(last_line)

def get_package_name():
    # 获取当前代码的包名
    return Path(__file__).parent.name

def _inner_exit(ctx, param, value):
    if value:
        sigint_handler(signal.SIGINT, None)

def _standardize_command(command: list) -> str:
    if not isinstance(command, list) or not command:
        raise ValueError("command must be a non-empty list")
    # 非彻底解决问题的patch,至少解决cmd /c cmd的命令，cmd是一个单命令，不可以是组合命令
    first_cmd = command[0].lstrip()
    seqs = first_cmd.split()
    if first_cmd.startswith("cmd") and len(seqs) > 2:
        command = ["cmd", "/c"] + seqs[2:] + command[1:]
    #
    if os.name == 'nt':
        from subprocess import list2cmdline
        # Windows：使用 list2cmdline 处理整个命令+参数
        command_str = list2cmdline(command)
    else:
        import shlex
        # 非 Windows：使用 shlex.join（Python 3.8+）或手动拼接
        command_str = shlex.join(command) if hasattr(shlex, 'join') else " ".join(shlex.quote(arg) for arg in command)
    return command_str

@click.command(context_settings={{"ignore_unknown_options": True}})
@click.pass_context
@click.option("-ov", 'verbose', is_flag=True, show_default=True, help="同步执行内部命令，输出命令执行信息")
@click.option("--olog-file", 'log_file', type=click.Path(), help="同步执行内部命令，并输出log到文件")
@click.option('--irun-sync', 'run_sync', is_flag=True, 
            help="同步运行内部命令。阻塞命令行直到内部命令执行完成，比较耗资源。未说明同步执行，默认后台执行内部命令")
@click.option("--icommand", 'act_command', is_flag=True, help="获取alias的内部命令")
@click.option("--oproject-name", '_project_name', is_flag=True, help="获取命令所在组名")
@click.option('-oh','--help', 'ohelp', is_flag=True, help="显示帮助信息。不会执行内部命令")
@click.option("--ihelp", "ihelp", is_flag=True, help="查看内部命令帮助信息，内部命令的--help")
#@click.option("--iexit", "iexit", callback=_inner_exit,
#    is_eager=True, expose_value=False, is_flag=True, help="退出正在后台执行的内部命令")
@click.argument("args", nargs=-1, metavar="INNER_ARGS")
def main(ctx, args, verbose, log_file, ohelp, ihelp, act_command, run_sync, _project_name):
    """{description}
    内部命令：{command}

    \b
    INNER_ARGS    内部命令的选项，使用--ihelp查看。如果内部命令不支持任何选项，该参数无效。
    """
    signal.signal(signal.SIGINT, sigint_handler)
    #out_print(f"执行目录：{{os.getcwd()}}")

    command = r"{command}"
    """
    # Windows 特殊处理：确保路径被双引号包裹
    if os.name == 'nt' and ' ' in command and not (command.startswith('"') and command.endswith('"')):
        print_command = f'"{{command}}"'  # 关键处理，在windows下shlex.quote无作用
    else:
        print_command = shlex.quote(command)
    """
    if act_command:
        out_print("ActCommand: " + _standardize_command([command]))
        return
    if _project_name:
        out_print("PackageName: " + get_package_name())
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
    command_str = _standardize_command([command] + _args)
    out_print(f"Excute command: {{command_str}}\n")
    
    creation_flags = 0
    if os.name == 'nt':
        creation_flags = subprocess.CREATE_NO_WINDOW
    try:
        env = {{
            **os.environ,  # 继承当前环境
            # 关键变量强制UTF-8
            'PYTHONIOENCODING': 'utf-8',
            'LC_ALL': 'en_US.UTF-8',
            'LANG': 'en_US.UTF-8',
            'LC_CTYPE': 'UTF-8',
            # Windows特定
            'CHCP': '65001'  # Windows代码页65001对应UTF-8
        }}
        proc = subprocess.Popen(
                command_str,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                universal_newlines=False,
                creationflags=creation_flags,
                cwd=os.getcwd(),
                env=env
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
        if not {is_gui} or verbose or ihelp:
            stdout_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stdout, f, False), daemon=True)
            stdout_thread.start()
        
        if not {is_gui} or run_sync or ihelp or verbose or log_file:
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
        sigint_handler(signal.SIGINT, None, False)
        out_print(f"Excute command '{{command_str}}' failed: {{e}}")
        out_print(ctx.get_help())
        sys.exit(1)

if __name__ == "__main__":
    main()
        '''