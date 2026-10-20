---
id: 01M5CWNMZ8NFJAK23G4MXWKDT7
module: feature.Wiki
entity: Generate
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py#write_wiki
- src/pmem/generate/wiki.py#project_wiki_dir
- src/pmem/cli/wiki_cmd.py#run_wiki
- src/pmem/service/base.py#_refresh_wiki
- src/pmem/cli/map_cmd.py#run_map
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Wiki 页面不能写出输出目录；配置里的 wiki.dir 不能指到项目外
verify: uv run pytest tests/test_wiki.py -k "escape or symlink or outside_project"
aliases:
- 路径穿越
- wiki.dir
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
需求来源：2026-10-20 安全审查，手写记忆的 module 字段可以在生成 Wiki 时写出目录。
必须保持：
- 页面文件名只能是合法模块名加 .md，或 index.md。含路径分隔符或 .. 的模块名不写文件，索引里用反引号标出来，不做相对链接。
- 解析后的路径必须是输出目录里的直接子文件。符号链接不跟随、也不删。
- 配置里的 wiki.dir 解析后必须仍在项目内（绝对路径、..、指到项目外的符号链接都拒绝）。pmem wiki 和 pmem map 返回 2；自动生成只在 warnings 里说明，记忆本身仍写入。
- --out 仍可以指到项目外的目录，但页面不能再跳出那个目录。指向已有文件返回 2、手写同名页不覆盖，这两条不变。
入口：generate/wiki.py 的 write_wiki、project_wiki_dir；
cli/wiki_cmd.py；
自动生成在 service/base.py 的 _refresh_wiki；
map 默认输出在 cli/map_cmd.py。
