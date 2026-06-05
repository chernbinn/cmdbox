# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import shutil
import filecmp
from pathlib import Path

# ========== 配置常量 ==========
DB_DIR = Path(os.environ.get("OWNPYGIT_DB", Path.home() / ".cmdbox" / "ownpygit" / "db"))
CONFIG_FILE = DB_DIR / "ownpygit_repo.cfg"
HISTORY_FILE = DB_DIR / "ownpygit_history.cfg"
ALIAS_FILE = DB_DIR / "ownpygit_alias.cfg"
CURRENT_DIR_FILE = DB_DIR / "ownpygit_current_dir.cfg"
PREV_DIR_FILE = DB_DIR / "ownpygit_prev_dir.cfg"

EXCLUDED_FILES = {".git", ".gitignore"}  # 使用集合加速查找


# ========== 辅助函数 ==========
def _ensure_db_dir() -> bool:
    """确保配置目录存在"""
    try:
        DB_DIR.mkdir(exist_ok=True, parents=True)
        if os.name == 'nt':
            os.system(f'attrib +h "{DB_DIR}"')
        return True
    except Exception as e:
        print(f"[错误] 创建配置目录失败: {e}")
        return False


def _get_working_dir():
    """返回 (repo, working_dir)"""
    repo = get_repo()
    if not repo:
        print("[错误] 未设置任意一个仓库")
        return None, None    

    if CURRENT_DIR_FILE.exists():
        current_dir = CURRENT_DIR_FILE.read_text(encoding='utf-8').strip()
        if current_dir and Path(current_dir).exists():
            return repo, Path(current_dir)
    return repo, repo

def _validate_repo_path(path: Path, repo: Path, allow_non_exist: bool = False) -> bool:
    """
    校验路径是否在仓库内且存在（可选）
    :param path: 待校验路径
    :param repo: 仓库根目录
    :param allow_non_exist: 是否允许路径不存在（用于创建前检查）
    :return: True 表示合法
    """
    if not allow_non_exist and not path.exists():
        print(f"[错误] 路径不存在: {path}")
        return False
    if not path.is_relative_to(repo):
        print(f"[错误] 路径不在仓库内: {path}")
        return False
    return True


def _save_out_working_dir(repo: Path):
    """保存当前工作目录（用于 cd -）"""
    cwd = Path.cwd()
    if not cwd.is_relative_to(repo):
        PREV_DIR_FILE.write_text(str(cwd), encoding='utf-8')

def _read_out_working_dir() -> Path:
    """读取保存的工作目录（用于 cd -）"""
    if PREV_DIR_FILE.exists():
        prev_dir = PREV_DIR_FILE.read_text(encoding='utf-8').strip()
        return Path(prev_dir)
    return None

# ========== 装饰器 ==========
def judge_repo_path(func):
    """验证仓库和工作目录，并通过关键字参数传递 _repo, _cwd"""
    def wrapper(*args, **kwargs):
        repo, cwd = _get_working_dir()
        if not repo or not cwd.is_relative_to(repo):
            print(f"[错误] 当前目录不是仓库目录: {cwd}")
            return False if func.__annotations__.get('return') == bool else None
        print(f"\033[33m[ownpygit] 当前仓库目录: {repo}\033[0m")
        print(f"\033[33m[ownpygit] 当前操作目录: {cwd}\033[0m\n")
        kwargs['_repo'] = repo
        kwargs['_cwd'] = cwd
        return func(*args, **kwargs)
    return wrapper

# ========== 核心业务函数 ==========
def set_repo(repo_path: str) -> bool:
    repo = Path(repo_path).absolute()
    if not repo.exists():
        print(f"[错误] 路径不存在: {repo}")
        return False
    if not (repo / ".git").exists():
        subprocess.run(["git", "init", str(repo)], check=True)

    CONFIG_FILE.write_text(str(repo), encoding='utf-8')

    # 追加到历史记录
    if not HISTORY_FILE.exists():
        HISTORY_FILE.touch()
    with open(HISTORY_FILE, "r+", encoding='utf-8') as f:
        existing = {line.strip() for line in f}
        if str(repo) not in existing:
            f.write(f"{repo}\n")

    print(f"[ownpygit] 已设置激活仓库: {repo}")
    return True


def create_repo(repo_path: str, alias: str = None) -> bool:
    repo = Path(repo_path).absolute()
    if repo.exists():
        print(f"[警告] 路径已存在: {repo}")
        return False
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True)
    if alias:
        with open(ALIAS_FILE, "a", encoding='utf-8') as f:
            f.write(f"{alias}={repo}\n")
    set_repo(repo)
    print(f"[ownpygit] 已创建仓库: {repo}" + (f" 别名为: {alias}" if alias else ""))
    return True


def get_repo() -> Path:
    if not CONFIG_FILE.exists():
        print("[ownpygit] 未设置激活仓库")
        return None
    repo_path = CONFIG_FILE.read_text(encoding='utf-8').strip()
    repo = Path(repo_path)
    if not repo.exists():
        print(f"[警告] 仓库路径不存在: {repo}")
        return None
    return repo


