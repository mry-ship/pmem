---
id: 01M6N8HH9F97NKM39FN3T9AYN5
module: feature.Onboarding
entity: WindowsConsole
kind: exclusion
status: active
supersedes: []
anchors: []
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: 排除：只把art hook改成pyw仍会弹
applies: Windows + pmem-art 出图闪窗排查
---
排除方向：以为 GenerateImage 的 art hook 改成 pyw 就够。不够。
出图还会经 Shell 跑 converge CLI，pmem 闸门若匹配 Shell，每条 Shell 仍弹窗；
CLI 若用 python/python3 控制台解释器也会弹。
必须同时：去掉 Shell 匹配 + CLI 用 pyw。
