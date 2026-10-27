---
id: 01M52HS37DKEM2KENXAF8CAJW6
module: feature.Onboarding
entity: Scan
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/scan/lite.py#skip_dir
- src/pmem/scan/lite.py#iter_code_files
- src/pmem/scan/files.py#FileIndex
revision: git:5003560
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 忽略目录
- 语言适配器
- 覆盖率
- vendor
- 构建产物
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:14.279+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：语言适配不再做独立适配器，只在 scan/lite.py 的跳过目录里补常见依赖与构建产物：vendor（Go/PHP）、Pods/Carthage/DerivedData（iOS）、TestResults（.NET）、site-packages 与 *.egg-info（Python）；target、bin、obj、__pycache__、venv、.gradle 原本就有。判断统一走 skip_dir()（名单、点开头、后缀），pmem anchors 也改为复用它，另加 Unity 的 Packages 和 com.* 内嵌包。

原因：扫描已改为通用轻量扫描、由 Agent 划分模块，各语言唯一的差别是哪些目录不是业务代码；漏掉时 doctor/health 把依赖代码算成未覆盖，覆盖率偏低，bootstrap 时还会把它们当模块候选。

风险：真叫 vendor 的业务目录会被跳过（覆盖率和扫描都看不到）；没加 packages（小写），因为 JS monorepo 的 packages/ 是业务代码，.NET 的 NuGet packages 目录需要项目自己写进 modules.yaml 的 third_party。
