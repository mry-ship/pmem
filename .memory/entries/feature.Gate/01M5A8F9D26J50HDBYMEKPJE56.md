---
id: 01M5A8F9D26J50HDBYMEKPJE56
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_guard
- src/pmem/hooks/gate.py#_target_modules
- src/pmem/hooks/gate.py#_confirm_cli_calls
- src/pmem/hooks/shell.py#cli_args
- src/pmem/hooks/shell.py#_nested
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 绕过闸门
- 通配符删除
- rm -rf
- pmem record 登记
- 并行命令
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
结论（2026-10-19 深度检查）：终端命令绕过闸门、登记有误的 7 处已修复，均有单测。
1) 通配符删除：rm -rf src/*、Remove-Item src\* 原样当路径，匹配不到模块就放行；
   现在按 glob 在项目根展开成实际文件和目录逐个检查（最多 200 个，展开结果不再二次展开），带通配符的目标也会做执行前后快照比对。
   rm *.log 这类展开后不属于模块的照常放行。
2) rm -rf . / ./ 原先前缀拼成 "./" 什么都匹配不上；lstrip("./") 会把 .github/** 削成 github/**。现在根目录算全部模块，前缀只去掉开头的 ./。
3) 终端 pmem record 原先执行前就登记为写过，写入失败、|| 后没执行也算，结束提醒被压掉；
   现在和 search 一样挂起（state 新字段 cli_record_pending），执行后输出里同时看到模块名和 draft_id 才登记，否则记 record_call_failed。
   拿不到输出（载荷无输出字段）时照旧登记。
4) 挂起的终端检索原先会被并行的 ls 拿走；现在只有这条命令本身也含 pmem 调用时才允许按“只剩一条”兜底。
5) bash -lc、sh -ec 等合并短参数现在识别为内联命令。
6) & pmem search、& "C:\...\pmem.exe" search 现在能识别。
7) 提问里 ./src/x 原先被 strip(".") 变成 /src/x 映射不到模块。
风险：glob 不匹配点开头文件（与 bash 一致，PowerShell 的 * 会匹配）；record 的成功判断依赖输出含 draft_id，以后改 record 输出格式要同步。
