---
id: 01M5CW5JCMEGQ7T32XHKNK01BH
module: feature.Wiki
entity: Generate
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py#write_wiki
- src/pmem/generate/wiki.py#_page
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 手写记忆的 module 字段可以在生成 Wiki 时写出目录并覆盖已有 Markdown
verify: 放一个 module 含 .. 的记忆文件后跑 pmem wiki，确认不会在 .memory/wiki 之外写出文件
aliases:
- 路径穿越
- path traversal
- 覆盖技能
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
风险：generate/wiki.py 的 write_wiki 用条目 YAML 头里的 module 拼文件名（模块名.md），写出前没有确认解析后的路径仍在 Wiki 目录内。
索引读的是文件头里的 module，不校验它是否合法模块名、也不要求它等于所在目录。
record_memory 会拒绝不合法的模块名，手写或合并进来的 md 可以绕过。
从 .memory/wiki 向上跳两级，可以覆盖仓库根的 AGENTS.md，或已存在的 .cursor/skills/<技能>/SKILL.md。
页面正文原样包含记忆内容。
wiki.auto 默认开着：任何人再写入一条记忆，或运行 pmem wiki，就会触发。删旧页只扫 Wiki 目录本身，覆盖出去的文件不会被清掉。
