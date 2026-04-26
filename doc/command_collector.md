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
支持选项重复使用以实现多行命令和多行描述，例如：
```
# 重复选项实现多行输入
cccmd add git -c "git push origin -tags" -c "git push origin 1.0.0" -d "推送所有tag到远程仓库" -d "推送本地tag 1.0.0到远程仓库"

# 一次输入多行命令和多行描述
cccmd add test -c """
test
这是一个测试命令
""" -d """
test
这是一个测试命令
"""

# 混合使用重复选项和一次输入多行命令和多行描述
cccmd add test -c """
test
这是一个测试命令
""" -d "test" -d "这是一个测试命令"
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

可以通过设置环境变量`CCCMD_DBCCCMD_DB`来更改命令存储目录，默认为`~/.cmdbox/command_collector`

## 常见问题
### 1. 命令识别错误
字符串转义不正确，导致存储的命令发生异变
比如
```
>> cccmd add win -c "handle F:\ | Select-Object -Skip 5 | ForEach-Object { $f = $_ -split '\s+';if ($f.Count -gt 2 -and ($f[2] -match '^\d+$')) { taskkill /F /T /PID $f[2] } }" -d "停止对F:\的占用，杀掉占用的进程"
>> cccmd list win
0: handle F:\ | Select-Object -Skip 5 | ForEach-Object { No matching handles found. =  -split '\s+';if (No matching handles found..Count -gt 2 -and (No matching handles found.[2] -match '^\d+$')) { taskkill /F /T /PID No matching handles found.[2] } } #停止对F:\的占用，杀掉占用的进程
```
这实际不是问题。命令字符串参数传输格式问题，确保参数是单纯的字符串不可以被执行的终端解释，比如linux系统，在单引号之间的字符串不会被解释执行；在powershell终端，单引号也会有用。但是如果是在cmd终端（windows系统默认终端），单引号会失效，双引号有用。
正确添加方式：
**powershell**
```powershell
> cccmd add win -c 'handle F:\ | Select-Object -Skip 5 | ForEach-Object { $f = $_ -split "\s+";if ($f.Count -gt 2 -and ($f[2] -match "^\d+$")) { taskkill /F /T /PID $f[2] } }' -d "停止对F:\的占用，杀掉占用的进程"
```
**cmd**
```cmd
> cccmd add win -c "handle F:\ | Select-Object -Skip 5 | ForEach-Object { $f = $_ -split \"\s+\";if ($f.Count -gt 2 -and ($f[2] -match \"^\d+$\")) { taskkill /F /T /PID $f[2] } }" -d "停止对F:\的占用，杀掉占用的进程"
```
注意：该添加的命令实际上是在powershell中执行的命令，在cmd下本身是不支持的。



