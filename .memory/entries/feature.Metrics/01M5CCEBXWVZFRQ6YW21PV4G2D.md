---
id: 01M5CCEBXWVZFRQ6YW21PV4G2D
module: feature.Metrics
entity: MemoryMap
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/memmap.py#build_memmap
- src/pmem/metrics/cleanup.py#cleanup_candidates
- src/pmem/cli/map_cmd.py#run_map
- src/pmem/metrics/health.py#_skipped
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: pmem map 演化图与自检；health 加跳过复查和严格清理候选（只建议归档）
aliases:
- 记忆图
- 演化图
- 清理
- 归档候选
---
需求来源：用户要求 v0.3.2 让记忆“看得见、可验收”（Issue #13 第 1、2、4、5 项）：画出记忆怎么演变、自检有没有漏记，以及严格的清理候选，只在相关性没有或很低时才建议归档。
必须保持的行为：
- pmem map：默认写 Wiki 目录下 map.html（单文件 SVG、数据内嵌、不联网；可缩放、拖动、按类型筛选、只看现行、点节点看全文，点自检条目定位节点），终端打印总评；
  --json 输出数据，--days 改漏记天数（默认 30）。
- 节点四组配色：失败或纠错（排除项、更正）、落地（结论、决定、功能）、注意（风险）、未实现（规划）；supersedes 实线，排除项之后同议题第一条落地虚线并标“推断”，撤销的合并标“已撤销”。
- 总评：模块数、现行和总条数、功能记录覆盖率、漏记、断链、悬而未决、过期；写明只衡量存储结构，不衡量对 AI 有没有用。
- pmem health 新增三节：改了代码却没写功能记录（按 stop 事件的 required，含回复“无需记录”）、建议归档、清理待核对；清理只建议归档、从不删除，每条附 ✓/✗ 依据。
- “建议归档”须同时满足：关联代码全部不存在（没写关联代码时看正文提到的文件和类，至少 2 处、找到不到 20%）、同议题没有其他现行记忆、没被其他记忆引用、统计期内本机没被用过（本机检索少于 20 次不看）；
  排除项、风险、更正、全项目级、种子最多到“待核对”。
入口：src/pmem/metrics/memmap.py 的 build_memmap、src/pmem/metrics/cleanup.py 的 cleanup_candidates、src/pmem/cli/map_cmd.py 的 run_map。
