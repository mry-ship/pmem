---
id: 01M5CAV7Z0N7FWRTBFEPT3GQE9
module: infra.Model
entity: LayeredKinds
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#Entry
- src/pmem/core/config.py
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 类型分教训与功能记录两层，新增 applies 字段及两项配置
aliases:
- 功能记录
- 分层
- feature
- plan
- 适用条件
---
用户要求（2026-10-19）：做功能也要落库，防止后来的 AI 把用户要求的行为当冗余改回去；教训要和功能记录分开、优先给出。
必须保持：类型分两层。
LESSON_KINDS（exclusion、risk、correction、decision、conclusion）是教训；
RECORD_KINDS（feature 功能、plan 规划）是功能记录。
新增可选字段 applies（适用条件，120 字以内，已加进 KNOWN_KEYS）。
配置 search.feature_limit（默认 3）和 gate.record_exempt（默认测试、生成代码、json/yaml/toml 等配置）。
入口：core/entry.py 的常量与 Entry.applies，core/config.py 的 DEFAULTS。
兼容：旧版 pmem 读到 feature / plan 会因 kind 不认识而跳过该文件，团队需一起升级。
