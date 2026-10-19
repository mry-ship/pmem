---
id: 01M5A8NFH6H7HCM2FHJJ0Q0RAD
module: feature.Curation
entity: Merge
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
- src/pmem/cli/anchors_cmd.py
- src/pmem/cli/format_cmd.py
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 每日上限
- 合并记忆
- compact
- 原子写入
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：合并记忆（compact）方案里“替代旧记忆的写入不受每日上限约束”这一句收窄为：被替代的记忆里至少有一条仍然现行，或带 draft_id 覆盖，才豁免每日上限。
原因：原规则下随便填一个早已被替代的 id 就能绕过上限无限写入。合并旧记忆时被合并的都是现行记忆，正常合并流程不受影响。
记忆 01M4Z58VYP1ZT8X81SW5TTQXCB 的其余内容（合并由 Agent 按 pmem-compact 完成、5 条以上提示等）仍然成立，只有这一句过时。

另：pmem anchors 和 pmem format 改写记忆文件改用原子写入（先写临时文件再 os.replace），中途中断不会留下半截文件。
