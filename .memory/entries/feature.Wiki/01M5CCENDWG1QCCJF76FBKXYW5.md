---
id: 01M5CCENDWG1QCCJF76FBKXYW5
module: feature.Wiki
entity: EvolutionDiagram
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py#render_wiki
- src/pmem/generate/memmap.py#render_mermaid
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Wiki 模块页附 Mermaid 演化图，最多 40 个节点，标签必须转义
aliases:
- 演化图
- Mermaid
- 记忆图
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
---
需求来源：用户要求记忆图同时出 Wiki 里的 Mermaid 版本（Issue #13 第 1 项），通读 Wiki 时就能看到议题怎么演变。
必须保持的行为：
- 每个模块页加“## 演化图”一节：每个议题一个分组，从新到旧排，节点带类型、日期和截断的标题，配色与 pmem map 一致，已被替代或归档的画灰色虚框；附图例说明。
- 每页最多 40 个节点，超出的较早议题不画，并提示用 pmem map 看完整的图；只有一条记忆、没有任何关系的模块不画。
- 标签里的 # " < > 必须转义（先换 #），否则 Mermaid 渲染失败或注入 HTML。
入口：src/pmem/generate/wiki.py 的 render_wiki，图由 src/pmem/generate/memmap.py 的 render_mermaid 生成。
