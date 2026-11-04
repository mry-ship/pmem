---
id: 01M6JWSFGFYXG8VN4NNJ0C6TG3
module: feature.Onboarding
entity: Templates
kind: correction
status: active
supersedes:
- 01M5CFJ4KYWXQDJDZDPCD2PW0J
anchors:
- src/pmem/generate/templates.py#CONFIG_TEMPLATE
- src/pmem/generate/integrations.py#_write_skills
revision: git:cef5279
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: pmem init 无条件覆盖技能和规则；技能模板花括号写成 {{ }}
verified: '2026-11-04'
verified_at: '2026-11-04T17:04:24.128+08:00'
---
更正：旧记忆说“生成标记不对时 pmem init 判断不出是自己生成的文件，会跳过更新”，不成立：init 写技能和规则文件是无条件覆盖。
当时 pmem-consolidate/SKILL.md 的真实问题是文件里残留了未替换的 {generated} 占位符，重新生成后修正。
仍有效：init 生成的 config.yaml 里 gate.mode 的注释是“检索成功返回才放行”，与闸门行为一致（检索返回错误或没有输出不算查过）；
已接入的项目要重新运行 pmem init 才会拿到新模板（config.yaml 已存在时不覆盖，注释不会变）。
