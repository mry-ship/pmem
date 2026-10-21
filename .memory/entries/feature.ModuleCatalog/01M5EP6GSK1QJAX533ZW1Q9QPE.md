---
id: 01M5EP6GSK1QJAX533ZW1Q9QPE
module: feature.ModuleCatalog
entity: Hierarchy
kind: feature
status: active
supersedes:
- 01M5EN0T1CBZXAGDK8MR5JPT97
anchors:
- src/pmem/core/registry.py#resolve_module
- src/pmem/catalog/migrate.py#plan_rename
- src/pmem/catalog/sync.py#_split_proposals
- src/pmem/catalog/coverage.py#coverage_report
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 模块名最多 4 段，父子由名字表达；父须先登记；改名级联子模块；sync 只提议拆子模块
verify: uv run pytest tests/test_module_hierarchy.py
applies: modules.yaml 使用点号多段模块名时；旧版 pmem 能读写已登记子模块但没有继承
aliases:
- 父子模块
- 子模块
- 多段模块名
- 模块层级
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户项目有约 4 个广告 SDK，每个 SDK 有自己的渠道，iOS/Android 打入的 SDK 不同，需要 system.Ads.AdMob 这样的父子模块。
用户确认：最多 4 段（大类+3 层），父子关系靠名字识别，名字看不出的深层关联写 related。
必须保持的行为：
- is_module_id 接受大类+1～3 段，每段同原命名规则；超过 4 段报“最多 4 段”。parent_module / ancestor_modules / is_lineage 按名字前缀+点号计算，不区分大小写。
- 旧的 parent 字段不再生效（读成 legacy_parent，只供 health 提示改名）；related 接受字符串或 {module, reason}。
- 短名：末段和每个带点后缀（AdMob.Android、Ads.AdMob.Android）都能解析；末段歧义时报歧义；depth>2 的歧义末段不参与正文提及匹配。
- 未登记子模块只有父模块已登记时才接受，id 按父模块的规范大小写和并入目标。
- migrate rename 父模块时子模块跟着改名（检查不超过 4 段、不撞名），旧完整名都登记为别名，并改写 merged_into、旧 parent、related；不能改名到自己下面；新名的父模块必须已登记。
- doctor：有子模块的父模块不算空壳；有多段模块时提示团队升级。
- sync 对 ≥60 个文件的模块，把 /** 路径下 ≥30 个文件或近期改动 ≥5 次的直接子目录提议为 <模块>.<目录名>，只提示并给出 migrate split 命令，不自动写。
入口：src/pmem/core/registry.py、catalog/migrate.py、catalog/sync.py、catalog/coverage.py、cli/doctor_cmd.py。
设计稿 docs/superpowers/specs/2026-10-21-pmem-module-hierarchy-design.md。
