---
id: 01M59YEJ1V04ZV6R8QSRZKCNS1
module: feature.ModuleCatalog
entity: Loading
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#RegistryError
- src/pmem/core/registry.py#resolve_module
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 错误码
- 模块名有误
- error code
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：RegistryError 增加 code 属性，供写入拒绝统计归类：解析模块名时的空名、未知、歧义、不合法为 module_invalid，未知大类为 category_unknown；
其余（modules.yaml 编码、格式、结构、merged_into 成环、路径重叠）默认 modules_yaml。
原因：健康报告原先靠匹配“模块”“大类”等中文字样归类，modules.yaml 有误也会被算成“模块名有误”，改提示措辞还会让统计失效。
影响：提示文字和抛出位置不变；新增 raise RegistryError 时默认归为 modules_yaml，属于用户写错模块名的要显式传 module_invalid。
