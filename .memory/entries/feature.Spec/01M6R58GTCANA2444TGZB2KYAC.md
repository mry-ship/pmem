---
id: 01M6R58GTCANA2444TGZB2KYAC
module: feature.Spec
entity: Reconstruct
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#spec_prefill
- src/pmem/generate/spec.py#_bodies
- src/pmem/cli/spec_cmd.py#_memory_prefill
revision: git:9c0cf10
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: spec 从现行 feature 记忆预填程序节入口/现状节必须保持，标待核对、不破九成八口径
verify: uv run pytest tests/test_spec.py -k prefill
aliases:
- 规格预填
- 防漂移
---
需求来源：spec complete 原来只铺空骨架，程序设计/模块现状节全靠 Agent 合上代码从零反推到九成八。用户要求从 feature 记忆预填起点，降负担、防 spec 与记忆漂移。

必须保持的行为：
- spec init/complete 铺骨架时，从该模块“现行、未被替代”的 feature 记忆预填：anchors → 程序设计/入口；summary（或标题，即必须保持的行为）→ 模块现状/必须保持。按模块精确匹配，别的模块不串。
- 预填内容标“（以下由 feature 记忆预填，待对照代码核对，核对后删除本行）”，提示是起点、须核对后才算数。
- 不破坏九成八口径：EMPTY 标记仍保留，--check 仍判未完成；只 feature 进预填（排除项/根因等教训不进规格）；不拷源码、不粘模板全文（沿用 SourceDenom/PhraseContains 排除项）。
- 预填数据来源：spec_cmd._memory_prefill 直接读记忆文件（FilesStorage.iter_all，不走索引/嵌入），算 superseded 后取 VISIBLE_STATUSES 的现行条目，调 spec.spec_prefill 构造；
  读失败一律吞掉返回空、照旧铺空骨架（预填只是便利）。
- spec.py 不依赖检索/索引：spec_prefill 接收 Entry 列表，init_specs/_ensure/_bodies 透传 prefill 字典。

入口：src/pmem/generate/spec.py#spec_prefill、#_bodies、#init_specs、#_ensure；src/pmem/cli/spec_cmd.py#_memory_prefill。
