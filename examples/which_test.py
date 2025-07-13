import shutil
import sys, os
from typing import Union

def check_command_exists(cmd: Union[str, os.PathLike]) -> bool:

    """检查命令是否存在于系统PATH中（兼容所有平台和Python版本）"""
    # 显式将PathLike转换为字符串
    cmd_str = os.fsdecode(cmd) if not isinstance(cmd, str) else cmd
    
    # 使用shutil.which的推荐方式
    if hasattr(shutil, 'which'):
        return shutil.which(cmd_str) is not None

    result = subprocess.run(f'which {command}', 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8')
    if result.returncode != 0:        
        # 兼容旧版Python的回退方案
        return _fallback_command_exists(cmd_str)
    if cmd_str in result.stdout.strip():
        click.echo(f"'{command}' already exist")
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


if __name__ == '__main__':
    print(shutil.which(sys.argv[1]))
    print(check_command_exists(sys.argv[1]))
