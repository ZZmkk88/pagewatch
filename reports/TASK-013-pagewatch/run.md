# TASK-013-pagewatch 执行记录

开工时间：2026-10-21
角色：本地验收（Grok Build）
仓库：E:\muse-bridge\in\TASK-013-pagewatch
临时目录：E:\muse-bridge\work\TASK-013-pagewatch

## 步骤 0 — 开工

已创建本文件。下一步：读 README 与仓库结构，再装依赖、跑测试、起服务。

## 步骤 1 — 仓库盘点（未改代码）

命令：`python --version`
输出：`Python 3.11.9`

命令：`git -C E:\muse-bridge\in\TASK-013-pagewatch log --stat -n 20`
输出摘要：仅 1 个提交 `171b64507759f33ba8b90240872585b73de8df75`，作者 ZZmkk88 <927675399@qq.com>，日期 Wed Oct 21 17:12:58 2026 +0800，说明 `test(pagewatch): 自动化测试与真实流程自测`。该提交新增 README.md（0 字节）、app.py（675 行）、static/index.html（291 行）、tests/live_selftest.py（179 行）、tests/test_app.py（370 行）。

命令：`git -C E:\muse-bridge\in\TASK-013-pagewatch ls-tree -r HEAD --name-only`
输出：
```
README.md
app.py
static/index.html
tests/live_selftest.py
tests/test_app.py
```
无 LICENSE、无 UPSTREAM、无 requirements.txt、无 pyproject.toml。

命令：`python -c "import fastapi, uvicorn, pydantic, pytest, httpx; ..."`
输出：`ModuleNotFoundError: No module named 'fastapi'`（当前系统 Python 未装项目依赖）。

README.md 经读取为空文件（工具返回 File is empty）。git 统计 `README.md | 0`。

本地探针（只读行为，脚本在工作临时目录，未改仓库）：
- `python E:\muse-bridge\work\TASK-013-pagewatch\redir_probe.py`
  - `/tofile`：`HTTPError HTTP Error 302: Found - Redirection to url 'file:///...' is not allowed`（本机 Python 3.11 的 urllib 拒绝跳到 file://）
  - `/toloop`：跟随 http 302 后 `STATUS 200`
- `python E:\muse-bridge\work\TASK-013-pagewatch\lock_probe.py`
  - `with sqlite3.connect()` 结束后 `os.remove` 失败：`PermissionError [WinError 32] 另一个程序正在使用此文件`
  - `close()` 之后删除成功：`REMOVE_AFTER_CLOSE_OK`
  - 另测：`sqlite3.Row` 在连接 close 之后仍可 `row['a']`（Python 3.11.9）

下一步：在临时目录建 venv 并安装 fastapi / uvicorn / pytest / httpx，再跑测试。

## 步骤 2 — 安装依赖

命令：`python -m venv E:\muse-bridge\work\TASK-013-pagewatch\venv`
退出码：0

命令：`E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe -m pip install fastapi uvicorn pytest httpx`
耗时：69.11s
退出码：0
安装结果（pip 输出末行）：
```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 certifi-2026.10.19 click-8.5.0 colorama-0.4.6 fastapi-0.156.8 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 idna-3.20 iniconfig-2.3.1 opentelemetry-api-1.45.1 packaging-26.3 pluggy-1.7.0 pydantic-2.14.1 pydantic-core-2.50.1 pygments-2.21.0 pytest-9.1.1 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```
说明：仓库没有 requirements.txt，README 为空，依赖是按 app.py / tests 的 import 安装的（fastapi、uvicorn、pytest、httpx；pydantic 与 starlette 由 fastapi 带入）。版本是本次 pip 解析到的版本，不是仓库声明的版本。

## 步骤 3 — 全量 pytest

