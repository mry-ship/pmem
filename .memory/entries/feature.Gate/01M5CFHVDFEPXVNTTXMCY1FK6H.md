---
id: 01M5CFHVDFEPXVNTTXMCY1FK6H
module: feature.Gate
entity: ShellParse
kind: correction
status: active
supersedes:
- 01M59J89XFMTC0CG2XRAQVGR7P
anchors:
- src/pmem/hooks/shell.py#_unwrap
- src/pmem/hooks/shell.py#_stages
- src/pmem/hooks/shell.py#scan
- src/pmem/hooks/memories.py#_target_modules
- src/pmem/hooks/snapshot.py#needs_snapshot
- src/pmem/hooks/state.py#_load
- src/pmem/cli/hook_cmd.py#run_hook
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: sudo/env/command 前缀和 >| 原先并未堵上，现已修复；CLI 检索提前登记已解决
verify: pytest tests/hooks/test_gate.py -k "shell_write_targets or may_change"
aliases:
- 绕过闸门
- 重定向
- sudo
- env 前缀
- 快照对比
- bypass
---
更正：旧记忆说 sudo/env/command 前缀和 >| 已堵上并有单测，核对时发现并没有：
- env 在只读白名单里，env A=1 rm src/x.py 解析不出目标、也不拍快照，直接放行；
- sudo rm、command rm 也解析不出目标，只能靠快照兜底；
- 命令先按 | 拆段，echo hi >| src/x.py 被拆坏，认不出目标。
现已修复：先去掉 sudo/doas/env（含 A=1 赋值）/command/nohup/exec/time/nice/stdbuf 前缀再识别命令（command -v 和单独的 env 仍是只读）；
拆管道时不拆 >|。
timeout、env -S 不拆前缀，按不认识的程序拍快照。
仍有效：带引号含空格的路径、&>>、-o>x 能认出，只有 stdout 重定向算丢弃；
sed -i/perl -i、cp -t、逗号分隔目标、Set-Content -Path/Out-File -FilePath 有单测；
删除整个目录时目录下所有模块都要先查过；
只剩一个待处理快照时当前命令也需要快照才借用；
状态文件损坏按默认值重建，PermissionError 重试 5 次，hook 只输出一次 JSON；
注入 draft_id 前先看草稿是否已提交。
旧记忆的“未解决”两项已解决：终端检索执行后看到输出才登记；Hook 出错会提醒用户。
