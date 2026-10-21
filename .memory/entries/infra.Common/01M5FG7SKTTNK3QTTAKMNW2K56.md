---
id: 01M5FG7SKTTNK3QTTAKMNW2K56
module: infra.Common
entity: Roadmap
kind: plan
status: active
supersedes: []
anchors: []
revision: git:37c9b3a
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: v0.6 类型安全与规则化：教训升级成规则、enforced_by、facets/when、边界校验、返回契约与 pyright
aliases:
- typesafe
- 类型安全
- 规则化
- 校验
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-21）在教美术用 Cursor 加技能调用 AI 接口，希望 pmem 加入 typesafe 做分流和各种校验，定为 v0.6 计划。
要实现的（设计稿 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md，进度 GitHub Issue #15）：
1) pmem health 新增“可以写成规则的教训”：同模块同议题现行排除项/风险/更正 ≥3 条，按路径建议规则形态（ruff/ESLint/Roslyn/技能参数校验）。
2) 记忆字段 enforced_by（路径#规则名）：规则文件改了记忆标需核实；展示“已由规则拦截”，摘要里排后。
3) config.yaml 声明 facets，记忆字段 when 按声明校验，search_memory(when=...) 明确冲突才排除。
4) core/schema.py 只用标准库统一校验 config.yaml、modules.yaml、记忆文件头、Hook 数据，报错带字段路径；29 处可能为空的访问核对。
5) MCP 返回写 TypedDict；Hook 组合类声明共享属性，pyright 基础模式纳入测试。
约束：Hook 不能引入 Pydantic（每次工具调用起进程，分层测试守着）；不结构化正文；pmem 不执行用户项目的检查。
现状基线：pyright 标准模式 316 个报错，其中 228 个是 hooks 组合类的假报错。
待确认：阈值 3 条、when 排除还是降权、摘要里已拦截的排后还是隐藏、是否先做 facets 给美术试点。
