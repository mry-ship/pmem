---
id: 01M5CWNZY61RCD3EYEVCQPPMXY
module: feature.Wiki
entity: Generate
kind: correction
status: active
supersedes:
- 01M5CW5JCMEGQ7T32XHKNK01BH
anchors:
- src/pmem/generate/wiki.py#write_wiki
- src/pmem/generate/wiki.py#project_wiki_dir
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Wiki 写出已限制在输出目录内，非法模块名和项目外的 wiki.dir 都会拒绝
verify: uv run pytest tests/test_wiki.py -k "escape or symlink or outside_project"
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
更正：手写记忆的 module 字段已经不能在生成 Wiki 时写出目录。
页面文件名只接受合法模块名，解析后必须是输出目录的直接子文件，符号链接不跟随。
配置里的 wiki.dir 指到项目外时，pmem wiki 和 pmem map 返回 2，自动生成只警告、不写文件。
--out 仍可以指到项目外，但页面不能再跳出该目录。
