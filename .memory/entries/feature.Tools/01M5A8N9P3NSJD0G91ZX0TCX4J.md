---
id: 01M5A8N9P3NSJD0G91ZX0TCX4J
module: feature.Tools
entity: Record
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/secrets.py
- src/pmem/service/record.py#_reaches
- src/pmem/service/record.py#_record
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 密钥检测
- 敏感信息
- secret
- 替代成环
- 每日上限
- daily cap
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：写入校验三处收紧/修正。
1) 带 draft_id 覆盖时，若新的 supersedes 能沿替代链走回被覆盖记忆本身，返回 supersede_cycle 错误；原先会形成环，环上的记忆全部被当成已替代，检索里同时消失。
2) entity 和 aliases 也做密钥检测，原先只查正文。
3) 每日上限（同一议题每天最多写入条数）原来只要填了 supersedes 就豁免，等于可以无限刷；现在只有被替代的记忆里有仍然现行的、或带 draft_id 覆盖时才豁免。

密钥“密钥赋值”规则重写：键名允许前后缀（SECRET_KEY、DB_PASSWORD、access_token），值只认可见 ASCII；不带引号的值要含数字或不少于 16 个字符且不含点，并排除函数调用、属性访问。
踩坑：值字符集一开始写成排除 \u0080-\uffff，在忽略大小写标志下 ſ、开尔文符号会折叠成 s、k，导致普通字母被排除，几乎全部漏报；改成显式的 ASCII 正向字符集。
另一个坑：未限定 ASCII 时，冒号后面的长段中文说明会被当成密钥，连本条记忆的初稿都被拦下。

风险：不带引号、不含数字且短于 16 个字符的明文密码会漏报，可以用 write.secret_patterns 补充项目自己的规则。
