# TASK-021-pagewatch 执行记录

开工：2026-10-21。工作目录 E:\muse-bridge\in\TASK-021-pagewatch。先审查再按清单修 P0/P1。

## 环境探测

命令：

```
py -3 --version
```

输出（exit 1）：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

`py` 启动器指向的 `E:\python.exe` 无法创建进程。改用 PATH 上的 `python`。

命令：

```
python --version
python -c "import sys; print(sys.executable); print(sys.version)"
python -m pip --version
```

输出：

```
Python 3.11.9
E:\muse-bridge\env\TASK-021-pagewatch\Scripts\python.exe
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
pip 24.0 from E:\muse-bridge\env\TASK-021-pagewatch\Lib\site-packages\pip (python 3.11)
```

该解释器已带 fastapi 0.156.4、uvicorn 0.54.0（site-packages 目录名）。尚未看到 pytest / httpx。下一步按 README 安装 requirements-dev.txt 并跑测试。

## 安装依赖

工作目录：`E:\muse-bridge\in\TASK-021-pagewatch`。未在仓库内建 `.venv`（PATH 上的 `python` 已是任务环境 `E:\muse-bridge\env\TASK-021-pagewatch`）。

命令：

```
python -m pip install -r requirements-dev.txt
```

输出（exit 0，节选）：

```
Requirement already satisfied: fastapi==0.156.4 ... (0.156.4)
Requirement already satisfied: uvicorn==0.54.0 ... (0.54.0)
Collecting httpx==0.28.1
Collecting pytest==9.1.1
...
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

无依赖冲突。pip 提示可升级到 26.2.2，未升级（不改环境里无关工具）。

## 自动化测试

命令（README 指定的那条）：

```
python -m pytest tests/ -q
```

输出（exit 0）：

```
...............                                                          [100%]
============================== warnings summary ===============================
..\..\env\TASK-021-pagewatch\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-021-pagewatch\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
15 passed, 1 warning in 3.08s
```

15 项全过，与 README 声称一致。1 条警告来自依赖库，不是失败。

## 真实流程自测

命令：

```
python tests/live_selftest.py
```

输出（exit 0）：

```
[PASS] 服务启动且健康检查 200
[PASS] 错误密码登录被拒 401
[PASS] 默认账号登录成功
[PASS] 首次登录提示改密
[PASS] 建监测项 201
[PASS] 第一次检查成功
[PASS] 第一份快照不算变化
[PASS] 内容没变时不报变化
[PASS] 无变化时没有提醒
[PASS] 改内容后检查报变化
[PASS] 监测项亮起未读变化标记
[PASS] 生成一条未读提醒
[PASS] 提醒摘要含增删行数 (新增 2 行，删除 1 行)
[PASS] diff 含改动行（价格 100→80）
[PASS] diff 含新增行（限时包邮）
[PASS] diff 计数正确
[PASS] 第一份快照的 diff 标记为首份
[PASS] 快照共 3 份
[PASS] 查看后未读标记清除
[PASS] 首页可打开

20/20 检查点通过
ALL PASS
```

20 个检查点全过，与 README 声称一致。该脚本自己用 `tempfile.mkdtemp` 写系统临时目录（测试代码如此，未改测试）。

## 起服务确认端口、首页、健康检查

数据库放到工作目录，避免在仓库里生成 `data/pagewatch.db`。脚本：`E:\muse-bridge\work\TASK-021-pagewatch\probe_before.py`（先起服务再做探针）。

实际启动命令（脚本内）：

```
E:\muse-bridge\env\TASK-021-pagewatch\Scripts\python.exe app.py
```

环境：`HOST=127.0.0.1` `PORT=8000` `PAGEWATCH_DB_PATH=E:\muse-bridge\work\TASK-021-pagewatch\serve-pagewatch.db`，cwd=`E:\muse-bridge\in\TASK-021-pagewatch`。

输出（exit 0，服务段）：

```
startup_ok=True elapsed=1.08s
health=status=200 ctype=application/json body={"status":"ok","app":"pagewatch"}
port_8000_open=True
home status=200 ctype=text/html; charset=utf-8
home_has_pagewatch True
after_stop port_8000_open=False
proc_return=1
server_log_snippet:
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:58254 - "GET /api/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:62752 - "GET / HTTP/1.1" 200 OK
```

`proc_return=1` 是进程被 `terminate()` 关掉时的退出码。端口随后已关闭（`port_8000_open=False`），启动本身成功。

## 修前探针（本机，未访问外网页面）

命令：

```
python E:\muse-bridge\work\TASK-021-pagewatch\probe_before.py
python E:\muse-bridge\work\TASK-021-pagewatch\probe_crlf.py
python E:\muse-bridge\work\TASK-021-pagewatch\probe_gzip.py
python E:\muse-bridge\work\TASK-021-pagewatch\probe_proxy.py
python E:\muse-bridge\work\TASK-021-pagewatch\probe_ip.py
```

关键输出：

```
EXTRACT "标题不该当正文\n正文"
REDIRECT_TO_LOOPBACK 200 True <html><body><p>TOPSECRET-INTERNAL</p></body></html>
REDIRECT_TO_FILE_ERR FetchError HTTP 302
REDIRECT_TO_FTP_ERR FetchError 抓取失败：<urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
LINK_LOCAL_INITIAL_ERR FetchError HTTP 502
CHANGE_PW 200 OLD_TOKEN_ME 200 OLD_PW 401
SNAPSHOTS 20 NOTIFS 24 DANGLING 4 sample_snap 2
STATIC_TRAVERSAL 404 application/json {"detail":"Not Found"}
NEWLINE_URL 201
FETCH_ERR InvalidURL URL can't contain control characters. '/ok\r\nX-Injected: pwned' (found at least '\r')
SEEN []
GZIP_HAS_PLAIN False
GZIP_LEN 59
BIG_STATUS 200 BIG_LEN 2000001
ALL_PROXY/HTTP_PROXY/HTTPS_PROXY scheme=http host=127.0.0.1 port=7890 has_user=False
NO_PROXY raw=127.0.0.1,localhost,::1
```

`probe_ip.py` 里 `169.254.169.254` 的 `is_global=False`、`is_link_local=True`；`100.100.100.200` 的 `is_global=False`；`224.0.0.1` 的 `is_global=True` 且为组播。

## 按清单修 P1 之后的测试

每修一项都跑了 `python -m pytest tests/ -q`，均为 `15 passed`。对应探针：

- P1-1 `probe_p1_fetch.py`：直连与同端口重定向 200；跨端口 `拒绝重定向到其他内网或本机地址`；`SECRET_HITS []`；链路本地在连接前被拒绝。
- P1-2 `probe_p1_token.py`：`CHANGE_PW 200`，`OLD_TOKEN_ME 401`，`OLD_PW 401`，`NEW_PW 200 must_change False`。
- P1-3 `probe_p1_logout.py`：`LOGOUT 200`，`T1_ME 401`，`T2_ME 200`，`LOGOUT_AGAIN 401`。
- P1-4 `probe_p1_snap.py`：`SNAPSHOTS 20`，`NOTIFS 24`，`DANGLING 0`，`NULLED 4`，`KEPT_LINK 20`。

四项都落地后的全量重跑：

```
python -m pytest tests/ -q
```

```
15 passed, 1 warning in 3.16s
```

```
python tests/live_selftest.py
```

```
20/20 检查点通过
ALL PASS
```

两条都是 exit 0。

```
git status --porcelain
```

```
 M app.py
 M static/index.html
```


