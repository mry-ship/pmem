---
id: 01M59J89XFMTC0CG2XRAQVGR7P
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell.py#scan
- src/pmem/hooks/shell.py#_redirects
- src/pmem/hooks/gate.py#_target_modules
- src/pmem/hooks/gate.py#_needs_snapshot
- src/pmem/hooks/gate.py#_draft_open
- src/pmem/hooks/state.py#_load
- src/pmem/cli/hook_cmd.py#run_hook
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 绕过闸门
- 重定向
- 删除目录
- 快照对比
- 状态文件损坏
- bypass
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
结论：终端命令绕过闸门的几个口子已堵上（均有单测）：
1) 重定向的更多写法：带引号含空格的路径、>| 和 &>>、-o>x；2>/dev/null 不再被当成“丢弃输出”；视为丢弃的只有 stdout 重定向。
2) sudo/env/command 前缀、sed -i/perl -i 就地修改、cp -t、rm 和 tee 的逗号分隔目标；
   PowerShell 的 Set-Content -Path/-LiteralPath、Out-File -FilePath 等。
3) 删除/移动整个目录时，目录下所有模块都要先查过（原先 Remove-Item src 一个模块都不查）。
4) 无法预先解析目标的命令要拍快照对比。只剩一个待处理快照时，只有当前命令本身也需要快照才借用；原先任何命令的 after 都会拿走别人的快照。
5) session 状态文件损坏时按默认值重建；Windows 替换文件遇 PermissionError 重试 5 次；hook 入口只输出一次 JSON。
6) 同议题自动注入 draft_id 前先看草稿是否已提交：长对话跨过 git 提交后，原先会注入旧 id，服务拒绝写入（2026-10-19 实测 3 次）。
未解决（见 GitHub issue）：pmem search CLI 在执行前就计入已查；闸门放行时用户看不到提示。
