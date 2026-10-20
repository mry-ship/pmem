---
id: 01M5CFHY7KWGT8BW26CM28C64Q
module: infra.Common
entity: ContentFile
kind: decision
status: active
supersedes:
- 01M5A8NCEC7G3F9ZVWG0MZHVJV
anchors:
- src/pmem/cli/main.py#_read_content_file
- src/pmem/vcs/git.py#commits_since
- src/pmem/server/app.py#build_server
- docs/pmem-guide.html
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: --content-file：UTF-16 BOM 按 utf-16，其余 utf-8-sig；读不出返回 input_unreadable
aliases:
- UTF-16
- 编码
- 乱码
- content-file
- 配置文档
---
决定：命令行 --content-file 读文件时 UTF-16 BOM 按 utf-16 解码，其余按 utf-8-sig；
文件不存在、读不出或解码失败返回 {ok:false, code:"input_unreadable"} 和具体原因，不抛异常栈。
原因：Windows PowerShell 5 的 Out-File / > 默认写 UTF-16，Agent 用它生成正文文件后 pmem record 直接崩溃；GBK 文件同样崩溃，且闸门看不到 pmem 的错误标记。
同时：手册 docs/pmem-guide.html 的配置示例补齐了 svn_auto_add、resume_markers、stop_reminder、secret_patterns、search、embedding、server 等配置项。
git commits_since 的 --since 带 00:00，只给日期时 git 按当前时刻截断会漏掉当天早些时候的提交。
更正：旧记忆说“MCP 服务改了 config.yaml 需要重启才生效”已不对。服务按 config.yaml 的修改时间和大小判断变更，下一次调用时重建；只有 server 下看门狗开关和超时两项要重启（手册已写明）。
