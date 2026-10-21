# TASK-034-pagewatch 执行记录

开工时间：2026-10-21（本地）
工作目录：E:\muse-bridge\in\TASK-034-pagewatch
临时目录：E:\muse-bridge\work\TASK-034-pagewatch
角色：本地验收（Grok Build），先审查再修 P0/P1。

---

## 步骤 0：环境探测

时间：2026-10-21（本机时钟未逐条打印；命令本身无时间戳）

命令：
```
python --version
```
输出：
```
Python 3.11.9
```
exit: 0

命令：
```
py -3 --version
```
输出：
```
Unable to create process using 'E:\python.exe --version': ???????????
```
exit: 1

说明：README Windows 节写的是 `py -m venv .venv`。本机 `py` 启动器指向不存在的 `E:\python.exe`，无法按字面命令建 venv。改用已可用的 `python`（3.11.9）。此为环境限制，不记为项目缺陷。

命令：
```
git status --porcelain
git log --oneline -20
git rev-parse --show-toplevel
```
输出：
```
（status --porcelain 空，工作区干净）
12bf01f docs(pagewatch): 环境变量表、口径落实记录与 DECISIONS.md
E:/muse-bridge/in/TASK-034-pagewatch
```
本克隆仅 1 个提交。

虚拟环境不放仓库内（任务允许写入路径不含仓库 .venv，且禁止 del/rm，无法事后清理）。放到 `E:\muse-bridge\work\TASK-034-pagewatch\venv`。

## 步骤 1：创建虚拟环境

命令：
```
python -m venv E:\muse-bridge\work\TASK-034-pagewatch\venv
```
输出：无（exit 0）。venv 已创建。

## 步骤 2：安装运行依赖

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-034-pagewatch\requirements.txt
```
输出片段（exit 0）：
```
Collecting fastapi==0.156.4
Collecting uvicorn==0.54.0
...
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.4 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```
pip 提示可升级 24.0 -> 26.2.2，未升级（任务不要求，且禁止改已有依赖版本号）。

## 步骤 3：安装开发依赖

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-034-pagewatch\requirements-dev.txt
```
输出片段（exit 0）：
```
Requirement already satisfied: fastapi==0.156.4
Requirement already satisfied: uvicorn==0.54.0
Collecting httpx==0.28.1
Collecting pytest==9.1.1
...
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 步骤 4：自动化测试

为避免仓库内出现 `__pycache__` / `.pytest_cache`，以及避免测试库落到系统 TEMP，用工作目录里的 `run_pytest.py` 设置 `TEMP`/`TMP`/`PYTHONDONTWRITEBYTECODE` 后再跑 pytest。等价于 README 的 `python -m pytest tests/ -q`。

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_pytest.py
```
其内部命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp E:\muse-bridge\work\TASK-034-pagewatch\pytest-basetemp
```
cwd：`E:\muse-bridge\in\TASK-034-pagewatch`

输出（exit 0）：
```
....................                                                     [100%]
============================== warnings summary ===============================
..\..\work\TASK-034-pagewatch\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-034-pagewatch\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
20 passed, 1 warning in 4.96s
```

## 步骤 5：真实流程自测 live_selftest

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_live.py
```
内部等价于 README 的 `python tests/live_selftest.py`（cwd 为仓库根，TEMP 指到工作目录）。

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

## 步骤 6：按 README 起服务（127.0.0.1:8000）并关掉

数据库改到工作目录，避免在仓库里生成 `data/pagewatch.db`。

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_server_check.py
```
内部启动：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\in\TASK-034-pagewatch\app.py
```
环境：`HOST=127.0.0.1` `PORT=8000` `PAGEWATCH_DB_PATH=E:\muse-bridge\work\TASK-034-pagewatch\pagewatch-manual.db`

输出（exit 0）：
```
PID 28660
HEALTH 200 {"status":"ok","app":"pagewatch"}
HOME 200 len 18747 has_pagewatch True
GET /docs 404 {"detail":"Not Found"}
GET /redoc 404 {"detail":"Not Found"}
GET /openapi.json 404 {"detail":"Not Found"}
GET /api/watches 401 {"detail":"未登录"}
GET /static/index.html 200
STOPPED 1
```
服务日志片段：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:56103 - "GET /api/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56103 - "GET / HTTP/1.1" 200 OK
```
`STOPPED 1` 是 `proc.terminate()` 在 Windows 上的退出码，进程已结束。随后用绑定端口确认 8000 已释放（见步骤 7）。

## 步骤 7：确认 8000 已释放

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\probe_port.py
```
输出（exit 0）：
```
BIND_OK port 8000 is free
```

