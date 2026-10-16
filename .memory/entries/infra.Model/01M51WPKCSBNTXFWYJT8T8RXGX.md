---
id: 01M51WPKCSBNTXFWYJT8T8RXGX
module: infra.Model
entity: Config
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/config.py#load_yaml
- src/pmem/core/registry.py#ModuleRegistry.load
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 配置缓存
- 解析缓存
- parsed
- yaml导入
---
决定：config.yaml、modules.yaml 统一经 core/config.py 的 load_yaml 读取，解析结果按“文件绝对路径”存到 <用户缓存>/pmem/parsed/<哈希>.json，以文件修改时间（纳秒）+ 大小判断是否失效；命中时不导入 yaml。原因：yaml 导入约 28 毫秒，是 Hook 进程启动里最大的一块，而每次工具调用都要起一次 Hook。Entry 的 YAML 头解析也改为用到时才导入 yaml。
注意：解析结果必须能转成 JSON 才会缓存（含日期等非 JSON 类型时直接不缓存，保持原语义）；缓存目录跟随 PMEM_CACHE_DIR。测试的 conftest 已把 PMEM_CACHE_DIR 指向每个用例的临时目录，避免测试往真实缓存目录写文件。