def list_repos():
    if not HISTORY_FILE.exists():
        print("[ownpygit] 暂无历史仓库记录")
        return
    repos = [line.strip() for line in HISTORY_FILE.read_text(encoding='utf-8').splitlines() if line.strip()]
    current = get_repo()
    print("历史仓库列表：")
    for i, repo in enumerate(repos, 1):
        prefix = " * " if current and str(current) == repo else "   "
        print(f"{prefix}{i}. {repo}")


def delete_repo(target: str, remove_dir: bool = False) -> bool:
    # 别名解析
    if ALIAS_FILE.exists():
        aliases = {}
        for line in ALIAS_FILE.read_text(encoding='utf-8').splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                aliases[k] = v.strip()
        if target in aliases:
            target = aliases[target]

    # 删除别名记录
    if ALIAS_FILE.exists():
        lines = [line for line in ALIAS_FILE.read_text(encoding='utf-8').splitlines()
                 if not line.startswith(target + "=")]
        ALIAS_FILE.write_text("\n".join(lines), encoding='utf-8')

    # 删除历史记录
    if HISTORY_FILE.exists():
        lines = [line for line in HISTORY_FILE.read_text(encoding='utf-8').splitlines()
                 if line.strip() != target]
        HISTORY_FILE.write_text("\n".join(lines), encoding='utf-8')

    # 删除实际目录
    if remove_dir:
        repo_path = Path(target)
        if repo_path.exists():
            try:
                if repo_path.is_dir():
                    shutil.rmtree(repo_path)
                else:
                    repo_path.unlink()
                print(f"[ownpygit] 已删除目录: {repo_path}")
            except Exception as e:
                print(f"[错误] 删除目录失败: {e}")
                return False

    print(f"[ownpygit] 已删除仓库记录: {target}")
    return True


@judge_repo_path
def ls_repo(path: str = None, *, _repo=None, _cwd=None) -> bool:
    target = _cwd if not path else (_cwd / path).resolve()
    if not _validate_repo_path(target, _repo):
        return False
    if target.is_dir():
        for item in target.iterdir():
            if item.name in EXCLUDED_FILES:
                continue
            print(f"  {'d' if item.is_dir() else '-'} {item.name}")
    else:
        print(f"  - {target.name}")
    return True


@judge_repo_path
def cp_file(src: str, dst: str = None, *, _repo=None, _cwd=None) -> bool:
    src_path = Path(src).expanduser().resolve()
    if not src_path.exists():
        print(f"[错误] 源路径不存在: {src_path}")
        return False

    if dst:
        dst_path = (_cwd / dst).resolve()
        if not _validate_repo_path(dst_path.parent, _repo, allow_non_exist=True):
            return False
    else:
        dst_path = _cwd / src_path.name

    try:
        if src_path.is_file():
            shutil.copy2(src_path, dst_path)
        else:
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        print(f"[ownpygit] 已拷贝: {src_path} -> {dst_path}")
        return True
    except Exception as e:
        print(f"[错误] 拷贝失败: {e}")
        return False


@judge_repo_path
def ocp_file(src: str, dst: str, *, _repo=None, _cwd=None) -> bool:
    src_path = (_cwd / src).resolve()
    if not _validate_repo_path(src_path, _repo):
        return False

    dst_path = Path(dst).expanduser().resolve()
    if dst_path.is_dir():
        dst_path = dst_path / src_path.name

    try:
        if src_path.is_file():
            shutil.copy2(src_path, dst_path)
        else:
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        print(f"[ownpygit] 已拷贝: {src_path} -> {dst_path}")
        return True
    except Exception as e:
        print(f"[错误] 拷贝失败: {e}")
        return False


@judge_repo_path
def compare_files(args: list, *, _repo=None, _cwd=None) -> bool:
    if not args:
        args = [str(_cwd)]

    for path in args:
        src = Path(path).expanduser().resolve()
        if not src.exists():
            print(f"[错误] 源路径不存在: {src}")
            continue

        if src.is_dir():
            src_files = {f.name for f in src.iterdir() if f.is_file()}
            dst_files = {f.name for f in _cwd.iterdir() if f.is_file()}
            common = src_files & dst_files
            print(f"[ownpygit] 对比目录: {src}")
            for name in common:
                if filecmp.cmp(src / name, _cwd / name, shallow=False):
                    print(f"  [一致] {name}")
                else:
                    print(f"  [差异] {name}")
            for name in src_files - common:
                print(f"  [仅源] {name}")
            for name in dst_files - common:
                print(f"  [仅仓库] {name}")
        else:
            dst = _cwd / src.name
            if not dst.exists():
                print(f"[ownpygit] 仓库中不存在: {dst}")
                continue
            print(f"[ownpygit] 对比文件: {src}")
            if filecmp.cmp(src, dst, shallow=False):
                print(f"  [一致]")
            else:
                print(f"  [差异]")
    return True


