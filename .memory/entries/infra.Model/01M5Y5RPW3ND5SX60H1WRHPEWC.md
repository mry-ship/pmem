---
id: 01M5Y5RPW3ND5SX60H1WRHPEWC
module: infra.Model
entity: Config
kind: feature
status: active
supersedes:
- 01M5Y1JG4GCA66T2YKDW3M1ZEQ
anchors:
- src/pmem/core/config.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: content_max 5000；sync/spec 缺省；analysis_reminder 缺省 false
verify: 改 DEFAULTS 后跑 tests/core/test_config.py；tests/hooks/test_gate.py -k analysis_reminder_defaults_off
applies: 未显式写死 content_max/sync/spec/analysis_reminder 的项目；改配置校验时
source:
  conversation: 519d8eba-5c64-4862-a68d-83aecb454824
---
需求来源：用户要求配置校验收紧、正文上限放宽、自动登记与规格/查阅结束提醒默认无感。

必须保持：
1) write.content_max 默认 5000；recommend_max 仍 600（超只提示）；content_min 仍 20。已写死 1200 的旧项目需手改。
2) Config 加载时校验各节类型与数值下限；列表项单字符串当一项；记忆头 supersedes/anchors/aliases 单值当一项，字典报 ValueError。
3) sync 缺省 {auto: apply, interval_minutes: 30, full_hours: 24}；auto 只能 off/remind/apply；YAML 布尔 false→off、true→apply。
4) spec.reminder、gate.analysis_reminder 缺省 false；
   spec.dir 默认 .memory/specs。
   未写这两项的旧项目升级后不弹对应结束提醒；
   文件里已是 true 的仍提醒。
   新项目模板与手册示例已对齐。

入口：core/config.py 的 DEFAULTS 与 Config.__init__；service/record.py 的 _invalid_content。
