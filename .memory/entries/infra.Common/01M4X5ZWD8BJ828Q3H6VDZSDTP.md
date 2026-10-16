---
id: 01M4X5ZWD8BJ828Q3H6VDZSDTP
module: infra.Common
entity: Testing
kind: risk
status: active
supersedes: []
anchors: []
revision: git:74edc08
author: 1002378395@qq.com
note_date: '2026-10-14'
---
在 Cursor 里用 Agent 编辑文件后立刻跑 pytest / ruff，偶尔会得到“旧代码”的结果：例如刚加的 import 报 NameError、traceback 里源码行显示为 ???、ruff 报 F821 未定义。
原因是编辑落盘有延迟（同一批并行提交的多个修改尤其明显），不是 pyc 缓存问题，也不是代码真有错。

处理：先确认文件内容（Select-String / 读文件）已是新版本，等 1–2 秒再跑；连续多次出现同一错误才当作真实失败排查。设置 PYTHONDONTWRITEBYTECODE=1 不能解决这个问题。
