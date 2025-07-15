import sys,os
import click
import subprocess
import threading
import base64
import shutil
from typing import Union
from pathlib import Path
from typing import Literal
from pydantic import BaseModel

def check_command_exists(cmd: Union[str, os.PathLike]) -> bool:

    """检查命令是否存在于系统PATH中（兼容所有平台和Python版本）"""
    # 显式将PathLike转换为字符串
    cmd_str = os.fsdecode(cmd) if not isinstance(cmd, str) else cmd
    
    # 使用shutil.which的推荐方式
    if hasattr(shutil, 'which'):
        return shutil.which(cmd_str) is not None

    result = subprocess.run(f'which {cmd_str}', 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8')
    if result.returncode != 0:        
        # 兼容旧版Python的回退方案
        return _fallback_command_exists(cmd_str)
    if cmd_str in result.stdout.strip():
        click.echo(f"'{cmd_str}' already exist")
        return True
    return _fallback_command_exists(cmd_str)

def _fallback_command_exists(cmd: str) -> bool:
    """兼容旧版Python的备用实现"""
    if os.name == 'nt':
        # Windows系统
        pathext = os.environ.get('PATHEXT', '').split(os.pathsep)
        paths = os.environ.get('PATH', '').split(os.pathsep)
        
        for ext in [''] + pathext:
            for path in paths:
                exe_path = os.path.join(path, f"{cmd}{ext}")
                if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                    return True
    else:
        # Unix-like系统
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            exe_path = os.path.join(path, cmd)
            if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                return True
    return False

class Base32V:
    @staticmethod
    def encrypt_version(base_version: str, secret: str) -> str:
        # 使用 base32 编码并转为小写
        encoded = base64.b32encode(secret.encode()).decode().lower().rstrip("=")
        return f"{base_version}+{encoded}"

    @staticmethod
    def decrypt_version(full_version: str) -> (str, str):
        if '+' not in full_version:
            return full_version, None
        base, _, local = full_version.partition('+')
        # 补全 padding =
        padded = local + "=" * ((8 - len(local) % 8) % 8)
        try:
            decoded = base64.b32decode(padded.upper()).decode()
            return base, decoded
        except Exception:
            return base, None

# -------------------------------------------------------------

def out_print(*args, file=sys.stdout, flush=True, **kw):
    print(*args, file=file, flush=flush, **kw)

def tee_stream(stream, output_file, is_stderr=False, buffer=None):
    for line in iter(stream.readline, ''):
        if not line:
            break
        line = line.rstrip()        
        if output_file:
            output_file.write(line)
            output_file.flush()
        if buffer:
            buffer.append(line)
        if is_stderr:
            #out_print(f"\033[31merror:\033[0m", line, file=sys.stderr)
            out_print(line, file=sys.stderr)
        else:
            out_print(line)        

class ChildResult(BaseModel):
    return_code: int
    stdout: str
    stderr: str

def child_run(args, verbose:Literal[0,1,2]=2, log_file:Path = None):
    out_print(f"Excute command: {args}")
    try:
        proc = subprocess.Popen(
                args,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                creationflags=0x08000000 if os.name == 'nt' else 0,
                #encoding='utf-8'
                cwd=os.getcwd()
            )
        stderr_thread = None
        stdout_thread = None

        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        result_stdout = []
        result_stderr = []

        stderr_thread = None
        stdout_thread = None
        if verbose > 0:
            stderr_thread = threading.Thread(
                target=tee_stream, 
                args=(proc.stderr, f, True, result_stderr), daemon=True)
            stderr_thread.start()

        if verbose > 1:
            stdout_thread = threading.Thread(
                    target=tee_stream, 
                    args=(proc.stdout, f, False, result_stdout), daemon=True)
            stdout_thread.start()

        exit_code = proc.wait()
        if stderr_thread:
            stderr_thread.join()
        if stdout_thread:
            stdout_thread.join()
        if f:
            f.close()

        return ChildResult(
            return_code=exit_code, 
            stdout="".join(result_stdout),
            stderr="".join(result_stderr)
        )    
    except Exception as e:
        out_print(f"Excute command '{args}' failed: {e}")
        return ChildResult(
            return_code=1, 
            stdout="", 
            stderr=str(e)
        )
        

