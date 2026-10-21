# pagewatch 验收审查

依赖能装上，自动化测试 15 项通过，真实流程自测 20/20，本机 `127.0.0.1:8000` 首页和 `/api/health` 都返回 200。没有 P0。确认了 4 个 P1：重定向可把抓取带到别的本机端口、改密不废止 Token、退出不废止 Token、快照轮转后提醒仍指向已删除快照。许可证附录与「独立重写」的说法不自洽；上游 commit 未联网核实。

## 本地跑通记录

解释器是任务环境里的 Python 3.11.9，路径 `E:\muse-bridge\env\TASK-021-pagewatch\Scripts\python.exe`。README 写的 `py -m venv` 在本机不可用（环境限制，不是仓库缺陷）：

```
py -3 --version
```

```
Unable to create process using 'E:\python.exe --version': ???????????
```

未在仓库里另建 `.venv`。运行时依赖已经在该环境中，开发依赖按 README 安装。

命令（cwd `E:\muse-bridge\in\TASK-021-pagewatch`）：

```
python -m pip install -r requirements-dev.txt
```

结果 exit 0。`fastapi==0.156.4`、`uvicorn==0.54.0` 已满足；新装 `httpx==0.28.1`、`pytest==9.1.1` 及其传递依赖。没有版本冲突。

命令：

```
python -m pytest tests/ -q
```

```
...............                                                          [100%]
15 passed, 1 warning in 3.08s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `fastapi\testclient.py:1`，15 项仍然全过。与 README 第 54 行「自动化测试 15 项全过」一致。

命令：

```
python tests/live_selftest.py
```

```
20/20 检查点通过
ALL PASS
```

exit 0。与 README 第 57 行「20 个检查点全过」一致。脚本用 `tempfile.mkdtemp` 写系统临时目录，这是测试代码自己的行为。

起服务（数据库放到 `E:\muse-bridge\work\TASK-021-pagewatch\serve-pagewatch.db`，避免写进仓库）：

```
HOST=127.0.0.1 PORT=8000 python app.py
```

约 1.08 秒后：

```
health=status=200 ctype=application/json body={"status":"ok","app":"pagewatch"}
port_8000_open=True
home status=200 ctype=text/html; charset=utf-8
home_has_pagewatch True
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

随后关掉进程。`port_8000_open=False`。进程退出码 1，是 `terminate()` 结束 uvicorn 的退出码，启动和两次 HTTP 200 已经发生。

完整命令原文在 `run.md`。

## README 与实际不符处

下面每条都是 README 的说法和当前代码对不上的地方。已核对并且一致的，不列在这里：默认账号 `admin`/`admin123`（README.md:18，app.py:37-38）、Token 24 小时（README.md:9，app.py:402）、快照最多 20 份（README.md:12，app.py:34 与 app.py:286-291）、`HOST`/`PORT` 默认 `127.0.0.1:8000`（README.md:39，app.py:673-674）、测试数量 15 和 20（见上一节实测）。

1. README.md:11 写「只抓静态 HTML 并抽取可见文本」。app.py:134 的 `_SKIP_TAGS` 含 `noscript`，不含 `title`。探针 `extract_text` 对「标题在 title、可见替代文字在 noscript、正文在 h1」的页面得到 `标题不该当正文\n正文`，title 进了快照，noscript 没进。无浏览器抓取时，noscript 才是页面上看得见的字。

2. README.md:11 写抓取有「体积上限（2MB）」。app.py:33 把上限定义为 `2_000_000`，app.py:202-208 的循环在读满后仍正常返回，不报错。探针请求 2_100_000 字节正文，结果 `BIG_STATUS 200 BIG_LEN 2000001`：多读了 1 字节，超限页面被当成成功抓取。

3. README.md:11 写「抓取带超时（15 秒）」并且「失败只记录错误状态、不影响其他监测项」。app.py:198 把 `timeout=15` 交给 `urlopen`，这是单次套接字操作的超时。app.py:320-338 只有一条调度线程，按监测项串行调用 `run_check`。app.py:337-338 确实把单个监测项的异常吞掉，所以抛错不会弄停线程；一个持续慢慢吐数据的连接会占住这根线程，后面的监测项要等它结束。

