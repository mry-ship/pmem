---
id: 01M5CAW955S71EA3DDAZ8WT5M6
module: infra.Common
entity: Encoding
kind: risk
status: active
supersedes: []
anchors: []
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: PowerShell 5 会把中文弯引号当引号，命令参数被截断
scope: project
verify: pmem record 返回 已写入 而不是 usage 报错
aliases:
- 中文引号
- 弯引号
- 参数截断
- unrecognized-arguments
---
风险：Windows PowerShell 5 把中文弯引号（左右双引号、左右单引号）也当作字符串引号。
命令参数里写了带中文引号的文字（如 --verify 或 --summary 里引用某段输出），参数会在引号处被截断，后半段变成多余参数，pmem record 报 unrecognized arguments 而整条没写进去。
另外别名或正文参数里以 -- 开头的词会被 argparse 当成选项。
避免：命令行参数里不用中文引号、不写以 -- 开头的词；
长文本或含引号的内容放进 UTF-8 文件用 --content-file。
