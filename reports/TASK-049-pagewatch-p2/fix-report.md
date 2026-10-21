# pagewatch P2 修复记录

修前基线：`20 passed, 1 warning in 4.53s`。每条之后重跑全量 pytest。未改 `tests/`、`LICENSE`、`UPSTREAM.md`、`requirements.txt`、`requirements-dev.txt`。

## P2-1 超限仍当成功快照

- 报告编号：上一轮 P2-1
- 文件：`app.py:299-300`（修前循环在 `app.py:293-310`）
- 改法：读完后若 `read > max_bytes`，抛 `FetchError`，不解码、不返回截断正文。`run_check` 原有的异常分支因此只记错误，不插入快照。正好等于上限的正文仍然成功。
- 验证命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\run_pytest.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\probe_p2_1.py
```

pytest（exit 0）：

```
20 passed, 1 warning in 4.29s
```

探针（exit 0）：

```
EXACT status=200 len=2000000 cap=2000000
OVER FetchError 页面超过体积上限（2000000 字节）
CHECK {'status': 'error', 'error': '页面超过体积上限（2000000 字节）'}
SNAP_COUNT 0
LAST_STATUS error LAST_ERROR 页面超过体积上限（2000000 字节）
```

## P2-2 默认数据库路径

- 报告编号：上一轮 P2-2
- 文件：`README.md:46`
- 改法：默认值改为 `<app.py 所在目录>/data/pagewatch.db`，说明写明不跟随进程当前目录。未改 `app.py` 的路径计算（`app.py:29-32` 本来就是这样）。
- 验证命令：同上 `run_pytest.py`。pytest（exit 0）：

```
20 passed, 1 warning in 4.81s
```

## P2-3 不区分响应是不是 HTML

- 报告编号：上一轮 P2-3
- 文件：`app.py:303-314`；`README.md:79`
- 改法：成功响应没有 `Content-Type`，或去掉参数后的主类型不是 `text/html`，抛 `FetchError`。状态码大于等于 400 仍先按 HTTP 错误返回。说明节补上同一句。`application/xhtml+xml` 也拒绝。
- 验证命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\run_pytest.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\probe_p2_3.py
```

pytest（exit 0）：

```
20 passed, 1 warning in 4.99s
```

探针（exit 0）：

```
HTML status=200 has_hello=True
REJECT http://127.0.0.1:53642/plain 不是 HTML 页面（Content-Type: text/plain）
REJECT http://127.0.0.1:53642/none 响应没有 Content-Type
REJECT http://127.0.0.1:53642/xhtml 不是 HTML 页面（Content-Type: application/xhtml+xml）
CHECK {'status': 'error', 'error': '不是 HTML 页面（Content-Type: text/plain）'}
SNAP_COUNT 0
```

## P2-4 单条标已读不清「有变化」

- 报告编号：上一轮 P2-4
- 文件：`app.py:766-785`；`static/index.html:238`
- 改法：标已读时先取出 `watch_id`。该监测项已经没有 `is_read = 0` 的提醒时，把 `has_unread_change` 置 0。还剩未读则不动。不存在的提醒仍是 404。前端 `readOne` 在刷新提醒后再 `loadWatches()`，列表上的「有变化」会跟着消失。没有浏览器，页面按钮没有点过。
- 验证命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\run_pytest.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\probe_p2_4.py
```

pytest（exit 0）：

```
20 passed, 1 warning in 5.50s
```

探针（exit 0）。甲有 2 条未读，乙有 1 条。读掉甲的一条时两边标记都还在；读完甲的两条后只清甲：

```
MISSING 404 {'detail': '提醒不存在'}
UNREAD 3 MINE 2 FLAGS {1: True, 2: True}
AFTER_ONE 200 UNREAD 2 FLAGS {1: True, 2: True}
AFTER_TWO 200 UNREAD 1 FLAGS {1: False, 2: True}
```

## P2-5 旧提醒指向已删除的快照

- 报告编号：上一轮 P2-5
- 文件：`app.py:384-392`；`static/index.html:234`
- 改法：删除超出 20 份的快照之前，把这些快照上的提醒 `snapshot_id` 置空。不删提醒。前端 `snapshot_id` 为空时显示「快照已清理」，不再调用 `gotoSnap`。没有加外键：`CREATE TABLE IF NOT EXISTS` 不会改已有库，置空语句对新旧库都生效。
- 验证命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\run_pytest.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\probe_p2_5.py
```

pytest（exit 0）：

```
20 passed, 1 warning in 3.62s
```

探针（exit 0）。25 次检查后仍是 20 份快照、24 条未读；其中 4 条 `snapshot_id` 为空，悬空引用 0：

```
SNAPS 20 UNREAD 24 ITEMS 24
NULLED 4 DANGLING 0
```

## P2-6 结构清单和依赖警告

- 报告编号：上一轮 P2-6
- 文件：`README.md:76-78`
- 改法：项目结构补上 `requirements.txt`、`requirements-dev.txt`、`LICENSE`。`requirements-dev.txt:2` 的 `httpx==0.28.1` 不动。测试能过，不是依赖冲突。警告仍在。
- 验证命令：同上 `run_pytest.py`。pytest（exit 0）：

```
20 passed, 1 warning in 4.92s
```

## P2-7 许可证表述

- 报告编号：上一轮 P2-7
- 不改。`LICENSE:189` 只有上游版权行。`UPSTREAM.md:8`、`UPSTREAM.md:16-20` 和 `README.md:5` 写独立重写、版权行逐字来自上游。本轮没有外网，不能核对上游原文。任务书禁止改 `LICENSE` / `UPSTREAM` 的事实性声明。不新写版权人，也不加 `NOTICE`。

## P2-8 提交号对不上

- 报告编号：上一轮 P2-8
- 不改。`DECISIONS.md:33` 写提交 `d9841ec2`。`git cat-file -t d9841ec2` exit 1：`fatal: Not a valid object name d9841ec2`。`git log --oneline` 只有 `12bf01f`。同句说的 `_ClosingConn`（`app.py:55-86`）和改密吊销其他会话（`app.py:515-529`）都在这棵树上。不能证明这句话应改成指向 `12bf01f`。

## 收尾全量测试

全部改完后重跑。命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\run_pytest.py
```

exit 0：

```
20 passed, 1 warning in 4.55s
```

另外跑了 `tests/live_selftest.py`（`run_live.py`，exit 0）：

```
20/20 检查点通过
ALL PASS
```

`git diff --stat`：

```
 README.md         |  7 +++++--
 app.py            | 38 ++++++++++++++++++++++++++++++++++----
 static/index.html |  4 ++--
 3 files changed, 41 insertions(+), 8 deletions(-)
```

没有 `tests/`、`LICENSE`、`UPSTREAM.md`、`requirements.txt`、`requirements-dev.txt`。没有 skip / xfail。页面上的「标已读」和「快照已清理」没有在浏览器里点过。

## git status --porcelain

```
 M README.md
 M app.py
 M static/index.html
```
