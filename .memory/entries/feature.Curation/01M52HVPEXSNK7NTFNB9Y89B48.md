---
id: 01M52HVPEXSNK7NTFNB9Y89B48
module: feature.Curation
entity: Anchors
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/anchors_cmd.py#FileIndex
- src/pmem/cli/seed_cmd.py#seed_plan
revision: git:5003560
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 补锚点
- 跳过目录
- 种子候选
---
决定：pmem anchors 遍历文件时的跳过目录改为复用 scan/lite.py 的 skip_dir()（依赖、构建产物、点开头目录、*.egg-info），另外仍跳过 Unity 的 Packages、com.* 内嵌包和第三方目录名单；
pmem seed --plan 不再列出已废弃的模块。
原因：原来 anchors 自己维护一份更短的名单，漏了 target、dist、vendor 等，正文提到的类名可能被关联到依赖代码里；
废弃模块不再接受新记忆，提炼种子没有意义。
风险：真叫 vendor、target 的业务目录里的文件不会被自动关联。