4. README.md:11 的「抽取可见文本」在常见 gzip 页面上不成立。app.py:198 使用 `urlopen`，没有按 `Content-Encoding` 解压。探针让本机返回 gzip 的 `<p>明文保温杯</p>`，结果 `GZIP_HAS_PLAIN False`，`GZIP_LEN 59`，正文是压缩字节被当成文本。

5. README.md:40 写数据库默认在 `data/pagewatch.db`。app.py:26-29 把相对位置锚定在 `app.py` 所在目录（`BASE_DIR`），不是进程当前工作目录。从别的目录执行 `python <路径>\app.py` 时，库文件出现在源码旁的 `data\`，不出现在当前目录的 `data\`。

## 许可证与署名核查

结论：条款文本是 Apache License 2.0；附录把版权记在上游作者名下，和 UPSTREAM 里「独立重写、未复制上游源码」不能同时成立。`source_commit` 未核实。本次不改 `LICENSE` 和 `UPSTREAM.md`。

本地能对上的部分：

- `LICENSE` 标题与第 1–9 条是 Apache License Version 2.0 的常见条款文本。没有联网和 apache.org 做字节级比对。
- `LICENSE:189` 附录版权行是 `Copyright (c) Leigh Morresi and the changedetection.io contributors`。
- `UPSTREAM.md:6-7` 写的 license 与 attribution 就是上面这一行。
- `UPSTREAM.md:16-17` 写这一行「逐字复制自上游仓库 LICENSE 原文附录」，并称本仓库 `LICENSE` 就是上游 Apache 2.0 全文。
- `app.py:1-5` 和 `static/index.html:1-6` 没有版权头，也没有「本文件已修改」的声明。

对不上的部分：

- `UPSTREAM.md:18-20` 写本项目是独立重写，未复制上游源码，只借鉴监测项、快照、哈希判变。Apache 附录的填法是换成**本作品**的版权人（`LICENSE:179-189` 的说明）。现在的附录等于声明这份作品的版权属于 Leigh Morresi 与 changedetection.io 贡献者。
- 若把它当成上游的衍生作品，则 `LICENSE:97-98`（第 4(b) 条）要求改过的文件带醒目的修改声明。源码文件里没有这种声明。独立重写和衍生作品两种说法，现有文件各满足一半。

未核实（按任务不访问外网，不用猜测补齐）：

- `UPSTREAM.md:5` 的 `source_commit` `be09f73c3af1bbc698d19a532ef6d3c9987e6370`。
- `UPSTREAM.md:12-13` 写该提交是 2026-10-21 经 GitHub 接口看到的默认分支 HEAD、提交时间 2026-10-19。
- `UPSTREAM.md:16` 写版权行与上游 LICENSE 原文逐字相同。本地没有上游 LICENSE，不能证明抄写没有走样。

`README.md` 通篇没有许可证名称。这是署名不容易被看到，不是另一条互相矛盾的事实。

## 分级修复清单

行号是修复前的源码位置。改完之后的行号写在 `fix-report.md`。

### P0

无。安装、pytest、live_selftest、8000 端口首页和健康检查都已跑通。

### P1

1. **重定向 SSRF，以及初始 URL 不拦链路本地地址。** `app.py:193-219`。探针：本机 A 端口 302 到另一端口，`fetch_url` 返回了 `TOPSECRET-INTERNAL`（`REDIRECT_TO_LOOPBACK 200`）。`file://` 被 Python 3.11 的 urllib 拒绝（`FetchError HTTP 302`）。`ftp://` 没有被拒绝，客户端去连了 `127.0.0.1` 的 FTP（`WinError 10061`）。初始 URL `http://169.254.169.254/latest/meta-data/` 未被代码拒绝，经环境代理 `127.0.0.1:7890` 得到 `FetchError HTTP 502`（响应体未记录）。修法：初始目标拒绝链路本地和云元数据地址；重定向只跟随 http/https，非公网地址仅在主机和端口与当前请求相同、且不是链路本地或元数据地址时才跟随。用户显式填写的 `127.0.0.1` 与私网地址仍允许直接抓取（测试和内网监测都靠这个）。

