import argparse
import os
from pathlib import Path
from cmdbox_commands.command_collector.CommandCollector import CommandCollector

class CustomHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)
    
    # 可用于重构usage格式
    def _format_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = "usage: "
        if usage is None and len(actions) > 0:
            usage = "cccmd [-h|--help] [COMMAND [OPTIONS]]"
        return super()._format_usage(usage, actions, groups, prefix).replace("usage: ", "usage: ", 1)
    
    def _format_action(self, action):
        if isinstance(action, argparse._SubParsersAction):
            parts = []
            #parts.append("COMMANDS:")
            # 这里收集所有子命令的帮助信息，用于显示在COMMANDS部分的内容
            subactions = action._get_subactions()
            for subaction in subactions:
                parts.append(f"    {subaction.dest.ljust(8)}{subaction.help}")
            return "\n".join(parts) + "\n"
        return super()._format_action(action)

def setup_main_parser():
    parser = argparse.ArgumentParser(
        prog="cccmd",
        description="命令收集器",
        formatter_class=CustomHelpFormatter,
        add_help=False,
        #usage="cccmd [-h|--help] [COMMAND [OPTIONS]]"
    )
    
    # 全局选项
    parser.add_argument(
        '-h', '--help',
        action='help',
        help='显示帮助信息'
    )
    # 输出存储目录    
    parser.add_argument(
        '-s', '--storage',
        action='store_true',
        help='显示当前 STORAGE_DIR 配置路径'
    )
    # 查看版本号   
    parser.add_argument(
        '-v', '--version',
        action='store_true',
        help='显示cmdbox版本号'
    )
    # 自定义帮助信息
    parser.epilog = "使用 'cccmd COMMAND --help|-h' 查看具体命令帮助"
    
    # 命令分组
    subparsers = parser.add_subparsers(
        title='COMMANDS',
        dest='action',
        metavar=''
    )

    # add 命令
    add_parser = subparsers.add_parser(
        'add',
        help='添加新命令到模块',
        formatter_class=CustomHelpFormatter,
        add_help=False,
        usage="cccmd add [-h|--help] module -c COMMAND -d DESCRIPTION"
    )
    add_parser.add_argument('module', help='目标模块名称')
    add_parser.add_argument('-c', '--command', required=True, help='命令内容')
    add_parser.add_argument('-d', '--description', required=True, help='命令描述信息')
    add_parser.add_argument('-h', '--help', action='help', help='显示此帮助信息')

    # delete 命令
    delete_parser = subparsers.add_parser(
        'del',
        help='删除指定模块或命令',
        formatter_class=CustomHelpFormatter,
        add_help=False,
        usage="cccmd del [-h|--help] module [--index INDEX]"
    )
    delete_parser.add_argument("module", help="模块名称")
    delete_parser.add_argument("--index", type=int, help="要删除的命令索引（不指定则删除整个模块）")
    delete_parser.add_argument('-h', '--help', action='help', help='显示此帮助信息')

    # 列出模块
    modules_parser = subparsers.add_parser(
        'modules',
        help='列出所有模块',
        formatter_class=CustomHelpFormatter,
        add_help=False,
        usage="cccmd modules [-h|--help]"
    )
    modules_parser.add_argument("module", help="模块名称")
    modules_parser.add_argument('-h', '--help', action='help', help='显示此帮助信息')

    # 列出模块/命令
    list_parser = subparsers.add_parser(
        'list',
        help='列出模块或命令',
        formatter_class=CustomHelpFormatter,
        add_help=False,
        usage="cccmd list [-h|--help] [module]"
    )
    list_parser.add_argument("module", nargs="?", help="模块名称（可选）")
    list_parser.add_argument('-h', '--help', action='help', help='显示此帮助信息')

    # 搜索命令
    search_parser = subparsers.add_parser(
        'search',
        help='搜索命令',
        formatter_class=CustomHelpFormatter,
        add_help=False,
        usage="cccmd search [-h|--help] keyword"
    )
    search_parser.add_argument("keyword", help="搜索关键词")
    search_parser.add_argument('-h', '--help', action='help', help='显示此帮助信息')

    return parser

def main():
    #import sys
    #print("cccmd.py使用的库路径:", [p for p in sys.path if 'site-packages' in p])
    storage_dir = os.environ.get("STORAGE_DIR", os.fspath(Path.home() / ".command_collector"))
    # print("---+++ storage_dir:", storage_dir)
    collector = CommandCollector(storage_dir) 
    
    parser = setup_main_parser()
    args = parser.parse_args()

    if args.storage:
        print(f"当前 STORAGE_DIR 配置路径: {storage_dir}")
        return
    
    if args.version:
        try:
            from cmdbox.cmdbox import _version
            _version()
        except:
            import traceback
            traceback.print_exc()
            print("cmdbox version 0.0.0")
        return

    if not args.action:
        parser.print_help()
        return

    if args.action == "add":
        collector.add_command(args.module, args.command, args.description)
    elif args.action == "del":
        res = collector.delete_command(args.module, args.index)
        if res:
            if args.index is not None:
                collector.list_commands(args.module)
            #else:
            #    collector.list_modules()

    elif args.action == "modules":
        collector.list_modules()
    elif args.action == "list":
        if args.module:  # 如果指定了模块
            collector.list_commands(args.module)
        else:  # 如果没有指定模块
            collector.list_modules()
    elif args.action == "search":
        results = collector.search_commands(args.keyword)
        for module, commands in results.items():
            print(f"\n模块 [{module}]:")
            for cmd in commands:
                print(f"{cmd['command']: <30} # {cmd['description']}")

if __name__ == "__main__":
    main()
