# 上游溯源（UPSTREAM）

本项目在设计阶段学习了开源社区网页变化监测工具的通行思路，按接力规范记录上游信息如下：

- **source_url**: https://github.com/dgtlmoon/changedetection.io
- **source_commit**: be09f73c3af1bbc698d19a532ef6d3c9987e6370
- **license**: Apache License 2.0
- **attribution**: Copyright (c) Leigh Morresi and the changedetection.io contributors

## 说明

- `source_commit` 是 2026-10-21 通过 GitHub 接口实查的上游默认分支 HEAD 提交
  （提交时间 2026-10-19）；当日做设计调研时查阅的上游内容正是这一提交，
  包括 README、changedetectionio/model/Watch.py（监测项与快照的数据结构）、
  changedetectionio/html_tools.py（HTML 转文本的做法）与 LICENSE 原文。
- `attribution` 的版权行逐字复制自上游仓库 `LICENSE` 原文附录，未做任何改动；
  本仓库 `LICENSE` 文件即上游所用的 Apache License 2.0 全文。
- 本项目代码为独立重写（Python + FastAPI + SQLite，文本抽取与 diff 均用
  Python 标准库实现），未复制上游源码；借鉴的是"监测项 + 快照 + 哈希判变"
  这类核心概念，具体调研记录见 NOTES.md。
