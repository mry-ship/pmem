---
id: 01M5KVZVB70S67YDST1C2RM2GG
module: feature.Spec
entity: ArtSection
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#_skeleton
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 规格固定四节；无画面的美术节写一句，不拿它卡首稿
applies: 给模块规格加画面说明时
aliases:
- 美术设计
- 无画面
verified: '2026-10-23'
verified_at: '2026-10-23T20:59:19.874+08:00'
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
用户确认（2026-10-23）：有画面的模块要单独有美术设计，规格才够拿去重做；不带画面的项目可以不写美术正文。
选定：四节标题都在骨架里，顺序是策划、美术、程序、现状。
美术节不放 spec:empty。
--check 仍只看程序和现状有没有写完。
无画面写成「本模块无画面」。
有画面写风格、布局、各状态的画面、动效、资源规格；
看不到的完整说明留 spec:design-gap。
图片和模型本身不放进这一份 markdown。
没把美术并进策划里的「表现」：表现是规则，美术是画面。也没让缺美术节的模块过不了 --check，否则命令行这类模块会被判未完成。
