---
id: 01M5EN0T1CBZXAGDK8MR5JPT97
module: feature.ModuleCatalog
entity: Hierarchy
kind: plan
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#is_module_id
- src/pmem/core/registry.py#ModuleRegistry
- src/pmem/index/store.py#search
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 模块名支持最多 4 段，父子关系由名字表达，查子模块带上祖先教训
applies: 尚未实现；以设计稿确认后的版本为准
aliases:
- 子模块
- 父子模块
- 多段模块名
- 模块层级
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
用户要求（2026-10-21）：项目常是“模块 → 子模块 → 共用基类”的结构（例：公共广告逻辑下有 4 个广告 SDK，每个 SDK 有自己的渠道，iOS 与 Android 打入的 SDK 不同），两段模块名表达不了。
已定：模块名最多 4 段（大类.段1.段2.段3），父模块=去掉最后一段，子模块继承父模块大类，不支持跨大类父子；
modules.yaml 的 parent 字段废弃；
名字看不出的深层关联用显式 related 字段登记；
平台、渠道、变体不做层级，用 applies、entity、variants。
选择点号命名而不是 parent 字段的原因：人和 Agent 一眼看懂、父子关系不会与字段不一致、可按前缀整体查；代价是父模块改名要连带后代，由 migrate rename 负责。
限 4 段的原因：检索默认 5 条教训，5 段时祖先 3 个会挤掉本模块记忆；需要第 5 段多半是把交叉维度编进了树。
设计稿：docs/superpowers/specs/2026-10-21-pmem-module-hierarchy-design.md（含改动分析、分 4 阶段实施、待确认 5 项）。
已知前置问题：hooks/memories.py 按“文字包含模块全名”判断提到的模块，多段名下 system.Ads 会误匹配 system.Ads.AdMob，需改成边界匹配。
兼容：旧版 pmem 的 Module.from_dict 不校验名字格式，已登记的多段模块在旧版里可当平级模块使用，混用降级不出错。
