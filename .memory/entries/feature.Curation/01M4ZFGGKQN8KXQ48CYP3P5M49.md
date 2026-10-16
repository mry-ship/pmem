---
id: 01M4ZFGGKQN8KXQ48CYP3P5M49
module: feature.Curation
entity: Anchors
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/cli/anchors_cmd.py
revision: git:fc9f6d8
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 锚点
- 关联代码
- 第三方
- 误关联
---
结论：pmem anchors 能为导入的旧记忆自动补上关联代码（锚点），但必须跳过第三方目录，否则会误关联。

TileMatch 导入的 855 条记忆全都没有 anchors，所以“使用前按代码核对”对它们不起作用。

初版：从正文里提到的文件名和“类名.成员”解析出唯一文件，270 条记忆得到 425 处锚点。
但其中“Menu.close”“Initialize”这类常见名字，被解析到 com.unity.uiextensions、Spine 等第三方代码里（TileMatch 的 modules.yaml 没有登记 third_party，也没有模块路径，无法靠注册表排除）。

修正：遍历文件时跳过 scan 用的第三方目录名单（THIRD_PARTY_NAMES：Plugins、Spine、各种 SDK……）和以 com. 开头的内嵌 UPM 包。
之后 256 条记忆得到 401 处锚点，约 90% 落在 GameMain/MonopolyGame/TileMatch/Jigsaw 四个业务脚本目录。
全量扫描约 4.5 秒。

数据文件（.asset/.prefab/.json）只在正文明确写出文件名时才关联，共 28 处。默认只预览，确认后用 --apply 写回，再提交 .memory/。
