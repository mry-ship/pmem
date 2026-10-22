---
id: 01M5HE0XEP27AHTSSD5T6NVVJT
module: infra.Model
entity: Config
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
- src/pmem/generate/templates.py
revision: git:8d3a154
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 新增 sync 配置段：auto apply/remind/off、interval_minutes 30、full_hours 24；布尔值按档位转换
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-22）要求自动发现并登记新模块。
必须保持：DEFAULTS 增加 sync: {auto: apply, interval_minutes: 30, full_hours: 24}；
sync 必须是键值对；
sync.auto 只能 off/remind/apply；
interval_minutes ≥0、full_hours ≥1。
YAML 把不加引号的 off/on 读成布尔值：sync.auto 为 false 当 off、true 当 apply（与 gate.mode 的布尔处理同理），否则用户写 auto: off 会报配置错误。
init 生成的 config.yaml 模板和手册配置示例已写上这三项。
