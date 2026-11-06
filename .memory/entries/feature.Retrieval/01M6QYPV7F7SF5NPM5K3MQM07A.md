---
id: 01M6QYPV7F7SF5NPM5K3MQM07A
module: feature.Retrieval
entity: StaleCheck
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#_read_anchor
- src/pmem/index/anchors.py#_check
revision: git:2bec8eb
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 过期核对读锚点前校验路径仍在项目内，越界按“已不存在”处理，不越界读磁盘
verify: uv run pytest tests/index/test_anchors.py -k outside_project
aliases:
- 路径遍历
- 越界读
- path traversal
---
过期核对读锚点文件前，路径解析后必须仍在项目目录内，否则按“已不存在”处理，不去读它。

坑：写入侧 _normalize_anchor 只拦绝对路径（Path(rel).is_absolute()），像 ../../x 这种相对越界锚点解析不出磁盘大小写、只给一条“路径在项目里不存在”的警告，但仍会被写进记忆文件。
之后 AnchorChecker._check 直接 (self.root / rel).read_text(errors=ignore) 读它，等于读了项目目录以外的任意文件。
读到的内容只用于和旧版本做相等比较、从不返回，所以不构成信息泄露；
锚点也来自同一团队，风险低，但越界读不该发生。

现在：anchors.py 新增 _read_anchor(rel)，root 与目标两边都 resolve 再 relative_to 校验（root 未规整时——短名、符号链接——不会把项目内文件也误判为越界），越界（ValueError）或 OSError 都返回 None，走“已不存在”分支，与“过期核对必须严格、宁可误报”的规则一致。
_check 里读文件统一走这个入口。

入口：src/pmem/index/anchors.py#_read_anchor（被 _check 调用）。注意 _symbol_problem 走的是 vcs.file_before（版本库取旧版，不碰磁盘路径），不受影响，无需改。
