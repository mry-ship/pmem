---
id: 01M59YF1ZCZBHC1M9SAN6MQK1F
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 参数默认值
- argparse
- 参数没生效
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：命令行 init 的 --gate、seed 的 --top 默认值改为 None（实际默认 block / 10 在各自的 run_* 里取），帮助文字注明“只在首次生成 config.yaml 时生效”“配合 --plan”。
原因：argparse 给了具体默认值后，后续代码分不清用户是否显式传了参数，没法提示“这个参数没生效”（见 feature.Onboarding / Init、feature.Curation / Seed）。
风险：直接调用 run_init / run_seed 的代码传 None 要能处理，两处都已兜底；以后加“只在某种情况生效”的参数，同样用 None 作默认值。
