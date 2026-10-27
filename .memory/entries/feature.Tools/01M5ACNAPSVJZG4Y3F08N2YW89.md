---
id: 01M5ACNAPSVJZG4Y3F08N2YW89
module: feature.Tools
entity: SeenDedupe
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#_collapse_seen
- src/pmem/service/search.py#_claim_conversation
- src/pmem/service/record.py#_record
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: 同一对话再查到已给过全文的记忆只返回标题，full=true 取全文
verify: 同一对话连续两次检索同一模块，第二次每条标 seen；pytest tests/test_quality_efficiency.py
aliases:
- 去重
- 重复返回
- 折叠
- seen
verified: '2026-10-27'
verified_at: '2026-10-27T17:33:08.864+08:00'
---
决定（v0.3 对话内去重）：同一对话里已经返回过全文的记忆，再次检索到时只返回 id、议题、类型、日期、过期标记和一句话标题（seen: true），附 seen_hint；
要全文时 search_memory 带 full=true，命令行加 --full。
原因：本仓库带对话 id 的检索有 40%～50% 的条目是同一对话里整条重复给的（pmem report“对话内重复”），白占上下文。
去重是单向的：读代码摘要只给标题，不算“给过全文”，否则 Agent 拿不到正文。
对话 id：MCP 用 Hook 注入的 source_conversation；终端 pmem search 没有对话 id，按 Hook 写的交接文件认领（见 infra.Common/SeenHandoff），拿不到就不去重。
上下文压缩后清空该对话的去重记录，压缩后需要重新给全文。
写入新增 summary / verify / scope 参数：summary 没填只提示并展示自动标题，不拒绝；
verify 超过 300 字拒绝；
scope 只能是 module / project，否则 code=scope_invalid；
草稿覆盖时没填的三个字段沿用旧值。
风险：MCP 服务不热加载代码，升级后要重启 MCP 服务才生效（升级当天 report 显示“已折叠 0 条”就是旧服务）。
