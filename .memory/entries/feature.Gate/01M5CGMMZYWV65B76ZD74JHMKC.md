---
id: 01M5CGMMZYWV65B76ZD74JHMKC
module: feature.Gate
entity: WildcardPath
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/guard.py#_guard
- src/pmem/hooks/gate.py#on_pre_tool
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 带方括号的路径曾被当通配符展开为空而放行；编辑工具按字面路径检查
verify: uv run pytest tests/hooks/test_gate.py -k brackets
aliases:
- 方括号
- 动态路由
- glob 误展开
- 闸门放行
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
根因：_guard 见到 `[` 就走 glob.glob，app/[id]/page.tsx 里的 [id] 被当成字符集，展开为空，next(...) 返回 None 即放行；Write/StrReplace 等编辑工具也走了这条路。
修复：编辑工具给的是字面路径，直接走 _guard_path，不再做通配符展开；
终端命令的目标先看字面路径是否存在，存在就按字面查；不存在时 glob 展开，只含方括号（没有 * ?）且展开为空时也按字面查。
不采用“展开为空就一律按字面查”：rm src/X/*.tmp 没有匹配时是空操作，按字面会在 block 档无谓地拦住。
影响：Next.js、SvelteKit 等动态路由目录下的文件现在受闸门保护。
