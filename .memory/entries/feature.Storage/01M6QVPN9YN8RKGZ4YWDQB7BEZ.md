---
id: 01M6QVPN9YN8RKGZ4YWDQB7BEZ
module: feature.Storage
entity: RunToolNoWindow
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/core/winproc.py#no_window_kwargs
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 复查：生产 subprocess 全藏窗；bench 漏网已补
verify: 全量 grep subprocess + hook 探测 bad=0
applies: Windows 生产路径
aliases:
- 黑框
- 查漏
---
复查：src/pmem 下全部 subprocess.run/Popen 生产调用均已带 CREATE_NO_WINDOW 或 no_window_kwargs（vcs/generate/bench/autosync/lazy_doctor/watchdog）。
Hook 全事件探测：pre-tool/post-tool 的 git 全带藏窗；
session/prompt/stop/edited/compact 本身不调 git；
启用 autosync 时 Popen python 亦含 CREATE_NO_WINDOW。
漏补：bench/runner 原先裸调 git/setup/check，已收口；助手从 vcs 下沉到 core.winproc，避免 generate→vcs 越层。
仍不归本修复：Cursor 外层用未藏窗 pwsh/cmd 拉起 pmemw Hook 的弹窗（既有 risk WindowsConsole）。
