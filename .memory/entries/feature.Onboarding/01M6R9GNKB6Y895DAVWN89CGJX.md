---
id: 01M6R9GNKB6Y895DAVWN89CGJX
module: feature.Onboarding
entity: Doctor
kind: feature
status: active
supersedes:
- 01M6N7K75C3TWX7YRTS4RHKX9E
- 01M6R7M2WRBYHP7CNGB5P4JR1V
anchors:
- src/pmem/cli/doctor_cmd.py#_is_console_python_hook
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: doctor 控制台 python 检测取首 token basename，认完整路径、python3.12 等小版本号
verify: uv run pytest tests/test_doctor_console_python.py
aliases:
- 控制台 python
- 黑框漏报
- python3.12
---
需求来源：用户体检清单指出 doctor 漏报完整路径的控制台 python（Windows 仍弹黑框却无提醒），后续又指出带小版本号的 python3.12 也漏。

必须保持：Windows 上控制台 python 起 Hook 要告警，覆盖 python / python3 / python3.12 这类小版本号，以及完整路径（C:\Python312\python.exe、带引号、/usr/bin/python3）；
pyw / pythonw / pythonw3.12 不告警。

做法：_is_console_python_hook 先用 findall 取第一个 token（可带引号），去掉目录与 .exe 得 basename；
pythonw(\d(\.\d+)?)?|pyw 排除，再 fullmatch py|python(\d(\.\d+)?)?。
原来 re.match 锚串首漏完整路径，fullmatch(python3?|py) 漏小版本号。
basename 含 python 但不是解释器（mypython-wrapper）不误报。
