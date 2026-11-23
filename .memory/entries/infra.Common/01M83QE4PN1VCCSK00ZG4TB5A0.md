---
id: 01M83QE4PN1VCCSK00ZG4TB5A0
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M7Z7VTY8C2EAXH19P9E0MFMK
- 01M83KK2NEZ4YGKNXRQP3AT6QA
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 当前安装包 0.7.4：闭集同一文件核对、规格摘录与整份对话已读
verify: uv run pmem --version；gh release view v0.7.4
applies: 发版或改路线表当前版本时
source:
  conversation: 913a2b7e-59bf-4672-aac5-d3572e39cc75
  kind: document
---
需求来源：0.7.3 之后把规格闭集核对、规格摘录和对话记录已读收成 0.7.4 发布。

必须保持：安装包当前为 0.7.4（pyproject.toml、src/pmem/__init__.py、uv.lock 同步）。不要再把 --version 期望成 0.7.0 或 0.7.3。
本版相对 0.7.3：pmem spec closed 仍只读，输出仍是一致 / 可能不一致 / 无法判断；原文先剥一行说明前缀，字面量只在同一文件内按顺序、相邻不超过 4000 字才算一致；无签名字段名只出现过不算一致。
规格闸门摘录改为契约各节全文，已读扫描整份对话记录；拒绝文案写明摘录后再改可放行。modules.yaml 顶层 schema_version 不再报不认识。
不改检索排序和采用判定。README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.7.4。效果栏「当前版本 0.7.4」沿用 2026-11-21 近 30 天 report。

入口：README 路线表当前版本；GitHub Release v0.7.4。
