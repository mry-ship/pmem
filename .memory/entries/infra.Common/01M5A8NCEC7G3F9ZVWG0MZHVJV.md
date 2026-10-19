---
id: 01M5A8NCEC7G3F9ZVWG0MZHVJV
module: infra.Common
entity: ContentFile
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#_read_content_file
- src/pmem/vcs/git.py#commits_since
- docs/pmem-guide.html
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- UTF-16
- 编码
- 乱码
- content-file
- 配置文档
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：命令行 --content-file 读文件时：UTF-16 BOM 按 utf-16 解码，其余按 utf-8-sig；
文件不存在、读不出或解码失败返回 {ok:false, code:"input_unreadable"} 和具体原因，不再抛 Python 异常栈。
原因：Windows PowerShell 5 的 Out-File / > 默认写 UTF-16，Agent 用它生成正文文件后 pmem record 直接崩溃；GBK 文件也同样崩溃，且闸门看不到 pmem 的错误标记。

同时：用户手册 docs/pmem-guide.html 的配置示例补齐了 svn_auto_add、resume_markers、stop_reminder、analysis_markers、secret_patterns、search、embedding、server 等配置项，并说明 MCP 服务改了 config.yaml 需要重启才生效（服务不热加载配置）。
另：git commits_since 的 --since 改为带 00:00，原来只给日期时 git 按当前时刻截断，当天早些时候的提交会漏掉。
