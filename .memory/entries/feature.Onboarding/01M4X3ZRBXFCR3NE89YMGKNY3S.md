---
id: 01M4X3ZRBXFCR3NE89YMGKNY3S
module: feature.Onboarding
entity: Doctor
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:e258c6e
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
决定：pmem doctor 是接入后的唯一自检入口，负责配置可读、模块覆盖率（代码文件映射到模块/第三方/忽略的比例，目标 95%，列出未覆盖目录）、路径重叠、空壳模块、Cursor 接入（mcp.json、hooks.json、规则、PATH 中的 pmem）、语义模型预热与最近 Hook 错误。
实测价值：新增 scripts/smoke_mcp.py 后 doctor 立即报出覆盖率 98.4% 并点名该文件。
注意测试中调用 doctor 时要把 embedding.backend 设为 none，否则会预热真实模型拖慢测试（4 秒变 14 秒）。
项目级 MCP 需要用户在 Cursor 设置里手动启用一次，无法由 Agent 代劳。
