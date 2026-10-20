---
id: 01M5CFJRTZHPMG8JHTR14QGSQ5
module: feature.Curation
entity: Seed
kind: decision
status: active
supersedes:
- 01M52G7HMJ9GR1WJKCAV5APHWV
anchors:
- src/pmem/cli/seed_cmd.py#run_seed
- src/pmem/cli/seed_cmd.py#seed_plan
- src/pmem/service/status.py#change_status
- src/pmem/hooks/gate.py#memory_lines
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 种子记忆解决冷启动；被退回的种子恢复后仍是 seed
aliases:
- 种子记忆
- 冷启动
- seed
- 转正
- 待确认
---
决定：种子记忆解决新接入项目记忆库为空的冷启动问题，由 Agent 按 pmem-seed 技能完成，pmem 只做确定性部分：
- pmem seed --plan：按近 180 天改动热度给模块排序，已有 10 条以上现行记忆的排后面，附提交说明查看命令和写入格式；
- Agent 用 pmem record --seed 写入，状态 seed，立即可被检索；
- pmem seed 列出待确认；--accept 需给 id、--module 或 --all，--reject 必须给 id，退回即归档。
可见标记：检索 JSON 带 status: seed；
--brief 和闸门摘要标“（种子，待确认）”；
规则写明 seed 依赖前先对照代码。
技能要求每模块 10～20 条、宁少勿错、写清依据、anchors 到函数。
不自动从提交说明生成记忆。
风险：种子受每日同议题上限（默认 5）约束；未转正的种子同样参与检索，负责人需尽快过目。
更正：restore 回到归档前的状态，被退回的种子恢复后仍是 seed（旧记忆说一律恢复为 active，已不对）。
