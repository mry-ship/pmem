---
id: 01M6R7M2WRBYHP7CNGB5P4JR1V
module: feature.Onboarding
entity: Doctor
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/cli/doctor_cmd.py#_is_console_python_hook
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: doctor 认不出带完整路径的控制台 python Hook
verify: 完整路径 python.exe 也应被判为控制台 Hook
---
_is_console_python_hook 只用 ^python3?|py 匹配命令开头。
Agent 或用户写成 C:\...\python.exe 或带空格的完整路径时漏报，Windows 仍弹黑框却无提醒。
应取命令第一个 token 的文件名再比，或允许路径前缀。
