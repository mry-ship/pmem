---
id: 01M6RDZES5C0WYFVDRDFJSP5FD
module: feature.Tools
entity: AnchorLine
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_normalize_anchor
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 写入锚点时先把换行收成一行
verify: uv run pytest tests/test_service.py tests/core/test_entry.py -q
applies: pmem record 或 record_memory 带 anchors 时
aliases:
- 锚点换行
---
需求来源：锚点整理只改斜杠和相对路径，不把中间的换行收掉。带换行的锚点会进记忆文件，规格预填和摘要再把它写出去。

必须保持：_normalize_anchor 先把整条锚点的空白和换行收成一行，再按 # 分成路径和符号，然后做相对路径和大小写核对。空锚点仍不写入。密钥检查仍覆盖锚点文本。

入口：RecordService._normalize_anchor。
