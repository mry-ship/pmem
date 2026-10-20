---
id: 01M5CCE24B2V64FKVG5JQ799VR
module: feature.Curation
entity: Merge
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/compact_cmd.py#run_compact
- src/pmem/cli/compact_cmd.py#render_revert
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: pmem compact --undo 撤销合并；FileIndex 移到 scan/files.py
aliases:
- 撤销合并
- 回滚
---
需求来源：用户要求合并可以回滚（Issue #13 第 3 项）。
必须保持的行为：
- pmem compact --undo <合并后的 id> 撤销一次合并，输出重新现行的原记忆和没恢复的原因；pmem compact 列出议题时附撤销提示。
- pmem-compact 技能写明合并错了用 --undo 撤销再重新合并。
- 代码文件索引 FileIndex 及正文提到的路径、类名的正则移到 src/pmem/scan/files.py，pmem anchors 从那里导入；
  anchors_cmd 仍导出 FileIndex（tests/test_anchors_cmd.py 从这里导入），补关联代码的行为不变。
入口：src/pmem/cli/compact_cmd.py 的 run_compact。
