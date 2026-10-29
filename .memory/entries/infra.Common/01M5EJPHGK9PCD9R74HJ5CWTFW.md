---
id: 01M5EJPHGK9PCD9R74HJ5CWTFW
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes:
- 01M5A2X278E033B7PHC34M2EME
- 01M5CFHWTQV49R4Y2EXQ7JDFH5
anchors:
- src/pmem/cli/main.py#build_parser
- src/pmem/cli/main.py#_migrate
- src/pmem/cli/brief.py#render_brief
- src/pmem/cli/main.py#_record_content
- src/pmem/cli/main.py#_read_content_file
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 命令行参数用 None 区分没传与默认值；--brief 解决终端乱码；正文按 UTF-8 读
verify: uv run pytest tests/test_cli.py
aliases:
- 乱码
- 命令行参数
verified: '2026-10-29'
verified_at: '2026-10-29T22:58:21.921+08:00'
---
命令行参数、输出与编码约定（现行）：
1) main.py 只解析参数和分发，逻辑在各 *_cmd.py 或 catalog/metrics 里（migrate move/split/sync 在 catalog，anchors --rename 在 anchors_cmd）；
   子命令特有参数在 _migrate 里用 getattr 取。
   新增的 *_cmd.py 要登记到对应模块的 paths，否则落到兜底的 infra.Common。
2) “没传”和“传了默认值”要分清时，argparse 默认值用 None，真正的默认在 run_* 或服务层取：
  - record 的 --supersedes/--anchor/--alias 配 --draft-id 时，不写沿用草稿原值，只写参数名表示清空，写了值就替换（原先默认空列表，覆盖草稿会清掉替代关系，旧记忆重新变成现行）。
  - init 的 --gate/--type、seed 的 --top：为了提示“这个参数没生效”；search 的 --limit 交给 search.limit 配置。
3) 可跟多个值的参数用 action=extend + nargs=*：--alias 闪退 崩溃，也可重复写；含空格的值加引号。
4) search、graph、record 的 --brief 每条一行“类型｜议题｜日期｜id：summary｜正文前 120 字”，本对话给过全文的只显示标题，过期的下一行标“⚠ 需核实：原因”；
   不带时输出 JSON。
   search 的 related 是字符串列表、graph 的是字典列表，渲染两种都要兼容（曾 TypeError）。
原因：终端乱码根因不是 pmem 输出（已统一 UTF-8），而是 Windows PowerShell 5 把输出接给 Select-String 等命令时按 GBK 解码；
--brief 让 Agent 直接看输出就够用，要处理 JSON 时在 Python 里按 UTF-8 解码字节，不要经 PowerShell 管道。
5) record 正文：stdin 读字节按 utf-8-sig 解码；--content-file 遇 UTF-16 BOM 按 utf-16，其余按 utf-8-sig 严格解码，失败返回 input_unreadable。
风险：脚本里写了 --alias 却不跟值会被当成清空；
直接调 run_init / run_seed 传 None 要能处理（已兜底）。
同一对话对同一模块同一议题连续用 MCP 写两条，闸门会自动注入上一条的 draft_id 而覆盖；
要拆成多条时换议题名或用终端 pmem record。
合并自 2 条记忆。
