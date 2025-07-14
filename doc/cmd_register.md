# 命令注册工具 (cmdr)

## 功能概述

命令注册工具用于将自定义命令注册到系统中，支持以下功能：

1. 注册自定义命令别名
2. 管理命令分组（项目）
3. 同步配置与安装状态
4. 列出已注册命令
5. 移除已注册命令

## 安装
[查看安装说明](start.md)

## 使用说明

### 基本命令

```bash
cmdr --help
Usage: cmdr [OPTIONS] COMMAND [ARGS]...

  命令注册工具，用于注册自定义命令。

  把不能通过命令行打开的工具注册为命令行打开的工具，通过命令行打开。
  把复杂的命令注册为简单的命令。

Options:
  -v, --version  显示版本号
  --debug        调试模式
  --path         获取配置文件路径
  --help         Show this message and exit.

Commands:
  add     注册自定义命令
  list    列出所有自定义命令。
  remove  删除自定义命令。
  sync    同步配置的自定义命令和安装的自定义命令，使配置和安装保持一致。

  cmdr COMMAND --help，查看子命令更多帮助
```

### 选项

- `-v, --version`: 显示版本号
- `--debug`: 调试模式
- `--path`: 获取配置文件路径

### 子命令

#### 1. 添加命令 (add)

```bash
cmdr add ALIAS COMMAND [OPTIONS]
```

参数：
- `ALIAS`: 自定义命令别名
- `COMMAND`: 实际执行的命令

选项：
- `-d, --description`: 命令描述
- `-p, --project`: 分组名称（默认为'default'）
- `--save-temp`: 保存中间临时文件

示例：
```bash
cmdr add mynotepad "C:\\Program Files\\Notepad++\\notepad++.exe" -d 'notepad++命令行打开文件'
mynotepad
# 查看命令帮助。帮助内容包含封装命令添加的帮助信息及被封装命令本身的帮助信息。
# 命令选项可以都可以使用
mynotepad --help
# 创建命令并打开文件
mynotepad test.txt
```

#### 2. 移除命令 (remove)

```bash
cmdr remove [ALIAS] [OPTIONS]
```

参数：
- `ALIAS`: 要移除的命令别名

选项：
- `-p, --project`: 指定项目名称（移除整个项目）

示例：
```bash
cmdr remove mycmd
cmdr remove -p myproject  # 移除整个项目
```

#### 3. 列出命令 (list)

```bash
cmdr list [OPTIONS ]
```

选项：
- `-p, --project`: 指定项目名称

#### 4. 同步命令 (sync)

```bash
cmdr sync [-s STRATEGY]
```

选项：
- `-s, --strategy`: 同步策略

策略：
- `installed`: 同步已安装的命令
- `configure`: 同步配置的命令
- `mix`: 混合同步

### 配置文件

默认配置文件路径：`~/.cmdbox/cmd_register/cmd_register.toml`
可以通过配置环境变量`CMD_REGISTER_DB`指定配置文件路径。

## 开发说明

### 代码结构

- `cmd_register.py`: 核心注册逻辑
- `cli.py`: 命令行接口
- `py_project/`: 项目安装管理。命令组已自动生成的python项目为单元，在代码中使用pipx安装管理命令
