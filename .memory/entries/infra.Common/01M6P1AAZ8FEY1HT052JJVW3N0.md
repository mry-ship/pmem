---
id: 01M6P1AAZ8FEY1HT052JJVW3N0
module: infra.Common
entity: LocalCache
kind: risk
status: active
supersedes:
- 01M6P0R9MMP6MJQGHNYYKEFBCR
- 01M6P0JQV8NJFBTWTVJMTWZNVD
anchors:
- .gitignore
revision: none
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: 忽略本地 .memory/cache 报告目录
verify: git status --short 不再显示 .memory/cache 下生成文件
applies: 仓库将 .memory/ 纳入版本控制时
---
本地健康报告与缓存文件由 .memory/cache/ 保存；
根目录 .gitignore 当前只忽略 .memory/wiki/，未忽略缓存目录，而 README 鼓励提交 .memory/，因此本机生成的报告可能被误提交。
应忽略 .memory/cache/，除非未来决定将其作为共享产物管理。
