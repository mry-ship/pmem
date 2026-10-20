---
id: 01M5CR7BTGHAJXZEHFG2DVSVKY
module: feature.Storage
entity: DraftCommitted
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/vcs/git.py#GitVCS.is_committed
- src/pmem/storage/files.py#FilesStorage._check_draft
- src/pmem/storage/files.py#FilesStorage.read
- src/pmem/storage/files.py#FilesStorage.rewrite
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 查不出草稿是否已提交时拒绝覆盖；记忆文件读写失败给错误码而不是异常栈
verify: uv run pytest tests/test_storage.py tests/test_service.py -k "draft or invalid"
aliases:
- draft_forbidden
- 是否已提交
- storage_read
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺。
必须保持：
1) 版本库查询失败（git 命令出错、不在仓库里、svn 出错）时，“草稿是否已提交”的结果是未知（None），draft_id 覆盖按 draft_forbidden 拒绝并说明“无法确认是否已提交”。
   原先查询失败被当成“未提交”，已提交的记忆可能被悄悄改写。
2) 仓库还没有任何提交（新建仓库）时算未提交，草稿可以覆盖。
3) Hook 注入 draft_id 前也只在明确“未提交”时注入。
4) 读记忆文件出错（YAML 写错、头不是键值对、缺 id/module/entity/kind/note_date、source 不是字典）抛 StorageError，code=storage_read；
   重写失败 code=storage_write，调用方据此逐条报告，不抛异常栈。
入口：vcs 的 is_committed、FilesStorage.read / rewrite / write。
