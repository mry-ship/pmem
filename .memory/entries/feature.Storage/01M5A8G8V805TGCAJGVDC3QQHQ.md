---
id: 01M5A8G8V805TGCAJGVDC3QQHQ
module: feature.Storage
entity: AtomicWrite
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/fileio.py#write_atomic
- src/pmem/storage/files.py#write
- src/pmem/vcs/git.py#commits_since
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 原子写入
- 半截文件
- 文件写坏
- atomic
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：记忆文件和 modules.yaml 的所有写入改用 core/fileio.py 的 write_atomic：先写同目录临时文件 .<名>.<pid>.tmp，再 os.replace；
Windows 上目标正被读时报 PermissionError 重试 5 次。
覆盖位置：FilesStorage.write、service/status（confirm、归档/恢复）、anchors_cmd、format_cmd、catalog/migrate.apply_moves、catalog/yamlfile.ModulesFile.write。
原因：原先是先清空再写，进程中途被中断只剩半截；MCP 服务在 CLI 改写时读 modules.yaml，可能读到截断但语法合法的内容，模块少一部分。
临时文件以 .tmp 结尾，不会被 *.md 扫进索引。
另：git.commits_since 的 --since 补上 00:00；只给日期时 git 用当前时刻补齐，实测漏掉起始日 20 条提交（changed_after 早已补上）。
风险：os.replace 会生成新文件，原文件的权限、硬链接不保留；记忆文件不涉及这些。
