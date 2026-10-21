# TASK-049-pagewatch-p2 执行记录

开工：2026-10-21。角色：本地执行方（Grok Build）。工作目录：`E:\muse-bridge\in\TASK-049-pagewatch-p2`。本轮只处理上一轮 `E:\muse-bridge\out\TASK-034-pagewatch\review.md` 中的 P2 条目，按报告顺序，最多 8 条。P0/P1 上一轮已修，本轮不重开。

第一步：只读打开上一轮审查报告，并查看本仓库结构。

上一轮报告：`E:\muse-bridge\out\TASK-034-pagewatch\review.md`。P2 共 8 条。本工作区 `git log --oneline` 只有 `12bf01f`，`git status --porcelain` 为空。`py -3 --version` 失败（启动器指向损坏的 `E:\python.exe`），`python --version` 为 Python 3.11.9。

复用已有虚拟环境（未新建、未 pip install）：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -m pip show fastapi uvicorn httpx pytest
```

版本与 `requirements.txt` / `requirements-dev.txt` 一致：fastapi 0.156.4、uvicorn 0.54.0、httpx 0.28.1、pytest 9.1.1。

接着跑修前全量 pytest。`--basetemp` 指到工作目录。`tests/test_app.py` 自己调用 `tempfile.mkdtemp`，这条基线没有改 `TEMP`，该目录仍落在进程默认临时目录。之后的 pytest 用工作目录里的运行脚本把 `TEMP`/`TMP` 指到 `E:\muse-bridge\work\TASK-049-pagewatch-p2\tmp`。

修前基线（工作目录为仓库根，`--rootdir` 指向仓库；`-B` 不写 pyc；`-p no:cacheprovider` 与 `--basetemp` 不把缓存写进仓库）：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B -m pytest E:\muse-bridge\in\TASK-049-pagewatch-p2\tests -q --rootdir E:\muse-bridge\in\TASK-049-pagewatch-p2 -p no:cacheprovider --basetemp E:\muse-bridge\work\TASK-049-pagewatch-p2\pytest-basetemp
```

exit 0：

```
20 passed, 1 warning in 4.53s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 venv 里的 `fastapi\testclient.py:1`。测试没有失败。

随后 `git status --porcelain` 无输出。`git cat-file -t d9841ec2` exit 1，原文：`fatal: Not a valid object name d9841ec2`。

## P2-1 之后

改 `app.py`：超过 `max_bytes` 抛 `FetchError`。然后：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\run_pytest.py
```

该脚本把 `TEMP`/`TMP` 设为 `E:\muse-bridge\work\TASK-049-pagewatch-p2\tmp`，再跑与基线相同的 pytest。exit 0：

```
20 passed, 1 warning in 4.29s
```

探针：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-049-pagewatch-p2\probe_p2_1.py
```

exit 0：

```
EXACT status=200 len=2000000 cap=2000000
OVER FetchError 页面超过体积上限（2000000 字节）
CHECK {'status': 'error', 'error': '页面超过体积上限（2000000 字节）'}
SNAP_COUNT 0
LAST_STATUS error LAST_ERROR 页面超过体积上限（2000000 字节）
```

## P2-2 之后

只改 `README.md:46`。再跑 `run_pytest.py`。exit 0：

```
20 passed, 1 warning in 4.81s
```

## P2-3 之后

`app.py` 增加 Content-Type 检查，`README.md:79` 补了一句。再跑 `run_pytest.py`。exit 0：

```
20 passed, 1 warning in 4.99s
```

探针 `probe_p2_3.py` exit 0：

```
HTML status=200 has_hello=True
REJECT http://127.0.0.1:53642/plain 不是 HTML 页面（Content-Type: text/plain）
REJECT http://127.0.0.1:53642/none 响应没有 Content-Type
REJECT http://127.0.0.1:53642/xhtml 不是 HTML 页面（Content-Type: application/xhtml+xml）
CHECK {'status': 'error', 'error': '不是 HTML 页面（Content-Type: text/plain）'}
SNAP_COUNT 0
```

## P2-4 之后

`app.py` 的单条已读会在该监测项没有未读提醒时清 `has_unread_change`。`static/index.html` 的 `readOne` 会再加载监测项。`run_pytest.py` exit 0：

```
20 passed, 1 warning in 5.50s
```

`probe_p2_4.py` exit 0：

```
MISSING 404 {'detail': '提醒不存在'}
UNREAD 3 MINE 2 FLAGS {1: True, 2: True}
AFTER_ONE 200 UNREAD 2 FLAGS {1: True, 2: True}
AFTER_TWO 200 UNREAD 1 FLAGS {1: False, 2: True}
```

## P2-5 之后

删除旧快照前把对应提醒的 `snapshot_id` 置空。`run_pytest.py` exit 0：

```
20 passed, 1 warning in 3.62s
```

`probe_p2_5.py` exit 0：

```
SNAPS 20 UNREAD 24 ITEMS 24
NULLED 4 DANGLING 0
```

## P2-6 之后

只补 `README.md` 结构清单。`run_pytest.py` exit 0：

```
20 passed, 1 warning in 4.92s
```

P2-7、P2-8 不改源码。

## 收尾

全部改完后重跑 `run_pytest.py`。exit 0：

```
20 passed, 1 warning in 4.55s
```

`run_live.py`（即 `tests/live_selftest.py`，`TEMP`/`TMP` 指向工作目录）exit 0：

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

`git status --porcelain`：

```
 M README.md
 M app.py
 M static/index.html
```
