---
id: 01M59E3RSE4EHAAXN78Y1F82Q9
module: infra.Model
entity: Config
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/config.py#DEFAULTS
revision: git:21d24e9
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 看门狗配置
- request_timeout
---
决定：配置新增 server.watchdog（默认 true）和 server.request_timeout（默认 120 秒），供 MCP 看门狗使用（详见 feature.Tools / Watchdog）。
已接入的项目不用改配置：读取时与默认值合并；
pmem init 生成的 config.yaml 模板也写上这两项和注释。
request_timeout 不是数字时按 120 秒处理，配置文件读不了时看门狗照常开启。
