# 本仓决定记录（DECISIONS）

记录本项目的具体决定与审查处理结论。全局统一口径见《项目口径总表》；
与总表冲突时以用户最新决定为准。

## 产品与范围

- **只抓静态 HTML，不做浏览器渲染**（2026-10-21 建仓决定）：Playwright 一类
  渲染依赖重、云端 2 核吃力；纯 JS 渲染页面抓不到正文的限制在 README 如实写明。
- **通知只做站内提醒**：不接邮件 / Telegram 等外部渠道。
- **快照每监测项保留最近 20 份**：够看变化历史，自用场景不无限堆积。

## 安全口径落实

- **首次改密只提示、不强制**（总表第 1 条，用户 2026-10-21 拍板）：登录后弹窗
  提示、可跳过，业务接口不因未改密被拦截。审查再报此项按已定决策关闭，
  不得以任何实现形式把强制改密加回来。
- **改密成功后吊销其他会话**（总表第 2 条）：与改密同一事务里删除该用户除
  本次会话外的全部令牌（保留当前会话；取不到当前令牌时不删）。与第 1 条是
  两回事，不得混为一谈。已配回归测试
  `test_change_password_revokes_other_sessions`。
- **默认只监听本机**（总表第 3 条）：HOST 环境变量默认 127.0.0.1，
  README 环境变量表注明放开前先改掉默认密码。
- **SSRF 防护用显式网段清单**（总表第 9 条）：禁用 `ipaddress.is_private`
  一刀切（云端假 IP 解析会误伤公网域名）；清单不含 198.18.0.0/15；
  本地调试开关 PAGEWATCH_ALLOW_PRIVATE_FETCH 默认关。
- **接口文档页关闭**（总表第 6 条）：/docs、/redoc、/openapi.json 返回 404。

## 审查处理记录

- **TASK-013（Grok 首轮审查，P0 0 / P1 2 / P2 11）**：其分支上的代码改动在
  桥的发布环节丢失（分支 app.py 与 main 逐字节相同，只剩报告），故两条 P1
  由我方在 main 上独立实现并验证后合入（提交 d9841ec2）：
  P1-1 数据库连接改为 `_ClosingConn` 包装（with 结束提交/回滚后关闭连接）；
  P1-2 改密吊销其他会话（见上）。P2 的 11 条本轮未动，其中"未改密前能调
  业务接口"一条与总表第 1 条口径相关，按已定决策保持现状。
- **TASK-021（Grok 第二轮审查，P0 0 / P1 4 / P2 13）**：基座比当前 main
  旧 4 个 commit，未直接合并，逐条手工搬运对账后合入 main：
  - P1-1（重定向 SSRF）与我方已有修法（3f7e1308）对账：Grok 方案初始目标
    放行用户手写的环回/私网、重定向守卫用 `not is_global`（即 is_private
    一刀切的变体），两处都与总表第 9 条冲突（且在云端假 IP 环境下会误拦
    公网重定向），故整体不采纳。只采纳其互补项：`_assert_url_allowed` 新增
    http/https 协议白名单、云元数据主机名显式拦截
    （metadata.google.internal / metadata.google.com）、`_BLOCKED_NETWORKS`
    追加 100.100.100.200/32（阿里云元数据）。配回归测试
    `test_ssrf_blocks_metadata_host_and_scheme`。
  - P1-2（改密删全部 token 含本次）与总表第 2 条冲突（保留本次会话），
    且我方 main 的实现（d9841ec2）已符合口径：不合入，关闭。
  - P1-3（新增 POST /api/logout 只废止当前会话）为新增真功能，采纳；
    前端 logout 先调接口再清本地（直接 fetch，避免 401 递归）。配回归测试
    `test_logout_revokes_only_current_session`。
  - P1-4（快照轮转后提醒悬空）为新增真修，采纳：删旧快照前把对应提醒
    snapshot_id 置 NULL（提醒行保留、未读数不变），前端条件渲染按钮并在
    sid 为空时提示。配回归测试
    `test_snapshot_rotation_unlinks_notifications`。
  - P2-8（强制改密）与总表第 1 条一致，Grok 本人也明确"不改"：永久不采纳，
    再报直接关闭。P2-11（/docs 无登录）已在总表第 6 条落实，无需动作。
    P2 其余 11 条本轮未动。
  - 红线核对：分支测试文件与基座（5ecbb22f）逐字节一致，未被动过；
    新 main 上重跑 pytest 23 项＋真实自测 20 检查点全部通过。
- **TASK-034（Grok 深度审查 P1-1 增量硬化，基座旧 3 commit）**：未直接合并，
  在当前 main 上正经实现。抓取改用 `http.client` 直连＋IP 钉住：
  `_checked_ips` 返回校验过的 IP 列表（解析失败/无法识别/无可用地址一律
  拒绝，不再静默放行）；`_PinnedHTTPConnection` / `_PinnedHTTPSConnection`
  只连接刚刚校验过的 IP（Host 头与 HTTPS SNI 仍用原主机名，防 DNS rebind）；
  不再走 urllib（避开 HTTP_PROXY 环境代理、避开连接时二次解析）；
  重定向手动跟、最多 10 跳、每一跳重新解析校验；协议白名单与
  PAGEWATCH_ALLOW_PRIVATE_FETCH 调试开关保留；198.18 排除保留
  （与总表第 9 条一致）。配 4 个回归测试（rebind 探针、重定向逐跳校验、
  10 跳上限、不可识别解析结果拒绝）。P1-2（logout）与 main 已有实现
  （0c5d4d0）重复，不合。
- **TASK-049（Grok P2 收口轮，基座旧）**：未直接合并，手工搬运
  P2-1/2/3/4/6，跳过 P2-5（与 0c5d4d0 的快照轮转解提醒同义重复）：
  P2-1 页面超 2MB 抛错不存快照（恰好等于上限仍成功）；
  P2-2 README 数据库路径改为 `<app.py 所在目录>/data/pagewatch.db`
  并注明不跟随进程当前目录；
  P2-3 非 text/html 响应拒绝（无 Content-Type 或主类型不对都拦，
  与 README「只抓静态 HTML」对齐）；
  P2-4 单条标已读后该监测项无未读则清 has_unread_change（前端 readOne
  补 loadWatches 刷新列表）；
  P2-6 README 项目结构补 requirements.txt / requirements-dev.txt /
  LICENSE。配 3 个回归测试。P2-7/P2-8 按报告结论不改。
  - 红线核对：两分支测试文件均未被动过；新 main 上 pytest 30 项＋
    真实自测 20 检查点全部通过。
