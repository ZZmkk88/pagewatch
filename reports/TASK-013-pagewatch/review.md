# pagewatch 验收报告

结论：补上第三方依赖之后，这个仓库能在本机跑通。pytest 15 项通过，真实流程自测 20/20，`127.0.0.1:8000` 的首页和 `/api/health` 都是 200。README 是 0 字节空文件，仓库没有 LICENSE、没有 UPSTREAM、没有依赖清单。代码没有跑不起来的 P0。有 2 个 P1：数据库连接用完不关（Windows 上数据库文件被锁住），以及改密后其他登录令牌仍然有效。行号都指修复前的源码。

## 本地跑通记录

环境：Python 3.11.9。系统解释器没有 fastapi（`ModuleNotFoundError: No module named 'fastapi'`）。README 为空，仓库没有 requirements.txt，依赖是按 import 安装的。

安装：

```
python -m venv E:\muse-bridge\work\TASK-013-pagewatch\venv
E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe -m pip install fastapi uvicorn pytest httpx
```

pip 耗时 69.11s，退出码 0。末行：

```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 certifi-2026.10.19 click-8.5.0 colorama-0.4.6 fastapi-0.156.8 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 idna-3.20 iniconfig-2.3.1 opentelemetry-api-1.45.1 packaging-26.3 pluggy-1.7.0 pydantic-2.14.1 pydantic-core-2.50.1 pygments-2.21.0 pytest-9.1.1 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

全量测试（临时目录设到 `E:\muse-bridge\work\TASK-013-pagewatch`，避免写到系统 TEMP）：

```
E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe -m pytest tests/test_app.py -v --tb=short
```

工作目录 `E:\muse-bridge\in\TASK-013-pagewatch`。结果摘要：

```
tests/test_app.py::test_login_wrong_password PASSED
tests/test_app.py::test_unauthenticated_401 PASSED
tests/test_app.py::test_login_and_me PASSED
tests/test_app.py::test_change_password_flow PASSED
tests/test_app.py::test_watch_crud_and_validation PASSED
tests/test_app.py::test_extract_text PASSED
tests/test_app.py::test_compute_diff_unit PASSED
tests/test_app.py::test_check_no_change_no_notification PASSED
tests/test_app.py::test_check_change_notification_and_diff PASSED
tests/test_app.py::test_first_snapshot_diff_is_first PASSED
tests/test_app.py::test_snapshot_get_and_404 PASSED
tests/test_app.py::test_fetch_error_state PASSED
tests/test_app.py::test_snapshot_cap_20 PASSED
tests/test_app.py::test_read_all_notifications PASSED
tests/test_app.py::test_fetch_url_against_local_server PASSED
======================== 15 passed, 1 warning in 4.11s ========================
EXIT 0
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 这是当前 Starlette 对 httpx 1.x 的提示，测试没有失败。不计入项目缺陷，也没有为消警告去改依赖。

真实流程自测：

```
E:\muse-bridge\work\TASK-013-pagewatch\venv\Scripts\python.exe tests\live_selftest.py
```

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
ELAPSED_SEC 2.58
EXIT 0
```

单独起服务（数据库放到工作临时目录，不写进仓库）：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:56767 - "GET /api/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56768 - "GET / HTTP/1.1" 200 OK
```

本机探测（urllib，未使用 curl）：

```
PATH /api/health
STATUS 200
CONTENT_TYPE application/json
BODY {"status":"ok","app":"pagewatch"}
PATH /
STATUS 200
CONTENT_TYPE text/html; charset=utf-8
BODY <!DOCTYPE html> ... <title>pagewatch · 网页变化监测</title>
```

随后停掉服务进程。再对 `127.0.0.1:8000` 执行 bind：`BIND_OK`（端口已释放）。

另外两条修复前探针（脚本在工作临时目录，数据库 `evidence.db`）：

```
=== leak: delete db after requests ===
login 200
REMOVE_FAIL PermissionError [WinError 32] 另一个程序正在使用此文件，进程无法访问。
=== token survives password change ===
change 200 {"ok":true}
other_session 200 {"username":"admin","must_change_password":false}
current_session 200 {"username":"admin","must_change_password":false}
=== writer blocked while check holds connection ===
concurrent_insert_ok 0.00s
check_result [('check', {'status': 'ok', 'is_change': False, 'snapshot_id': 1})]
```

抓取进行时另一条插入没有被堵住。连接泄漏表现为请求结束后文件仍被占用，不是这次探针里的写锁死。

## README 与实际不符处

`README.md` 长度为 0（`git log --stat` 中 `README.md | 0`）。文件里没有句子，因此没有「README 写了 A、代码做了 B」这种正面矛盾。下面每条都是：README 空白，对应行为只存在于代码。README 一侧没有行可引，行号给代码。

