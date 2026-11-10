---
id: 01M72R0NERD3JK0HPECFQ5SC79
module: feature.Tools
entity: HarnessContext
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#_attach_context
revision: git:dbfdab4
author: 1002378395@qq.com
note_date: '2026-11-10'
summary: search_memory 带 path 时返回 context 节（harness 实验）
verify: uv run pytest tests/hooks/test_harness.py -k search_attaches
---
需求：改前上下文经检索送达，不靠 Hook 附加。必须保持的行为：
- harness.mode 非 off 且调用带 path 时，成功检索的返回可含 context（常一起改、修复提交、该模块规格必须保持最多 3 条）。
- 同一对话同一文件只给一次全文 context（与 seen 去重共用机制）。
- harness.mode=off 时行为与以前完全一致，不加 context。
入口：service/search.py 的 _attach_context；命令行 --brief 也会打印 context。
