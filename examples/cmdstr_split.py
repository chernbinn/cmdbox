import shlex
import os
import shlex

def _standardize_command(command: list) -> str:
    if not isinstance(command, list) or not command:
        raise ValueError("command must be a non-empty list")

    
    if os.name == 'nt':
        """
        # 非彻底解决问题的patch,至少解决cmd /c cmd的命令，cmd是一个单命令，不可以是组合命令
        first_cmd = command[0].lower().lstrip()
        if first_cmd == "cmd" and len(command) > 2 and command[1].lower() == "/c":
            pass
        elif first_cmd.startswith("cmd ") and len(first_cmd.split()) > 2:
            seqs = first_cmd.split()
            command = ["cmd", "/c"] + seqs[2:] + command[1:]
        #
        """
        from subprocess import list2cmdline
        # Windows：使用 list2cmdline 处理整个命令+参数
        print(f"+++command: {command}")
        command_str = list2cmdline(command) # 有局限性，仅限windows平台使用
    else:
        command_str = shlex.join(command) if hasattr(shlex, 'join') else " ".join(arg for arg in command)
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
    print(f"input path: {path}")
    # repr会根据字符串本身的引号，自动错开添加引号
    strv = repr(path)
    print(f"repr path: {strv}")

    return strv[1:-1]

def generate_command(args: list) -> str:
    base_command = "'C:\\Program Files\\Notepad++\\notepad++.exe'"
    base_command = ensure_path(base_command)

    parts = smart_split(base_command)
    print(f"parts: {parts}")
    print(f"repr parts: {repr(parts)}")
    print(f"single command: {_standardize_command(parts)}")

    parts.extend(args)
    print(f"parts: {parts}")
    return _standardize_command(parts)

def generate_command_1(args: list) -> str:
    base_command = '"C:\\Program Files\\Notepad++\\notepad++.exe"  test'
    base_command = ensure_path(base_command)
    parts = smart_split(base_command)
    print(f"parts: {parts}")
    print(f"repr parts: {repr(parts)}")
    print(f"single command: {_standardize_command(parts)}")

    parts.extend(args)
    print(f"parts: {parts}")
    return _standardize_command(parts)

def main():
    cmdstr = '"akdfja adjfalf" agadljk'
    parts = smart_split(cmdstr)
    print(parts)
    print()
    cmdstr = 'aldjk | aldfjk | "agadljk aldkf"'
    parts = smart_split(cmdstr)
    print(_standardize_command(parts))
    print()
    command = r"C:\\Program Files\\Notepad++\\notepad++.exe"
    print(shlex.quote(command))
    print("smart_split:", smart_split(command))
    print()
    command = r'"C:\\Program Files\\Notepad++\\notepad++.exe" -multiInst afad'
    print(_standardize_command(smart_split(command)))
    print()
    command_parts = ['git', 'commit', '-m', 'fix: bug']
    print(fr"""
    command_seqs = {repr(command_parts)}
    """)
    print()
    command = generate_command(["-multiInst", "afad"])
    print("repr generate command: ", repr(command))
    print("generate command: ", command)
    # expect: '"C:\\\\Program Files\\\\Notepad++\\\\notepad++.exe" -multiInst afad'
    print()
    command = generate_command_1(["-multiInst", "afad"])
    print("repr generate command 1: ", repr(command))
    print("generate command 1: ", command)
    # expect: '"C:\\\\Program Files\\\\Notepad++\\\\notepad++.exe" test -multiInst afad'

if __name__ == '__main__':
    main()

"""
总结：
1.命令中的反斜杠不可以直接使用，不能使用转义字符，否则命令会被识别错误
2.shlex.split()已空格为分隔符，将命令字符串解析为命令参数列表，如果空格在引号内，不做拆分。
    注意：1》这里的引号必须包含在被拆分字符串内
         2》包含字符串本身的引号会在处理字符串时被移除，相当于只是字符串的容器。因此需要字符串本身包含引号，引号需要在字符串容器之内被包含
         3》如果容器符号和被包含的引号相同，被包含的引号会被加上转义字符
3.repr同时会输出字符串容器本身，即包括引号。本质上repr是改变了原本字符串的值，相当于生成了一个新的字符串，字符串添加了原字符串的容器引号。
即把用户输入字符串使用的字符串容器引号赋值为字符串的值，从而接收的字符串内容多了一部分容器引号。在使用shlex拆分时会被识别为一个整体，从而无法有效拆分
"""