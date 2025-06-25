import os
import json
from pathlib import Path
from typing import Dict, List
from colorama import init, Fore

# 控制ASCII是否转码转码，转码为True；
# 如果转码，txt打开json文件，中文显示为编码；不转码，utf-8编码打开文件中文显示正常
CAHGE_CODING = False

class CommandCollector:
    def __init__(self, storage_dir: str = os.fspath(Path(__file__).parent.parent.parent / ".command_collector")):
        self.storage_dir = Path(storage_dir).expanduser()
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_module_path(self, module: str) -> Path:
        return self.storage_dir / f"{module}.json"

    def add_command(self, module: str, command: str, description: str):
        """添加命令到指定模块"""
        module_path = self._get_module_path(module)
        data = self._load_module(module_path)
            
        # 找到并替换
        for idx, cmd in enumerate(data):
            if cmd['command'] == command:
                # 提示是否覆盖
                print(f"命令 [{command}] 已存在于模块 [{module}]")
                confirm = input(f"是否覆盖模块 [{module}] 中的命令 [{command}] 吗？(y/n): ")
                if confirm.lower()!= 'y':
                    print("取消添加")
                    return False
                data[idx] = {
                    "command": command,
                    "description": description
                }

                with open(module_path, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=CAHGE_CODING)
                print(f"命令已更新到模块 [{module}]")
                return True
        
        data.append({
            "command": command,
            "description": description
        })
        
        # 使用json格式保存，支持注释
        with open(module_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=CAHGE_CODING)
        print(f"命令已添加到模块 [{module}]")

    def delete_command(self, module: str, command_index: int = None):
        """删除指定模块的命令或整个模块"""
        module_path = self._get_module_path(module)
        if not module_path.exists():
            print(f"模块 [{module}] 不存在")
            return False
        
        data = self._load_module(module_path)
        
        if command_index is None:  # 删除整个模块
            confirm = input(f"确认删除整个模块 [{module}] 吗？(y/n): ")
            if confirm.lower() != 'y':
                print("取消删除")
                return False
            module_path.unlink()
            print(f"模块 [{module}] 已删除")
            return True
        else:  # 删除指定命令
            try:
                deleted = data.pop(command_index)
                with open(module_path, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=CAHGE_CODING)
                print(f"已从模块 [{module}] 删除命令: {deleted['command']}")
                # 如果data为空，删除整个模块
                if not data:
                    module_path.unlink()
                    print(f"模块 [{module}] 已清空，已删除模块")
                return True
            except IndexError:
                print(f"错误: 命令索引 {command_index} 超出范围")
                return False

    def _list_modules(self) -> List[str]:
        """列出所有模块"""
        return [
            f.stem for f in self.storage_dir.glob("*.json") 
            if f.is_file()
        ]

    def list_modules(self):
        modules = self._list_modules()
        print("\n可用模块:")
        for mod in modules:
            print(f"- {mod}")

    def _list_commands(self, module: str) -> List[Dict]:
        """列出指定模块的所有命令"""
        module_path = self._get_module_path(module)
        if not module_path.exists():
            return []
        return self._load_module(module_path)

    def list_commands(self, module: str) -> List[Dict]:
        """列出指定模块的所有命令（带索引号）"""
        init()  # 初始化colorama
        print()
        module_path = self._get_module_path(module)
        if not module_path.exists():
            print(f"模块 [{module}] 不存在")
            return False
        
        commands = self._load_module(module_path)
        if not commands:
            print(f"模块 [{module}] 中没有命令")
            return True
        
        print(f"模块 [{module}] 中的命令:")
        for idx, cmd in enumerate(commands):
            # 格式化输出：索引 + 命令 + 描述（自动换行对齐）
            cmd_line = f"{idx}: {cmd['command']}"
            #if cmd['description']:
            #    # 计算对齐空格（固定30字符或命令长度+2，取较大值）
            #    align_len = max(30, len(cmd['command']) + 2)
            #    print(f"{cmd_line.ljust(align_len)} # {cmd['description']}")
            #else:
            #    print(cmd_line)
            print(
                f"{Fore.YELLOW}{idx}:{Fore.RESET} {Fore.CYAN}{cmd['command']}{Fore.RESET}"
                #f"{' ' * (max(30, len(cmd['command']) - len(cmd['command'])))}"
                f"{Fore.GREEN} #{cmd['description']}{Fore.RESET}"
            )
        return True

    def search_commands(self, keyword: str, _module: str = None) -> Dict[str, List[Dict]]:
        """全局搜索命令"""
        results = {}
        target_modules = []
        if _module != None:
            target_modules.append(_module)
        else:
            target_modules = self._list_modules()

        for module in target_modules:
            commands = [
                cmd for cmd in self._list_commands(module)
                if keyword.lower() in cmd["command"].lower() or 
                   keyword.lower() in cmd["description"].lower()
            ]
            if commands:
                results[module] = commands
        return results

    def _load_module(self, path: Path) -> List[Dict]:
        """加载模块数据"""
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)