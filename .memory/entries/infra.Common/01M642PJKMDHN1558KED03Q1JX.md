---
id: 01M642PJKMDHN1558KED03Q1JX
module: infra.Common
entity: LazyDoctor
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
- src/pmem/cli/main.py#_doctor
revision: git:e6c9bfc
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: pmem doctor 对外 help 只显示 --root，后台用隐藏 --quiet/--source
verify: uv run pmem doctor --help
applies: 终端或后台调用 pmem doctor
aliases:
- 记忆医生
- 懒医生
- quiet
---
需求来源：用户要求本仓库也做记忆医生。后台要跑同一条 pmem doctor，但不能改变前台对外界面。
必须保持：pmem doctor --help 只出现 --root，不出现 --quiet 和 --source；
不传这两个参数时 quiet=false、source=cli，前台仍打印自检。
后台进程用隐藏参数 pmem doctor --quiet --source <事件> 走同一入口，由 _doctor 原样交给 run_doctor。
隐藏方式与 serve --worker 相同，用 argparse.SUPPRESS。
适用条件：终端或后台调用 pmem doctor。
入口：src/pmem/cli/main.py 的 build_parser（doctor 子解析器）和 _doctor。
