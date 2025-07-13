import sys,os
import click
import subprocess
import threading
import base64
from pathlib import Path
from typing import Literal
from pydantic import BaseModel

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

def stderr_print(line):
    print(line, file=sys.stdout, flush=True)

def tee_stream(stream, output_file, is_stderr=False, buffer=None, verbose:Literal[0,1,2]=0):
    for line in iter(stream.readline, ''):
        if not line:
            break
        if buffer and line.strip():
            buffer.append(line.strip())
        if output_file:
            output_file.write(line)
            output_file.flush()
        if (is_stderr and verbose > 0) or verbose > 1:
            stderr_print(line)

class ChildResult(BaseModel):
    return_code: int
    stdout: str
    stderr: str

def child_run(args, verbose:Literal[0,1,2]=0, log_file:Path = None):
    stderr_print(f"Excute command: {args}")
    
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
            )
        stderr_thread = None
        stdout_thread = None

        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        result_stdout = []
        result_stderr = []
        stderr_thread = threading.Thread(
            target=tee_stream, 
            args=(proc.stderr, f, True, result_stderr, verbose), daemon=True)
        stderr_thread.start()

        stdout_thread = threading.Thread(
                target=tee_stream, 
                args=(proc.stdout, f, False, result_stdout, verbose), daemon=True)
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
        stderr_print(f"Excute command '{args}' failed: {e}")
        return ChildResult(
            return_code=1, 
            stdout="", 
            stderr=str(e)
        )
        

