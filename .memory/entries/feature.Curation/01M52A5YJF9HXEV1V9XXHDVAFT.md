---
id: 01M52A5YJF9HXEV1V9XXHDVAFT
module: feature.Curation
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/format_cmd.py#run_format
revision: git:b383fc9
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 格式化记忆
- 断行
- pmem format
---
决定：新增 pmem format [--module] [--apply]，把已有记忆里过长的正文行断开（规则见 infra.Model / ContentFormat）。
默认只预览：打印需要整理的条数和第一条整理后的前 8 行；
--apply 才原地写回，只改正文，YAML 头（id、日期、替代关系等）不变。
原因：新写入和导入已自动整理，但接入前导入的旧记忆仍是一整行，需要一次性整理。
写回后记得提交 .memory/。
