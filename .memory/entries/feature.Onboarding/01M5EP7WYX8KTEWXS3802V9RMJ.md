---
id: 01M5EP7WYX8KTEWXS3802V9RMJ
module: feature.Onboarding
entity: TemplateBraces
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- src/pmem/generate/integrations.py
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 技能模板和 RULE 会经 str.format，正文里的花括号必须写成 {{ }}，否则 pmem init 报 KeyError
verify: uv run python -c "from pmem.generate import templates as t; [getattr(t,n).format(generated='x')
  for n in ('BOOTSTRAP_SKILL','CONSOLIDATE_SKILL','COMPACT_SKILL','SEED_SKILL','NORMALIZE_SKILL','RULE')]"
aliases:
- KeyError
- 花括号转义
- format 占位符
verified: '2026-10-27'
verified_at: '2026-10-27T14:54:07.882+08:00'
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
风险：templates.py 里的技能模板（BOOTSTRAP_SKILL 等）在 integrations.py 写文件时调用 body.format(generated=...)，正文里出现的 YAML 示例如 `{ module: X, reason: Y }` 会被当成格式占位符，pmem init 直接报 KeyError: ' module'。
必须写成 `{{ module: X, reason: Y }}`。
RULE 是由 RULE_BODY 自动转义拼出来的，RULE_BODY 里可以直接写花括号；MODULES_HEADER 是字符串拼接、不经 format，也可以直接写。
全量测试不一定覆盖到，改完模板自己跑一遍。
