---
id: 01M5CWWXMDQF4K2P94ETXZD6R9
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes: []
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 主页和手册必须写明 Wiki 不能写出目录、嵌入地址不能随意指向远程
verify: 打开 README 已知限制和手册配置示例，能看到这两条限制
applies: 改 README、docs/pmem-guide.html 或 docs/architecture.md 里关于 Wiki 和嵌入的说明时
verified: '2026-10-23'
verified_at: '2026-10-23T21:07:40.165+08:00'
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
需求来源：用户 2026-10-20 要求提交后更新 GitHub 主页和使用手册。
必须保持：README 的已知限制、手册的命令表和配置示例、架构说明里的写入与嵌入段落，都写明两件事：Wiki 页面不能写出输出目录，wiki.dir 指到项目外时 pmem wiki 和 pmem map 返回 2、自动生成只警告；
嵌入地址只接受本机和 https://api.openai.com，其他地址要本机 PMEM_EMBED_ALLOW_REMOTE=1，OPENAI_API_KEY 只发给官方地址。
入口：README.md、docs/pmem-guide.html、docs/architecture.md。设计文档配置示例里的 base_url 注释同样写明这条限制。