命令：`E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-013-pagewatch\run_pytest.py`
（脚本把 TEMP/TMP 设到工作临时目录，再执行 `python -m pytest tests/test_app.py -v --tb=short`，cwd 为仓库）
耗时：5.17s（pytest 自身报告 4.11s）
退出码：0
结果行：`15 passed, 1 warning in 4.11s`
警告：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
副作用：仓库里出现 `.pytest_cache` 和 `__pycache__`。稍后用脚本删掉，不留在交付 diff 里。

## 步骤 4 — live_selftest

命令：`E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-013-pagewatch\run_live.py`
（脚本设置 TEMP/TMP 与 PYTHONDONTWRITEBYTECODE，再执行 `tests\live_selftest.py`）
耗时：2.58s
退出码：0
结果行：`20/20 检查点通过` / `ALL PASS`

## 步骤 5 — 起服务、探测、关掉

命令：`E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-013-pagewatch\serve_once.py`
数据库：`E:\muse-bridge\work\TASK-013-pagewatch\manual-pagewatch.db`
监听日志：
```
INFO:     Started server process [444]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:56767 - "GET /api/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56768 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:56067 - "GET /docs HTTP/1.1" 200 OK
INFO:     127.0.0.1:56068 - "GET /redoc HTTP/1.1" 200 OK
INFO:     127.0.0.1:56069 - "GET /openapi.json HTTP/1.1" 200 OK
```

探测命令：`...\venv\Scripts\python.exe ...\http_probe.py`
```
PATH /api/health
STATUS 200
CONTENT_TYPE application/json
BODY {"status":"ok","app":"pagewatch"}
PATH /
STATUS 200
CONTENT_TYPE text/html; charset=utf-8
BODY 开头为 <!DOCTYPE html>，title 为 pagewatch · 网页变化监测
```

文档探测 `http_probe_docs.py`：`/docs`、`/redoc`、`/openapi.json` 均为 STATUS 200。

停止：结束上述 serve_once 进程（未使用 taskkill）。随后 `port_bind.py` 对 127.0.0.1:8000 bind，输出 `BIND_OK`。

## 步骤 6 — 修复前缺陷探针

命令：`...\venv\Scripts\python.exe ...\evidence_probe.py`
```
login 200
REMOVE_FAIL PermissionError [WinError 32] 另一个程序正在使用此文件，进程无法访问。
change 200 {"ok":true}
other_session 200 {"username":"admin","must_change_password":false}
current_session 200 {"username":"admin","must_change_password":false}
concurrent_insert_ok 0.00s
```

审查结论已写入 `E:\muse-bridge\out\TASK-013-pagewatch\review.md`。下一步只修清单中的 P1-1、P1-2。

## 步骤 7 — 修复 P1-1 后验证

改动：`app.py` 的 `get_db` 退出时关闭连接。

命令：`...\venv\Scripts\python.exe ...\run_pytest.py`
结果：`15 passed, 1 warning in 3.43s`，`EXIT 0`，耗时 4.36s。

命令：`...\venv\Scripts\python.exe ...\leak_recheck.py`
输出：
```
login 200
watches 200 []
REMOVE_OK
```

## 步骤 8 — 修复 P1-2 后验证

改动：`change_password` 删除其它 token。

命令：`...\venv\Scripts\python.exe ...\run_pytest_one.py`
结果：`3 passed, 1 warning in 1.39s`，`EXIT 0`，耗时 2.46s。

命令：`...\venv\Scripts\python.exe ...\token_recheck.py`
输出：
```
change 200 {"ok":true}
other_session 401 {"detail":"登录已过期，请重新登录"}
current_session 200 {"username":"admin","must_change_password":false}
relogin 200 False
```

## 步骤 9 — 全量重跑

命令：`...\run_pytest.py`
结果：`15 passed, 1 warning in 4.05s`，`ELAPSED_SEC 5.00`，`EXIT 0`。

命令：`...\run_live.py`
结果：`20/20 检查点通过`，`ALL PASS`，`ELAPSED_SEC 2.51`，`EXIT 0`。

`git status --short` 最终只剩 `M app.py`。pytest 写到仓库里的 `.pytest_cache` 和 `__pycache__` 已删掉。
