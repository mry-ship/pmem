---
id: 01M5EP7RHFHGS1Q7NZ6NA51E3B
module: feature.Onboarding
entity: Hierarchy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 规则和技能模板写明多段模块名、结论写在最高一层、细分梯子；平台渠道不单独成层
verify: uv run pytest tests/test_feature_records.py tests/test_module_hierarchy.py
applies: pmem init 生成的规则、技能和 modules.yaml 文件头
aliases:
- 规则模板
- 技能模板
- 子模块划分
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块设计第四阶段。
必须保持的行为：
- RULE_BODY：模块格式写“子模块用点号续写，最多 4 段”；教训一条后加“结论写在适用的最高一层”。总长仍须 <1400 字（tests/test_feature_records.py），现约 1256。
- pmem-bootstrap 技能：细分梯子 议题 → 组件/变体 → 子模块 → 独立模块；父模块先登记、可只作分组；平台、渠道、版本写进 applies，除非有独立代码目录；深层关联写 related。
- pmem-consolidate 技能：处理 health 的“父子模块结构”一节和 sync 提议的子模块。
- modules.yaml 文件头注释加了子模块和 related 示例。
- doctor：有多段模块时提示团队升级 pmem。
已接入项目要重跑 pmem init 才拿到新规则和技能；本仓库已重新生成。
入口：src/pmem/generate/templates.py、cli/doctor_cmd.py。
