---
id: 01M5EJP9HMGC5SEM9YMA3S24JA
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes:
- 01M5A8F9D26J50HDBYMEKPJE56
- 01M5CFHVDFEPXVNTTXMCY1FK6H
- 01M5CR9MG1HYP06JFCESGTAN1M
anchors:
- src/pmem/hooks/guard.py#_guard
- src/pmem/hooks/memories.py#_target_modules
- src/pmem/hooks/mcp.py#_confirm_cli_calls
- src/pmem/hooks/shell.py#cli_args
- src/pmem/hooks/shell.py#_nested
- src/pmem/hooks/shell.py#_unwrap
- src/pmem/hooks/shell.py#_stages
- src/pmem/hooks/shell.py#scan
- src/pmem/hooks/snapshot.py#needs_snapshot
- src/pmem/hooks/state.py#_load
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 终端命令写目标的事前解析：认得出的写法、拆语句与目录规则、正则性能坑
verify: uv run pytest tests/hooks/test_gate.py
aliases:
- 闸门误拦
- 闸门漏拦
- 绕过闸门
---
结论：闸门事前解析终端命令的写目标（改文件、删文件），规则集中在 hooks/shell.py，gate.py 只管拦截；认不出的交给执行前后快照比对。

认得出（均有单测）：
- 重定向（>|、&>>、-o>x；只有 stdout 重定向算丢弃）、tee、sed -i/--in-place、perl -pi、删除、复制移动（cp -t/-T、Copy-Item -Path a b）、git checkout/restore/rm/mv/apply（-C、--work-tree；checkout 不带 -- 只认工作区里存在的路径）、[IO.File]::Write*、Set-Content -Path、-Path:x、数组参数 a, b（分词后再并）。
- 套一层的 powershell -Command/-File、cmd /c、bash -c/-lc、sh -ec、直接运行的脚本（最多 3 层）；
  python 的 open(wt/r+)、Node 只认 fs.xxx( / xxxSync(（裸 rm( 会误中 norm(）。
- 先去掉 sudo/doas/env A=1/command/nohup/exec/time/nice/stdbuf 前缀再识别；command -v、单独的 env 仍只读；timeout、env -S 按不认识的程序走快照。
- 只读名单里能写的：find -fprint/-ok、sort -o、git --output、rg --pre。
- 目录：cd、Set-Location、pushd/popd、cd /d 后按新目录算；bash -c "cd x && …" 只沿用到右引号；写进已有目录取“目录/文件名”。
- 通配符 rm -rf src/*、Remove-Item src\* 在项目根展开（最多 200 个）逐个查；
  rm -rf . 算全部模块，只去掉开头的 ./（lstrip 会把 .github 削成 github）；
  删目录时其下所有模块都要先查过。
- 拆语句：; && || | 换行和单个 &（2>&1、&> 除外）；引号里的命令被拆开后两半仍能识别，不要改成严格引号解析。

坑：here-string、heredoc 正文当数据；
只用正则找开头、结束符单独找、最多 20 处，超 64KB 直接拍快照（整段 .*? 曾 69KB 跑 98 秒）。
token 尾部逗号、分号要去掉。
通用参数值（-ErrorAction、-NewName）不是路径；
指向工作目录或其上级的字面量不算目标；
提问里的 ./src/x 不能 strip(".")。
风险：glob 不匹配点开头文件（同 bash）；rmtree(ROOT)、cd ~ 之后的相对路径只靠快照提醒。合并自 3 条记忆。
