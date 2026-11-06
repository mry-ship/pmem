---
id: 01M6R9XKGR10NG30RTSTDSPGSZ
module: feature.Onboarding
entity: Doctor
kind: correction
status: active
supersedes:
- 01M6R7M2WRBYHP7CNGB5P4JR1V
anchors:
- src/pmem/cli/doctor_cmd.py#_is_console_python_hook
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: doctor 已能识别完整路径的控制台 python Hook
---
已修：_is_console_python_hook 先取首 token 的 basename 再 fullmatch python3?|py，完整路径 python.exe 能识别。
见功能记录 01M6R9GNKB6Y895DAVWN89CGJX。
