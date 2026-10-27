---
id: 01M5Y1JERGN19VEY9KHXP17RF5
module: infra.Model
entity: Config
kind: conclusion
status: active
supersedes:
- 01M51WPKCSBNTXFWYJT8T8RXGX
- 01M5CFJH62GP7DFKH0Z5F6BJNM
- 01M5CFK2NSSX4X0ZVR3K3CZW9A
- 01M5M2WN01T1SJ5F372G1XGPSC
anchors:
- src/pmem/core/config.py#load_yaml
- src/pmem/core/config.py#Config.__init__
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: config 经 load_yaml 缓存；节类型与数值校验；resume_markers 与 spec.reminder 缺省 false
verify: 改 DEFAULTS 或 Config.__init__ 后跑 tests/core/test_config.py
---
结论：config.yaml 与 modules.yaml 统一经 core/config.py 的 load_yaml 读取；
解析结果按文件绝对路径缓存到用户缓存/pmem/parsed/，以改时间（纳秒）+ 大小判断失效，命中时不导入 yaml，缩短每次 Hook 启动。
结果须能转成 JSON 才缓存；
缓存目录跟随 PMEM_CACHE_DIR。

校验：gate/write/search/server/embedding/wiki/project/sync/spec 等节须是键值对；
数值有下限且 content_max≥content_min；
列表项写成单个字符串时当一项。
YAML 语法错、顶层非键值对、secret_patterns 非法 → ConfigError；
MCP call 捕获后返回原因。
配置读失败时看门狗仍开。

gate.resume_markers 默认 ["恢复记忆","resume-memory"]，与 skip_markers 同匹配规则；模板里是生效配置行，不是注释示例。

spec.reminder 缺省 false；磁盘没写该项的旧项目升级后不再弹规格提醒；文件里已是 true 的仍提醒。init 不回写已有 config.yaml。

modules.yaml 没写 categories 时按已登记模块与候选推断，都没有时用 feature/infra（不再回落游戏预设）。

合并自 4 条教训（2 决定 + 2 更正）。
