---
id: 01M6P0JQV8NJFBTWTVJMTWZNVD
module: infra.Common
entity: LocalCache
kind: risk
status: active
supersedes: []
anchors:
- .gitignore
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: 根目录 .memory/cache 未忽略，提交 .memory 时会带入本机缓存
scope: project
verify: 查看 .gitignore 与 git status --short；.memory/cache 不应作为未跟踪文件出现。
applies: 项目根目录中的 .memory/cache 存放本机缓存或健康报告时
source:
  conversation: 01a1abf4-b50c-7a00-88c8-3c3db2d9829f
---
审查当前工作区发现：根目录 .gitignore 只忽略 .memory/wiki/，没有忽略 .memory/cache/；
当前 git status 因而显示 ?? .memory/cache/，目录内有 health-latest.json、health-latest.txt 和 health-action-needed.txt 等本机健康报告文件。
README 快速接入要求提交 .memory/，照做时会把这些本机缓存一并纳入版本控制。
应补充针对本地缓存目录的忽略规则，并确认缓存内容不是团队共享数据。
