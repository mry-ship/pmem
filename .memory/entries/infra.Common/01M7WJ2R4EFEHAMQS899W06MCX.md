---
id: 01M7WJ2R4EFEHAMQS899W06MCX
module: infra.Common
entity: Roadmap
kind: conclusion
status: active
supersedes:
- 01M5Y2349BAC0R4HACKF1VF0E1
- 01M5Y1SRC18WCERGWZXSCTKMC1
anchors:
- docs/superpowers/specs/2026-10-14-pmem-design.md
- README.md
- docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md
- src/pmem/core/schema.py
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 路线：v0.7 类型安全已于 0.7.0 发布
verify: 'README 路线表与 Issue #15；pmem --version'
applies: 排版本或改 README/设计路线表时
---
版本路线以设计文档第 14 节与 GitHub Issue 为准。

现行：
- v0.4：转正提示与召回审计已实现；团队汇总与中心服务长期搁置。
- v0.6：模块规格已发布。
- v0.7：类型安全与规则化已于 2026-11-20 发 0.7.0（enforced_by、facets/when、边界校验、返回契约、pyright）。

适用：排版本或改 README/设计路线表时。
验证：README 路线表与设计稿、Issue #15；pmem --version 为 0.7.0。
