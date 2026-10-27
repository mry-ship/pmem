---
id: 01M5CFJ4KYWXQDJDZDPCD2PW0J
module: feature.Onboarding
entity: Templates
kind: correction
status: active
supersedes:
- 01M5A8NH3B1WETQV69J7FVPNKQ
anchors:
- src/pmem/generate/templates.py#CONFIG_TEMPLATE
- src/pmem/generate/integrations.py#_write_skills
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: init 无条件覆盖技能和规则；当时修的是残留的 {generated} 占位符
aliases:
- 初始化
- init
- 模板
- 生成标记
verified: '2026-10-27'
verified_at: '2026-10-27T17:33:08.864+08:00'
---
更正：旧记忆说“生成标记不对时 pmem init 判断不出是自己生成的文件，会跳过更新”，不成立：init 写技能和规则文件是无条件覆盖。
当时 pmem-consolidate/SKILL.md 的真实问题是文件里残留了未替换的 {generated} 占位符，重新生成后修正。
仍有效：init 生成的 config.yaml 里 gate.mode 的注释是“检索成功返回才放行”，与闸门行为一致（检索返回错误或没有输出不算查过）；
已接入的项目要重新运行 pmem init 才会拿到新模板（config.yaml 已存在时不覆盖，注释不会变）。
