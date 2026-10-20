---
id: 01M59TEXNSS0FEYGWDGA2QGP04
module: feature.Curation
entity: Anchors
kind: decision
status: active
supersedes:
- 01M52HVPEXSNK7NTFNB9Y89B48
anchors:
- src/pmem/scan/files.py#FileIndex
- src/pmem/scan/lite.py#kept_dirs
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 自动补关联代码
- 跳过目录
- 误关联第三方
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：pmem anchors 遍历文件时的目录过滤改为复用 scan/lite.py 的 kept_dirs(同层子目录)，与覆盖率、sync 的扫描同一口径：依赖、构建产物、点开头目录、*.egg-info 在任意深度跳过；
Unity 的 Library/Temp/Logs/UserSettings 只在同层有 Assets 和 ProjectSettings 时跳过。
另外仍跳过 Unity 的 Packages、com.* 内嵌包和第三方目录名单（THIRD_PARTY_NAMES）。
原因：原先按目录名在任意深度跳过 Library/Logs，业务里的 Scripts/Logs、src/Library 下的类不会被自动关联；
更早时 anchors 自己维护的名单还漏了 target、dist、vendor，正文提到的类名会被关联到依赖代码。
影响：只影响自动补关联代码时能解析到的文件范围；pmem seed --plan 仍不列已废弃模块。
风险：真叫 vendor、target、build 等的业务目录里的文件仍不会被自动关联；业务里的 Logs/Library 现在会参与同名类匹配，可能让原先唯一的类名变成重名而不再关联。
