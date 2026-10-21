# pagewatch 修复记录

只修了 review.md 清单里的 P1-1、P1-2。P0 无。P2 未改。

## P1-1 SSRF 校验可被绕过

文件：`app.py:253-387`（`_checked_ips`、钉住 IP 的连接、`fetch_url`）。替换了原来的 `app.py:254-310`（`_assert_url_allowed` 里解析失败就 `continue`，以及 urllib 打开器）。

改法：

- 解析出的每一条地址都要能识别；带网卡后缀的先去掉后缀。认不出，或命中内网清单，就拒绝。
- 连接只用刚刚校验通过的那个 IP，Host 头和 HTTPS 证书仍用原主机名。
- 不再使用 urllib，因此不走 `HTTP_PROXY` / 系统代理。
- 重定向最多 10 跳，每一跳重新解析、重新校验。只允许 http/https。
- `PAGEWATCH_ALLOW_PRIVATE_FETCH=1` 时仍按主机名直连，不拦内网。体积截断的旧循环没改（仍是 P2）。

验证命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_pytest.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_live.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\verify_p1_ssrf.py
```

pytest（exit 0）：

```
20 passed, 1 warning in 5.20s
```

live_selftest（exit 0）：

```
20/20 检查点通过
ALL PASS
```

探针（exit 0，当时 `HTTP_PROXY=http://127.0.0.1:7890` 仍在）：

```
dns rebind.test #1 port=None
REBIND FetchError 抓取失败：timed out
REBIND hits [] name lookups 1
dns weird.test #1 port=None
WEIRD FetchError 禁止抓取内网地址（weird.test）
WEIRD hits [] name lookups 1
REDIR FetchError 禁止抓取内网地址（169.254.169.254）
REDIR hits ['/go']
BLOCK http://127.0.0.1:9/secret FetchError 禁止抓取内网地址（127.0.0.1）
BLOCK http://169.254.169.254/latest/meta-data/ FetchError 禁止抓取内网地址（169.254.169.254）
BLOCK file:///C:/Windows/win.ini FetchError 不支持的网址协议（file）
```

和修之前对比：伪造的二次解析不再打进本机监听（hits 为空，主机名只解析 1 次）；`127.0.0.1%eth0` 被当成回环拒绝；重定向到 `169.254.169.254` 被拒绝，且只访问了 `/go`；代理还开着，但错误是连接超时，不是代理的 `HTTP 502`。

## P1-2 退出不吊销令牌

文件：`app.py:610-624` 新增 `POST /api/logout`；`static/index.html:142-148` 的 `logout()` 在清掉本地令牌后调用该接口。

改法：用当前 Bearer 到 `tokens` 表里删掉这一枚令牌，其它会话不删。前端先把内存和 `localStorage` 里的令牌清掉，再用清掉前的那枚令牌发请求，避免 401 处理函数来回调用。

验证命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\verify_logout.py
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_pytest.py
```

第一次跑验证脚本失败，原因是脚本自己没调用 `init_db()`，报错原文：`sqlite3.OperationalError: no such table: users`。这不是接口回归。补上 `init_db()` 后重跑，exit 0：

```
LOGIN 200 must_change True
LOGIN 200 must_change True
ME_A_BEFORE 200
ME_B_BEFORE 200
LOGOUT_A 200 {"ok":true}
ME_A_AFTER 401 {"detail":"登录已过期，请重新登录"}
ME_B_AFTER 200
LOGOUT_A_AGAIN 401 {"detail":"登录已过期，请重新登录"}
```

同一账号两个会话：退出 A 之后 A 的令牌失效，B 仍然有效。对已失效的令牌再退出得到 401。

同一时刻的 pytest（退出接口已经在代码里）exit 0：`20 passed, 1 warning in 4.96s`。

没有浏览器工具，前端按钮没有在页面里点过。核对了 `static/index.html:142-148`：`logout()` 会 `POST /api/logout`，并带上退出前的 Bearer。

## 全量重跑

两条修复都进工作区之后重跑。

pytest 命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_pytest.py
```

结果（exit 0）：

```
20 passed, 1 warning in 7.66s
```

警告仍是 Starlette 对 `httpx` 的弃用提示（`requirements-dev.txt` 钉的是 `httpx==0.28.1`），没有失败项。

live_selftest 命令：

```
E:\muse-bridge\work\TASK-034-pagewatch\venv\Scripts\python.exe E:\muse-bridge\work\TASK-034-pagewatch\run_live.py
```

结果（exit 0）：

```
20/20 检查点通过
ALL PASS
```

没有仍然失败的测试。

## git status --porcelain

命令：

```
git status --porcelain
```

输出：

```
 M app.py
 M static/index.html
```
