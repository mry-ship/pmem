---
id: 01M5HFRMPT5Y8TSHE3FVAETE6Y
module: feature.ModuleCatalog
entity: AutoSync
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/catalog/autosync.py
revision: git:0a86e6e
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 自动登记只追加：手工删掉的模块会被下次扫描加回来，不想登记的目录要写进 ignored
verify: uv run pytest tests/test_autosync.py -k ignored
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
风险：sync.auto 为 apply（默认）时，在 modules.yaml 里手工删掉某个模块条目，文件修改时间变了→目录指纹变了→后台重扫，那个目录又没归属，会被重新登记。
处理：不想登记的目录写进 ignored（或 third_party），map_files 按排除处理、不再规划；改名合并用 pmem migrate rename/merge，路径跟着走不会被加回。
手册和 README 已写明。
