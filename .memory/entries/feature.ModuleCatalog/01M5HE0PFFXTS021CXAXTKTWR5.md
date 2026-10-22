---
id: 01M5HE0PFFXTS021CXAXTKTWR5
module: feature.ModuleCatalog
entity: AutoSync
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/catalog/autosync.py
revision: git:8d3a154
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 自动扫描平时不读提交历史：SVN 大项目读历史 37～120 秒，找新目录本身只要约 3 秒
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
决定：后台自动同步的快速扫描不读提交历史、不统计记忆，只按文件数分新模块（≥3 个）和冷候选；热度只在 full_hours 的完整扫描里算。
实测（2026-10-22，Windows，缓存热）：
- 本仓库 151 个代码文件（git）：pmem sync 合计约 0.9 秒，读历史 0.19 秒。
- TileMatch_iLar 4681 个代码文件（SVN）：遍历 1.2 秒，读记忆 1.1 秒（冷启动 10 秒），读提交历史 37 秒（冷启动 120 秒，走网络），规划 4.8 秒→通配符缓存后 2.1 秒。
- 目录指纹没变时只花遍历的 1.2 秒，有变化约 3.3 秒。
被排除的方向：固定间隔全量扫描（要么慢要么漏）；把扫描放进 Hook 同步做（每次工具调用都起 Hook，只能做毫秒级判断）。
Hook 层不能导入 catalog（分层测试），所以 Hook 只拉起 pmem sync --auto 子进程。
代价：快速扫描新增的 ≥3 文件目录一律成新模块，即使还没提交过；只追加，名字不对事后 rename。
