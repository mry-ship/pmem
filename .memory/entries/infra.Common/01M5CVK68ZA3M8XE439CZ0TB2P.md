---
id: 01M5CVK68ZA3M8XE439CZ0TB2P
module: infra.Common
entity: ConcurrentEdits
kind: risk
status: active
supersedes: []
anchors: []
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 另一个对话恢复检查点会把本对话改过的文件一起改回；同一文件别混用脚本和编辑工具写
scope: project
verify: 改完用脚本按标记字符串清点本对话改动是否都在；测试数和上次对比
aliases:
- 改动丢失
- 文件被回退
- 检查点恢复
- checkpoint
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
风险一：2026-10-20 21:47 本仓库约 25 个文件被整体改回旧内容（规则精简、--to 示例、命令行测试等都丢了），当时另一个 Cursor 对话也在改同一仓库，文件修改时间集中在同一秒，符合在其中一个对话里恢复检查点。
恢复只看文件，不分是哪个对话改的。
处理：发现测试突然不过、已改的内容不见时，先用 Get-ChildItem 按修改时间找同一秒被写的文件，再用标记字符串清点本对话的改动逐个补回；不要马上重改，也不要凭记忆判断是否已完成。多个对话同时改一个仓库时尽早提交。
风险二：同一个文件先用终端脚本改、再用编辑工具（StrReplace）改，编辑工具可能拿着脚本改之前的内容写回，脚本的改动悄悄丢失（main.py 的 type=int 替换就这样丢了，测试才发现）。
同一文件只用一种方式改；
批量替换用编辑工具的 replace_all。
