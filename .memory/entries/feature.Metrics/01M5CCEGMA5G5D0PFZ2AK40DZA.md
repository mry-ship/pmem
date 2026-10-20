---
id: 01M5CCEGMA5G5D0PFZ2AK40DZA
module: feature.Metrics
entity: Cleanup
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/cleanup.py#cleanup_candidates
- src/pmem/scan/files.py#present_symbols
- src/pmem/scan/files.py#code_mentions
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 清理候选：关联代码还在就不算；正文只认源码路径；类名再搜源码
verify: uv run pmem health 本仓库建议归档和清理待核对均为 0；pytest tests/test_memmap.py -k cleanup
aliases:
- 误报
- 清理候选
- 归档建议
---
决定：清理候选的判断比 Issue #13 原文收紧了两处，并修正了类名核对方式。
1) 关联代码还有一处在就不算候选。原文里“关联代码全部不存在”和“正文提到的代码找不到”任一满足即进候选，本仓库首跑 11 条待核对全是误报：关联代码都在，只是正文提到的文件找不到。
2) 正文提到的文件只认源码文件和带目录的路径。
   不带目录的 config.yaml、hooks.json 多是运行时生成或别的项目里的文件（.memory/ 是点目录，本来就不在文件索引里），Next.js 这类是产品名，原先都被当成“代码已删除”。
3) 类名先按同名文件找（C#、Java 类名等于文件名），找不到再整词搜一遍源码。
   原先只按文件名，Python 的 MemoryIndex 定义在 store.py 里，被判成找不到。
   搜源码对所有记忆共用一遍、全部找到就提前结束，本仓库 health 总耗时约 5 秒。
结果：本仓库清理候选从 11 条误报降到 0 条。
没选：用 git grep 搜类名（只支持 Git，SVN 项目用不了）。
风险：大型 Unity 项目里若有大量记忆提到已删除的类，搜源码要读完所有源码文件，health 会变慢。
