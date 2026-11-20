---
id: 01M7WHQ0GMKZVJ45D4XFH83G5Q
module: feature.Gate
entity: GateAttrs
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 混入类继承 GateAttrs；共享 root/config/state 类型声明
verify: uv run pytest tests/hooks/test_gate.py -q
applies: 改闸门混入或扩大 pyright 到 hooks 时
---
需求来源：v0.7 设计稿 §3.6。

必须保持：
- hooks/types.py 的 GateAttrs 声明混入类共享属性；各混入类继承它。
- pyright 基础模式覆盖 core/index/service/catalog（pyrightconfig.json）；tests/test_pyright.py 纳入 CI 向测试。
- 开发依赖含 pyright（uv sync --group dev）。

适用：改闸门混入或扩大 pyright 范围时。