2. **改密后旧 Token 继续有效。** `app.py:414-427`。探针：`CHANGE_PW 200`，同一 Token 再请求 `/api/me` 仍是 `OLD_TOKEN_ME 200`；旧密码登录 `OLD_PW 401`。修法：改密成功后删除该用户全部 Token，前端改密成功后回到登录页。

3. **退出登录只清浏览器里的 Token。** `static/index.html:142` 的 `logout()` 只做 `localStorage.removeItem`；`app.py` 鉴权段（约 `386-427` 行）没有作废 Token 的接口。修法：增加 `POST /api/logout` 删除当前 Token，前端退出时调用它。

4. **快照只留 20 份后，提醒仍指向已删快照。** `app.py:112-118` 的 `notifications.snapshot_id` 没有外键；`app.py:286-291` 直接删除旧快照。探针在 25 次变化检查后：`SNAPSHOTS 20`、`NOTIFS 24`、`DANGLING 4`。修法：删除快照前把对应提醒的 `snapshot_id` 置空；前端在 `snapshot_id` 为空时不显示「看对比」。不减少提醒条数（`tests/test_app.py` 的 `test_snapshot_cap_20` 要求未读数为 24）。

### P2

本次不改。

1. **gzip 不解压，快照不是可见文本。** `app.py:198-219`。见不符第 4 条。修法：仅在 `Content-Encoding` 为 gzip（或 deflate）时解压，再走现有的体积上限。
2. **超限页面被截断后仍算成功。** `app.py:202-208`。见不符第 2 条。修法：读到超过 `FETCH_MAX_BYTES` 就抛 `FetchError`，不写快照。
3. **调度是单线程，慢请求会堵住其他监测项。** `app.py:320-338`。见不符第 3 条。修法：为每次抓取设总截止时间，调度上不要让一个监测项占住整轮。
4. **数据库路径相对源码目录，README 写成 `data/pagewatch.db`。** `app.py:26-29`，`README.md:40`。修法：在 README 写明是 `app.py` 所在目录下的 `data/pagewatch.db`。
5. **`<title>` 进正文、`<noscript>` 被跳过。** `app.py:134-172`。见不符第 1 条。修法：跳过 `head`/`title`，不要把 `noscript` 放进 `_SKIP_TAGS`。
6. **含 CR/LF 的网址可以入库。** `app.py:439-448` 接受了 `http://127.0.0.1/a\r\nX-Injected: 1`（探针 `NEWLINE_URL 201`）。真正抓取时 urllib 拒绝：`InvalidURL URL can't contain control characters`，请求没有发出（`SEEN []`）。修法：校验阶段拒绝空白和控制字符。
7. **抓取跟随进程环境里的代理。** 本机 `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` 都是 `http://127.0.0.1:7890`（无用户信息），`NO_PROXY=127.0.0.1,localhost,::1`。所以本机测试能直接连；链路本地地址会先送到代理。修法：若要避免监测网址进入环境代理，在 opener 里显式关闭代理；出网环境需要代理时不要默认关掉。
8. **默认口令可以跳过不改。** `static/index.html:266-276` 有「稍后再说」。这和 README.md:9、README.md:18 的「提示改密」一致。强制改完才能用 API 会让现有测试在登录后直接调接口失败。不改。
9. **无变化的检查也占用 20 份快照名额。** 和 README.md:12「每次成功检查存一份」一致。`tests/test_app.py` 在内容不变时断言快照数为 2。不改。
10. **pbkdf2-SHA256 迭代 120_000。** `app.py:61-63`。存储格式没有写迭代次数，改常量会让已有库登不上。不改。
11. **`/docs` 与 OpenAPI 无登录。** FastAPI 默认路由，`app.py:355` 没有关掉。修法：生产入口关闭 `docs_url`。
12. **测试依赖弃用警告。** `requirements-dev.txt:2` 的 `httpx==0.28.1` 触发 Starlette 的 httpx2 提示。测试仍通过，没有依赖冲突。不改版本号。
13. **许可证附录与独立重写声明不自洽。** 见上一节。在核实上游 LICENSE 与 commit 之前不改 `LICENSE` / `UPSTREAM.md`。
