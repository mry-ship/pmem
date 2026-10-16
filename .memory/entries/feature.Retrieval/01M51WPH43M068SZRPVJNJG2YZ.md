---
id: 01M51WPH43M068SZRPVJNJG2YZ
module: feature.Retrieval
entity: StaleCheck
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/index/anchors.py#AnchorChecker._worktree_state
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 过期缓存
- 需核实缓存
- anchors.json
- 核对缓存
- stale
---
决定：过期核对（AnchorChecker）的结果跨进程缓存到本机缓存目录的 anchors.json。原因：Hook、命令行、Wiki 各自是新进程，原来的进程内 60 秒缓存用不上；本仓库冷核对一次约 0.54 秒（十几次 git log/diff/show），是 Wiki 和写入后自动生成 Wiki 的主要耗时，Wiki 渲染本身只要约 20 毫秒，所以“增量 Wiki”没有单独做，靠这层缓存解决。
失效规则：工作区指纹 = 当前提交号 + 今天日期 + 记忆目录（.memory/）以外的未提交文件及其修改时间和大小，任一变化整份作废；单条按 id、写入日、核对日、锚点命中，新写或确认一条记忆只重核这一条；另有 10 分钟过期，兜住被 gitignore 的锚点文件。取指纹要 2 次 git 调用（约 70 毫秒）。只有 Git 下缓存（dirty_files 返回 None 的 SVN/无版本库照旧每次核对）。pmem reindex 会删除该文件。
实测：pmem wiki 约 1.0 秒降到约 0.58 秒（剩下主要是打开服务的固定开销），读代码附摘要的 Hook 约 0.46 秒降到约 0.30 秒。
风险：缓存目录如果放在仓库内且没被忽略，缓存文件本身会让指纹每次都变，退化为不缓存（结果仍正确）。
