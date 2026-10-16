---
id: 01M4ZRSQKWJM852QYD2FDKZM08
module: infra.Common
entity: Encoding
kind: risk
status: active
supersedes: []
anchors: []
revision: git:bfe2969
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 乱码
- 编码损坏
- BOM
- UTF-16
- PowerShell
---
风险：在 Windows PowerShell 5 里用命令改含中文的源码或文档，很容易把文件编码弄坏，而且测试不一定能发现。

本仓库实测踩到的几种：
- Get-Content 不带 -Encoding 时按系统 ANSI（GBK）读 UTF-8 文件，再用 Set-Content 写回，中文全部变成乱码；
  Set-Content -Encoding utf8 还会在文件头加 BOM。
  service.py 因此被破坏过一次，pytest 仍然 251 个全过（测试只断言 ok 和 id，不比对中文提示语）。
- 用 > 重定向保存命令输出，得到的是 UTF-16 文件，json.load 直接报错。
- 管道把中文 JSON 传给 python 会被转码，解析报“Invalid control character”。
- 编辑工具改一个已有 BOM 的文件时会保留 BOM。

做法：改文件只用编辑工具，或用 Python 按字节读写；需要保存命令输出时让程序自己写 UTF-8 文件，或用 cmd /c 重定向；改完用 Python 检查文件头没有 EF BB BF、关键中文按 UTF-8 编码后能在文件里找到。
