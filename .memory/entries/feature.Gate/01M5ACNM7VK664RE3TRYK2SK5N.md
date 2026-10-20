---
id: 01M5ACNM7VK664RE3TRYK2SK5N
module: feature.Gate
entity: ProjectPitfalls
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/memories.py#take_project_pitfalls
- src/pmem/hooks/review.py#_offer_digest
- src/pmem/hooks/gate.py#on_compact
- src/pmem/hooks/mcp.py#_note_cli_calls
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: 摘要只列标题并附全项目级坑（每对话一次），结束提醒改为有教训才写
aliases:
- 全项目
- 项目级坑
- 无新教训
- 结束提醒
- 摘要标题
---
决定（v0.3）：读代码摘要和拦截提示改为只列一句话标题，并附上全项目级的坑。
标题：用 summary，没有时取正文第一句并去掉“决定：”这类前缀，修掉了以前“决定：决定：”的重复前缀。
全项目级坑：scope: project 的排除项、风险、更正，读任何模块（包括还没有记忆的模块）的代码时附至多 3 条，拦截提示也带；
同一对话只给一次（会话状态 project_shown）。
上下文压缩后同时清空 project_shown 和对话内去重记录。
终端命令里有 pmem search 时，pre-tool 阶段写交接文件，让命令行能认领对话 id 做去重。
结束提醒改为“有教训才写”：逐项问被排除的方向、根因或坑、看代码看不出的约束、为什么这样选；都没有就回复“无新教训”。原因：旧提醒要求“改了哪个模块就写一条”，产出大多是变更记录（决定占 65%，排除项只有 2 条）。
风险：项目级坑的预筛先按文本匹配 scope: project 再解析，文件头格式被手工改乱时可能漏掉。
