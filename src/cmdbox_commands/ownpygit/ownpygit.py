# -*- coding: utf-8 -*-
import sys, os
import subprocess
from pathlib import Path
import shutil

# 配置目录和文件路径
DB_DIR = Path.home() / ".ownpygit" / "db"
CONFIG_FILE = DB_DIR / "ownpygit_repo.cfg"
HISTORY_FILE = DB_DIR / "ownpygit_history.cfg"
ALIAS_FILE = DB_DIR / "ownpygit_alias.cfg"
CURRENT_DIR_FILE = DB_DIR / "ownpygit_current_dir.cfg"
PREV_DIR_FILE = DB_DIR / "ownpygit_prev_dir.cfg"

def _ensure_db_dir():
    """确保配置目录存在"""
    if DB_DIR.exists():
        return True
    try:
        DB_DIR.mkdir(exist_ok=True)
        # 设置隐藏属性（仅Windows）
        if os.name == 'nt':
            os.system(f'attrib +h "{DB_DIR}"')
        return True
    except Exception as e:
        print(f"[错误] 创建配置目录失败: {e}")
        return False

def _get_working_dir()->Path:
    """确保在执行命令前切换到当前目录"""
    if not CURRENT_DIR_FILE.exists():
        return get_repo()
    with open(CURRENT_DIR_FILE, 'r', encoding='utf-8') as f:
        current_dir = f.read().strip()
    if current_dir and Path(current_dir).exists():
        #os.chdir(current_dir)
        return Path(current_dir)
    return get_repo()

def _judge_repo_path(func):    
    def wapper(*args, **kwargs):
        workingdir = _get_working_dir()
        repo = get_repo()
        if not repo or not workingdir.is_relative_to(repo):
            print(f"[错误] 当前目录不是仓库目录: {workingdir}")
            # 获取func的返回值类型
            return_type = func.__annotations__.get('return')
            if return_type == bool:
                return False
            return None
        print(f"\033[33m[ownpygit] 当前仓库目录: {repo}\033[0m")
        print(f"\033[33m[ownpygit] 当前操作目录: {workingdir}\033[0m\n")
        return func(*args, **kwargs)
    return wapper

def set_repo(repo_path):
    """设置激活仓库路径"""
    repo = Path(repo_path).absolute()
    if not repo.exists():
        print(f"[错误] 路径不存在: {repo}")
        return False
    
    # 自动初始化Git仓库（如果不存在）
    if not (repo / ".git").exists():
        subprocess.run(["git", "init", str(repo)], check=True)
    
    # 写入当前激活仓库
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(str(repo))
    
    # 追加到历史记录文件（不重复)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.touch()
    
    with open(HISTORY_FILE, "r+", encoding="utf-8") as f:
        existing = {line.strip() for line in f.readlines()}
        if str(repo) not in existing:
            f.write(f"{repo}\n")
    
    print(f"[ownpygit] 已设置激活仓库: {repo}")
    return True