@judge_repo_path
def run_git_command(git_args: list, *, _repo=None, _cwd=None) -> bool:
    result = subprocess.run(["git", "-C", str(_repo)] + git_args,
                            check=False)
    return result.returncode == 0

@judge_repo_path
def cd_repo(path: str = None, *, _repo=None, _cwd=None) -> bool:
    if path == '-':
        # 使用实际进程的工作目录判断当前位置
        actual_cwd = Path.cwd()
        if actual_cwd.is_relative_to(_repo):
            # 当前在仓库内：输出进入仓库前的目录
            print("当前在仓库内，切换到进入仓库前的目录")
            prev_dir = _read_out_working_dir()
            if prev_dir:
                if prev_dir.exists():
                    print(f"cd {prev_dir}")
                else:
                    print("[ownpygit] 错误: 保存的初始目录无效")
                    return False
            else:
                print("[ownpygit] 错误: 未保存初始目录")
                return False
        else:
            print("当前在仓库外，切换到仓库内的工作目录")
            # 当前在仓库外：输出软件记录的工作目录
            # 保存当前实际进程目录（用于 cd -）
            _save_out_working_dir(_repo)
            print(f"cd {_cwd}")
        return True

    # 实际切换目录（path 不是 '-'）
    if path is None:
        target = _repo
    else:
        target = (_cwd / path).resolve()
        if not target.is_relative_to(_repo):
            print(f"[ownpygit] 错误: 路径不在仓库内: {target}")
            return False

    if not target.exists():
        print(f"[ownpygit] 错误: 路径不存在: {target}")
        return False
    if not target.is_dir():
        print(f"[ownpygit] 错误: 路径不是目录: {target}")
        return False
    
    # 实际切换进程目录
    os.chdir(str(target))
    # 更新软件记录的工作目录
    CURRENT_DIR_FILE.write_text(str(target), encoding='utf-8')
    print(f"[ownpygit] 已切换到目录: {target}")
    return True


# ========== 命令行分发 ==========
def _print_help():
    print("""Usage:
  ownpygit create-repo <path> [alias]   创建仓库并可选设置别名
  ownpygit set-repo <path>              设置激活仓库
  ownpygit get-repo                     查看当前仓库
  ownpygit list-repo                    列出历史仓库
  ownpygit delete-repo <path/alias> [--remove-dir]  删除仓库记录或目录
  ownpygit <git command>                执行任意Git命令（如 add, commit）
  ownpygit ls [<relpath>]               列出仓库工作目录下的内容
  ownpygit compare <file|dir>           对比文件/目录与仓库工作目录
  ownpygit cp <src> [<dst>]             拷贝文件/目录到仓库工作目录或指定的相对仓库工作目录的路径
  ownpygit ocp <src> <dst>              从仓库内拷贝文件/目录到外部
  ownpygit cd [<path>|-]                切换仓库工作目录或返回仓库工作目录或外部目录
  ownpygit --path                       显示配置目录
  ownpygit --version                    显示版本信息
Options:
  -h, --help                            显示此帮助
""")


def cli():
    _ensure_db_dir()
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        _print_help()
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    # 命令映射（函数，最小参数数量，错误提示）
    handlers = {
        "set-repo": (lambda: set_repo(args[0]), 1, "请指定仓库路径"),
        "get-repo": (lambda: print(get_repo()), 0, None),
        "list-repo": (list_repos, 0, None),
        "create-repo": (lambda: create_repo(args[0], args[1] if len(args) > 1 else None), 1, "请指定仓库路径"),
        "delete-repo": (lambda: delete_repo(args[0], "--remove-dir" in args), 1, "请指定要删除的路径或别名"),
        "ls": (lambda: ls_repo(args[0] if args else None), 0, None),
        "compare": (lambda: compare_files(args), 1, "请指定要对比的文件路径"),
        "cp": (lambda: cp_file(args[0], args[1] if len(args) > 1 else None), 1, "请指定要拷贝的文件路径"),
        "ocp": (lambda: ocp_file(args[0], args[1]), 2, "请指定要拷贝的仓库文件路径和目标路径"),
        "cd": (lambda: cd_repo(args[0] if args else None), 0, None),
        "--path": (lambda: print(DB_DIR), 0, None),
        "--version": (lambda: _print_version(), 0, None),
    }

    if cmd in handlers:
        func, min_args, err_msg = handlers[cmd]
        if len(args) < min_args:
            if err_msg:
                print(f"[错误] {err_msg}")
            return
        try:
            func()
        except Exception as e:
            print(f"[错误] 执行失败: {e}")
    else:
        # 默认当作 git 命令执行
        run_git_command(sys.argv[1:])


def _print_version():
    try:
        from cmdbox.cmdbox import _version
        _version()
    except ImportError:
        print("ownpygit version 0.0.0")


def main():
    try:
        cli()
    except KeyboardInterrupt:
        print("\nCtrl+C")
        sys.exit(0)


if __name__ == "__main__":
    sys.exit(main())