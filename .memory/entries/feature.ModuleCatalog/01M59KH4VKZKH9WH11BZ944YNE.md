---
id: 01M59KH4VKZKH9WH11BZ944YNE
module: feature.ModuleCatalog
entity: Coverage
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/catalog/coverage.py#map_files
- src/pmem/catalog/coverage.py#module_heat
- src/pmem/core/registry.py#is_module_id
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 覆盖率
- 模块热度
- 重复常量
- WILDCARD
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:14.279+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：“代码文件 → 模块”的映射和“文件热度 → 模块热度”的汇总各只留一份，在 catalog/coverage.py：map_files 返回 FileMapping（files、excluded、owner、conflicted、unmapped），module_heat 把文件热度按 modules.yaml 汇到模块（可选是否算候选模块）。
coverage_report、sync 规划、seed 选模块、report 都用它们。

registry 里的通配符正则 WILDCARD、并入标记 MERGED_PREFIX 改为公开，新增 is_module_id；migrate、sync 不再各自复制一份。

原因：原先 sync、coverage、seed、report 各写一遍遍历文件并匹配模块的循环，模块名校验和通配符正则也有两三份拷贝；改一处规则（如冲突归属、排除第三方）容易漏改其他处，各命令对同一仓库给出不同结果。

影响：行为不变，全量测试通过；sync 把冲突文件的归属记为空字符串，与原先一致。
