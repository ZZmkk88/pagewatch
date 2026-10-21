# pagewatch P2 第二轮审查

结论：上一轮 P2 共 8 条。P2-1 到 P2-6 已改，P2-7、P2-8 不改。修前 pytest 为 `20 passed, 1 warning in 4.53s`。收尾全量 pytest 为 `20 passed, 1 warning in 4.55s`。`live_selftest.py` 为 `20/20 检查点通过`，末行 `ALL PASS`。没有新的 P0。未改 `tests/`、`LICENSE`、`UPSTREAM.md` 和依赖版本。改法与每次 pytest 结果在 `fix-report.md`。下面行号除另行注明外都是修前行号。

本工作区没有上一轮那两处 P1 补丁（见文末「不重开」）。任务书规定本轮只处理 P2，不把它们再修一遍。

## 基线

Python `3.11.9`（`python --version`）。`py -3 --version` 失败，原文含 `Unable to create process using 'E:\python.exe --version'`。虚拟环境复用 `E:\muse-bridge\work\TASK-034-pagewatch\venv`，未重新安装。`pip show`：`fastapi==0.156.4`、`uvicorn==0.54.0`、`httpx==0.28.1`、`pytest==9.1.1`，与两份 requirements 一致。

```
20 passed, 1 warning in 4.53s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 修前 `git status --porcelain` 无输出。`git log --oneline` 只有 `12bf01f`。

## 八条现状

1. 超限仍当成功快照。`app.py:293-299` 的循环条件是 `read <= max_bytes`，每次最多再读 `max_bytes + 1 - read`。读完后 `app.py:307-310` 直接解码返回，没有和 `FETCH_MAX_BYTES`（`app.py:36`，`2_000_000`）比较。`run_check`（`app.py:352-374`）只在抓取抛错时记 `error`，否则把正文存成快照。
2. 默认数据库路径容易理解成当前目录。`README.md:46` 默认值写成 `data/pagewatch.db`。`app.py:29-32` 实际是 `os.path.join(BASE_DIR, "data", "pagewatch.db")`，`BASE_DIR` 是 `app.py` 所在目录。
3. 不区分响应是不是 HTML。`app.py:300-310` 只取 charset 并解码，不看 `Content-Type`。`README.md:11`、`README.md:79` 写的是只抓静态 HTML。
4. 单条标已读不清监测项上的「有变化」。`app.py:746-756` 只把这一条 `is_read` 置 1。`app.py:759-763` 的全部已读才会把 `has_unread_change` 置 0。`static/index.html:238` 的 `readOne` 只调用 `/api/notifications/${id}/read` 再 `loadNotifs()`，不走 `/seen`，也不刷新监测项列表。`tests/test_app.py:252-259` 在单条已读之后还调用了 `/seen`，中间没有断言标记仍为真，因此后端在「该监测项已无未读提醒」时清标记不会撞上这条测试。
5. 快照只留 20 份，更早的提醒仍指向已删除的快照。`app.py:376-382` 删掉超出 `SNAPSHOT_KEEP` 的快照。`app.py:145` 的 `snapshot_id` 没有外键。`tests/test_app.py:318-321` 要求 25 次检查后快照为 20、未读提醒为 24。不能靠删提醒来修。
6. 结构清单漏文件；依赖警告不是冲突。`README.md:67-75` 没有 `requirements.txt`、`requirements-dev.txt`、`LICENSE`。这三个文件都在仓库根。警告来自 `requirements-dev.txt:2` 的 `httpx==0.28.1`。测试能过，版本号不动。
7. 许可证表述。`LICENSE:189` 只有上游版权行。`UPSTREAM.md:8`、`UPSTREAM.md:16-20` 与 `README.md:5` 写独立重写、版权行逐字来自上游。本轮没有外网，不能核对上游原文。任务书禁止改 `LICENSE` / `UPSTREAM` 的事实性声明。不改，也不新写版权人。
8. `DECISIONS.md:33` 的提交号 `d9841ec2` 不在本克隆。`git cat-file -t d9841ec2` exit 1：`fatal: Not a valid object name d9841ec2`。唯一提交是 `12bf01f9ad333ec271d12d4c06bd53383941d0ce`。同句描述的 `_ClosingConn`（`app.py:55-86`）和改密吊销其他会话（`app.py:515-529`）都在这棵树上。不能证明该哈希应改写成 `12bf01f`。不改。

## 分级修复清单

### P0

无。修前 20 项 pytest 已通过。

### P1

无新增。上一轮两条 P1 不在本工作区，本轮不重开，见文末。

### P2

1. `app.py:293-310`。修法：读完后若 `read > max_bytes` 就抛 `FetchError`，不把截断正文返回，也不存成功快照。
2. `README.md:46`。修法：写明默认文件是 `app.py` 所在目录下的 `data/pagewatch.db`，不跟随进程当前目录。
3. `app.py:300-310`。修法：成功响应若没有 `Content-Type`，或主类型不是 `text/html`，抛 `FetchError`。HTTP 状态码大于等于 400 仍按原错误返回。
4. `app.py:746-756`、`static/index.html:238`。修法：这条提醒标已读后，若该监测项已经没有未读提醒，就把 `has_unread_change` 置 0。前端 `readOne` 随后刷新监测项列表。
5. `app.py:376-382`。修法：删除旧快照之前，把即将被删快照的提醒 `snapshot_id` 置空。不删提醒，以保住未读数 24。前端在 `snapshot_id` 为空时不再显示「看对比」。
6. `README.md:67-75`。修法：补上 `requirements.txt`、`requirements-dev.txt`、`LICENSE`。不改 `httpx` 版本。
7. 不改。理由见第 7 条。
8. 不改。理由见第 8 条。

## 不重开（上一轮 P1，本工作区未见补丁）

- SSRF：`app.py:268-269` 解析结果无法被 `ipaddress` 识别时 `continue`；一条都认不出就会放行。`app.py:287` 仍用 `build_opener(_GuardedRedirectHandler())` 打开原始主机名。本轮没有重跑绕过探针。
- 退出：全仓库没有 `POST /api/logout`。`static/index.html:142` 的 `logout()` 只清 `localStorage`。本轮没有再发退出请求。
