# 任务管理器 (Task Manager)

一个命令行任务管理工具，可以提交、查看、终止和管理后台任务。

## 功能特性

- 提交后台任务并自动记录日志
- 查看所有运行中和已完成的任务
- 终止指定任务
- 清理已结束任务

## 安装
正式环境
```bash
pipx install .
```
开发模式
```bash
pipx install -e .
```

## 使用方法

### 提交任务
```bash
# 单次任务
taskbm submit "your_command" --name "任务名称"
# 循环任务，直到命令执行成功
taskbm submit "your_command" --name "任务名称" --until-succeed --interval 5
```

### 列出所有任务
```bash
taskbm list
```

### 终止任务
```bash
taskbm kill <task_id>
```

### 清理已结束任务
```bash
taskbm clean
```
