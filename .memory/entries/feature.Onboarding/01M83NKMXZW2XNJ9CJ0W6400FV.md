---
id: 01M83NKMXZW2XNJ9CJ0W6400FV
module: feature.Onboarding
entity: Doctor
kind: feature
status: active
supersedes:
- 01M6QWCFPCS2JH5D0S0BB2VERA
- 01M6R9GNKB6Y895DAVWN89CGJX
- 01M7WTATGM87QPCV6NT8QBZTQ4
anchors:
- src/pmem/cli/doctor_cmd.py#run_doctor
- src/pmem/cli/doctor_cmd.py#_is_console_python_hook
- src/pmem/cli/doctor_cmd.py#_check_when_facets
- src/pmem/cli/doctor_cmd.py#_run_doctor_body
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: doctor 指出真闪框、控制台 python 和 when/facets
aliases:
- 控制台python
- facets
- 闪框
source:
  kind: document
---
需求来源：Hooks=full 之后 doctor 仍要指出真闪框来源；控制台 python 漏报；v0.7 要看见 when/facets。

必须保持：
1) Windows 自检末尾写明 Hook 内 git/svn 已 CREATE_NO_WINDOW；若仍弹多半是 Cursor 外层 pwsh/cmd；明确不要靠拆闸门或读码摘要消黑框。
2) Windows 上控制台 python 起 Hook 要告警：python / python3 / python3.12 及完整路径、带引号路径；
   pyw / pythonw / pythonw3.12 不告警。
   先取首 token 的 basename 再匹配；
   mypython-wrapper 这类不误报。
3) 配置/modules 拼错键与 facets 过多出现在 doctor。
   现行记忆写了 when 但未声明 facets，或 when 与 facets 不符，要警告（最多 8 条）。
   storage.warnings 前几条打印。
   Hook 字段类型不对写入 hook-errors.log，近 24 小时能看到。

入口：cli/doctor_cmd.py run_doctor、_is_console_python_hook、_check_when_facets。
测试 test_doctor_warns_when_without_facets_and_bad_when。

合并自 3 条功能记录（含「完整路径已能识别」那条更正所指向的行为）。
