---
id: 01M5CFK2NSSX4X0ZVR3K3CZW9A
module: infra.Model
entity: Config
kind: correction
status: active
supersedes:
- 01M59J7XTA0F2XAT6J2G5GY82G
anchors:
- src/pmem/core/config.py#load
- src/pmem/core/config.py#Config
- src/pmem/server/app.py#call
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 配置写错统一报 ConfigError；MCP 调用返回“改好再调用即可”
aliases:
- 配置写错
- 配置校验
- 敏感信息正则
- ConfigError
---
更正：看门狗是独立模块 infra.Watchdog；server.watchdog（默认 true）和 server.request_timeout（默认 120 秒）含义不变，配置文件读不了时看门狗照常开启。
Config.load 把 config.yaml 的 YAML 语法错误、顶层不是键值对、write.secret_patterns 不是列表或含非法正则统一报 ConfigError（带具体原因）；
MCP 的 call 单独捕获 ConfigError，返回原因并提示改好再调用即可。
原因：yaml.YAMLError 不是 ValueError 子类，原先会让看门狗主进程崩溃；
非法正则要到写入时才抛 re.error，不在 returns_errors 的捕获范围内（旧记忆写的 _returns_errors 已改名为 returns_errors）。
