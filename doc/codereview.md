# codereview

代码审查工具，用于同步上游分支到 Gerrit 审核分支，将上游的 merge commit 转换为线性提交，便于代码审核。
依赖搭建好的gerrit服务，需要在gerrit服务端配置好项目。gerrit本地搭建，参照仓库
- gitee local_gerrit https://gitee.com/binnchern/local_gerrit
- github local_gerrit https://github.com/binnchern/local_gerrit

## 功能概述

codereview 工具用于管理 Gerrit 代码审查工作流程，支持以下功能：

1. 同步上游分支到 Gerrit 审核分支
2. 智能处理 merge commit，转换为线性提交
3. 项目配置管理
4. 提交类型分析
5. 同步状态跟踪

## 安装

[查看安装说明](start.md)

## 使用说明

### 基本命令

```bash
codereview --help
Usage: codereview [OPTIONS] COMMAND [ARGS]...

  代码审查工具 - 同步上游分支到 Gerrit 审核分支

Options:
  --help  Show this message and exit.

Commands:
  analyze  分析单个 commit 的类型
  config   配置管理命令
  sync     同步上游分支到 Gerrit 审核分支
```

### 配置管理命令 (config)

配置管理提供多个项目的配置文件，配置存储在 `~/.gerrit_review/` 目录下。

#### 1. 添加项目配置 (add)

```bash
codereview config add <project>
```

添加新项目配置，会启动交互式向导，填写配置项包括：
- `repo_path`: 项目根路径（默认为当前目录
- `upstream_remote`: 上游远程仓库（默认：origin
- `remote_branch`: 上游分支（默认：main）
- `track_branch`: 本地追踪分支（默认：main）
- `target_branch`: 目标分支（默认：gerrit-main）
- `gerrit_remote`: Gerrit远程仓库（默认：gerrit）
- `gerrit_branch`: Gerrit分支（默认：gerrit-main）

示例：
```bash
codereview config add myproject
```

#### 2. 删除项目配置 (del)

```bash
codereview config del <project>
```

#### 3. 显示项目配置 (show)

```bash
codereview config show <project>
```

#### 4. 修改项目配置 (set)

```bash
codereview config set <project>
```

交互式修改已有项目配置。

#### 5. 重置项目配置 (reset)

```bash
codereview config reset <project>
```

#### 6. 显示项目同步状态 (show-state)

```bash
codereview config show-state <project>
```

显示上次成功同步的最后一个 commit。

### 同步命令 (sync)

```bash
codereview sync <project>
```

执行完整的同步流程：

1. 检查当前分支
2. 更新本地追踪分支
3. 从上次同步点开始获取新提交
4. 智能处理 merge commit
5. 同步到目标分支

**智能处理 merge commit 的策略：

- **普通提交**：直接 cherry-pick
- **空合并**：跳过
- **有冲突的合并**：squash 为一个提交
- **无冲突且子分支线性**：逐个 cherry-pick 子分支的所有提交
- **子分支含有 merge commit**：整体 squash 为一个提交

### 分析命令 (analyze)

```bash
codereview analyze <commit_hash>
```

分析单个 commit 的类型，包括：
- 判断是否为普通提交
- 判断是否为 merge commit
- 判断 merge commit 的状态

示例：
```bash
codereview analyze abc123
```

## 配置文件

默认配置文件路径：`~/.gerrit_review/<project>.json

可以配置环境变量 `GERIT_REVIEW_CONFIG` 指定配置目录。

配置文件格式：
```json
{
  "repo_path": "/path/to/repo",
  "upstream_remote": "origin",
  "remote_branch": "main",
  "track_branch": "main",
  "target_branch": "gerrit-main",
  "gerrit_remote": "gerrit",
  "gerrit_branch": "gerrit-main"
}
```

## 开发说明

### 代码结构

- [codereview.py](file:///f:/python_programs/shellcommand/cmdbox/src/cmdbox_commands/codereview/codereview.py): 命令行入口
- [config.py](file:///f:/python_programs/shellcommand/cmdbox/src/cmdbox_commands/codereview/config.py): 配置管理
- [sync.py](file:///f:/python_programs/shellcommand/cmdbox/src/cmdbox_commands/codereview/sync.py): 同步逻辑
- [git_operations.py](file:///f:/python_programs/shellcommand/cmdbox/src/cmdbox_commands/codereview/git_operations.py): Git 操作封装
- [analyze.py](file:///f:/python_programs/shellcommand/cmdbox/src/cmdbox_commands/codereview/analyze.py): 提交分析
- [logger.py](file:///f:/python_programs/shellcommand/cmdbox/src/cmdbox_commands/codereview/logger.py): 日志配置

## 使用示例

### 快速开始

1. 添加项目配置：
```bash
codereview config add myproject
```

2. 执行同步：
```bash
codereview sync myproject
```

3. 推送到 Gerrit 进行审核：
```bash
git push gerrit HEAD:refs/for/gerrit-main
```

### 分析提交

```bash
# 分析某个提交
codereview analyze abc1234

# 查看配置
codereview config show myproject

# 查看同步状态
codereview config show-state myproject
```
