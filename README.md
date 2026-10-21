# pagewatch · 网页变化监测

一句话定位：一个轻量、可自托管的网页变化监测工具——盯住一批网页，定时抓取文本存快照，内容一变就逐行标出改动并在站内提醒，单用户自用。

设计学习了开源社区同类工具的通行思路（监测项、快照存档、内容判变），代码为独立实现（溯源见 UPSTREAM.md）。

## 功能清单

- 单用户登录（Token 24 小时有效，首次登录提示改密）
- 监测项管理：新建 / 编辑 / 删除（名称、网址、检查间隔分钟数），可暂停 / 恢复，可手动「立即检查」
- 定时抓取：进程内调度按每个监测项自己的间隔自动检查；只抓静态 HTML 并抽取可见文本，抓取带超时（15 秒）与体积上限（2MB），失败只记录错误状态、不影响其他监测项；抓取前会校验目标不指向内网地址（SSRF 防护，含重定向逐跳校验）
- 快照存档：每次成功检查存一份文本快照，每个监测项最多保留最近 20 份
- 变化判定与对比：新快照与上一份逐行对比（diff），增行 / 删行高亮显示；监测项列表能打开任意一份快照看它与上一份的对比，也能看快照原文
- 站内提醒：发现变化即生成提醒（带增删行数摘要），提醒列表可看、可单条标已读、可全部标已读；监测项上有「有变化」未读标记，查看后清除

## 快速开始

默认账号：`admin` / `admin123`（首次登录会提示改密）。

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows（PowerShell）

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

启动后打开 http://127.0.0.1:8000 ，用默认账号登录即可。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | 监听地址。默认只监听本机；确实需要局域网/对外访问时才改 `0.0.0.0`，**放开前务必先改掉默认密码** |
| `PORT` | `8000` | 监听端口 |
| `PAGEWATCH_DB_PATH` | `data/pagewatch.db` | 数据库文件位置 |
| `PAGEWATCH_ALLOW_PRIVATE_FETCH` | 关 | 设为 `1` 时关闭抓取的内网地址拦截。仅供本地调试/自测（监测对象就在本机时），正式环境不要开启 |
| `PAGEWATCH_DISABLE_SCHEDULER` | 关 | 设为 `1` 时不启动进程内定时调度（测试用） |

## 测试

先装开发依赖，再跑自动化测试与真实流程自测：

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python tests/live_selftest.py
```

（Windows 同样是这两条命令，在已激活 venv 的 PowerShell 里执行。）

实测结果（2026-10-21，云端 2 核环境）：自动化测试 20 项全过；
`live_selftest.py` 会真的起一个服务进程加一个本地假页面，走一遍
"登录 → 建监测项 → 检查得首份快照 → 改假页面内容 → 再检查报变化 →
看 diff 改动行 → 提醒生成 → 标已读"的完整流程，20 个检查点全过。

## 项目结构

- `app.py` — 后端（FastAPI + SQLite）：账号、监测项、抓取、快照、diff、提醒与调度
- `static/index.html` — 单页前端（原生 HTML/JS，无构建步骤）
- `tests/test_app.py` — 自动化测试
- `tests/live_selftest.py` — 真实服务自测脚本
- `NOTES.md` — 设计调研笔记
- `UPSTREAM.md` — 上游溯源信息
- `DECISIONS.md` — 本仓的决定记录（口径落实与审查处理）

## 说明

- **只抓静态 HTML**：纯靠前端 JavaScript 渲染出正文的页面抓不到内容，本项目不支持浏览器渲染抓取，选监测对象时请避开这类页面。
- 抓取带 SSRF 防护：目标主机名解析出的任一地址命中内网/保留网段即拒绝抓取，重定向每一跳重新校验；接口文档页（/docs 等）默认关闭。
- 只做站内提醒，不发邮件 / Telegram 等外部通知。
- 本项目为个人自托管用途的单用户版本，不含多用户、内容筛选器、价格监控等功能。
