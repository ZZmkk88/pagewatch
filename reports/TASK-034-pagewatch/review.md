# pagewatch 验收

结论：仓库能在本机跑通。自动化测试 20 项通过，真实流程自测 20/20 通过，按 README 启动后 `127.0.0.1:8000` 的首页和 `/api/health` 都是 200，服务已关掉。没有 P0。P1 有 2 条：抓取的 SSRF 校验可以被绕过；页面上的「退出」不吊销令牌。本轮只修这两条。

## 本地跑通记录

环境：Python 3.11.9（`python --version`）。本机 `py -3 --version` 失败，原文：`Unable to create process using 'E:\python.exe --version'`。这是启动器损坏，README 的 `py -m venv` 在正常 Windows 上仍成立，不记为项目缺陷。虚拟环境放在 `E:\muse-bridge\work\TASK-034-pagewatch\venv`，没有写进仓库。

运行依赖安装成功（exit 0），装上的就是钉死的版本：`fastapi==0.156.4`、`uvicorn==0.54.0`。开发依赖同样成功：`httpx==0.28.1`、`pytest==9.1.1`。

自动化测试命令（等价于 README 的 `python -m pytest tests/ -q`，另外把临时目录和 pytest 缓存指到工作目录）：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp E:\muse-bridge\work\TASK-034-pagewatch\pytest-basetemp
```

输出（exit 0）：

```
20 passed, 1 warning in 4.96s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 测试没有失败。

真实流程自测（等价于 README 的 `python tests/live_selftest.py`）exit 0，末尾：

```
20/20 检查点通过
ALL PASS
```

按 README 起服务：`python app.py`，`HOST=127.0.0.1`，`PORT=8000`，数据库改到工作目录，避免在仓库里生成 `data/pagewatch.db`。输出：

```
HEALTH 200 {"status":"ok","app":"pagewatch"}
HOME 200 len 18747 has_pagewatch True
GET /docs 404 {"detail":"Not Found"}
GET /redoc 404 {"detail":"Not Found"}
GET /openapi.json 404 {"detail":"Not Found"}
GET /api/watches 401 {"detail":"未登录"}
```

服务日志：`Uvicorn running on http://127.0.0.1:8000`。`proc.terminate()` 后退出码 1（Windows 上正常）。随后绑定 `127.0.0.1:8000` 成功：`BIND_OK port 8000 is free`。

本机有 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY`，都是 `http://127.0.0.1:7890`。带 `PAGEWATCH_ALLOW_PRIVATE_FETCH=1` 的本地假页面测试仍然通过，因为这类地址没有被代理截走。

## README 与实际不符处

1. README.md:11 写抓取有「体积上限（2MB）」。`app.py:36` 的上限是 `2_000_000`，但 `app.py:293-299` 的循环条件是 `read <= max_bytes`，单次还能再读 `max_bytes + 1 - read`。本地假页面返回 2_500_000 字节时，结果是 `oversize status 200 len 2000001 cap 2000000`：多读 1 字节，超限仍当成功快照，不报错。
2. README.md:11 和 README.md:80 写抓取前会拒绝内网地址，重定向每一跳重新校验。直接访问 `127.0.0.1`、`169.254.169.254`、`::1` 确实会被 `app.py:270-271` 拒绝，无代理时重定向到 `127.0.0.1` 也会被拦住（探针里秘密路径没有被打开）。不符的是校验守不住：`app.py:265-269` 遇到无法解析的地址会 `continue` 然后放行；`app.py:285-289` 用 urllib 默认打开器，连接时会再解析一次，并且会走环境变量里的 HTTP 代理。关掉代理后的探针：`rebind result 200 HIT`、`weird result 200 HIT`，本机监听都收到了请求。开着代理时同一次伪造域名得到 `HTTP 502`，`getaddrinfo` 只调用了 1 次，说明请求交给了 `127.0.0.1:7890`，没有连到校验过的地址。
3. README.md:46 默认数据库写成 `data/pagewatch.db`。`app.py:29-32` 实际是 `app.py` 所在目录下的 `data/pagewatch.db`，不跟随进程当前目录。从仓库根目录按 README 启动时两条路径重合。
4. README.md:11、README.md:79 写只抓静态 HTML。`app.py:286-310` 不看 `Content-Type`，任意响应体都按字符集解码后抽文本。不执行 JavaScript 这一点和 README 一致。
5. README.md:67-75 的结构清单没有列出 `requirements.txt`、`requirements-dev.txt`、`LICENSE`。这三个文件都在仓库根目录。

以下与代码一致，不列入不符：默认账号 `admin` / `admin123`（README.md:18，`app.py:40-41`）；Token 24 小时（README.md:9，`app.py:495`）；快照最多 20 份（README.md:12，`app.py:37`）；`HOST` / `PORT` 默认 `127.0.0.1:8000`（README.md:44-45，`app.py:784-785`，服务日志已证实）；`/docs`、`/redoc`、`openapi.json` 关闭（README.md:80，实测 404）；README.md:62-65 的「20 项测试、20 个检查点」与本次本地结果一致。

## 许可证与署名核查

`LICENSE` 正文是 Apache License 2.0 的第 1–9 条和附录说明（`LICENSE:1-187`）。没有重新下载 apache.org 做逐字节比对，外部文本记为未核实。

附录版权行 `LICENSE:189`：

