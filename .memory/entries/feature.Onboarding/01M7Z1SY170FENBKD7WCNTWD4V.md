---
id: 01M7Z1SY170FENBKD7WCNTWD4V
module: feature.Onboarding
entity: Init
kind: feature
status: active
supersedes:
- 01M5M38K4M36HGFDS81Z1J2HJY
- 01M5M2X2JKVT38JQJ9KPYX3HT5
anchors:
- src/pmem/cli/init_cmd.py#choose_spec_reminder
- src/pmem/generate/templates.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 首次 init 规格提醒默认开启，回车保持开，输入 n 才关
verify: uv run pytest tests/test_cli_flow.py -q -k spec_reminder
applies: pmem init 还没有 config.yaml 时
source:
  conversation: 5500e8d7-007c-460c-b7d7-15a5bb04aee9
---
需求来源：用户要求 Spec Reminder 与改代码前读取相关规格都默认开启。
必须保持：新项目模板里 spec.reminder 与 spec.read_before_edit 都是 true。
只在还没有 config.yaml 时询问规格提醒。
直接回车、y、yes、「是」或没有终端都保持开启。
输入 n、no 或「否」才把 reminder 写成 false，并把该行注释改成「已关闭」。
read_before_edit 不单独询问。
已有 config.yaml 不覆盖。
入口：pmem init 首次写出 .memory/config.yaml。
