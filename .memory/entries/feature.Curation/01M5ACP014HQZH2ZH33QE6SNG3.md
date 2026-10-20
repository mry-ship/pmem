---
id: 01M5ACP014HQZH2ZH33QE6SNG3
module: feature.Curation
entity: ChangelogDetect
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/core/quality.py#content_hints
- src/pmem/core/quality.py#verify_hint
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: 变更记录检测曾被决定前缀绕过，现先去掉决定/结论标签再判断
verify: pytest tests/core/test_quality.py tests/test_quality_efficiency.py
aliases:
- 变更记录
- 写作提示
- changelog
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
---
更正：写作提示里的变更记录检测曾被绕过。正文以“决定：”或“结论：”开头时，标签本身就命中了“写了原因”的词表，提示从不触发。
现在先去掉开头的“决定/结论”标签再判断；“根因：”“风险：”不去掉，因为它们本身就是在讲原因（去掉会让“根因：xxx”被误判成变更记录，单测发现过）。
新增两条提示：decision 没写取舍（因为、为了、避免、而不是…）时提示补“为什么这样选”；conclusion、correction 没填 verify 时提示写验证方法。
风险：TileMatch 项目里有一份 quality.py 副本，规则改动要同步过去，否则两边提示不一致。
