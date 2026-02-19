# cmdbox 命令行工具集

## 功能介绍
cmdbox 是一个命令行工具集合，包含以下功能模块：
- **ownpygit**: Git仓库管理工具，提供仓库创建/切换、文件对比拷贝等功能
- **cccmd**: 命令收集器，可添加/删除/搜索常用命令
- **taskbm**: 后台任务管理器，提供任务跟踪和管理功能
- **pycompare**: 文本对比工具，支持并行对比和差异高亮显示
- **cmdr**: 命令注册工具，可注册自定义命令

## 命令
查看支持的命令
```bash
cmdbox --list
```

## 下载代码
```bash
git clone https://gitee.com/binnchern/cmdbox.git
```
## 配置
默认配置文件路径：`~/.cmdbox`
包含的命令可以分别配置路径，具体配置参照命令文档

## 开发环境部署
1. 创建虚拟环境
```bash
python -m venv .venv
.venv\Scripts\activate
```
2. 安装
```bash
pip install -e .[dev]
```
3. 安装pre-commit hook，用于版本号自动化管理
```bash
pre-commit install -t commit-msg
```
版本号升级方案基于setuptools-git-versioning实现。
版本号（X.Y.Z）升级说明：
升级Y版本号：commit msg以"newfeat"开头，"newfeat!"认为无效msg，会报错
升级X版本号：commit msg以"feat!"开头

## 发布模式部署
1. 全局环境安装pipx
```bash
# 1.安装pipx包
pip install pipx
# 2.添加pipx命令到系统环境变量
python -m pipx ensurepath
# 3. 重启命令行窗口
pipx --version
# 如果显示版本号，说明安装成功
```
2. 安装
```bash
pipx install .
```
3. 查看已安装的命令
```bash
> pipx list
venvs are in C:\Users\bing\pipx\venvs
apps are exposed on your $PATH at C:\Users\bing\.local\bin
manual pages are exposed at C:\Users\bing\.local\share\man
   package cmdbox 0.1.0.post3+dirty, installed using Python 3.11.2
    - cccmd.exe
    - cmdbox.exe
    - ownpygit.exe
    - taskbm.exe
```
4. 查看命令帮助
```bash
cccmd --help
ownpygit --help
taskbm --help
cmdbox --help
```
cmdbox只是查看包含的命令行工具，不具备其他能力。

## 注意
1. 部署操作都是在代码根目录下执行
2. 如果要求在任意位置可使用命令且与全局环境隔离，使用"发布模式部署"
