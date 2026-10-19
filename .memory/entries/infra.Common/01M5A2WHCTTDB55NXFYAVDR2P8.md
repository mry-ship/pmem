---
id: 01M5A2WHCTTDB55NXFYAVDR2P8
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes:
- 01M51QHMP55X8Z4JRXVM609WZZ
- 01M59J9C0FFHN1CMZ9PD2M4PB5
anchors:
- src/pmem/cli/brief.py#render_brief
- src/pmem/cli/main.py#_record_content
revision: git:93c4987
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 乱码
- 编码
- GBK
- --brief
- 精简输出
- stdin
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
命令行输出与编码（现行）：
1) search、graph、record 支持 --brief：每条一行中文摘要（类型｜议题｜日期｜id：正文前 120 字），过期的下一行标“⚠ 需核实：原因”，末尾附提示和相关模块；不带时输出 JSON 供程序解析。
原因：终端乱码的根因不是 pmem 输出（已统一 UTF-8），而是 Windows PowerShell 5 把输出接给 Select-String 等命令时按 GBK 解码。
JSON 太长时 Agent 习惯接管道筛选就会乱码，--brief 让直接看输出就够用。
需要处理 JSON 时在 Python 里用 subprocess 读字节再按 UTF-8 解码，不要经 PowerShell 管道。
2) record 从 stdin 读正文时读字节、按 utf-8-sig 解码（兼容 PowerShell 带的 BOM）；
   原先用 sys.stdin 按系统编码（中文 Windows 为 GBK）解码，Agent 管道传来的中文变乱码甚至报 UnicodeDecodeError。
   --content-file 同样按 utf-8-sig 读。
注意：search 返回的 related 是字符串列表，graph 返回的是字典列表（module、via、entities），渲染 --brief 时两种都要兼容，曾因此在真实仓库上报 TypeError。合并自 2 条记忆。
