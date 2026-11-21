---
id: 01M7YXT6JGMPMK2A6875FKC7C4
module: feature.Onboarding
entity: MinimalChange
kind: plan
status: active
supersedes: []
anchors:
- src/pmem/generate/integrations.py#upsert_block
- src/pmem/generate/templates.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: P0 冻结：一条规则两个技能，跳过口令分开
verify: 缺结束标记时用户原文仍在；两组标记各一份；不传参数的 upsert_block 与现测试一致
applies: 冻结后的 P0 尚未改代码时
aliases:
- 最小充分实现
- Minimal Complete Change
- 最小方案
- pmem-minimal
- pmem-review
- 跳过质量
- 跳过最小方案
source:
  conversation: dd30165a-9192-4f39-b74b-d91fa990fa34
---
需求来源：P0 只做一条独立短规则 pmem-quality，以及 pmem-minimal、pmem-review。不加第三个技能，不加 Workflow、Verify、Audit。
必须保持：记忆规则正文、检索排序、召回闸门、条目类型、Markdown 权威存储，以及 doctor、health、report、bench、MCP 工具说明都不变。RULE_BODY 不写这套流程，测试上限 1400。
跳过口令：「跳过质量」本轮不加载两个技能；「跳过最小方案」只不加载 pmem-minimal，pmem-review 仍按触发条件执行。两句都不影响记忆规则。明显的安全、数据损坏、资源泄漏和正确性风险仍要指出。
审查触发：用户明说「最小审查」或「按 pmem-review」就执行，即使只改了一个文件。
另外在新增文件、依赖、模块或抽象，改了多个模块，或改变对外契约、持久化数据、权限、资源生命周期或失败语义时执行。
契约不变的单文件内部修正不强制完整审查。
upsert_block 增加起止标记参数，默认仍是 pmem:begin / pmem:end，不传参数时行为与现在一致。
质量段用 pmem-quality 标记。
缺结束标记时沿用现在的做法：只去掉孤立的开始标记，保留其后正文，把新段落追加到文末；
不得从开始标记删到文末。
两组标记互不覆盖，重复 init 后每组仍然只有一份。
入口：模板写出 Cursor 的 pmem-quality.mdc，以及 Claude、Codex 的独立段落；技能写到三家 skills 目录。接入完成要三家各做一次真实调用，文件存在不算模型读过。
临时妥协仍用 decision 或 risk。读规格按 feature.Spec 的决定：闭集和原文按字面，预填待核对不算已生效约束，编码任务里不跑 pmem spec complete。
