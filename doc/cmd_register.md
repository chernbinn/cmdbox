# 命令注册工具 (cmdr)

## 功能概述

命令注册工具用于将自定义命令注册到系统中，支持以下功能：

1. 注册自定义命令别名
2. 管理命令分组（项目）
3. 同步配置与安装状态
4. 列出已注册命令
5. 移除已注册命令

推荐使用lnb代替该工具，功能更加强大，从设计角度，cmdr的设计方式显得有些重，作为一种范式，保留cmdr源码。lnb的安装方式"npm install -g lnb"，是基于node生态的工具，跨平台使用。如果对python生态更加熟悉，该命令可以扩展为lnb的方式。

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
- `--save-temp`: 保存中间临时文件，便于分析生成的命令工程代码

示例：
```bash
cmdr add mynotepad '"C:\\Program Files\\Notepad++\\notepad++.exe"' -d 'notepad++命令行打开文件' -g --save-temp
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

## 注意事项
### 1.注册命令时注意字符串值的转义问题
例如
```powershell
> cmdr add mynotepad '"C:\\Program Files\\Notepad++\\notepad++.exe"' -g -d "命令行打开notepad++"
```
mynotepad的执行命令"C:\\Program Files\\Notepad++\\notepad++.exe"包含有空格，不许用引号单独括起来，告诉程序这是一个原子参数，不能被空格分割。在windows下路径需要使用转义字符加以保护，使用"\\"。

### 2.多参数命令
```powershell
例如通过命令启动有道云笔记应用
> cmdr add ydnote 'start "" "C:\\Program Files\\ynote-desktop\\youdaonote.exe"' -d '打开有道云笔记' -g
```
-g: 说明程序是异步运行的，否则会同步执行，会阻塞命令行执行其他命令，直到应用退出。
-d: 说明命令的描述，方便查看。
start的第一个参数是一个字符串，这里传值为空字符串。启动一个应用是否需要使用start，取决于实际测试，比如notepad++可以不使用start启动。
在代码中，使用subprocess.Popen运行被封装的命令，为了支持管道，使用shell=True执行，本质上命令运行在cmd.exe终端环境下，因此命令可以现在cmd.exe上测试成功后再使用cmdr添加封装为一个简单的命令。

### 3.集成git支持的linux格式命令

当windows系统安装了git工具，git包含了很多linux下支持的命令，如ls、rm等命令。当习惯了linux命令，能在windows下使用linux命令，是一件开心的事情。
但是在powershell终端或者cmd.exe中存在相同名称的命令，从而出现使用不便，比如，powershell中支持ls命令，使用git下的ls，需要使用cmd /c ls，有些复杂，可以通过cmdr添加为myls
```
cmdr add myls 'ls' -d 'git下的ls命令'
```
注意：这里封装的命令没有使用cmd /c，因为Popen本质运行在cmd.exe下，因此省略cmd /c，当封装的命令myls在powershell中执行的使用，实际上是在cmd.exe下执行ls命令，可以使用myls --ihelp查看到和linux ls一样的命令选项。
再例如rm命令
```
cmdr add myrm 'rm' -d 'git下的rm命令'
```
注意：集成git命令方法，找到git路径，例如
```
C:\Program Files\Git\
```
把以下路径添加到环境变量path下
```
C:\Program Files\Git\mingw64\bin
C:\Program Files\Git\usr\bin
```
windows会支持一些linux系统下常用的命令。

### 4.卸载自定义命令
cmdr remove命令支持卸载自定义命令
```
> cmdr remove --help
Usage: cmdr remove [OPTIONS]

  删除自定义命令。

Options:
  -a, --alias TEXT    自定义命令名称
  -p, --project TEXT  分组名称
  --help              Show this message and exit.
> cmdr remove -a myls
> cmdr remove -p default
```
-p: 分组名称，默认是default。也是实际生成命令组项目的项目名称，通过pipx查看，则是包名。分组命令可以在添加命令时指定
-a: 自定义命令名称
当使用cmdr remove卸载命令失败时，可以分步实现卸载
```
# 第一步，卸载实际安装的命令
# pipx uninstall [包名]
> pipx uninstall default
# 使用pipx卸载，会卸载整个组（包）下的所有命令
# 第二部，使用cmdr remove删除配置文件中的命令
> cmdr remove -a myrm
# 或者，同样删除这个组的命令。删除default组下所有命令
> cmdr remove -p default
# 删除testtest组下所有的命令，在命令行test及python中，test是一个命令，因此不要使用一些类似test的命令作为分组名称
> cmdr remove -p testtest

# 查看安装或卸载情况
> pipx list
venvs are in C:\Users\bing\pipx\venvs
apps are exposed on your $PATH at C:\Users\bing\.local\bin
manual pages are exposed at C:\Users\bing\.local\share\man
   package cmdbox 0.8.0.post8, installed using Python 3.11.2
    - cccmd.exe
    - cmdbox.exe
    - cmdr.exe
    - ownpygit.exe
    - pycompare.exe
    - taskbm.exe
   package default 0.8.0+mnwwi4s7mrswmylvnr2a, installed using Python 3.11.2
    - myls.exe
    - mynotepad.exe
    - myrm.exe
    - ydnote.exe
# 或者
> cmdr list
命令组: default
已安装命令:
  ydnote: start "" "C:\\Program Files\\ynote-desktop\\youdaonote.exe"
  myls: ls
  mynotepad: "C:\\Program Files\\Notepad++\\notepad++.exe"
  myrm: rm
```
