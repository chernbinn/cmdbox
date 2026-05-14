本地分支跟踪上有分支，转上游分支为本地线性提交的分支。有限展开merge commit为线性提交，便于推送到gerrit进行审核。
```pseudocode
# 上游跟踪：将 upstream/main 的线性历史同步到 integration 分支
# 假设当前在 integration 分支，且已设置好 remote: upstream

LAST_SYNC = 上次成功同步的上游 commit ID（初始为某个起点）

# 获取主干上的所有提交（普通 + merge），按正向拓扑顺序，仅第一父链
MAIN_COMMITS = $(git rev-list --reverse --first-parent upstream/main ^$LAST_SYNC)

for C in $MAIN_COMMITS; do
    # 1. 判断是否为普通提交（只有一个父节点）
    PARENT_COUNT = $(git rev-list --parents -n 1 $C | awk '{print NF-1}')
    if [ $PARENT_COUNT -eq 1 ]; then
        # 普通提交：直接应用
        git cherry-pick -n $C
        git commit -m "$(git log -1 --format=%B $C)"
        continue
    fi

    # 2. 处理 merge commit
    P1 = $(git rev-parse $C^1)
    P2 = $(git rev-parse $C^2)

    # 2.1 检查是否为空合并（无文件变更）
    if git diff --quiet $P1 $C; then
        echo "空合并，跳过: $C"
        continue
    fi

    # 2.2 判断 merge commit 是否有冲突解决
    BASE = $(git merge-base $P1 $P2)
    AUTO_TREE = $(git merge-tree --write-tree $BASE $P1 $P2)
    REAL_TREE = $(git rev-parse $C^{tree})
    if [ "$AUTO_TREE" != "$REAL_TREE" ]; then
        echo "有冲突合并，直接 squash: $C"
        git read-tree --reset -u $C
        git commit -m "$(git log -1 --format=%B $C)"
        continue
    fi

    # 2.3 无冲突合并：获取子分支提交列表（正向顺序）
    SUBS = $(git rev-list --reverse $P1..$P2)

    # 2.4 检查子分支中是否包含 merge commit（有则无法 cherry-pick）
    need_squash = false
    for sub in $SUBS; do
        sub_parents = $(git rev-list --parents -n 1 $sub | awk '{print NF-1}')
        if [ $sub_parents -ne 1 ]; then
            need_squash = true
            break
        fi
    done

    if $need_squash; then
        echo "子分支内含有 merge commit，整体 squash: $C"
        git read-tree --reset -u $C
        git commit -m "$(git log -1 --format=%B $C)"
    else
        echo "无冲突且子分支线性，逐个 cherry-pick 子提交"
        for sub in $SUBS; do
            git cherry-pick -n $sub
            git commit -m "$(git log -1 --format=%B $sub)"
        done
    fi
done

# 更新 LAST_SYNC 为 upstream/main 的最新 commit
LAST_SYNC = $(git rev-parse upstream/main)
```