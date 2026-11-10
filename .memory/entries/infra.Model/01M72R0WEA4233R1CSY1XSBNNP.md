---
id: 01M72R0WEA4233R1CSY1XSBNNP
module: infra.Model
entity: HarnessConfig
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
revision: git:dbfdab4
author: 1002378395@qq.com
note_date: '2026-11-10'
summary: config 增加 harness 节：mode/阈值/验证命令，默认 off
verify: uv run pytest tests/core/test_config.py
---
需求：实验开关与阈值。必须保持的行为：
- DEFAULTS 含 harness.mode=off、window_days、min_pair、min_ratio、max_files、refresh_hours、verify_commands。
- YAML 把 mode 读成布尔时按 off/hint 纠正；未写 harness 节的项目与 DEFAULTS 合并后仍合法。
入口：core/config.py。
