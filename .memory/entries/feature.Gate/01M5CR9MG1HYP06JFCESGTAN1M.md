---
id: 01M5CR9MG1HYP06JFCESGTAN1M
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell.py#_cut_bodies
- src/pmem/hooks/shell.py#_changes_unseen
- src/pmem/hooks/shell.py#_copy_targets
- src/pmem/hooks/shell.py#_scan
- src/pmem/hooks/shell.py#_tokens
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 两轮复查补齐 20 余种绕过写法；跨整段的 heredoc 正则是平方级，已改成分段查找
verify: uv run pytest tests/hooks/test_gate.py -k "edge_cases or found_in_review or
  existing_directory or parse_fast or working_directory"
aliases:
- 绕过闸门
- 误拦
- 正则卡死
- catastrophic backtracking
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
结论（2026-10-20 两轮复查，均有单测）：下列写法原先认不出写入目标、目标错位或误拦。
- 拆语句：单个 &（两侧不必有空格，2>&1、&> 除外）。
- PowerShell：数组参数 a, b（分词后再并，分词前并会拆坏 "a.py", "b.py"）、-Path:x、Copy-Item -Path a b、通用参数值（-ErrorAction、-NewName）不是路径、管道下游的删除/移动一律拍快照。
- 目录：pushd/popd、cd /d、bash -c "cd x && …" 的 cd 只沿用到右引号那一段、写进已有目录取“目录/文件名”。
- 参数：cp -t/-T、--target-directory=、sed --in-place/--expression=/-es…、git -C/--work-tree、git checkout <目录>。
- 只读名单里能写的：find -fprint/-ok、sort -o、git --output、rg --pre。
- 代码写文件：open 的 wt/r+；Node 只认 fs.xxx( 和 xxxSync(（裸 rm(/rename( 会误中 norm(、df.rename(）；指向工作目录或其上级的字面量不算目标。
坑：空 heredoc 的可选组用贪婪 ? 会吞掉中间命令；用一整段 .*? 匹配 heredoc 在结束符缺失时是平方级（69KB 命令 98 秒）。现在正则只找开头、结束符单独查找、最多 20 处，超过 64KB 的命令直接拍快照。
风险：rmtree(ROOT) 这类删整个仓库的脚本、cd ~ 之后的相对路径只靠执行后的快照提醒。
