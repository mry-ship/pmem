---
id: 01M5CAWR4SW0BKCA827YBPT7KV
module: feature.Gate
entity: ProjectPitfalls
kind: correction
status: active
supersedes:
- 01M5ACNM7VK664RE3TRYK2SK5N
anchors:
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/hooks/memories.py#take_project_pitfalls
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 结束提醒改为按模块写功能记录、有教训另写；标题与全项目级坑规则不变
verify: pytest tests/test_quality_efficiency.py tests/test_feature_records.py
aliases:
- 结束提醒
- 无新教训
- 无需记录
---
更正（2026-10-19，v0.3.1）：结束提醒不再是“有教训才写、没有就回复无新教训”。
现在每个改过的模块要写一条功能记录（kind=feature），另有教训再写；
确实不用记时回复“无需记录：原因”。
原因：用户要求做功能也要落库，只记教训会让用户要求的行为没有记录、被后来的 AI 改回去（见 feature.Gate / FeatureReminder 功能记录）。

仍有效（v0.3）：读代码摘要和拦截提示只列一句话标题（summary，没有时取正文第一句并去掉“决定：”这类前缀）。
全项目级坑（scope: project 的排除项、风险、更正）读任何模块的代码时附至多 3 条，拦截提示也带；
同一对话只给一次（会话状态 project_shown，全部给完后 project_done 停止扫描），上下文压缩后清空并重新给。
终端命令里有 pmem search 时，pre-tool 阶段写交接文件，让命令行能认领对话 id 做去重。
风险：项目级坑的预筛先按文本匹配 scope: project 再解析，文件头格式被手工改乱时可能漏掉。
