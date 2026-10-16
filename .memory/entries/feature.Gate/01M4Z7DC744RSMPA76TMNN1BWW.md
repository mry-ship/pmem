---
id: 01M4Z7DC744RSMPA76TMNN1BWW
module: feature.Gate
entity: AnalysisReminder
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py
- src/pmem/metrics/report.py
revision: git:7c1880c
author: 1002378395@qq.com
note_date: '2026-10-15'
---
决定：只排查、没改代码的对话结束时，默认不提醒记录结论，先只统计；提醒做成开关 gate.analysis_reminder，默认关闭。

依据：TileMatch 的数据显示写入本来就偏多，54% 的用户轮次都有写入，基本是“每轮回复一条”。
再加一个触发点，容易引出应付式写入。
853 条记忆里明确标注“仅分析、未改代码”的只有 17 条（2%），说明分析结论有人在记，但漏记了多少没有数据。

判定：
- 提问里含排查类用语（gate.analysis_markers：为什么、原因、排查、报错、崩溃、闪退、不生效、bug、why……，英文不分大小写）；
- 查过某模块的记忆（consulted，压缩上下文时不清空）；
- 结束时该模块既没改也没写记忆。

stop 事件会记下 analyzed，pmem report 的“习惯”里显示：排查类对话有多少个，其中多少个结束时仍有这样的模块。

验证：排查类用语在 Windows 转码后的乱码形态下也能识别。5 条排查类提问全部识别，10 条普通需求（加功能、调动画、写文档等）无一误判。

下一步：攒到二三十个排查类对话后看报告。如果“结束时仍未记”的比例高，再考虑默认打开提醒。
