---
id: 01M5EPMY9XZ37EY90PTMX62BSJ
module: feature.Onboarding
entity: ReplyFormat
kind: feature
status: active
supersedes:
- 01M5EJPP5YKB4M6FCESZ47CCXR
anchors:
- src/pmem/generate/templates.py
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 生成规则要求回复开头写【pmem检索】，结尾分段写【pmem查询】和【pmem修改】，前后空一行
verify: uv run pytest tests/test_feature_records.py -k trimmed_rule
applies: pmem init 生成的规则（.cursor/rules/pmem.mdc 及其他工具的规则块）
aliases:
- 回复格式
- 【pmem检索】
- 【pmem修改】
- 记忆查询提示
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-21）：开头要先显示查了什么记忆，结尾说清查到什么、改了什么，当次说完不再弹新消息；前缀用【pmem检索】【pmem查询】【pmem修改】区分，并且要换行。
必须保持的行为（RULE_BODY “回复里的【pmem】行”一节）：
- 开头先写再查：【pmem检索】<模块>（<要点>）；不涉及项目代码写【pmem检索】不涉及项目模块，未查。
- 结尾：【pmem查询】<模块>，用到「标题」/没有相关记忆；【pmem修改】<模块> 已写功能记录「标题」；<模块> 无需记录（原因）；没改代码写【pmem修改】本轮未改代码，无新结论。
- 每行各自成段、前后空一行：Markdown 会把单个换行合并成一段，用户看到的是挤在一起的一长行。
- 写法和 stop Hook 的解析（feature.Gate / ReplyDeclaration）是一对，改前缀或“无需记录”“无新结论”措辞要同步改解析。
- RULE_BODY 须 < 1400 字（现约 1373），tests/test_feature_records.py 守着这些短语。
已接入项目重跑 pmem init 生效；本仓库已重新生成。
入口：src/pmem/generate/templates.py 的 RULE_BODY。
