from __future__ import annotations

GENERATED = "由 pmem init 生成，重新运行 pmem init 会覆盖；如需调整请改 .memory/config.yaml"

CATEGORY_PRESETS: dict[str, dict[str, str]] = {
    "game": {
        "activity": "限时运营活动（有开始结束时间）",
        "gameplay": "核心与常驻玩法",
        "level": "关卡与难度",
        "economy": "货币、商店、奖励与数值",
        "system": "平台与商业化（登录、广告、支付、推送、埋点）",
        "infra": "技术底座（框架、UI 基础、资源、存档、网络）",
    },
    "app": {
        "feature": "面向用户的业务功能",
        "domain": "领域模型、业务规则与数据",
        "platform": "平台能力（账号、支付、推送、埋点）",
        "infra": "技术底座（框架、网络、存储、构建）",
    },
    "backend": {
        "domain": "领域与业务服务",
        "api": "接口层与对外协议",
        "integration": "外部系统集成",
        "data": "数据模型、存储与迁移",
        "infra": "技术底座（框架、部署、监控）",
    },
    "generic": {
        "feature": "业务功能",
        "infra": "技术底座",
    },
}

CONFIG_TEMPLATE = """\
# pmem 项目配置（提交到版本库，团队共用）
schema_version: 1
project:
  name: {name}
  type: {type}
vcs: auto                 # auto / git / svn / none
gate:
  mode: {gate}             # off 只靠规则 / warn 首次修改有记忆的模块时先提醒查 / block 未查不许改
  watch: []               # 为空 = 所有已登记模块的路径都受守护
  ignore: ["**/*.md", "docs/**", ".memory/**", ".cursor/**"]
  skip_markers: ["跳过记忆", "skip-memory"]
write:
  default_status: active  # active 直接生效 / draft 需审阅
  content_min: 20
  content_max: 1200
  max_per_day_per_entity: 5
embedding:
  backend: auto           # auto：装了 pmem[embed] 就用语义检索，否则关键词检索
"""

MODULES_HEADER = """\
# pmem 模块目录：模块是“业务单元”而不是目录，一个模块可以拥有多个路径。
# 首次划分：在 Cursor 里对 Agent 说“按 pmem-bootstrap 技能划分模块”。之后新增模块直接在这里加。
#
# modules:
#   gameplay.Jigsaw:
#     paths: ["Assets/Game/Jigsaw/**", "Assets/UI/JigsawPanel/**"]
#     aliases: [Puzzle]            # 别名，写入/检索时自动归一
#     entities: [Reward, Config]   # 模块内常用议题
# candidates: 冷门目录，先登记路径，有记忆写入后再转为正式模块
# third_party / ignored: 第三方 SDK、示例、生成代码，不参与闸门
"""

RULE = """\
---
description: 项目研发记忆（pmem）使用约定
alwaysApply: true
---
<!-- {generated} -->
# 项目研发记忆（pmem）

本项目用 pmem MCP 按模块（`category.Module`）沉淀研发结论，团队共享。

## 何时查
- 修改代码前，按要改的文件查一次：`search_memory(path="<文件路径>")`；同一模块一个对话查一次即可。
- 排查问题时把现象写进 `query`；不确定模块名时先 `list_modules()`。
- 返回中 `stale: true` 表示关联代码已变化，参考时需核实。

## 何时写（只在这三个时机）
1. 根因确认；2. 某个方向被排除，或方案确定；3. 改完并验证通过。

- `kind`：conclusion 结论 / exclusion 排除项 / correction 更正 / risk 风险 / decision 决定。
- 正文自包含：现象、原因、证据、影响范围；不写“改了哪个方法”这类版本库已有的信息。
- 同一任务对同一模块只留一条：再次写入时带上次返回的 `draft_id` 覆盖。
- 推翻旧结论：新写一条，`supersedes` 填旧记忆 id。
- 不写密码、密钥、个人信息。

用户说“跳过记忆”时，本对话不查也不写。
"""

BOOTSTRAP_SKILL = """\
---
name: pmem-bootstrap
description: 为项目首次划分 pmem 模块并写入 .memory/modules.yaml。用户说“划分模块”“按 pmem-bootstrap”“初始化记忆模块”时使用。
---
<!-- {generated} -->
# pmem 模块划分

目标：产出一份**业务单元**粒度的 `.memory/modules.yaml`，让每个常改的代码文件都能映射到一个模块。

## 步骤

1. 运行 `pmem scan`，阅读目录概览（代码文件数 / 近 180 天改动热度）。必要时再看具体目录内容。
2. 按下面的原则起草模块，**先以表格给用户确认**（模块、大类、路径、理由），用户确认前不写文件：
   - 模块是业务单元，不是技术层：`UI/`、`Data/`、`Net/` 这类层目录里的子目录，按业务名归到对应模块；
     同一业务散落在多个目录（如 `Game/Jigsaw`、`UI/JigsawPanel`、`Config/Jigsaw*`）合并为一个模块的多个 `paths`。
   - 粒度：近半年有改动（热度 ≥ 5）或代码量较大（≥ 30 个文件）的业务单独成模块；
     很小的技术组件折叠进一个伞形模块（如 `infra.Framework`，在 `components` 里列出子组件名）；
     零散工具类归入 `infra.Common`；冷门且很小的业务目录放进 `candidates`。
   - 第三方 SDK、插件、生成代码放进 `third_party` 或 `ignored`，不要做成模块。
   - 大类只能用 `modules.yaml` 里 `categories` 已有的；确实不合适时向用户提议调整大类，确认后再改。
   - 模块名用 PascalCase 英文；有常见别称的写进 `aliases`。
3. 写入 `.memory/modules.yaml`（保留文件头注释与 `categories`）。
4. 运行 `pmem doctor`，处理“未覆盖目录”“路径重叠”“空壳模块”，直到覆盖率 ≥ 95%。
5. 告诉用户：划分已完成，可以提交 `.memory/` 与 `.cursor/` 到版本库，团队成员安装 pmem 后即可使用。

## 注意
- 不要为了覆盖率把无关目录硬塞进模块；确实不需要守护的放进 `ignored` 并写明 `reason`。
- 一次只问用户必要的问题（例如某个目录属于哪个业务、某两个模块是否合并），最多 10 个。
"""

HOOK_EVENTS = {
    "beforeSubmitPrompt": {"command": "pmem hook prompt"},
    "preToolUse": {
        "command": "pmem hook pre-tool",
        "matcher": "Write|StrReplace|Edit|MultiEdit|EditNotebook|Delete|Shell|MCP|record_memory|search_memory",
        "failClosed": False,
    },
    "beforeMCPExecution": {"command": "pmem hook before-mcp"},
    "afterMCPExecution": {"command": "pmem hook after-mcp"},
    "afterFileEdit": {"command": "pmem hook edited"},
    "preCompact": {"command": "pmem hook compact"},
    "stop": {"command": "pmem hook stop", "loop_limit": 1},
}

MCP_SERVER = {"command": "pmem", "args": ["serve", "--root", "${workspaceFolder}"]}