def create_repo(repo_path, alias=None):
    """创建新仓库并可选设置别名"""
    repo = Path(repo_path).absolute()
    if repo.exists():
        print(f"[警告] 路径已存在: {repo}")
        return False

    # 创建目录并初始化Git仓库
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True)

    # 设置别名
    if alias:
        if not ALIAS_FILE.exists():
            ALIAS_FILE.touch()
        with open(ALIAS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{alias}={repo}\n")

    # 设置为当前激活仓库
    set_repo(repo)
    print(f"[ownpygit] 已创建仓库: {repo}" + (f" 别名为: {alias}" if alias else ""))
    return True

def get_repo()->Path:
    """获取当前激活仓库"""
    if not CONFIG_FILE.exists():
        print("[ownpygit] 未设置激活仓库")
        return None
    
    with open(CONFIG_FILE, encoding="utf-8") as f:
        repo_path = Path(f.read().strip())
    
    if not repo_path.exists():
        print(f"[警告] 仓库路径不存在: {repo_path}")
        return None
    
    return repo_path

def list_repos():
    """列出所有历史仓库"""
    if not HISTORY_FILE.exists():
        print("[ownpygit] 暂无历史仓库记录")
        return []
    
    with open(HISTORY_FILE, encoding="utf-8") as f:
        repos = [line.strip() for line in f.readlines() if line.strip()]
    
    current_repo = get_repo()
    
    print("历史仓库列表：")
    for i, repo in enumerate(repos, 1):
        prefix = " * " if current_repo and str(current_repo) == repo else "   "
        print(f"{prefix}{i}. {repo}")
    
    return repos

def delete_repo(target, remove_dir=False):
    """删除仓库记录或目录"""
    # 通过别名查找路径
    if ALIAS_FILE.exists():
        with open(ALIAS_FILE, "r", encoding="utf-8") as f:
            aliases = {line.split("=")[0]: line.split("=")[1].strip() for line in f.readlines()}
        if target in aliases:
            target = aliases[target]

    # 删除别名记录
    if ALIAS_FILE.exists():
        with open(ALIAS_FILE, "r+", encoding="utf-8") as f:
            lines = [line for line in f.readlines() if not line.startswith(target + "=")]
            f.seek(0)
            f.writelines(lines)
            f.truncate()

    # 删除历史记录
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r+", encoding="utf-8") as f:
            lines = [line for line in f.readlines() if line.strip() != target]
            f.seek(0)
            f.writelines(lines)
            f.truncate()

    # 删除实际目录
    if remove_dir:
        try:
            repo = Path(target)
            if repo.exists():
                if repo.is_dir():
                    subprocess.run(["rmdir", "/s", "/q", str(repo)], shell=True)
                else:
                    repo.unlink()
                print(f"[ownpygit] 已删除目录: {repo}")
        except Exception as e:
            print(f"[错误] 删除目录失败: {e}")

    print(f"[ownpygit] 已删除仓库记录: {target}")
    return True

@_judge_repo_path
def ls_repo()->None:
    """列出当前激活仓库的文件和目录"""
    repo_dir = _get_working_dir()
    try:
        print(f"[ownpygit] 仓库内容: {repo_dir}")
        repo_path = Path(repo_dir)
        for item in repo_path.iterdir():
            if item.is_dir():
                print(f"  d {item.name}/")
            elif item.is_file():
                print(f"  - {item.name}")
    except Exception as e:
        print(f"[错误] 列出仓库内容失败: {e}")

@_judge_repo_path
def cp_file(file_path, dst_path=None)->bool:
    """将文件拷贝到当前激活仓库"""    
    cwd = _get_working_dir()
    src = Path(file_path)    
    dst = None
    if dst_path:
        dst = cwd / Path(dst_path)
    else:
        dst = cwd / src.name

    print(f"源路径：{src}")
    print(f"目标路径：{dst}")
    if not src.exists():
        print(f"[错误] 源路径不存在: {src}")
        return False
    if not dst.exists():
        print(f"[错误] 目标路径不存在: {dst}")
        return False

    try:
        if src.is_file():            
            shutil.copy2(src, dst)
            print(f"[ownpygit] 文件已拷贝: {src} -> {dst}")
            return True
        else:
            shutil.copytree(src, dst)
            print(f"[ownpygit] 目录已拷贝: {src} -> {dst}")
            return True
    except Exception as e:
        print(f"[错误] 拷贝失败: {e}")
        return False

@_judge_repo_path
def ocp_file(in_path, out_path):
    """将仓库文件拷贝到指定路径"""
    cwd = _get_working_dir()
    in_path = cwd / in_path
    if not in_path.exists():
        print(f"[错误] 仓库路径不存在: {in_path}")
        return False

    out_path = Path(out_path)
    if out_path.is_dir():
        out_path = out_path / in_path.name

    if in_path.is_file():
        try:
            shutil.copy2(in_path, out_path)
            print(f"[ownpygit] 文件已拷贝: {in_path} -> {out_path}")
            return True
        except Exception as e:
            print(f"[错误] 拷贝文件失败: {e}")
            return False
    else:
        try:
            shutil.copytree(in_path, out_path)
            print(f"[ownpygit] 目录已拷贝: {in_path} -> {out_path}")
            return True
        except Exception as e:
            print(f"[错误] 拷贝目录失败: {e}")
            return False

@_judge_repo_path
def compare_files(args)->bool:
    """对比仓库文件和指定文件或目录的内容差异"""
    import filecmp
    repo = get_repo()
    cwd = _get_working_dir()

    if not args:
        # 如果没有指定路径，对比当前目录
        args = [str(cwd)]

    for path in args:
        src = Path(path)
        if not src.exists():
            print(f"[错误] 源路径不存在: {src}")
            continue

        if src.is_dir():
            # 对比目录
            src_files = set(f.name for f in src.iterdir() if f.is_file())
            dst_files = set(f.name for f in cwd.iterdir() if f.is_file())
            common_files = src_files & dst_files

            print(f"[ownpygit] 对比目录: {src}")
            for file_name in common_files:
                src_file = src / file_name
                dst_file = cwd / file_name
                if filecmp.cmp(src_file, dst_file, shallow=False):
                    print(f"  [一致] {src_file} 和 {dst_file}")
                else:
                    print(f"  [差异] {src_file} 和 {dst_file}")
            if len(src_files - common_files) > 0: print()
            for file_name in src_files - common_files:
                print(f"  [差异] {src / file_name} 不在 仓库：{cwd} 中")
            if len(dst_files - common_files) > 0: print()
            for file_name in dst_files - common_files:
                print(f"  [差异] 仓库：{cwd / file_name} 不在 {src} 中")
            print()
        else:
            # 对比单个文件
            if not src.is_file():
                print(f"[错误] 源路径不是文件: {src}")
                continue

            dst = cwd / src.name
            if not dst.exists():
                print(f"[ownpygit] 当前目录中不存在文件: {dst}")
                continue

            print(f"[ownpygit] 对比文件: {src}")
            if filecmp.cmp(src, dst, shallow=False):
                print(f"  [一致] {src} 和 {dst}")
            else:
                print(f"  [差异] {src} 和 {dst}")

    return True

@_judge_repo_path
def run_git_command(git_args)->bool:
    """在激活仓库执行Git命令，自动处理文件不存在的情况"""
    repo = get_repo()
    cwd = _get_working_dir()
    
    try:
        """
        # 特殊处理 add 命令        
        if git_args and git_args[0].lower() == "add":
            files = git_args[1:]
            copied_files = []
            
            for file in files:
                src = Path(file)
                if not src.exists():
                    print(f"[错误] 源文件不存在: {src}")
                    continue
                
                # 拷贝文件到仓库
                dst = cwd / src.name
                try:
                    shutil.copy2(src, dst)
                    copied_files.append(dst.name)
                    print(f"[ownpygit] 已拷贝文件到仓库: {src} -> {dst}")
                except Exception as e:
                    print(f"[错误] 拷贝文件失败: {e}")
                    continue
            
            if not copied_files:
                return False
            
            # 执行真正的git add
            print(f"[ownpygit] 操作仓库: {repo}")
            result = subprocess.run(
                ["git", "-C", str(repo), "add"] + copied_files,
                shell=True,
                check=False
            )
            return result.returncode == 0
        """
        # 普通Git命令
        print(f"[ownpygit] 操作仓库: {repo}")
        result = subprocess.run(
            ["git", "-C", str(repo)] + git_args,
            shell=True,
            check=False
        )
        return result.returncode == 0
    
    except Exception as e:
        print(f"[错误] 执行失败: {e}")
        return False

@_judge_repo_path
def chdir_repo(path):
    """切换仓库子目录"""
    repo = get_repo()    
    if path == None:
        target = repo
    else:
        target = _get_working_dir() / path
    if not target.exists():
        print(f"[错误] 路径不存在: {target}")
        return False
    
    target = target.resolve()
    if not target.is_relative_to(repo):
        print(f"[错误] 目录不是仓库的子目录: {target}")
        return
    
    if not target.is_dir():
        print(f"[错误] 路径不是目录: {target}")
        return False
    
    os.chdir(str(target))
    with open(CURRENT_DIR_FILE, 'w', encoding='utf-8') as f:
        f.write(str(target))
    print(f"[ownpygit] 已切换到目录: {target}")
    return True

# 说明：
# 1.bat脚本是在子进程中运行的，无法通过执行bat命令改变命令行的路径
# 2.鉴于bat的运行机制，cd命令无法直接改变命令行的路径，通过提示信息手动切换路径
@_judge_repo_path
def cd_repo(path=None):
    """切换仓库目录或返回初始目录"""
    repo = get_repo()
    cwd = _get_working_dir()

    if path == "-":
        if not PREV_DIR_FILE.exists():
            print("[错误] 未保存初始目录")
            return False
        with open(PREV_DIR_FILE, 'r', encoding='utf-8') as f:
            prev_dir = f.read().strip()
        if not prev_dir or not Path(prev_dir).exists():
            print("[错误] 初始目录不存在")
            return False
        print(f"cd {prev_dir}")
        return True

    if path is None:
        target = repo
    else:
        target = cwd / path

    if not target.exists():
        print(f"[错误] 路径不存在: {target}")
        return False

    if not target.is_relative_to(repo):
        print(f"[错误] 目录不是仓库的子目录: {target}")
        return False

    # 保存当前目录
    cwd = Path.cwd()
    if not cwd.is_relative_to(repo):
        if not PREV_DIR_FILE.exists():
            PREV_DIR_FILE.touch()
        with open(PREV_DIR_FILE, 'w', encoding='utf-8') as f:
            f.write(str(cwd))

    print(f"cd {target}")
    return True

def is_development_mode():
    """
    判断当前包是否处于开发模式。
    :return: 如果包是以可编辑(-e)模式安装的返回True，否则返回False。
    """
    # 获取所有site-packages目录
    site_paths = [Path(p) for p in sys.path if "site-packages" in p]
    
    # 检查是否存在.egg-link文件
    for path in site_paths:
        # 检查 .egg-link 文件（用于旧版 setuptools）
        if any(path.glob("ownpygit*.egg-link")):
            #print("egg-link")
            return True

        # 检查 __editable__ 文件（用于现代 editable 安装，如 setuptools >=64）
        if any(path.glob("__editable__.ownpygit*.pth")):
            #print("__editable__")
            return True

        # 如果找到了 ownpygit 目录，则说明是正常安装（非开发模式）
        if (path / "ownpygit").exists():
            #print("ownpygit")
            return False

    return True

def main():
    _ensure_db_dir()
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print("Usage:")
        print("  ownpygit create-repo <path> [alias] 创建仓库并可选设置别名")
        print("  ownpygit set-repo <path>   设置激活仓库")
        print("  ownpygit get-repo          查看当前仓库")
        print("  ownpygit list-repo         列出历史仓库")        
        print("  ownpygit delete-repo <path/alias> [--remove-dir] 删除仓库记录或目录")
        print("                             指定--remove-dir参数时，同时删除目录，不指定时只删除记录")
        print("  ownpygit <git命令>         执行Git操作。'git命令'是git命令的参数，如add, commit等，使用ownpygit代替git，参数和直接使用git相同")
        print("  ownpygit ls                列出仓库文件")
        print("  ownpygit compare <file|dir> 指定文件或目录与仓库工作目录下的文件对比")
        print("  ownpygit cp <file|dir> [dst]   将文件拷贝到当前仓库工作目录，如果不指定dst，默认拷贝到当前仓库工作目录且相同名称")
        print("                                 如果指定dst，dst是相对当前仓库工作目录的路径，可以用于指定目标文件的名称")   
        print("  ownpygit ocp <file|dir> <path> 将仓库文件拷贝到指定路径。仓库文件路径是相对于仓库工作目录的路径")
        print("  ownpygit chdir <path>      切换仓库工作目录")
        print("  ownpygit cd <path|->       进入仓库目录或返回初始目录,path是相对目标仓库的子路径，-是返回进入目标仓库前的外部目录")
        print("                             注意：cd命令是进入当前仓库下的目录，不会改变仓库的工作目录")
        print("Options:")
        print("  -h, --help   显示帮助信息")
        print("  --version    显示版本信息")
        return
    
    command = sys.argv[1].lower()
    
    if command == "set-repo":
        if len(sys.argv) < 3:
            print("请指定仓库路径")
            return
        set_repo(sys.argv[2])
    elif command == "get-repo":
        if repo := get_repo():
            print(repo)
    elif command == "list-repo":  # 新增命令处理
        list_repos()
    elif command == "create-repo":
        if len(sys.argv) < 3:
            print("请指定仓库路径")
            return
        alias = sys.argv[3] if len(sys.argv) > 3 else None
        create_repo(sys.argv[2], alias)
    elif command == "--version":
        try:
            from cmdbox.cmdbox import _version
            _version()
        except:
            print("cmdbox version 0.0.0")
    elif command == "ls":
        ls_repo()
    elif command == "delete-repo":
        if len(sys.argv) < 3:
            print("请指定要删除的路径或别名")
            return
        remove_dir = "--remove-dir" in sys.argv
        delete_repo(sys.argv[2], remove_dir)
    elif command == "compare":
        if len(sys.argv) < 3:
            print("请指定要对比的文件路径")
            return
        compare_files(sys.argv[2:])
    elif command == "chdir":
        if len(sys.argv) < 3:
            chdir_repo(None)
            return
        chdir_repo(sys.argv[2])
    elif command == "cd":
        if len(sys.argv) > 3:
            print("[错误] 参数过多")
            return
        path = sys.argv[2] if len(sys.argv) > 2 else None
        cd_repo(path)
    elif command == "cp":
        if len(sys.argv) < 3:
            print("请指定要拷贝的文件路径")
            return
        dst = None
        if len(sys.argv) > 3:
            dst = sys.argv[3]
        cp_file(sys.argv[2], dst)
    elif command == "ocp":
        if len(sys.argv) < 4:
            print("请指定要拷贝的仓库文件路径和目标路径")
            return
        ocp_file(sys.argv[2], sys.argv[3])
    else:
        run_git_command(sys.argv[1:])

if __name__ == "__main__":
    main()