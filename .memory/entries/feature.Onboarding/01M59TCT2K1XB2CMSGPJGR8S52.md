---
id: 01M59TCT2K1XB2CMSGPJGR8S52
module: feature.Onboarding
entity: Scan
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/scan/lite.py#kept_dirs
- src/pmem/scan/lite.py#iter_code_files
- src/pmem/scan/files.py#FileIndex
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 跳过目录
- 覆盖率不准
- 误跳业务目录
- Library
- Logs
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：Unity 编辑器生成的 Library、Temp、Logs、UserSettings 不再在任意深度跳过，只有同一层同时有 Assets 和 ProjectSettings（即 Unity 工程根，可在仓库子目录如 client/）时才跳过。
原因：原先按目录名在任意深度匹配，业务里的 Scripts/Logs（日志模块）、src/Library 等会被当成生成目录，覆盖率、pmem sync、pmem anchors 都看不到，doctor 仍显示 100%，属于静默漏报。
跳过判断收到 scan/lite.py 的 kept_dirs(同层子目录)，iter_code_files 和 anchors 的 FileIndex 共用，不额外访问文件系统。
未改：node_modules、bin、obj、build、dist、out、target、vendor 等仍在任意深度跳过——.NET 的 bin/obj、Maven 的 target、monorepo 的 dist 本来就在各子项目里；
风险是真叫这些名字的业务目录仍会被忽略。
