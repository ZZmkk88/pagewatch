# pagewatch 修复记录

只修 `review.md` 分级清单里的 P1。P0 无。P2 未改。

## P1-1 重定向 SSRF / 链路本地与云元数据

问题编号：P1-1

文件：`app.py:196-342`（新增目标判断与 `_GuardRedirect`；`fetch_url` 改为走这个 opener）

改法：初始网址拒绝链路本地地址（含 `169.254.169.254`）、`100.100.100.200` 和 `metadata.google.internal` / `metadata.google.com`。重定向只跟随 http/https；目标不是公网地址时，仅当主机和端口与当前请求相同、且不是链路本地或元数据地址才跟随。用户写明的 `127.0.0.1` 和私网地址仍可直接抓取。

验证命令：

```
python -m pytest tests/ -q
python E:\muse-bridge\work\TASK-021-pagewatch\probe_p1_fetch.py
```

pytest 输出（exit 0）：

```
...............                                                          [100%]
15 passed, 1 warning in 3.18s
```

警告仍是依赖里的 `StarletteDeprecationWarning`（httpx / httpx2），不是失败。

探针输出（exit 0）：

```
DIRECT OK status=200 plain=True secret=False
REDIR_SAME OK status=200 plain=True secret=False
REDIR_OTHER ERR FetchError: 拒绝重定向到其他内网或本机地址
REDIR_FTP ERR FetchError: 拒绝重定向到非 http(s)
REDIR_FILE ERR FetchError: HTTP 302
LINK_LOCAL ERR FetchError: 拒绝访问链路本地或云元数据地址
METADATA_HOST ERR FetchError: 拒绝访问云元数据地址
ALIBABA_META ERR FetchError: 拒绝访问链路本地或云元数据地址
SECRET_HITS []
```

跨端口重定向没有打到秘密端口（`SECRET_HITS []`）。同一主机同一端口的重定向仍然成功。`file://` 仍由 Python 3.11 的 urllib 拒绝。链路本地地址在连接前被拒绝，不再出现修前的 `HTTP 502`。

## P1-2 改密后旧 Token 继续有效

问题编号：P1-2

文件：`app.py:559` 在更新密码后增加 `DELETE FROM tokens WHERE user_id = ?`。`static/index.html:282` 改密成功后提示重新登录并调用 `logout()`。

改法：改密成功后删掉该用户已签发的全部 Token。页面改密成功后清掉本地 Token 并回到登录页，避免界面还拿着已经作废的 Token。

验证命令：

```
python -m pytest tests/ -q
python E:\muse-bridge\work\TASK-021-pagewatch\probe_p1_token.py
```

pytest 输出（exit 0）：

```
15 passed, 1 warning in 3.21s
```

探针输出（exit 0）：

```
CHANGE_PW 200
OLD_TOKEN_ME 401
OLD_PW 401
NEW_PW 200 must_change False
```

修前同一探针是 `OLD_TOKEN_ME 200`。现为 401。新密码可以登录，且 `must_change_password` 已清除。旧密码不能登录。官方 `test_change_password_flow` 仍在 15 项通过里。

## P1-3 退出登录不废止服务端 Token

问题编号：P1-3

文件：`app.py:563-574` 新增 `POST /api/logout`。`static/index.html:142` 的 `logout()` 在清掉本地 Token 后，用原来的 Token 调用该接口。

改法：服务端按当前 Bearer Token 删除这一条会话。别的登录会话保留。前端不用会在 401 时递归的 `api()`，直接 `fetch`，避免退出请求自己再触发退出。

验证命令：

```
python -m pytest tests/ -q
python E:\muse-bridge\work\TASK-021-pagewatch\probe_p1_logout.py
```

pytest 输出（exit 0）：

```
15 passed, 1 warning in 3.17s
```

探针输出（exit 0）：

```
LOGOUT 200 {'ok': True}
T1_ME 401
T2_ME 200
LOGOUT_AGAIN 401
```

被退出的 Token 再访问 `/api/me` 为 401，另一枚 Token 仍是 200。已作废的 Token 再调退出接口也是 401。

## P1-4 快照轮转后提醒悬空

问题编号：P1-4

文件：`app.py:408-423` 在删除旧快照之前把对应提醒的 `snapshot_id` 置为 NULL。`static/index.html:234` 仅在 `snapshot_id` 有值时渲染「看对比」。`static/index.html:240` 在 `sid == null` 时提示已超出保留上限并返回。

改法：提醒行保留，所以未读数不变；点不到已经不存在的快照。

验证命令：

```
python -m pytest tests/ -q
python E:\muse-bridge\work\TASK-021-pagewatch\probe_p1_snap.py
```

pytest 输出（exit 0）：

```
15 passed, 1 warning in 2.75s
```

探针输出（exit 0）：

```
SNAPSHOTS 20
NOTIFS 24 items 24
DANGLING 0
NULLED 4
KEPT_LINK 20
```

修前是 `DANGLING 4`。现为 0，其中 4 条提醒的 `snapshot_id` 已清空，其余 20 条仍指向还在的快照。`test_snapshot_cap_20` 要求的 20 份快照和 24 条未读都还在。

## 全量重跑

四项都落地之后重跑 README 里的两套测试。没有失败项。

命令：

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
15 passed, 1 warning in 3.16s
```

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

未改测试，未改 `requirements.txt` / `requirements-dev.txt` 的版本号，未改 `LICENSE` / `UPSTREAM.md`。P2 未动。

## git status

命令：

```
git status --porcelain
```

输出：

```
 M app.py
 M static/index.html
```


