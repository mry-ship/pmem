---
id: 01M641EMQVGN2NXPGY2TR3EFZY
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes: []
anchors:
- pyproject.toml
- src/pmem/__init__.py
- README.md
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 当前安装包 0.6.1：检索采用与防错记忆补丁，不占 v0.7
verify: uv run pmem --version
applies: 发 0.6 补丁或改 README 路线当前版本时
---
需求来源：用户要求把本轮检索采用与防错记忆优化发成可辨认的版本，并提交推送。
必须保持：安装包、README 徽章、手册页眉页脚、uv.lock 同为 0.6.1。这是 0.6 补丁，不占 v0.7。
v0.7 路线表仍为进行中；类型安全发版前不要跳到 0.7.0。
v0.6.1 内容：无关键词速览防错优先且默认名额内结论最多 2 条；
同一对话带 query 再查时未见全文先占名额；
written 损坏时凭 recorded id 不再催已写模块；
compact 合并后保持 exclusion/risk/correction。
入口：pyproject.toml、src/pmem/__init__.py、README.md 路线表、docs/pmem-guide.html 页眉页脚。
