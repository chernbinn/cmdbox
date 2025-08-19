# test_input_behavior.py
import os
import sys
import json
import shlex
import pprint

def test_input():
    print("=" * 60)
    print("Python input() 字符串与路径处理行为测试")
    print("操作系统:", "Windows" if os.name == 'nt' else "Unix/Linux/macOS")
    print("Python 版本:", sys.version)
    print("=" * 60)

    cases = [
        # 描述, 示例输入（你实际输入的内容）
        ("纯路径（含空格）", r'C:\Program Files\Notepad++\notepad++.exe'),
        ("带双引号的路径", r'"C:\Program Files\Notepad++\notepad++.exe"'),
        ("带单引号的路径", r"'C:\Program Files\Notepad++\notepad++.exe'"),
        ("Unix 路径含空格", '/home/user/my docs/file.txt'),
        ("带引号的 Unix 路径", '"/home/user/my docs/file.txt"'),
        ("多个参数（空格分隔）", 'notepad++.exe -multiInst "C:\\My File.txt"'),
        ("含反斜杠转义", r'C:\\Program Files\\App\\app.exe'),
        ("含正斜杠（Unix 风格）", '/usr/bin/python3 /path with spaces/script.py'),
        ("JSON 格式输入", '["/path/with space", "--flag", "value"]'),
        ("空输入", ''),
    ]

    results = []

    for i, (desc, example) in enumerate(cases, 1):
        print(f"\n[{i}] {desc}")
        print(f"   示例输入（你应输入）: {example}")
        print("   请输入相同内容 > ", end='', flush=True)

        try:
            user_input = input()
        except EOFError:
            user_input = ""
            print("(EOF / 空输入)")

        # 分析输入
        result = {
            'description': desc,
            'input_raw': user_input,
            'len': len(user_input),
            'repr': repr(user_input),
            'has_spaces': ' ' in user_input,
            'starts_with_quote': user_input.startswith(('"', "'")),
            'ends_with_quote': user_input.endswith(('"', "'")),
        }

        # 尝试解析为命令行参数
        if user_input.strip():
            try:
                tokens = shlex.split(user_input, posix=(os.name != 'nt'))
                result['shlex_tokens'] = tokens
            except Exception as e:
                result['shlex_tokens'] = f"解析失败: {e}"

            # 尝试解析为 JSON
            try:
                json_parsed = json.loads(user_input)
                result['json_parsed'] = json_parsed
            except Exception:
                result['json_parsed'] = None

        results.append(result)

    # 输出汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for r in results:
        print(f"\n📌 {r['description']}:")
        print(f"   输入内容: {r['input_raw']}")
        print(f"   repr 形式: {r['repr']}")
        print(f"   长度: {r['len']}, 含空格: {r['has_spaces']}")
        if isinstance(r.get('shlex_tokens'), list):
            print(f"   shlex 分词: {r['shlex_tokens']}")
        else:
            print(f"   shlex: {r.get('shlex_tokens', 'N/A')}")
        if r.get('json_parsed'):
            print(f"   JSON 解析: {r['json_parsed']}")

    return results

if __name__ == '__main__':
    test_input()

"""
总结:
1.从终端输入后，终端应用会对输入内容进行解析，使需要转义的字符加上转义符
2.repr是输出字符串原内容，而不是解析后的内容
3.终端执行命令时，对路径中多余的反斜杠不影响识别路径，只要反斜杠是正确转义，即反斜杠是成对的，否则会出现路径被转义错误
4.终端对输入的内容默认自动添加转义字符，在使用时，如果不添加转义字符或者使用repr，赋值为解析后的字符串。实际内存存储的是转义前的字符串。
也即在同一个程序中，一般同一个字符串只会被解析一次。可能存在特殊情况。在解析时包括执行字符串中程序支持的语法，替换为执行结果。
5.跨进程传输内容，总是经过编码再解码，解码后又涉及执行。因此字符串解析过程存在：编码-解码-解释，
编码会根据字符串含义添加转义字符，解码时会根据转义字符解析为原始字符串，解释时会根据字符串在程序中支持的语法执行，不支持的语法则认为是普通字符。
6.在跨进程或程序传输数据时（比如字符串），希望字符串在目标程序中表现为某种格式，则需要避免在中转过程中被解释。
7.跨程序传输字符串，存在很复杂的因素，不同程序支持的解释不同，如果需要正确传输，需要对经过的程序对字符串的处理有很深的理解。
"""