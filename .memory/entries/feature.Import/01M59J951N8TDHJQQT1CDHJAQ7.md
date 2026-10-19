---
id: 01M59J951N8TDHJQQT1CDHJAQ7
module: feature.Import
entity: LanceDB
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/importers/lancedb.py#import_rows
- src/pmem/cli/import_cmd.py#_merge_catalog
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 导入
- 密钥泄露
- 敏感信息
- 模块目录注释丢失
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
结论：从 LanceDB 导入旧记忆时，原先只用内置的敏感信息规则，忽略了项目 config.yaml 里的 write.secret_patterns，项目自定义的密钥格式会被原样导入。
现在 import_rows 接收并使用配置里的规则，与 record_memory 一致。
另：导入时合并模块目录改用 catalog 的 ModulesFile 读写，原先自己用 yaml.safe_dump 写，会丢弃 modules.yaml 的文件头注释，并在 Windows 上写成 CRLF。
