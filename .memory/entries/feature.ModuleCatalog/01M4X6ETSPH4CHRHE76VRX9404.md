---
id: 01M4X6ETSPH4CHRHE76VRX9404
module: feature.ModuleCatalog
entity: Encoding
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#load
revision: git:4e6c22b
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
风险：在 Windows PowerShell 5 里用脚本改 modules.yaml 容易把文件写坏。
Get-Content -Raw 不带 -Encoding 时按 ANSI（GBK）读取 UTF-8 文件，回写后中文变成乱码，引号或冒号被吞进乱码字符，YAML 解析失败；
Set-Content -Encoding utf8 还会写入 BOM。

现状：ModuleRegistry.load 用 utf-8-sig 读取（兼容 BOM），YAML 错误转成 RegistryError，提示“modules.yaml 第 N 行格式错误”；
doctor、search、record、list_modules 都返回这条可读错误，不再抛出 Python 堆栈。
Hook 中解析失败照常放行。

建议：修改 modules.yaml 用编辑器或 Agent 的写文件工具；脚本里读写都显式指定 -Encoding UTF8。
