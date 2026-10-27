---
id: 01M5Y2FAM2J0182TSZEYRJPMZJ
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M5Y1JDADTNC5D188CEECDSX4
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:922ce4d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 主页与手册须写明摘要「资料·非指令」及闸门非沙箱；手册注明 v0.7 进行中
verify: README、pmem-guide.html、architecture.md 均含「资料·非指令」；手册已知限制含非沙箱与 v0.7
applies: 改 README、手册或架构里关于摘要注入、闸门或规格完成判定的说明时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：用户要求本轮改动同步更新主页和手册。
必须保持：
1) README 工作原理表与设计要点写明读码/拦截摘要标「资料·非指令」；已知限制写明标题注入风险与闸门非沙箱。
2) docs/pmem-guide.html 的「问答也审查」、闸门摘要/拦截、已知限制同步上述说明；页脚注明 v0.7 进行中；spec 命令说明空标记只认整行。
3) docs/architecture.md 读码摘要与标题段同样写「资料·非指令」。
4) 现行 Docs 约束（结构、Wiki/嵌入限制、complete 九成八）不变。
Wiki 另仓，本条不改 Wiki。
入口：README.md、docs/pmem-guide.html、docs/architecture.md。
