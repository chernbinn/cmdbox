from typing import Optional, Any

class ClickOption:
    @staticmethod
    def _generic_callback(ctx, param, value):
        if value:
            # 这里实现一个通用的option回调函数
            ctx.obj[param.name] = value

    def generate_option(
        self,
        name: str,
        param_name: str,
        help: str,
        short: Optional[str] = None,
        opt_type: Optional[str] = None,
        is_flag: Optional[bool] = None,
        default: Optional[Any] = None,
        show_default: Optional[bool] = None,
        required: Optional[bool] = None,
        is_eager: bool = True,
        expose_value: bool = False,
        enabled: bool = True
    ) -> str:
        """通用选项生成器
        
        Args:
            name: 选项名称 (e.g. '--irun-sync')
            param_name: 参数名称 (e.g. 'run_sync')
            help: 帮助文本
            short: 短选项名称 (e.g. '-s')
            opt_type: 参数类型 (e.g. click.Path())
            is_flag: 是否作为标志选项
            default: 默认值
            show_default: 是否显示默认值
            required: 是否必须
            is_eager: 是否优先处理
            expose_value: 是否暴露值
            enabled: 是否启用该选项
        """
        if not enabled:
            return ""
            
        callback_ref = f"callback={self.__class__.__name__}._generic_callback"
        
        parts = [
            f"'{name}', '{param_name}'",
            f"is_eager={is_eager}",
            f"expose_value={expose_value}",
            callback_ref,
        ]
        insert_index = 0
        if short:
            parts.insert(insert_index, f"'{short}'")
            insert_index += 1
        
        # 处理opt_type
        if opt_type:
            parts.insert(1+insert_index, f"type={opt_type}")
            insert_index += 1
        
        if is_flag is not None:
            parts.insert(1+insert_index, f"is_flag={is_flag}")
            insert_index += 1

        if default is not None:
            parts.insert(1+insert_index, f"default={default}")
            insert_index += 1
        
        if show_default is not None:
            parts.insert(1+insert_index, f"show_default={show_default}")
            insert_index += 1

        if required is not None:
            parts.insert(1+insert_index, f"required={required}")
            insert_index += 1
        
        parts.append(f'help="""{help}"""')

        # 指定位置换行或者每三个参数换一行，help独占一行
        new_parts = ["@click.option("]
        new_line = 0
        for i in range(0, len(parts)-1):
            new_parts[-1] =  f"{new_parts[-1]}{parts[i]}, "
            if any([
                parts[i].startswith("default"),
                parts[i].startswith("required"),
                parts[i].startswith("callback"),
            ]):
                new_parts.append("")
                new_line = 0

            new_line += 1
            if new_line == 3:
                new_parts.append("")
                new_line = 0

        if not new_parts[-1]:
            new_parts.pop()
        new_parts.append(f"{parts[-1]}")
        return "\n    ".join(new_parts) + ")"
    
    def generate_option_is_gui(self, is_gui:bool) -> str:
        if is_gui:
            """生成GUI相关选项"""
            return self.generate_option(
                name='--irun-sync',
                param_name='run_sync',
                help="同步运行内部命令。阻塞命令行直到内部命令执行完成，比较耗资源。未说明同步执行，默认后台执行内部命令",
                is_flag=True,
                is_eager=True,
                expose_value=False,
                enabled=is_gui
            )
        return ""

def smart_split(s: str) -> list:
    """
    按空格分割字符串，保留引号内的内容（支持单双引号嵌套）
    增强功能：
    - 自动处理Windows和Unix路径差异
    - 保留原始引号信息（用于后续处理）
    - 更好的错误处理
    
    >>> smart_split('cmd "/path with space"')
    ['cmd', '/path with space']
    >>> smart_split("git commit -m 'fix: bug'")
    ['git', 'commit', '-m', 'fix: bug']
    """
    if not s.strip():
            return []
        
    try:
        import shlex
        # 保留引号内的原始内容（posix=False时Windows路径更友好）
        #lex = shlex.shlex(s, posix=(os.name != 'nt')) # 实际测试，posix=True时更通用
        lex = shlex.shlex(s, posix=True) # 实际测试，posix=True时更通用
        lex.whitespace_split = True
        lex.escape = ''
        return list(lex)
    except ValueError as e:
        raise ValueError(f"命令解析失败 - 请检查引号匹配: {str(e)}\n原始命令: {s}")

