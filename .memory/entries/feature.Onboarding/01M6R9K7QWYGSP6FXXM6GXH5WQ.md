---
id: 01M6R9K7QWYGSP6FXXM6GXH5WQ
module: feature.Onboarding
entity: ProjectTrust
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/mcp_enable.py#_claude_project_keys
- src/pmem/generate/mcp_enable.py#enable_claude_project_mcp
- src/pmem/generate/mcp_enable.py#enable_codex_project_mcp
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: Claude 启用按解析后真实绝对路径精确匹配（不按目录名）；claude/codex 配置改原子写
verify: uv run pytest tests/test_mcp_enable.py -k 'same_name or claude or codex'
aliases:
- 同名项目
- 误信任
- 原子写配置
---
需求来源：用户体检清单。两处修复。

必须保持：
1) Claude 项目启用只认 ~/.claude.json 里“绝对路径且解析后与 root.resolve() 相等”的项，不再按目录名 basename 匹配。
   原来把所有 basename==root.name 的 key 都写 enabledMcpjsonServers+=pmem 并设 hasTrustDialogAccepted=True，同名不同路径（~/a/pmem 与 ~/b/pmem）被一起启用+标信任。
   另：只对 is_absolute() 的 key 做 resolve 比较——相对/短路径 key 的 resolve() 会按当前 cwd 解析，可能误命中别的项目（Claude 实际写绝对路径，误伤面窄，但按绝对路径更稳）。
2) 写 ~/.claude.json、~/.codex/config.toml 一律走 core.fileio.write_atomic（先写 .tmp 再 os.replace），写一半崩溃不毁全局配置。原来是裸 write_text。

入口：src/pmem/generate/mcp_enable.py 的 _claude_project_keys、enable_claude_project_mcp、enable_codex_project_mcp。
