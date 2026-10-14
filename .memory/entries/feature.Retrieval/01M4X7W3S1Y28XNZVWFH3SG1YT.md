---
id: 01M4X7W3S1Y28XNZVWFH3SG1YT
module: feature.Retrieval
entity: Ranking
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/index/store.py
revision: git:1201d1a
author: 1002378395@qq.com
note_date: '2026-10-14'
---
结论：与参考实现（tilematch-dev-memory，LanceDB + Ollama nomic-embed-text）在同一批 TileMatch 真实记忆（853 条/53 模块）上对比，pmem 检索明显更准，差距来自排序方式而不是嵌入模型。

证据（13 个限定模块的查询，每个都事先人工确认了目标记忆，取前 3 条）：pmem 9/13，参考实现 4/13；其中 6 个针对模块内较早记忆的查询 pmem 4/6、参考实现 0/6。参考实现只命中 DDA（4 条）、IAP（9 条）、AdChase（11 条）这类小模块，因为整个模块都在返回范围内。

原因（读参考实现 store.search_memory 确认）：先按向量取 max(limit×5, 20) 条候选，再按 note_date/created_at 从新到旧截取 limit 条。因此 ≤20 条的模块（53 个中 42 个）查询词完全不影响结果，总是返回最新几条；大模块里老结论会被新记忆挤掉。实测 FarmSudoku 三个毫不相干的查询返回同一组 3 条；Monopoly 查“魔法骰子”取 10 条都没有 MagicDice。参考实现也不支持全局（跨模块）检索，module 必填。

对 pmem 的启示：坚持“相关度为主、90 天半衰期只占 30% 权重”的排序，不要改成按时间排；对外宣传收益可直接引用这组对比（已写入 README“真实数据实测”）。两边共同短板是同义改写（闪退/崩溃、红点/小圆点），属于写作规范问题，见同模块 Ranking 排除项。
