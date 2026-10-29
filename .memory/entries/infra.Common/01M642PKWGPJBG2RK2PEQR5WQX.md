---
id: 01M642PKWGPJBG2RK2PEQR5WQX
module: infra.Common
entity: LazyDoctor
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
revision: git:e6c9bfc
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 不要另开医生子命令，也不要把 --quiet 做成公开选项
verify: uv run pmem doctor --help
applies: 给 doctor 加后台入口时
aliases:
- 记忆医生
- 懒医生
- doctor-lazy
---
不要给医生新开子命令（例如 doctor-lazy），也不要把 --quiet / --source 做成公开选项。
公开 --quiet 会让人以为前台也可以静默跑，help 也会变，违反“对外仍只有 --root”。
另开子命令会让后台和前台两套入口，状态和退出码容易分叉。
现行：doctor 子解析器上挂隐藏参数，沿用 serve --worker 的 argparse.SUPPRESS，由 _doctor 转给 run_doctor。
