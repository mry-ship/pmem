---
id: 01M5CFJZRQ4M5TX0995HDTBR4K
module: feature.Metrics
entity: Events
kind: conclusion
status: active
supersedes:
- 01M4X5ZT04CKHE886GP8S08RM6
anchors:
- src/pmem/hooks/gate.py#on_stop
- src/pmem/hooks/gate.py#on_after_mcp
- src/pmem/metrics/report.py#_link_cli_searches
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: stop 的 token 是单轮值按对话求和；mcp_search 逐层解析 JSON 取 id
aliases:
- 事件日志
- token 统计
- 收益口径
---
收益统计的数据口径（Cursor 3.9 实测）：stop Hook 的 input_tokens / output_tokens / cache_read_tokens / cache_write_tokens 是单轮值，按对话求和；
input_tokens 已包含 cache_read_tokens。
stop payload 带 user_email，事件日志不记录。
events.jsonl 只在用户缓存目录（不进仓库），PMEM_NO_EVENTS=1 可关闭。
MCP 检索在服务端记 search 事件，对话 id 来自 Hook 注入的 source_conversation（已实测生效，见 AutoAnchors）；
Hook 侧另记 mcp_search 作为兜底。
更正：mcp_search 的 id 不是用正则抠，而是逐层解析返回的 JSON、按 ULID 格式校验；
终端 pmem search 没有对话 id，report 在前后 30 秒内找时间最近的 search_call（含 search_call_unseen）关联，不只是“紧邻的前一条”。
“对话对照”只是观察数据，每组少于 5 个对话时注明样本不足，严格对比用 pmem bench。
