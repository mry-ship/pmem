---
id: 01M5Y1JG4GCA66T2YKDW3M1ZEQ
module: infra.Model
entity: Config
kind: feature
status: active
supersedes:
- 01M5CVMB77DQN1N2FYMPN2JNS5
- 01M5EM5XZZQ3B1Z3H05QY9AYGC
- 01M5HE0XEP27AHTSSD5T6NVVJT
anchors:
- src/pmem/core/config.py
- src/pmem/service/record.py#_invalid_content
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: content_max 默认 5000；sync/spec 缺省与列表单值当一项；categories 无则 feature/infra
applies: 未显式写死 content_max/sync/spec 的项目；改配置校验时
---
需求来源：用户要求配置校验收紧、正文上限放宽、自动登记与规格提醒默认无感。

必须保持：
1) write.content_max 默认 5000；recommend_max 仍 600（超只提示）；content_min 仍 20。已写死 1200 的旧项目需手改。
2) Config 加载时校验各节类型与数值下限；列表项单字符串当一项；记忆头 supersedes/anchors/aliases 单值当一项，字典报 ValueError。
3) sync 缺省 {auto: apply, interval_minutes: 30, full_hours: 24}；auto 只能 off/remind/apply；YAML 布尔 false→off、true→apply。
4) spec.reminder 缺省 false；spec.dir 默认 .memory/specs。新项目模板与手册示例已对齐。

入口：core/config.py 的 DEFAULTS 与 Config.__init__；service/record.py 的 _invalid_content。

合并自 3 条功能记录。