## 步骤 8：本地安全探针（不抓外网页面）

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\probe_security.py
```
输出片段（exit 0）：
```
EXC http://127.0.0.1:9/secret -> FetchError: 禁止抓取内网地址（127.0.0.1）
EXC http://localhost/ -> FetchError: 禁止抓取内网地址（localhost）
EXC http://169.254.169.254/latest/meta-data/ -> FetchError: 禁止抓取内网地址（169.254.169.254）
EXC http://[::1]/ -> FetchError: 禁止抓取内网地址（::1）
EXC http://[::ffff:127.0.0.1]/ -> FetchError: 禁止抓取内网地址（::ffff:127.0.0.1）
OK  http://8.8.8.8/ -> 'allowed'
（只做了地址校验，没有发 HTTP 请求）
EXC http://2130706433/ -> FetchError: 域名解析失败：[Errno 11001] getaddrinfo failed
EXC file:///C:/Windows/win.ini -> FetchError: 网址缺少主机名
POST /api/logout 404 {"detail":"Not Found"}
GET /api/me after logout attempt 200 {"username":"admin","must_change_password":true}
oversize status 200 len 2000001 cap 2000000
after select in_transaction False
```
同一次探针里，在本机仍开着 HTTP 代理时，伪造 DNS 的重绑定请求得到的是 `FetchError: HTTP 502`，且 `getaddrinfo` 只被调用 1 次（请求交给了代理，没有打到本机监听）。

命令：
```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\probe_proxy.py
```
输出片段（exit 0）：
```
ENV HTTP_PROXY=http://127.0.0.1:7890 (len=21)
ENV HTTPS_PROXY=http://127.0.0.1:7890 (len=21)
ENV ALL_PROXY=http://127.0.0.1:7890 (len=21)
PROXY http=http://127.0.0.1:7890 (len=21)
=== no-proxy rebind ===
  dns rebind.test call#1 port=None
  dns rebind.test call#2 port=50655
rebind result 200 HIT hits 1 paths ['/x'] dns 2
=== no-proxy fail-open ===
  dns weird.test call#1 port=None
  dns weird.test call#2 port=52094
weird result 200 HIT hits 1 paths ['/x'] dns 2
=== no-proxy redirect to 127.0.0.1 ===
  dns public.test call#1 port=None
  dns public.test call#2 port=60727
redir exc FetchError 禁止抓取内网地址（127.0.0.1） hits 1 paths ['/go'] dns 2
```
无代理时：校验看到的是公网测试地址 `203.0.113.9`，连接阶段第二次解析落到 `127.0.0.1`，本机服务收到了请求（`200 HIT`）。解析结果故意做成 `127.0.0.1%eth0` 时同样打进了本机服务。重定向到 `127.0.0.1` 会被拦住，`/secret` 没有被访问。

## 步骤 9：P1-1 修复后的验证

命令与结果写在 `fix-report.md` 的 P1-1。摘要：pytest `20 passed, 1 warning in 5.20s`；live_selftest `20/20` `ALL PASS`；重绑定探针在代理仍开着时得到 `抓取失败：timed out`，本机监听 `hits []`，主机名只解析 1 次。

## 步骤 10：P1-2 修复后的验证

`verify_logout.py` 第一次因脚本未调用 `init_db()` 失败：`sqlite3.OperationalError: no such table: users`。补上之后 exit 0：`LOGOUT_A 200`，`ME_A_AFTER 401`，`ME_B_AFTER 200`。同时 pytest `20 passed, 1 warning in 4.96s`。

## 步骤 11：收尾全量重跑

pytest（exit 0）：`20 passed, 1 warning in 7.66s`。

live_selftest（exit 0）：`20/20 检查点通过` / `ALL PASS`。

`git status --porcelain`：

```
 M app.py
 M static/index.html
```

---
