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
from queue import Queue

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

def is_likely_text(s: str, threshold=0.8) -> bool:
    """快速检查字符串是否可能是有效文本"""
    MAX_LEN = 20
    printable_chars = sum(c.isprintable() or c.isspace() for c in s[:MAX_LEN])  # 仅检查前MAX_LEN字符
    return (printable_chars / len(s[:MAX_LEN])) >= threshold if s else False

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
            #out_print("---encoding:", encoding)
            #out_print("---line_str:", line_str)
            #out_print("---is_likely_text:", is_likely_text(line_str))

            # 简单验证解码结果是否可打印
            if line_str: # and is_likely_text(line_str):
                return line_str
        except Exception:
            continue
    
    # 最终兜底方案：替换不可解码字符
    return line_bytes.decode('utf-8', errors='replace').rstrip()

def tee_stream(stream, output_file, is_stderr=False, result:object=None, verbose:Literal[0,1,2]=2):
    def record_line(line: str):
        if not line.endswith("\n"):
            newline = line + "\n"
        if is_stderr:
            result.stderr += f"{newline}"
            #out_print(f"\033[31merror:\033[0m", line, file=sys.stderr)
            if verbose > 0:
                out_print(line, file=sys.stderr)
        else:
            result.stdout += f"{newline}"
            if verbose > 1:
                out_print(line)

        if output_file:
            output_file.write(f"{newline}")
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

class ChildResult:
    def __init__(self, returncode: int=1, stdout: str="", stderr: str=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def child_run(args, verbose:Literal[0,1,2]=2, log_file:Path = None):
    out_print(f"--Excute command: {args}")
    env = {
        **os.environ,  # 继承当前环境
        # 关键变量强制UTF-8
        'PYTHONIOENCODING': 'utf-8',
        'LC_ALL': 'en_US.UTF-8',
        'LANG': 'en_US.UTF-8',
        'LC_CTYPE': 'UTF-8',
        # Windows特定
        'CHCP': '65001'  # Windows代码页65001对应UTF-8
    }
    try:
        proc = subprocess.Popen(
                args,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                universal_newlines=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                cwd=os.getcwd(),
                env=env
            )
        stderr_thread = None
        stdout_thread = None
        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        result = ChildResult(1, "", "")
        stderr_thread = None
        stdout_thread = None

        stderr_thread = threading.Thread(
            target=tee_stream, 
            args=(proc.stderr, f, True, result, verbose), daemon=True)
        stderr_thread.start()

        stdout_thread = threading.Thread(
                target=tee_stream, 
                args=(proc.stdout, f, False, result, verbose), daemon=True)
        stdout_thread.start()

        exit_code = proc.wait()
        if stderr_thread:
            stderr_thread.join()
        if stdout_thread:
            stdout_thread.join()
        if f:
            f.close()
        
        """
        out_print(f"--Excute command: {args}")
        out_print(f"--Excute command stdout: {''.join(result_stdout)}")
        out_print(f"--Excute command stderr: {''.join(result_stderr)}")
        out_print(f"--Excute command exit code: {exit_code}")
        """
        result.returncode = exit_code
        return result
    except Exception as e:
        out_print(f"Excute command '{args}' failed: {e}")
        return ChildResult(
            returncode=1, 
            stdout="", 
            stderr=str(e)
        )
        

