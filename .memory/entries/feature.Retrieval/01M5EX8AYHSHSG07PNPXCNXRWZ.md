---
id: 01M5EX8AYHSHSG07PNPXCNXRWZ
module: feature.Retrieval
entity: Benchmark
kind: conclusion
status: active
supersedes: []
anchors: []
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: v0.3→v0.5 同一记忆库回放：真实题前三 80%→90%；每次检索多约 450 token、慢约 5 毫秒
verify: 抽 v0.3 工作树、拷入 .memory、scripts/eval_real_queries.py 和 tests/fixtures/eval，两边各跑
  uv run python scripts/eval_real_queries.py run --root . --set real|path|alias
aliases:
- 版本对比
- 效果数字
- token 消耗
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
结论（2026-10-21，本仓库现行记忆库，语义+关键词，GPT-4o o200k 分词）：把 v0.3（e637c17）抽到临时工作树、拷入同一份 .memory 和题目，与当前 v0.5 对比。
- 真实检索 91 题：前三 73→82（80%→90%），第一 37→40，MRR 0.603→0.657。
- 按文件 115 题：两版都是前三 113、第一 100、MRR 0.928。
- 换说法 112 题：前三都是 110，第一 97→96。
- 规则正文 1034→853 token；五个工具说明 747→842 token。
- 单次按模块+问题检索返回（106 次）：中位 1923→2375 token，p90 2536→2898，最多 2723→3288。
  多出的主要是功能记录标题组（features）和字段说明提示；
  提示在真实对话里每个对话只给一次，脚本里没有对话 id 所以每次都算了。
- 单次检索耗时中位 1.8→6.5 毫秒（p90 2.2→8.4），差值多半来自 v0.4 更严的过期核对，未单独拆分。
坑：v0.3 不认识 feature/plan 类型，每次检索在 warnings 里列出大量解析失败，直接测会得到中位 5811 token 的假数字，对比时要去掉 warnings。
也因此 v0.3 的候选池里少了功能记录这类干扰项，对它略有利。
未测：父子模块继承（本仓库没有子模块）、Hook 耗时、端到端纠正率和总 token。
