---
id: 01M7JG78H0MZVJ4ZQ5DFMTPGXG
module: infra.Common
entity: Encoding
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/service/record.py
revision: git:8455451
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: 风险：PowerShell 写中文内容文件或摘要可能乱码，弄坏 YAML 头并导致替代关系失效
scope: project
verify: 打开刚写入的 .md，正文应为中文且 front matter 以单独一行 --- 结束
applies: Windows PowerShell 下 pmem record 写中文时
---
风险：在 Windows PowerShell 里用 Set-Content -Encoding utf8 或这里字符串写 pmem record 的 --content-file / --summary 时，中文可能被错误转码。
轻则 summary 乱码，重则 YAML 头的结束 --- 被吃进 applies，整条记忆解析异常，supersedes 失效、旧记忆继续出现在检索里。
处理：正文与中文参数用 Python Path.write_text(..., encoding="utf-8") 写临时文件，或 uv run python 调 MemoryService.record；
写完打开 .memory/entries 下文件确认能读中文、头尾各有一行 ---。
