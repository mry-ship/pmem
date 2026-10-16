---
id: 01M51WQ1HAX8QZH4XGKYCJCMRR
module: feature.ModuleCatalog
entity: Loading
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#ModuleRegistry.load
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 模块表缓存
- modules.yaml缓存
---
决定：ModuleRegistry.load 改经 core/config.py 的 load_yaml 读取 modules.yaml，解析结果按修改时间+大小缓存为 JSON（<用户缓存>/pmem/parsed/），Hook 进程命中时不必导入 yaml。
编码与格式错误的提示不变：非 UTF-8 仍报“不是 UTF-8 编码”，YAML 格式错误仍报第几行；
其他异常照常抛出。
手工改 modules.yaml 后修改时间变化即失效，无需清缓存。
