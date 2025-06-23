# cccmd

命令收集器，是一个通过命令行收集和管理常用命令的命令行工具。

## 功能特性

- 按模块分类存储命令
- 支持命令的添加、删除、查询
- 支持全局搜索命令

## 使用方法

### 添加命令
```bash
cccmd add <模块名> -c "<命令>" -d "<描述>"
```

### 删除命令
```bash
cccmd del <模块名> --index <命令索引>
```
例如：
```
cccmd add git -c "git push origin -tags" -d "推送所有tag到远程仓库"
```

### 列出模块
```bash
cccmd modules
```

### 列出命令
```bash
cccmd list <模块名>
```
例如：
```
> cccmd list git

模块 [git] 中的命令:
0: git remote add origin <仓库地址> #本地仓库添加远端仓库，例如：git remote add origin git@github.com:你的用户名/仓库名.git
1: git remote set-url origin <新地址> #修改远端地址
2: git branch --set-upstream-to=origin/master master #本地master分支与远端master分支关联，git branch -vv查看
3: git push -u origin main #推送本地分支main到远端仓库main
4: git push --force origin master #确定当前分支内容是正确的时候，使用--force强制推送，覆盖远端分支内容，有风险
5: git pull --rebase origin master #使用变基方式合并远端代码：1.先找到本地分支与远端的功能祖先 2.在祖先代码上合并远端分支内容 3.再合并本地基于祖先的修改
6: git push origin 1.0.0 #推送本地tag 1.0.0到远程仓库
7: git push origin -tags #推送所有tag到远程仓库
```


### 搜索命令
```bash
cccmd search <关键词>
```

## 配置

可以通过设置环境变量`STORAGE_DIR`来更改命令存储目录，默认为`~/.command_collector`







