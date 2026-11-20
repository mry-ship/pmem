---
id: 01M7WHQ4BZJB7DM3MFCXRV60E3
module: infra.Common
entity: Pyright
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: pyright 基础模式覆盖 core/index/service/catalog 并纳入测试
verify: uv run pytest tests/test_pyright.py
applies: 改类型检查范围或开发依赖时
---
需求来源：v0.7 设计稿 §3.6。

必须保持：
- hooks/types.py 的 GateAttrs 声明混入类共享属性；各混入类继承它。
- pyright 基础模式覆盖 core/index/service/catalog（pyrightconfig.json）；tests/test_pyright.py 纳入 CI 向测试。
- 开发依赖含 pyright（uv sync --group dev）。

适用：改闸门混入或扩大 pyright 范围时。
