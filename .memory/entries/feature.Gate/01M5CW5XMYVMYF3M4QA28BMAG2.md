---
id: 01M5CW5XMYVMYF3M4QA28BMAG2
module: feature.Gate
entity: PromptReview
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/memories.py#memory_lines
- src/pmem/hooks/review.py#_offer_digest
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 记忆标题会在读代码时自动注入 Agent，全项目级条目读任何模块都会带上
verify: 写一条 scope 为 project、标题含操作指令的记忆，读另一个模块的文件，确认摘要把它标成资料而不是必须执行的指令
aliases:
- 提示注入
- prompt injection
- 全项目级坑
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
风险：读代码摘要（hooks/memories.py 的摘要行）把记忆标题原样放进 additional_context，规则要求 Agent 按记忆行事。
标题最长约 200 字，够写一条操作指令。
scope 为 project 的排除项、风险和更正，每个对话在读任何模块时最多带 3 条。
search_memory 再返回全文。
这和恶意代码要运行才生效不同：能往 .memory/entries 提交文件的人，只要队友读代码或提问就会注入。摘要没有把记忆标成资料、与必须执行的指令分开。
闸门挡的是忘了查记忆的 Agent，不是沙箱：Hook 出错默认放行，编码后的 PowerShell 和认不出的程序事前看不出写了哪些文件。