```
Copyright (c) Leigh Morresi and the changedetection.io contributors
```

与 `UPSTREAM.md:8` 的 attribution 逐字相同。`UPSTREAM.md:7` 写的许可证是 Apache License 2.0，和 `LICENSE` 的许可证种类一致。

对不上的是「这是谁的代码」：

- `README.md:5`、`UPSTREAM.md:18-20` 写代码是独立重写，没有复制上游源码。
- `LICENSE:180-187` 的附录说明要求填**本作品**的版权人。现在唯一的版权行是上游作者（`LICENSE:189`），源码文件里没有本仓库自己的版权声明，也没有 `NOTICE` 把「借鉴了概念」和「这段代码的版权」分开。
- 仓库内没有 changedetection.io 的源码树。`NOTES.md:14-15` 写上游用 inscriptis 做文本抽取；本仓库 `app.py:173-213` 用的是标准库 `HTMLParser`。就本仓库内容看，不像整文件抄来的。上游仓库本身没有拉下来比对，**不能证明**「未复制」或「版权行逐字来自上游 LICENSE」（`UPSTREAM.md:12-17`）这两句外部事实。`source_commit` `be09f73c3af1bbc698d19a532ef6d3c9987e6370`（`UPSTREAM.md:6`）同样未核实。

因此：许可证种类内部一致；署名和「独立实现」的说法不自洽。外部上游原文未核实，本轮不改 `LICENSE` 和 `UPSTREAM.md`。

另外，`DECISIONS.md:33` 写 P1 修复合入提交 `d9841ec2`。本克隆 `git log` 只有 `12bf01f`，看不到那个哈希。`_ClosingConn`（`app.py:55-86`）和改密吊销其他会话（`app.py:515-529`）的代码都在。更像是交付时历史被压成了一个提交，不据此改 `DECISIONS.md`。

不算缺陷、也不修：`DECISIONS.md:15-17` 规定首次改密只提示、不强制；`DECISIONS.md:24-26` 规定黑名单不含 `198.18.0.0/15`，且不用 `ipaddress.is_private` 一刀切。代码与这两条决定一致。

## 分级修复清单

### P0

无。服务能起，测试能过。

### P1

1. **SSRF 校验可以被绕过（安全）。** `app.py:265-271` 解析结果无法被 `ipaddress` 识别时直接跳过，一个都认不出就放行；`app.py:282-289` 校验之后仍用 urllib 打开原始主机名，连接时重新解析，并使用环境代理。修法：不走环境代理，只连接刚刚校验过的那个 IP；解析结果有任何一条认不出，或命中内网清单，就拒绝；重定向每一跳按同样规则再查一次。`PAGEWATCH_ALLOW_PRIVATE_FETCH=1` 时仍跳过内网拦截，避免弄坏现有自测。
2. **退出不吊销令牌（权限）。** `static/index.html:142` 的 `logout()` 只清 `localStorage`。后端没有退出接口，探针 `POST /api/logout` 返回 404，随后 `GET /api/me` 仍是 200。修法：增加 `POST /api/logout`，删除当前 Bearer 令牌；前端退出时先清本地状态，再用该令牌调用这个接口。

### P2

1. **超限仍当成功快照（数据质量）。** `app.py:293-310`。修法：读到超过 `FETCH_MAX_BYTES` 就抛 `FetchError`，不要把截断正文存成成功快照。本轮不改，避免和 P1 的抓取改动缠在一起。
2. **默认数据库路径容易理解成当前目录。** `README.md:46`，实际在 `app.py:29-32`。修法：README 写明是 `app.py` 所在目录下的 `data/pagewatch.db`。本轮不改文档。
3. **不区分响应是不是 HTML。** `app.py:300-310`。修法：非 `text/html`（以及没有类型的正文）记为错误，或在 README 写明「不看 Content-Type」。本轮不改。
4. **单条标已读不清监测项上的「有变化」。** `app.py:746-756` 只更新那一条提醒；`app.py:759-763` 的全部已读会清 `has_unread_change`。前端 `static/index.html:238` 的「标已读」不走 `/seen`。修法：这条提醒已读后，若该监测项已没有未读提醒，就把 `has_unread_change` 置 0。本轮不改。
5. **快照只留 20 份，更早的提醒仍指向已删除的快照。** `app.py:377-382` 删除旧快照，`app.py:142-148` 的 `snapshot_id` 没有外键。`tests/test_app.py:321` 要求 25 次变化后未读提醒仍是 24，所以不能靠删提醒来修。本轮不改。
6. **结构清单和依赖警告。** `README.md:67-75` 漏了三个根目录文件。测试警告来自 `requirements-dev.txt:2` 钉死的 `httpx==0.28.1`，Starlette 提示要换 `httpx2`。修法：补 README 清单；依赖版本本轮不动（测试能过，不是冲突）。
7. **许可证表述。** `LICENSE:189`、`UPSTREAM.md:8`、`UPSTREAM.md:18-20`、`README.md:5`。修法：保留上游版权行，另加本仓库自己的版权说明和 `NOTICE`。外部原文未核实，本轮不改 `LICENSE` / `UPSTREAM.md`。
8. **本克隆对不上 DECISIONS 里的提交号。** `DECISIONS.md:33` 的 `d9841ec2` 不在 `git log`（只有 `12bf01f`）。修法：若确认是压历史造成的，改这句话指向当前提交。证据不足，本轮不改。
