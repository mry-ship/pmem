---
id: 01M6JQ0P2Z063ECDX1Y5PA1K3E
module: feature.Onboarding
entity: WindowsConsole
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/cli/doctor_cmd.py
revision: git:f034aa1
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: hooks 命令含 || 或 .cmd 必弹控制台
verify: doctor 对 || 告警；Art 已改为单 py -3
applies: Windows + Cursor hooks.json
---
风险：hooks.json 命令含 ||、或指向 .cmd/.sh，Cursor 在 Windows 上会经 shell 启动，几乎必弹控制台；与是否 pmemw 无关。
doctor 已检测 || 并告警。第三方自建 Hook（如美术流水线）也须改成单个可执行/解释器调用。
