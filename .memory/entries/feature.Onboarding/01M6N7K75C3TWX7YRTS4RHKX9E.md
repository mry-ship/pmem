---
id: 01M6N7K75C3TWX7YRTS4RHKX9E
module: feature.Onboarding
entity: Doctor
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/doctor_cmd.py#_is_console_python_hook
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: Windows doctor 告警 hooks 用控制台 python3/py
verify: pytest tests/test_doctor_console_python.py -q
applies: Windows；项目 hooks 含非 pmem 的 python 启动器
verified: '2026-11-06'
verified_at: '2026-11-06T15:32:48.705+08:00'
---
功能：pmem doctor 在 Windows 上扫描 .cursor/hooks.json 与 Claude/Codex hooks：若 command 以控制台版 python3/python/py 开头（排除 pyw/pythonw），告警改成 pyw -3 -u；
macOS/Linux 的 python3 不告警。
需求：第三方/美术 hook 用 python3 在 Windows 必弹黑框，与 pmemw 闸门无关。
入口：doctor_cmd._is_console_python_hook / _iter_hook_commands。
