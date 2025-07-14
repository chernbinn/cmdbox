# ownpygit

ownpygit是一个基于Python的Git管理工具，在任意目录对仓库目录进行git操作，基于此实现，快捷的在其他项目目录下添加封装称模块的常用的代码备份到通过ownpygit管理的仓库中。提供了一系列命令，使得用户可以方便地创建、切换和管理多个Git仓库，同时支持标准的Git操作，如添加、提交、推送等。

## 命令概览

1. **create-repo** <路径> [别名] - 创建新仓库并可选设置别名
2. **set-repo** <路径> - 设置激活仓库
3. **get-repo** - 查看当前仓库路径
4. **list-repo** - 列出历史仓库记录
5. **delete-repo** <路径/别名> [--remove-dir] - 删除仓库记录或目录
6. **ls** - 列出仓库文件
7. **compare** <文件|目录> - 对比文件/目录与仓库内容
8. **cp** <文件|目录> [目标路径] - 拷贝文件到仓库
9. **ocp** <仓库文件> <目标路径> - 从仓库拷贝文件到外部
10. **chdir** <路径> - 切换仓库工作目录
11. **cd** <路径|-> - 进入仓库目录或返回初始目录
12. **<git命令>** - 执行标准Git操作

## 详细说明

### 仓库管理

- `create-repo`: 创建新Git仓库，可选设置别名
  ```
  ownpygit create-repo /path/to/repo myalias
  ```

- `set-repo`: 设置当前激活仓库
  ```
  ownpygit set-repo /path/to/repo
  ```

- `get-repo`: 显示当前激活仓库路径
  ```
  ownpygit get-repo
  ```

- `list-repo`: 列出所有历史仓库记录
  ```
  ownpygit list-repo
  ```

- `delete-repo`: 删除仓库记录(可选删除目录)
  ```
  ownpygit delete-repo /path/to/repo --remove-dir
  ```

### 文件操作

- `ls`: 列出当前仓库工作目录内容
  ```
  ownpygit ls
  ```

- `compare`: 对比文件/目录与仓库内容
  ```
  ownpygit compare /path/to/file
  ```

- `cp`: 拷贝外部文件到仓库
  ```
  ownpygit cp /path/to/file [dest_in_repo]
  ```

- `ocp`: 从仓库拷贝文件到外部
  ```
  ownpygit ocp repo_file /external/path
  ```

### 目录导航

- `chdir`: 切换仓库工作目录
  ```
  ownpygit chdir subdir
  ```

- `cd`: 进入仓库目录或返回初始位置
  ```
  ownpygit cd subdir  # 进入子目录
  ownpygit cd -      # 返回初始目录
  ```
  **注意：** 该命令只是输出切换目录的命令，不能真实的自动切换目录。

### Git命令

支持所有标准Git命令，用法与git相同：
```
ownpygit add .
ownpygit commit -m "message"
ownpygit push
```

## 配置
默认配置文件路径：`~/.cmdbox/ownpygit`
可以通过配置环境变量`OWNPYGIT_DB`来更改配置文件路径。