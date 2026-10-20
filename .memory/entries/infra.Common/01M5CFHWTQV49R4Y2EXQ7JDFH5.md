---
id: 01M5CFHWTQV49R4Y2EXQ7JDFH5
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes:
- 01M5A2WHCTTDB55NXFYAVDR2P8
anchors:
- src/pmem/cli/brief.py#render_brief
- src/pmem/cli/main.py#_record_content
- src/pmem/cli/main.py#_read_content_file
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: --brief 一行摘要避免 PowerShell 管道乱码；stdin 按 utf-8-sig 读
aliases:
- 乱码
- 编码
- GBK
- brief 参数
- 精简输出
- stdin
---
命令行输出与编码（现行，更正旧记忆两处细节）：
1) search、graph、record 支持 --brief：每条一行“类型｜议题｜日期｜id：summary｜正文前 120 字”，本对话已给过全文的只显示标题；
   过期的下一行标“⚠ 需核实：原因”，末尾附提示和相关模块；
   不带时输出 JSON。
原因：终端乱码的根因不是 pmem 输出（已统一 UTF-8），而是 Windows PowerShell 5 把输出接给 Select-String 等命令时按 GBK 解码；
--brief 让 Agent 直接看输出就够用。
要处理 JSON 时在 Python 里读字节按 UTF-8 解码，不要经 PowerShell 管道。
2) record 从 stdin 读正文时读字节、按 utf-8-sig 解码（兼容 BOM；原先按系统编码 GBK 解码会乱码或报错）。
更正：--content-file 不是“同样按 utf-8-sig”，而是 UTF-16 BOM 按 utf-16、其余按 utf-8-sig 严格解码，失败返回 input_unreadable（见 ContentFile 记忆）。
注意：search 的 related 是字符串列表，graph 的是字典列表，渲染 --brief 两种都要兼容（曾在真实仓库报 TypeError）。
