---
id: 01M5CVMB77DQN1N2FYMPN2JNS5
module: infra.Model
entity: Config
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/config.py#Config.__init__
- src/pmem/core/entry.py#_str_list
- src/pmem/core/registry.py#ModuleRegistry.__init__
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 配置的数值和列表项加载时就校验；单个字符串当一项；大类缺失时按已登记模块推断
verify: uv run pytest tests/test_robustness.py -k "config or categories or single_value"
aliases:
- 配置校验
- 未知大类
- ConfigError
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求两轮复查后全部修复。
必须保持：
1) Config 加载时校验：gate/write/search/server/embedding/wiki/project 必须是键值对；
   content_min、content_max、search.limit、max_per_day_per_entity 等数值项必须是数字且不小于下限，content_max 不能小于 content_min。
   原先写成字符串时写入、检索才抛异常栈，content_max<content_min 会拒绝所有写入。
2) gate.watch/ignore/skip_markers 等列表项写成单个字符串时当一项（原先按字符匹配，闸门静默失效），写成其他类型报 ConfigError。
3) 记忆文件头里 supersedes/anchors/aliases 写成单个值时当一项（原先字符串被拆成单个字符，替代关系悄悄失效），写成字典报 ValueError。
4) modules.yaml 没写 categories 时按已登记模块和候选的大类推断，都没有时用通用预设 feature/infra；原先固定回落到游戏预设，非游戏项目的 feature.* 记忆全部报“未知大类”。
入口：core/config.py Config.__init__、core/entry.py _str_list、core/registry.py ModuleRegistry.__init__。
