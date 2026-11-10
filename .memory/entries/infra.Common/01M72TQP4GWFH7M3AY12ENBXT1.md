---
id: 01M72TQP4GWFH7M3AY12ENBXT1
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M6REZRNRX1G8WW5YR8SNHB9X
anchors:
- src/pmem/__init__.py
- pyproject.toml
revision: git:ea57053
author: 1002378395@qq.com
note_date: '2026-11-10'
summary: 当前安装包 0.6.6：harness 实验，不占 v0.7
verify: uv run pmem --version；gh release view v0.6.6
applies: 发版或改路线表当前版本时
---
需求来源：0.6.5 之后合入 harness 执行框架实验，发 0.6.6，不占 v0.7。

必须保持：安装包当前为 0.6.6（pyproject.toml、src/pmem/__init__.py、uv.lock 同步为 0.6.6）。0.6 补丁线，v0.7 类型安全仍进行中，不要跳 0.7.0。

v0.6.6：harness.mode 默认 off；
hint 档 search_memory 带 path 时返回 context（常一起改、修复提交、规格必须保持）；
check 档 Stop 漏改与验证检查；
pmem context；
report 三项指标。

README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.6.6。

入口：README 路线表当前版本；GitHub Release v0.6.6；发下一个 0.6 补丁或改路线表当前版本时更新本条。
