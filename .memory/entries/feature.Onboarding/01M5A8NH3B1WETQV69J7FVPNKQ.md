---
id: 01M5A8NH3B1WETQV69J7FVPNKQ
module: feature.Onboarding
entity: Templates
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- .cursor/skills/pmem-consolidate/SKILL.md
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 初始化
- init
- 模板
- 生成标记
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：init 生成的 config.yaml 里 gate.mode 的注释改为“检索成功返回才放行”，与闸门实际行为一致（检索返回错误或没有输出不算查过）；本仓库 .memory/config.yaml 同步修改。
另：.cursor/skills/pmem-consolidate/SKILL.md 按模板重新生成，修正了生成标记行；标记不对时 pmem init 判断不出是自己生成的文件，会跳过更新。
风险：已经接入的其他项目要重新运行 pmem init 才会拿到新注释。
