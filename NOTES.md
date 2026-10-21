# 调研笔记（pagewatch）

2026-10-21，通过 GitHub 接口通读上游 changedetection.io（HEAD be09f73c）后记录。

## 上游的设计要点（查到的事实）

- 定位：自托管网页变化监测。核心对象是 watch（监测项）：一个网址、一个检查
  间隔，外加一串按时间存档的历史快照。
- 数据模型（changedetectionio/model/Watch.py）：watch 的关键字段包括
  `url`、`time_between_check`（按秒/分/时/天换算的检查间隔）、`last_checked`、
  `last_changed`、`last_viewed`（看过最新变化就不再算"有未读变化"）、
  `history_snapshot_max_length`（快照保留上限）；历史快照以时间戳为键逐份存文件，
  每份带内容校验值，判变就是比最新快照的内容变没变。
- 文本抽取（html_tools.html_to_text）：用 inscriptis 把 HTML 转成纯文本再对比；
  diff 视图支持按行 / 按词 / 按字三种粒度。
- 抓取后端可插拔：普通 HTTP 请求之外还能走 Playwright 等浏览器渲染，
  配套 CSS/XPath/JSON 筛选器、价格/库存（restock）监控等重型功能。
- 通知：通过 apprise 库发往邮件、Telegram 等几十种外部渠道，每个 watch 单独配。
- 许可证：Apache License 2.0（LICENSE 原文已逐字核对），署名行为
  "Copyright (c) Leigh Morresi and the changedetection.io contributors"。

## 本项目的取舍（设计决定）

- 骨架沿用"监测项 + 时间序列快照 + 内容哈希判变 + 未读变化标记"这套核心思路，
  落到 SQLite 表：watches / snapshots / notifications（外加 users / tokens 管登录）。
- 快照上限：每个监测项最多保留最近 20 份（上游同样有上限概念，数值按自用场景定）。
- 文本抽取：用 Python 标准库 html.parser 自写轻量抽取器——块级元素断行、
  行内空白折叠、跳过 script/style 等不可见内容，不引 inscriptis/lxml 依赖；
  diff 用标准库 difflib 逐行对比，前端把增行标绿、删行标红。
- 抓取：标准库 urllib，超时 15 秒、单页最多读 2MB，非 2xx/3xx 记为 error 状态；
  抓取失败只落状态和错误信息，不存快照、不发提醒，也不会拖垮调度
  （调度线程对每个监测项单独兜底）。调度为进程内线程，按各监测项自己的间隔触发。
- 明确砍掉：浏览器渲染抓取（Playwright 一类依赖重、云端 2 核吃力）、外部通知
  （只做站内提醒列表）、多用户、筛选器、价格监控、截图等。
- 已知限制：只抓静态 HTML，纯靠前端 JS 渲染出正文的页面抓不到内容，
  这一条在 README 里如实写明，不假装支持。
- 登录沿用本团队既有做法：pbkdf2 密码哈希、Token 24 小时、首次登录提示改密、
  默认账号 admin / admin123。
- 资源核对：单进程 FastAPI + SQLite + 一个调度线程，无外部服务、无 GPU 需求；
  云端为 2 核 / 约 7.9G 内存，本项目负载主要是偶尔的 HTTP 抓取与文本对比，
  绰绰有余（实测数字见 README 的测试一节）。

## 口径落实补充（2026-10-21，对照《项目口径总表》自查后补）

- SSRF 防护（总表第 9 条）：抓取前解析目标主机名，任一地址命中显式内网清单
  （回环、RFC1918、169.254/16、100.64/10、组播、保留段及 IPv6 对应段，含
  v4 映射地址）即拒绝；重定向每一跳重新校验。清单刻意不含 198.18.0.0/15，
  且禁用 is_private 一刀切——运行环境 DNS 是假 IP 模式，公网域名会解析到
  198.18 段，一刀切会把正常网站全拦掉。本地调试可用
  PAGEWATCH_ALLOW_PRIVATE_FETCH=1 临时放开（默认关，README 已写明）。
- 接口文档页（第 6 条）：FastAPI 的 /docs、/redoc、/openapi.json 已关闭。
- 超长输入（第 10 条）：名称（100 字）与网址（2000 字）超限返回 400，
  报错信息带上限与当前长度，不静默截断。
