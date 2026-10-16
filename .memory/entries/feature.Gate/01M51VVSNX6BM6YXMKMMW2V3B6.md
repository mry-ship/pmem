---
id: 01M51VVSNX6BM6YXMKMMW2V3B6
module: feature.Gate
entity: Encoding
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/payload.py#_pua_bytes
- src/pmem/hooks/payload.py#parse_payload
- src/pmem/hooks/gate.py#cli_args
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 乱码
- 私有区
- PUA
- 吞换行
- 记了却提醒没写
- 误提醒
---
根因：终端命令里的中文让 GBK 误解码吞掉了换行，同一条命令里的第一个 pmem record 没被登记，结束时误提醒“feature.Storage 还没写记忆”（记忆其实已写）。

过程：Cursor 在中文 Windows 上按代码页 936 解码 Hook 输入。
“符”的 UTF-8 尾字节 A6 和紧跟的 \n 转义里的反斜杠 5C 被拼成一个字符；
这对字节落在 GBK 用户自定义区，Windows 把它解成私有区字符 U+E6C2。
JSON 仍然合法，所以 parse_payload 直接用了这份有损的结果，命令里少了一个换行，两行 pmem record 黏成一段。
参数解析时，后一个 --module 覆盖了前一个。
原先的 GBK 回转用的是 Python 的 gbk 编码表，没有这段私有区映射，还原不回来。

修复：
1. 回转时按 Windows 规则把私有区字符还原成原字节（AAA1–AFFE → U+E000 起，F8A1–FEFE → U+E234 起，A140–A7A0 → U+E4C6 起，每个前导字节 96 个尾字节、跳过 7F）。
   用 MultiByteToWideChar 对全部 1894 个私有区字符逐一核对，无一不符。
2. 原样和回转都能解析成 JSON 时，取替换符加私有区字符更少的那份。
3. 同一段命令里出现多个 --module 或 --path 时取第一个。

验证：用录下的原始输入回放，4 个 pmem record 全部认出。

仍有的风险：回转之后，单独落在空格或引号前的前导字节已经被替换成 U+FFFD，这部分字符无法恢复（只影响别名等中文文本，不影响模块名）。
