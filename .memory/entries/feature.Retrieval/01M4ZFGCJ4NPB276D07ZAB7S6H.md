---
id: 01M4ZFGCJ4NPB276D07ZAB7S6H
module: feature.Retrieval
entity: Verify
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#check_anchors
- src/pmem/index/synonyms.py
revision: git:fc9f6d8
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 过期
- 失效
- 同义词
- 搜不到
---
结论：检索时按当前代码核对记忆（stale 过期/失效判定）以及同义词扩展，在 TileMatch 真实数据上验证有效。

核对规则：满足任一条就标 stale，并在 check 里写明原因：锚点文件已不存在；文件里找不到锚点符号；文件在 max(note_date, verified) 之后改过。改动日期向版本库批量查询，结果缓存 60 秒。先选出结果，再只核对这几条的锚点，所以检索含核对只要 30–100 毫秒（TileMatch 855 条）。

没有版本库时会退回看文件修改时间（mtime），误报很多：TileMatch 837 个脚本里有 102 个 mtime 是当天，可能是 Unity 或工具碰过。例如 ProcessType.cs 在 SVN 里最后提交是 10-12、本地也没改，按 mtime 却显示“今天改过”。有版本库就必须用版本库的提交日期。

同义词：TileMatch 记忆里“闪退”出现 0 次、“崩溃”28 次、“crash”15 次。在 modules.yaml 加 synonyms: [闪退, 崩溃, crash] 后，在 Jigsaw 的 87 条记忆里搜“拼图 闪退”，前 2 条正好是两条提到崩溃的记忆；不加同义词时，前 3 条一条都不是。扩展词按 0.8 权重计入 BM25，并拼进向量查询。条目自己的 aliases 只并入该条的索引文本，不用来扩展查询，因为一条记忆的别名可能混着几种互不相关的叫法。
