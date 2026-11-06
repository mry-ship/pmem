---
id: 01M6QVPKA2CJBNA7F55YNSTYAJ
module: feature.Storage
entity: RunToolNoWindow
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/winproc.py#no_window_kwargs
- tests/core/test_winproc_coverage.py#test_all_production_subprocess_calls_hide_console_on_windows
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 生产 subprocess 必须藏窗，由 AST 覆盖测试锁住
verify: uv run pytest tests/core/test_winproc_coverage.py -q
applies: 改 src/pmem 内 subprocess 调用时
aliases:
- 黑框
- 覆盖测试
---
需求：复查黑框修复时防止以后再漏加藏窗，并纠正 doctor 提示避免再靠拆 Hooks 消框。
必须保持：src/pmem 内每个 subprocess.run/Popen 须带 CREATE_NO_WINDOW 或 no_window_kwargs（由 tests/core/test_winproc_coverage.py 锁住）；
Windows doctor 防弹窗提示须说明 Hook 内 git/svn 已藏窗、残留弹窗来自 Cursor 外层、禁止拆闸门/读码摘要。
适用：Windows；改 subprocess 调用或 doctor 文案时。
入口：core/winproc.py；cli/doctor_cmd.py 防弹窗提示；tests/core/test_winproc_coverage.py。
