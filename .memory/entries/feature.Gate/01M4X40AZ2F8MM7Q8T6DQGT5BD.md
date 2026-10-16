---
id: 01M4X40AZ2F8MM7Q8T6DQGT5BD
module: feature.Gate
entity: Encoding
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/payload.py#parse_payload
revision: git:e258c6e
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
Windows 中文系统（ANSI 代码页 936）上，Cursor 3.9 经 PowerShell 转发 Hook 标准输入：UTF-8 字节先被按 GBK 解码，再以带 BOM 的 UTF-8 写出。只要 payload 含中文（例如 Write 的 content），JSON 常被破坏（引号被并入乱码字符），json.loads 失败。改用 cmd /c 或 .cmd 包装无效。

对策：Hook 只依赖 ASCII 字段（conversation_id、tool_name、file_path、command），解析按“原样 → GBK 回转 → 正则提取”三级兜底；中文跳过标记按误解码后的形态匹配（随机 2000 组无漏检无误报）；Hook 输出一律 ensure_ascii。

证据：tests/fixtures/hook_payloads/ 中 afterFileEdit、preToolUse_Write 等真实样本均为非法 JSON。开启 Windows“使用 Unicode UTF-8 提供全球语言支持”可从根上避免。

同类坑：PowerShell 会把中文弯引号当字符串定界符，命令行传含引号的中文长文本会被截断，pmem record 用 --content-file 传正文。
