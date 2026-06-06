import os, sys
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

    def add_command(self, module: str, command, description):
        """添加命令到指定模块
        
        Args:
            module: 模块名称
            command: 命令内容（支持多个命令，用换行分隔）
            description: 命令描述（支持多个描述，用换行分隔）
        """
        module_path = self._get_module_path(module)
        data = self._load_module(module_path)
        
        # 如果command或description是列表，则用换行连接
        # if isinstance(command, list):
        #     command = '\n'.join(command)
        # if isinstance(description, list):
        #     description = '\n'.join(description)
        command = '\n'.join(command)
        description = '\n'.join(description)
            
        # 找到并替换
        for idx, cmd in enumerate(data):
            if cmd['command'] == command:
                # 提示是否覆盖
                print(f"命令 [{command}] 已存在于模块 [{module}]")
                confirm = input(f"是否覆盖模块 [{module}] 中的命令 [{command}] 吗？(y/n): ")
                if confirm.lower()!= 'y':
                    print("取消添加")
                    return True
                data[idx] = {
                    "command": command,
                    "description": description
                }

                self._save_module(module_path, data)
                print(f"命令已更新到模块 [{module}]")
                return True
        
        data.append({
            "command": command,
            "description": description
        })
        
        # 使用json格式保存，支持注释
        self._save_module(module_path, data)
        print(f"命令已添加到模块 [{module}]")
    
    def modify_command(self, module: str, command_index: int = None, command: List[str] = None, description: List[str] = None):
        """修改指定模块的命令或描述"""
        command = '\n'.join(command)
        description = '\n'.join(description)
        
        module_path = self._get_module_path(module)
        if not module_path.exists():
            print(f"模块 [{module}] 不存在")
            return False
        data = self._load_module(module_path)
        
        if command_index is None:
            print(f"必须指定命令索引")
            return False
        elif command_index < 0 or command_index >= len(data):
            print(f"命令索引 [{command_index}] 超出范围")
            return False
        
        if command is None and description is None:
            print(f"必须指定修改后的命令或描述")
            return False
        
        if command is not None:
            data[command_index]['command'] = command
        if description is not None:
            data[command_index]['description'] = description
        
        self._save_module(module_path, data)
        print(f"命令已更新到模块 [{module}]")

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
                self._save_module(module_path, data)
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

    def _show_commands(self, module: str, commands: List[Dict]) -> None:
        """显示指定模块的所有命令"""
        print(f"模块 [{module}] 中的命令:")
        for idx, cmd in enumerate(commands):
            # 分割命令和描述为多行
            cmd_lines = cmd['command'].split('\n')
            desc_lines = cmd['description'].split('\n') if cmd['description'] else []
            
            # 第一行：索引 + 命令
            print(f"{Fore.YELLOW}{idx}:{Fore.RESET} {Fore.CYAN}{cmd_lines[0]}{Fore.RESET}")
            
            # 后续命令行：缩进对齐
            for i in range(1, len(cmd_lines)):
                print(f"{' ' * (len(str(idx)) + 2)}{Fore.CYAN}{cmd_lines[i]}{Fore.RESET}")
            
            # 描述行：每行前加#
            for desc in desc_lines:
                print(f"{' ' * (len(str(idx)) + 2)}{Fore.GREEN}# {desc}{Fore.RESET}")

    def list_commands(self, module: str) -> List[Dict]:
        """列出指定模块的所有命令（带索引号）"""
        init()  # 初始化colorama
        print()
        module_path = self._get_module_path(module)
        if not module_path.exists():
            print(f"模块 [{module}] 不存在")
            return []
        
        commands = self._load_module(module_path)
        if not commands:
            print(f"模块 [{module}] 中没有命令")
            return []
        
        self._show_commands(module, commands)
        return commands

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

        for module, commands in results.items():
            self._show_commands(module, commands)
        return results

    def _load_module(self, path: Path) -> List[Dict]:
        """加载模块数据"""
        if not path.exists():
            return []
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"加载模块 [{path}] 失败: {e}")
            print(f"请检查文件 [{path}] 是否为正确的json格式")
            self._handle_critical_error(e)
        except UnicodeDecodeError as e:
            print(f"加载模块 [{path}] 失败: {e}")
            print(f"请检查文件 [{path}] 是否为utf-8编码")
            self._handle_critical_error(e)
        except Exception as e:
            print(f"加载模块 [{path}] 失败: {e}")
            self._handle_critical_error(e)        

    def _save_module(self, path: Path, data: List[Dict]):
        """保存模块数据"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=CAHGE_CODING)
        except Exception as e:
            print(f"保存模块 [{path}] 失败: {e}")
            self._handle_critical_error(e)

    def _handle_critical_error(self, e: Exception):
        """处理关键错误"""
        print(f"关键错误: {e}")
        print(f"手动备份数据并修复数据，路径：{self.storage_dir}")
        sys.exit(1)
            