1. 没有安装说明，也没有依赖清单。`git ls-tree -r HEAD --name-only` 只有 README.md、app.py、static/index.html、tests/live_selftest.py、tests/test_app.py。直接 import 在 `app.py:21`（fastapi）、`app.py:24`（pydantic）、`app.py:669`（uvicorn）。测试还 import pytest（`tests/test_app.py:13`）和 httpx（`tests/live_selftest.py:21`）。
2. 没有启动方式。入口是 `app.py:668`，默认监听 `app.py:673` 的 `127.0.0.1` 和 `app.py:674` 的 `8000`。
3. 没有健康检查和首页说明。`app.py:386` 的 `GET /api/health` 返回 `{"status":"ok","app":"pagewatch"}`。`app.py:659` 的 `GET /` 返回 `static/index.html`。
4. 没有默认账号说明。`app.py:37` 与 `app.py:38` 是 `admin` / `admin123`。`app.py:123` 在用户表为空时写入，并设 `must_change_password=1`。页面文字在 `static/index.html:270`，写明默认密码是 admin123，并提供「稍后再说」。
5. 没有环境变量说明。`app.py:27` 的 `PAGEWATCH_DB_PATH` 默认 `data/pagewatch.db`。`app.py:347` 的 `PAGEWATCH_DISABLE_SCHEDULER=1` 关闭调度。`app.py:673` 的 `HOST`、`app.py:674` 的 `PORT` 覆盖监听地址。
6. 没有测试命令。自动化测试文件是 `tests/test_app.py:1`。自测用法写在 `tests/live_selftest.py:7`，该行是 `.venv/bin/python tests/live_selftest.py`。本次在 Windows 上实际使用的是 `venv\Scripts\python.exe`。
7. 没有产品行为说明。代码自己的说明在 `app.py:3`：只抓静态 HTML、不做浏览器渲染；调度是进程内线程。`app.py:35` 调度每 10 秒醒一次。`app.py:32` 抓取超时 15 秒。`app.py:34` 每个监测项最多留 20 份快照。
8. 没有鉴权说明。`app.py:371` 要求 `Authorization: Bearer`。`app.py:402` 令牌有效期 24 小时。

## 许可证与署名核查

HEAD 里没有 LICENSE、UPSTREAM、NOTICE，源码和 `static/index.html` 里也没有版权头、SPDX 或许可证句子。README 为空，同样没有授权或作者声明。

唯一署名在 git：提交 `171b64507759f33ba8b90240872585b73de8df75`，作者 `ZZmkk88 <927675399@qq.com>`，时间 `Wed Oct 21 17:12:58 2026 +0800`，说明为 `test(pagewatch): 自动化测试与真实流程自测`。这次提交加入了全部 5 个文件，不只是测试。

这些材料彼此不冲突：没有任何一份声明了许可证，也就没有两份声明互相打架。同时也没有任何文件把版权让给使用方。不能从现状推断 MIT、Apache 或其他许可证。本次没有新建或改写 LICENSE。未做外网代码溯源（任务不允许抓取外部页面）。

## 分级修复清单

### P0 跑不起来 / 阻断

无。依据见上一节：15 passed、ALL PASS、健康检查 200、首页 200、停服务后 `BIND_OK`。

### P1 安全、数据、权限

1. 数据库连接泄漏。`app.py:52` 的 `get_db` 把 `sqlite3.connect` 的连接交出去，调用方用 `with` 包住。Python 3.11 里连接的上下文管理器只提交或回滚，不关闭连接。请求已经返回之后，删除数据库文件仍失败：`PermissionError [WinError 32]`。调度线程（`app.py:324`）和每个接口都走 `get_db`，进程会一直占着文件句柄。修法：包一层上下文管理器，退出时 `commit`/`rollback` 并 `close`。
2. 改密后其他会话仍有效。`app.py:421` 只更新 `password_hash` 和 `must_change_password`，不删 `tokens`。探针里另一枚 Bearer 在改密后访问 `GET /api/me` 仍是 200。修法：改密成功时删除该用户除当前这枚以外的 token。

### P2 本次不改

1. 空 README、无 requirements.txt。见上一节第 1 条。修法：补依赖清单和启动说明。不阻断「依赖装上之后」的运行，本次不改文档。
2. 默认口令可以一直调用业务接口。`app.py:37`、`app.py:414` 没有把 `must_change_password` 当作拦截条件。`static/index.html:270` 允许稍后再说。`tests/test_app.py:90` 在未改密时请求 `/api/me` 并要求成功。修法若改成强制改密，会破坏现有测试；测试文件禁止修改，所以不修。
3. 任意 `http://` / `https://` 都可抓，包括本机。校验在 `app.py:444`。`tests/test_app.py:364` 对 `127.0.0.1` 抓取做了断言。这是监测功能本身。修法：保持可抓本机；部署时不要在未改默认口令的情况下把 `HOST` 设成 `0.0.0.0`（默认绑定见 `app.py:673`）。
4. `/docs`、`/redoc`、`/openapi.json` 未登录返回 200（本次实测）。修法：需要时把 FastAPI 的 `docs_url` / `redoc_url` / `openapi_url` 设为 `None`。接口本身仍要登录，本次不改。
5. 快照只留 20 份（`app.py:286`），通知表没有指向快照的外键（`app.py:112`）。旧通知会指向已删快照。`tests/test_app.py:321` 要求 25 次检查后未读仍是 24。修法会改变这条计数的，不能改。
6. `tests/live_selftest.py:7` 写成 Unix 虚拟环境路径。测试文件禁止改。
7. `tests/live_selftest.py:78` 没有设置 `PAGEWATCH_DISABLE_SCHEDULER`。调度间隔是 `app.py:35` 的 10 秒。本次自测 2.58 秒结束，没有撞上额外抓取。测试文件禁止改。
8. `app.py:33` 注释写最多 2MB，`app.py:202` 的条件是 `read <= max_bytes`，会多读 1 字节。修法：改为读到上限即停。不影响现有测试，留在 P2。
9. 过期 token 没有清理，表定义在 `app.py:86`。修法：登录或调度时删掉 `expires_at` 已过的行。本次不改。
10. 登录无限速，入口 `app.py:391`。修法：对失败次数做短期限制。本次不改。
11. 没有许可证文件。修法：由作者选定许可证后再加 LICENSE。本次不编造授权文本。
