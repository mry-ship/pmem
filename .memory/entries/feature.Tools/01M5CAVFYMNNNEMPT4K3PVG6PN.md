---
id: 01M5CAVFYMNNNEMPT4K3PVG6PN
module: feature.Tools
entity: Layered
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#_by_ids
- src/pmem/service/search.py#_search
- src/pmem/service/record.py#_record
- src/pmem/server/app.py#build_server
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 检索返回 features 标题组和 ids 取全文，写入支持 applies
verify: pytest tests/test_feature_records.py
aliases:
- 功能记录
- 按id取
- 全文
---
用户要求（2026-10-19）：功能记录在检索里只给标题，但要能一步取到全文核对；适用条件要提醒 AI 自检。
必须保持：search_memory 返回 items（教训全文）和 features（功能记录、规划标题），有 features 时附 features_hint（改动会改变这些行为时先取全文、不要改回去；规划不是现状）；
新增参数 ids（命令行 --id）按 id 取全文，给了就忽略其他条件，也返回已被替代或归档的并标状态，找不到的列在 missing。
任一行带 applies 时附 applies_hint。
record_memory 新增 applies（覆盖草稿时沿用旧值，参与密钥检测，超过 120 字拒绝）。
MCP 说明和 INSTRUCTIONS 改为“改了模块写功能记录，有教训另写”。
入口：service/search.py 的 search、_by_ids；service/record.py 的 _record；server/app.py。
注意：MCP 服务不热加载代码，升级后要在 Cursor 里重启 pmem 服务，否则 kind=feature 会被旧进程拒绝。