def ensure_path(path: str) -> str:
    """
    确保路径路径经过后续处理后依然有效
    """
    strv = repr(path)
    return strv[1:-1]

def generator_src(command: str, description: str, is_gui: bool):
    click_option = ClickOption()
    # command引号外按照空格分割
    command_parts = smart_split(ensure_path(command))
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

class ClickOption:
    @staticmethod
    def _generic_callback(ctx, param, value):
        if ctx.obj is None:
            ctx.obj = {{}}
        # 关键：只要 value 不是 None 就保存（允许 False, 0, ""）
        if value is not None:
            # 这里实现一个通用的option回调函数
            ctx.obj[param.name] = tuple([param.type, value])
        return value

    @staticmethod
    def get(ctx, param_name: str, default: any = None) -> any:
        if ctx.obj is None:
            return default
        return ctx.obj.get(param_name, (None, default))[1]

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
    if os.name == 'nt':
        from subprocess import list2cmdline
        # Windows：使用 list2cmdline 处理整个命令+参数
        command_str = list2cmdline(command) # 有局限性，仅限windows平台使用
    else:
        import shlex
        # shlex.join虽然跨平台，但是命令是被使用单引号括起来的，在windows下会报错
        command_str = shlex.join(command) if hasattr(shlex, 'join') else " ".join(arg for arg in command)
    return command_str

@click.command(context_settings={{"ignore_unknown_options": True}})
@click.pass_context
{click_option.generate_option("--overbose", "verbose", help="同步执行内部命令，输出命令执行信息",
    short="-ov", is_flag=True, show_default=True, enabled=is_gui)}
{click_option.generate_option("--olog-file", "log_file", help="同步执行内部命令，输出命令执行信息",
    opt_type="click.Path()", is_flag=True, show_default=True, enabled=is_gui)}
{click_option.generate_option_is_gui(is_gui)}
@click.option("--icommand", 'act_command', is_flag=True, help="获取alias的内部命令")
@click.option("--oproject-name", '_project_name', is_flag=True, help="获取命令所在组名")
@click.option('-oh','--help', 'ohelp', is_flag=True, help="显示帮助信息。不会执行内部命令")
@click.option("--ihelp", "ihelp", is_flag=True, help="查看内部命令帮助信息，内部命令的--help")
#@click.option("--iexit", "iexit", callback=_inner_exit,
#    is_eager=True, expose_value=False, is_flag=True, help="退出正在后台执行的内部命令")
@click.argument("args", nargs=-1, metavar="INNER_ARGS")
def main(ctx, args, ohelp, ihelp, act_command, _project_name):
    """
    {description}
    
    内部命令：{repr(command)}

    \b
    INNER_ARGS    内部命令的选项，使用--ihelp查看。如果内部命令不支持任何选项，该参数无效。
    """
    signal.signal(signal.SIGINT, sigint_handler)
    #out_print(f"执行目录：{{os.getcwd()}}")

    command_seqs = {command_parts}
    command = _standardize_command(command_seqs)

    if act_command:
        out_print("ActCommand: " + command)
        return
    if _project_name:
        out_print("PackageName: " + get_package_name())
        return
    if ohelp:
        out_print("")
        out_print(ctx.get_help())
        out_print("")
        return

    log_file = ClickOption.get(ctx, "log_file")
    if log_file:
        out_print(f"log_file: {{log_file}}")

    _args = [item for item in args]
    if ihelp:
        _args.extend(['--help'])
    command_str = _standardize_command(command_seqs + _args)
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

        verbose = ClickOption.get(ctx, "verbose", False)
        if not {is_gui} or verbose or ihelp:
            stdout_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stdout, f, False), daemon=True)
            stdout_thread.start()
        
        if not {is_gui} or ctx.obj.get("run_sync", False) or ihelp or verbose or log_file:
            global _child_process
            _child_process = proc            
            if os.name == 'nt':
                # 解决windows下在wait时无法响应ctrl+c的问题
                try:
                    while True:
                        if _child_process.poll() is not None:
                            break
                        if _should_exit:
                            break
                        time.sleep(1)
                except KeyboardInterrupt:
                    sigint_handler(signal.SIGINT, None)
            exit_code = proc.wait()
            # out_print(f"Exit code: {{exit_code}}")
            
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