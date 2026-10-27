---
id: 01M51WPVG6P4VR20F8R50MNWY4
module: feature.Storage
entity: Testing
kind: decision
status: active
supersedes: []
anchors:
- tests/conftest.py#_isolated_cache
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 测试缓存
- PMEM_CACHE_DIR
- 测试隔离
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:12.602+08:00'
---
决定：tests/conftest.py 增加自动生效的夹具，把 PMEM_CACHE_DIR 指向每个用例自己的临时目录。
原因：配置解析缓存（parsed/）和过期核对缓存（anchors.json）都写在用户缓存目录，测试项目建在随机临时目录，不隔离就会往 %LOCALAPPDATA%\pmem 里不断堆积文件。
注意：测试里的缓存文件不能放进 git_repo 夹具的仓库目录，否则它会变成未跟踪文件，让工作区指纹每次都变、缓存永远不命中；
需要单独缓存路径时用 tmp_path_factory。
