---
id: 01M4Z6PF0W0JKGVBCR03Z5RC3S
module: feature.Metrics
entity: Citation
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py
revision: git:f2062ca
author: 1002378395@qq.com
note_date: '2026-10-15'
verified: '2026-10-16'
---
更正：收益报告里的“记忆被采用”曾经严重虚高。本仓库报告显示 12/13（92%），但被判为采用的 12 条全是同一对话里 Agent 自己刚写的记忆：写完后又被检索出来、在回复中复述，被算成了“复用”。

原因：原先靠写入事件里的对话 id 排除“本对话自己写的”，但终端里 `pmem record` 写入的事件不带对话 id（之前闸门还漏识别 `uv run --extra embed pmem record` 这种写法），所以一条也没排除掉。

处理：按记忆文件判断，不再依赖事件日志。本机作者在对话进行期间（首尾各放宽 60 秒）新建的记忆，不计入该对话的返回、采用和对话对照。修正后本仓库为 5/5，剩下的都是 Hook 接入前写的。

同时新增“记忆使用”统计，同一对话只算一次：
- 最常被用到的记忆；
- 在能判定采用的对话里返回 3 次以上却从没被用到的记忆，可能过时、写得不清楚或归错模块；
- 统计期之前写、期内一次都没被检索到的条数，检索少于 20 次时不显示。

局限：数据只来自本机事件日志，团队层面的使用情况需要各人分别看报告。
