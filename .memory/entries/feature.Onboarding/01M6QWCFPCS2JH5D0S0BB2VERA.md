---
id: 01M6QWCFPCS2JH5D0S0BB2VERA
module: feature.Onboarding
entity: Doctor
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: doctor 防弹窗提示区分 git 藏窗与 Cursor 外层弹窗
verify: pmem doctor 输出含 CREATE_NO_WINDOW 与不要靠拆掉
applies: Windows；pmem doctor
aliases:
- 黑框
- 防弹窗
---
需求：用户要求 Hooks=full 不拆功能消黑框后，doctor 仍只写「仍弹可试 ConPTY」，易让人以为 git 闪框没修、或再去拆摘要。
必须保持：Windows 自检末尾提示写明 Hook 内 git/svn 已 CREATE_NO_WINDOW；若仍弹多半是 Cursor 外层 pwsh/cmd；明确不要靠拆闸门或读码摘要消黑框。
适用：Windows 跑 pmem doctor。
入口：cli/doctor_cmd.py run_doctor 末尾防弹窗提示。
