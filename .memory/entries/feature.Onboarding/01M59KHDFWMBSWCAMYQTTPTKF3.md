---
id: 01M59KHDFWMBSWCAMYQTTPTKF3
module: feature.Onboarding
entity: Scan
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/scan/lite.py#file_heat_windows
- src/pmem/scan/lite.py#file_heat
- src/pmem/generate/templates.py#CURSOR_HOOKS
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 热度
- file_heat
- HOOK_EVENTS 重名
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：scan/lite.py 不再自己调 git log / svn log，file_heat、file_heat_windows 接受可选的 vcs 参数（不传则 detect_vcs），历史由适配器的 commits_since 提供，返回的版本库名也来自适配器。
sync、seed、report 传入已有的 vcs，尊重 config 里的 vcs 设置，也不重复探测。

generate/templates.py 里 Cursor 的 Hook 事件表从 HOOK_EVENTS 改名 CURSOR_HOOKS：原名与 cli/main.py 的 HOOK_EVENTS（pmem hook 子命令可接受的事件）重名但含义不同，容易改错一处。

影响：行为不变，全量测试通过。
