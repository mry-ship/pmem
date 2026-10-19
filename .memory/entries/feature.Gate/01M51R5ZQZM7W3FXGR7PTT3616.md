---
id: 01M51R5ZQZM7W3FXGR7PTT3616
module: feature.Gate
entity: Bypass
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#shell_write_targets
- src/pmem/hooks/gate.py#_search_digest
- src/pmem/hooks/gate.py#_unreviewed
- src/pmem/hooks/gate.py#on_pre_tool
- src/pmem/hooks/payload.py#turn_tool_paths
revision: git:874e444
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 绕过闸门
- 漏查
- 不查记忆
- 绕过
verified: '2026-10-19'
---
结论：有 3 个“不查记忆也没人知道”的漏洞，已修复。

1. 不走 Read 的问答不审查：摘要原先只在 Read 后附上，Grep、Glob、语义搜索看代码时没有；提问没写模块名、别名或路径时，结束审查也认不出。
   现在：
   - 搜索范围限定在某个模块的文件或目录时附摘要。Cursor 的 Grep 输出不含命中文件，只能用参数里的路径（实测字段是 file_path）。
   - stop 时从对话记录取本轮 Agent 用读代码、搜索工具看过的路径，有记忆却没查的模块同样追问（“本轮看过 X 的代码”），旧版 hooks.json 也能兜住。
2. 终端写文件识别不全。新增：
   - cp、mv、Copy-Item、Move-Item；
   - git checkout -- 文件、restore、rm、mv、apply（读补丁里的路径）；
   - [IO.File]::WriteAll*；
   - python 或 node 内联代码及所运行的脚本：出现写文件调用时，代码里像路径的字面字符串都算写入目标，宁可多拦。
   uv run pytest 不读测试文件。脚本里拼接出来的路径仍然认不出。
3. 命令里带 pmem search 时整条直接放行，“查 A 再写 B”也能过。现在只放行查过的模块。
