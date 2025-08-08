import shlex
import os

def _standardize_command(command: list) -> str:
    if not isinstance(command, list) or not command:
        raise ValueError("command must be a non-empty list")

    if os.name == 'nt':
        # 非彻底解决问题的patch,至少解决cmd /c cmd的命令，cmd是一个单命令，不可以是组合命令
        first_cmd = command[0].lower().lstrip()
        if first_cmd == "cmd" and len(command) > 2 and command[1].lower() == "/c":
            pass
        elif first_cmd.startswith("cmd ") and len(first_cmd.split()) > 2:
            seqs = first_cmd.split()
            command = ["cmd", "/c"] + seqs[2:] + command[1:]
        #
        from subprocess import list2cmdline
        # Windows：使用 list2cmdline 处理整个命令+参数
        command_str = list2cmdline(command)
    else:
        import shlex
        # 非 Windows：使用 shlex.join（Python 3.8+）或手动拼接
        command_str = shlex.join(command) if hasattr(shlex, 'join') else " ".join(shlex.quote(arg) for arg in command)
    return command_str

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
        # lex = shlex.shlex(s, posix=(os.name != 'nt')) # 实际测试，posix=True时更通用
        lex = shlex.shlex(s, posix=True)
        lex.whitespace_split = True
        lex.escape = ''
        return list(lex)
    except ValueError as e:
        raise ValueError(f"命令解析失败 - 请检查引号匹配: {str(e)}\n原始命令: {s}")


def main():
    cmdstr = '"akdfja adjfalf" agadljk'
    parts = smart_split(cmdstr)
    print(parts)

    cmdstr = 'aldjk | aldfjk | "agadljk aldkf"'
    parts = smart_split(cmdstr)
    print(_standardize_command(parts))

    command = r"C:\\Program Files\\Notepad++\\notepad++.exe"
    print(shlex.quote(command))

    command = r'"C:\\Program Files\\Notepad++\\notepad++.exe" -multiInst afad'
    print(_standardize_command(smart_split(command)))

    command_parts = ['git', 'commit', '-m', 'fix: bug']
    print(fr"""
    command_seqs = {repr(command_parts)}

    """)


if __name__ == '__main__':
    main()