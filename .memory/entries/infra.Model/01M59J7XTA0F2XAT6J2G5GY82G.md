---
id: 01M59J7XTA0F2XAT6J2G5GY82G
module: infra.Model
entity: Config
kind: correction
status: active
supersedes:
- 01M59E3RSE4EHAAXN78Y1F82Q9
anchors:
- src/pmem/core/config.py#load
- src/pmem/core/config.py#Config
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 配置写错
- 配置校验
- 敏感信息正则
- ConfigError
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正：上一条 Config 记忆写的“详见 feature.Tools / Watchdog”已过时，看门狗现在是独立模块 infra.Watchdog。
server.watchdog（默认 true）和 server.request_timeout（默认 120 秒）的含义不变，配置文件读不了时看门狗照常开启。
新增：Config.load 把 config.yaml 的 YAML 语法错误、顶层不是键值对、write.secret_patterns 不是列表或含非法正则统一报 ConfigError（带具体原因）。
原因：yaml.YAMLError 不是 ValueError 子类，原先会让看门狗主进程直接崩溃；
非法正则要到写入时才抛 re.error，而且不在 _returns_errors 的捕获范围内。
