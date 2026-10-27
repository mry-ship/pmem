---
id: 01M5KV8EYC94KA97JJ6QBBMJT7
module: feature.Onboarding
entity: Skills
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- src/pmem/generate/integrations.py#_write_skills
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: init 给已登记模块铺规格骨架，并提示补全模块规格
verify: uv run pytest tests/test_spec.py -q -k "skill or project_init"
applies: pmem init 生成技能和配置模板时
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:23.529+08:00'
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
用户要求：规格正文由技能写。一个模块一个目录，四份分开。正文写模块现在的设计，并且一句一行。pmem init 要接入规格骨架。
必须保持：pmem init 把 pmem-spec 写到各 Agent 的技能目录。
技能写明四份文件名、美术文件不放代码路径、无画面写「本模块无画面」、一句一行、父模块不写子模块正文、不写「这一轮只新增」、当轮更新不整篇重写、写前 search_memory、用户说「补全模块规格」或运行 pmem spec fill 时按首稿把列出的模块写全。
已有 config.yaml 不被 init 改写。
模块已登记时 init 补还没有的规格骨架，不写正文；
名单还是空的就只提示等划分模块后再补。
下一步写明对 Agent 说「补全模块规格」。
