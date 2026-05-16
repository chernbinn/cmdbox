"""工具函数模块"""

import sys
import os
import click
import subprocess
import threading
import base64
import shutil
from typing import Union, Optional, Tuple, Literal, List
from pathlib import Path

# 文本检查的默认阈值
TEXT_THRESHOLD = 0.8
# 文本检查的最大长度
MAX_TEXT_LEN = 20
# 编码优先级列表
ENCODING_PRIORITY = ["gbk", "utf-8", "utf-8-sig", "ascii", "gb18030", "latin1"]

def safe_join_path(base_path: Union[str, Path], *paths: str) -> Path:
    """安全地拼接路径，防止路径遍历攻击"""
    base = Path(base_path).resolve()
    # 拼接所有路径，并解析符号链接和相对路径
    full = base.joinpath(*paths).resolve()
    # 检查最终路径是否仍在 base 下
    if not full.is_relative_to(base):
        raise ValueError(f"Path traversal attempt: {full} is not under {base}")
    return full

def check_command_exists(cmd: Union[str, os.PathLike]) -> bool:
    
    """检查命令是否存在于系统PATH中（兼容所有平台和Python版本）"""
    # 显式将PathLike转换为字符串
    cmd_str = os.fsdecode(cmd) if not isinstance(cmd, str) else cmd

    if hasattr(shutil, "which"):
        return shutil.which(cmd_str) is not None

    result = subprocess.run(f"which {cmd_str}", 
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
    if os.name == "nt":
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        paths = os.environ.get("PATH", "").split(os.pathsep)

        for ext in [""] + pathext:
            for path in paths:
                exe_path = os.path.join(path, f"{cmd}{ext}")
                if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                    return True
    else:
        paths = os.environ.get("PATH", "").split(os.pathsep)
        for path in paths:
            exe_path = os.path.join(path, cmd)
            if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                return True
    return False

class Base32V:
    """Base32版本加密解密工具类"""

    @staticmethod
    def encrypt_version(base_version: str, secret: str) -> str:
        """加密版本号"""
        # 使用 base32 编码并转为小写
        encoded = base64.b32encode(secret.encode()).decode().lower().rstrip("=")
        return f"{base_version}+{encoded}"

    @staticmethod
    def decrypt_version(full_version: str) -> Tuple[str, Optional[str]]:
        """解密版本号"""
        if "+" not in full_version:
            return full_version, None
        base, _, local = full_version.partition("+")
        padded = local + "=" * ((8 - len(local) % 8) % 8)
        try:
            decoded = base64.b32decode(padded.upper()).decode()
            return base, decoded
        except Exception:
            return base, None

def out_print(*args, file=sys.stdout, flush=True, **kw) -> None:
    """输出打印函数"""
    print(*args, file=file, flush=flush, **kw)

def is_likely_text(s: str, threshold: float = TEXT_THRESHOLD) -> bool:
    """快速检查字符串是否可能是有效文本"""
    printable_chars = sum(c.isprintable() or c.isspace() for c in s[:MAX_TEXT_LEN])
    return (printable_chars / len(s[:MAX_TEXT_LEN])) >= threshold if s else False

def str_decode(line_bytes: bytes) -> str:
    """解码字节串为字符串，尝试多种编码"""
    # 优先尝试系统默认编码（Windows为gbk，Linux为utf-8）
    default_encoding = "gbk" if os.name == "nt" else "utf-8"
    encodings_to_try = [default_encoding] + [enc for enc in ENCODING_PRIORITY if enc != default_encoding]

    for encoding in encodings_to_try:
        try:
            line_str = line_bytes.decode(encoding).rstrip()
            if line_str:
                return line_str
        except Exception:
            continue
    # 最终兜底方案：替换不可解码字符
    return line_bytes.decode("utf-8", errors="replace").rstrip()

class VerboseType:
    """详细程度类型"""
    NO_LOGS = 0
    ERROR = 1
    DEBUG = 2

def tee_stream(stream, output_file, is_stderr: bool = False, result: Optional[object] = None, 
    verbose: Literal[VerboseType.NO_LOGS, VerboseType.ERROR, VerboseType.DEBUG] = VerboseType.DEBUG) -> None:
    """流式处理函数"""
    def record_line(line: str) -> None:
        newline = line if line.endswith("\n") else line + "\n"
        if is_stderr:
            result.stderr += newline
            if verbose >= VerboseType.ERROR:
                out_print(line, file=sys.stderr)
        else:
            result.stdout += newline
            if verbose >= VerboseType.DEBUG:
                out_print(line)

        if output_file:
            output_file.write(newline)
            output_file.flush()

    for line_bytes in iter(stream.readline, b""):
        if not line_bytes:
            break
        line = str_decode(line_bytes)
        record_line(line)

    remaining = stream.read()
    if remaining:
        last_line = str_decode(remaining)
        record_line(last_line)

class ChildResult:
    """子进程执行结果类"""
    RETURN_CODE_SUCCESS = 0
    RETURN_CODE_FAILED = 1

    def __init__(self, returncode: int = RETURN_CODE_FAILED, stdout: str = "", stderr: str = ""):
        """初始化结果"""
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def child_run(args: str, verbose: Literal[VerboseType.NO_LOGS, VerboseType.ERROR, VerboseType.DEBUG] = VerboseType.NO_LOGS,
       log_file: Optional[Path] = None) -> ChildResult:
    """执行子进程命令"""
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "LC_ALL": "en_US.UTF-8",
        "LANG": "en_US.UTF-8",
        "LC_CTYPE": "UTF-8",
        "CHCP": "65001"
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                cwd=os.getcwd(),
                env=env
            )

        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        result = ChildResult(ChildResult.RETURN_CODE_FAILED, "", "")

        stderr_thread = threading.Thread(
            target=tee_stream,
            args=(proc.stderr, f, True, result, verbose), daemon=True)
        stderr_thread.start()

        stdout_thread = threading.Thread(
                target=tee_stream,
                args=(proc.stdout, f, False, result, verbose), daemon=True)
        stdout_thread.start()

        exit_code = proc.wait()
        stderr_thread.join()
        stdout_thread.join()
        if f:
            f.close()

        result.returncode = exit_code
        return result
    except Exception as e:
        out_print(f"Excute command '{args}' failed: {e}")
        return ChildResult(
            returncode=ChildResult.RETURN_CODE_FAILED,
            stdout="",
            stderr=str(e)
        )
        