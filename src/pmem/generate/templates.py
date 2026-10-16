from __future__ import annotations

import json

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
  mode: {gate}             # block 未查该模块的记忆不许改（尝试过检索即放行）/ warn 只提醒一次 / off 只靠规则
  watch: []               # 为空 = 所有已登记模块的路径都受守护
  ignore: ["**/*.md", "docs/**", ".memory/**", ".cursor/**"]
  skip_markers: ["跳过记忆", "skip-memory"]       # 用户这样说时，本对话不查也不写（须是独立短语）
  resume_markers: ["恢复记忆", "resume-memory"]   # 误判或改主意时，说这个重新打开
  analysis_reminder: true   # 对话只查了记忆、没改代码也没写记忆时，结束时提醒一次
  read_digest: true         # Agent 读某模块的代码时，自动附上该模块的记忆摘要（每个对话每个模块一次）
  question_review: true     # 提问涉及某模块、回答前却没看过它的记忆时，回合结束让 Agent 补查并核对回答
write:
  default_status: active  # active 直接生效 / draft 需审阅
  content_min: 20
  content_max: 1200
  recommend_max: 600      # 超过只提示、不拒绝
  max_per_day_per_entity: 5
embedding:
  backend: auto           # auto：装了 pmem[embed] 就用语义检索，否则关键词检索
wiki:
  auto: true              # 写入或确认记忆后自动重新生成浏览用的 Wiki
  dir: .memory/wiki       # 首次生成时放一个 .gitignore 不进版本库；想提交就删掉它
"""

MODULES_HEADER = """\
# pmem 模块目录：模块是“业务单元”而不是目录，一个模块可以拥有多个路径。
# 首次划分：对 Agent 说“按 pmem-bootstrap 技能划分模块”。之后新增模块直接在这里加。
#
# modules:
#   gameplay.Jigsaw:
#     paths: ["Assets/Game/Jigsaw/**", "Assets/UI/JigsawPanel/**"]
#     aliases: [Puzzle]            # 别名，写入/检索时自动归一
#     entities: [Reward, Config]   # 模块内常用议题
# synonyms: 同一件事的不同叫法，检索时互相展开，如 - [闪退, 崩溃, crash]（可按 pmem-normalize 技能整理）
# candidates: 冷门目录，先登记路径，有记忆写入后再转为正式模块
# third_party / ignored: 第三方 SDK、示例、生成代码，不参与闸门
"""

RULE_BODY = """\
# 项目研发记忆（pmem）

本项目用 pmem MCP 按模块（`category.Module`）沉淀研发结论，团队共享。

## 何时查
- 修改代码前，按要改的文件查一次：`search_memory(path="<文件路径>")`；同一模块一个对话查一次即可。
- 回答涉及某个模块的问题（原因、方案、现状）前，同样先查：`search_memory(module=..., query="<问题要点>")`。
- 排查问题时把现象写进 `query`；不确定模块名时先 `list_modules()`。
- 想一次看清模块全貌（各议题的现行结论）：`memory_graph(module=...)`。
- 想知道一个议题怎么演变、和哪些模块相关：`memory_graph(module=..., entity=...)`；
  问“当时的结论”时给 `search_memory` 带 `as_of="YYYY-MM-DD"`。
- 这些工具必须来自 pmem 服务。pmem 的 MCP 工具不可用（没启用，或只有别的记忆服务的同名工具）时，
  改在终端运行 `pmem search --module <模块> --brief "<要点>"`，写入用 `pmem record`；
  `pmem` 命令也找不到时，告诉用户先安装 pmem，否则记忆检查和闸门都不会生效。

## 用之前核对
- `stale: true` 表示记忆写下（或上次核对）之后，关联代码又改过或已不存在，`check` 里列出了具体文件。
- 依赖这类记忆前先打开关联代码核对：仍然成立就调用 `confirm_memory(ids=[...])` 刷新核对日期；
  已不成立就写一条 `correction`，`supersedes` 填旧记忆 id。

## 何时写（只在这三个时机）
1. 根因确认；2. 某个方向被排除，或方案确定；3. 改完并验证通过。

- 到了时机就直接写，不问用户、不等结束提醒。本轮改了哪些模块的代码，结束回答前每个模块写一条
  （为什么这样改、影响范围、风险）；只有纯格式化、改错别字这类改动可以不写。
- `kind`：conclusion 结论 / exclusion 排除项 / correction 更正 / risk 风险 / decision 决定。
- 正文自包含：现象、原因、证据、影响范围；不写“改了哪个方法”这类版本库已有的信息。
- `aliases` 填现象和关键术语的其他常用叫法（如 `["闪退", "崩溃", "crash"]`），以后换个说法也能搜到。
- `anchors` 尽量写到函数：`路径#函数名`。只写文件时，该文件以后任何改动都会让这条记忆标为“需核实”。
- 写入返回的 `similar` 是同模块最相近的已有记忆：新结论与其中某条重复或推翻了它，就带 `draft_id` 重写、
  `supersedes` 填那条的 id；无关则忽略。
- 同一任务对同一模块只留一条：再次写入时带上次返回的 `draft_id` 覆盖。
- 不写密码、密钥、个人信息。

用户说“跳过记忆”时，本对话不查也不写。
"""

RULE = """\
---
description: 项目研发记忆（pmem）使用约定
alwaysApply: true
---
<!-- {generated} -->
""" + RULE_BODY.replace("{", "{{").replace("}", "}}")

BLOCK_BEGIN = "<!-- pmem:begin -->"
BLOCK_END = "<!-- pmem:end -->"
RULE_BLOCK = (
    f"{BLOCK_BEGIN}\n<!-- 本段由 pmem init 生成，重新运行会覆盖本段；本段之外的内容不受影响 -->\n"
    f"{RULE_BODY}{BLOCK_END}\n"
)

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
5. 告诉用户：划分已完成，可以提交 `.memory/` 与 pmem init 生成的 Agent 配置到版本库，团队成员安装 pmem 后即可使用。

## 注意
- 不要为了覆盖率把无关目录硬塞进模块；确实不需要守护的放进 `ignored` 并写明 `reason`。
- 一次只问用户必要的问题（例如某个目录属于哪个业务、某两个模块是否合并），最多 10 个。
"""

COMPACT_SKILL = """\
---
name: pmem-compact
description: 把同一议题下积累的多条零碎 pmem 记忆合并成一条。用户说“合并记忆”“整理记忆”“按 pmem-compact”，或 pmem doctor 提示有议题可合并时使用。
---
<!-- {generated} -->
# pmem 记忆合并

同一议题陆续写了很多条记忆（常见于一个功能连续迭代几天），检索时它们互相挤占名额，读起来也像流水账。
合并的目标：下一个人只读一条，就知道这个议题**现在**成立的结论、排除过的方向和要注意的风险。

## 步骤

1. 运行 `pmem compact`，列出可合并的议题（默认每个至少 5 条）。用户指定了模块时加 `--module <模块>`。
2. 逐个议题处理，一次一个：运行 `pmem compact --module <模块> --entity <议题>` 读全部正文（从旧到新）。
3. 起草合并后的正文，写进 UTF-8 文件（如 `$env:TEMP/merged.md`）：
   - 只保留现在仍成立的内容；后来被推翻或修正的，只写最终结论，必要时一句话说明“曾以为 X，实为 Y”。
   - 保留原因、证据、排除过的方向和风险；删掉“改了哪个方法”“编译 0 错误”这类版本库已有或无长期价值的信息。
   - 现象写上常用的不同叫法，方便以后搜到。
   - 一条放不下（超过 1200 字）时，按子议题拆成 2～3 条，每条只 `--supersedes` 它覆盖的那几条旧记忆。
   - 类型：有排除项或风险且是重点时用 exclusion / risk，否则用 conclusion。
4. 执行上一步 `pmem compact` 输出里给出的 `pmem record ... --supersedes <id> ...` 命令写入。旧记忆不会被删除，只是不再出现在检索结果里；关联代码自动继承。
5. 全部处理完后运行 `pmem doctor` 确认提示消失，并提醒用户提交 `.memory/`。

## 注意
- 拿不准某条旧结论是否仍成立时，保留它并注明“待确认”，不要擅自丢弃。
- 不同作者的记忆也可以合并，合并后的作者是你；在正文末尾注明“合并自 N 条记忆”即可。
- 不要用 `delete` 或直接删文件。
"""

NORMALIZE_SKILL = """\
---
name: pmem-normalize
description: 整理 pmem 记忆里同一件事的不同叫法（如闪退/崩溃、红点/小圆点），登记为同义词组，让换个说法也能搜到。用户说“整理同义词”“按 pmem-normalize”，或发现换个叫法搜不到记忆时使用。
---
<!-- {generated} -->
# pmem 同义叫法整理

检索主要靠字面匹配：“闪退”搜不到只写了“崩溃”的记忆。这一步由你来做规整：找出项目里同一概念的不同叫法，
登记成同义词组。之后检索时会自动互相展开，已有记忆不用改写。

## 步骤

1. 运行 `pmem terms`（可加 `--module <模块>`），读高频词表：词、出现在几条记忆里、所在模块。
2. 找出指同一件事的不同叫法，按组起草，例如 `[闪退, 崩溃, crash]`、`[红点, 小圆点]`、`[首充, 破冰]`：
   - 只合并可以互换的说法；只是相关或有包含关系的（如“广告”和“激励视频”）不要放一组；
   - 项目内部叫法、通用叫法、中英文叫法都算；
   - 拿不准的问用户，一次最多问 10 组。
3. 以表格给用户确认后，写进 `.memory/modules.yaml` 的 `synonyms`，每组一行，如 `- [闪退, 崩溃, crash]`。
4. 用 `pmem search "<其中一个叫法>"` 验证能搜到只写了另一个叫法的记忆。
5. 提醒用户提交 `.memory/modules.yaml`。

## 注意
- 新记忆写入时用 `aliases` 带上常用叫法，pmem 会把它们并入检索展开；本技能主要补历史记忆。
- 不要改写或删除已有记忆的正文。
"""

HOOK_WRAPPER = ".memory/bin/pmem-hook"
# 新对话开始时经包装脚本调用：本机没装 pmem 时，其他 Hook 都起不来、静默放行，只有这里能告诉 Agent
MISSING_PMEM = (
    "[pmem] 本机找不到 pmem 命令：本项目的研发记忆检查和改代码前的闸门都没有生效。"
    "请在这次回复里先告诉用户：按项目 README 安装 pmem（需要 uv），装好后重启 Cursor。"
)
# Windows 下 Cursor 经 PowerShell 转发 Hook 输出，只用 ASCII
_MISSING_JSON = json.dumps({"additional_context": MISSING_PMEM}, ensure_ascii=True)

HOOK_WRAPPER_SH = f"""\
#!/bin/sh
# {GENERATED}
# Hook 入口：装了 pmem 就交给它；没装时给出提醒，而不是让 Hook 报错后静默放行。
if command -v pmem >/dev/null 2>&1; then
  exec pmem hook "$@"
fi
case "$1" in
  session) printf '%s' '{_MISSING_JSON}' ;;
  pre-tool) printf '%s' '{{"permission":"allow"}}' ;;
  prompt) printf '%s' '{{"continue":true}}' ;;
  *) printf '%s' '{{}}' ;;
esac
"""

HOOK_WRAPPER_CMD = f"""\
@echo off
rem Hook entry generated by pmem init: run pmem when installed, otherwise tell the agent instead of failing silently.
where pmem >nul 2>nul
if not errorlevel 1 (
  call pmem hook %*
  exit /b
)
if /i "%~1"=="session" goto session
if /i "%~1"=="pre-tool" goto allow
if /i "%~1"=="prompt" goto continue
echo {{}}
exit /b 0
:session
echo {_MISSING_JSON}
exit /b 0
:allow
echo {{"permission":"allow"}}
exit /b 0
:continue
echo {{"continue":true}}
exit /b 0
"""

HOOK_EVENTS = {
    "sessionStart": {"command": f"{HOOK_WRAPPER} session"},
    "beforeSubmitPrompt": {"command": "pmem hook prompt"},
    "preToolUse": {
        "command": "pmem hook pre-tool",
        "matcher": "Write|StrReplace|Edit|MultiEdit|EditNotebook|Delete|Shell|MCP|record_memory|search_memory",
        "failClosed": False,
    },
    "afterMCPExecution": {"command": "pmem hook after-mcp"},
    "afterFileEdit": {"command": "pmem hook edited"},
    "postToolUse": {"command": "pmem hook post-tool", "matcher": "Read|Grep|Glob|SemanticSearch|codebase_search|Shell"},
    "preCompact": {"command": "pmem hook compact"},
    "stop": {"command": "pmem hook stop", "loop_limit": 1},
}

MCP_SERVER = {"command": "pmem", "args": ["serve", "--root", "${workspaceFolder}"]}
# Claude Code / Codex 启动 MCP 时工作目录就是项目（Claude Code 另有 CLAUDE_PROJECT_DIR），无需 --root
PLAIN_MCP_SERVER = {"command": "pmem", "args": ["serve"]}


def _agent_hooks(agent: str, pre_matcher: str, post_matcher: str) -> dict:
    def handler(event: str) -> list[dict]:
        return [{"type": "command", "command": f"pmem hook {event} --agent {agent}", "timeout": 30}]

    return {
        "UserPromptSubmit": [{"hooks": handler("prompt")}],
        "PreToolUse": [{"matcher": pre_matcher, "hooks": handler("pre-tool")}],
        "PostToolUse": [{"matcher": post_matcher, "hooks": handler("post-tool")}],
        "PreCompact": [{"hooks": handler("compact")}],
        "Stop": [{"hooks": handler("stop")}],
    }


CLAUDE_HOOKS = _agent_hooks(
    "claude",
    "^(Write|Edit|MultiEdit|NotebookEdit|Bash|mcp__pmem__.*)$",
    "^(Write|Edit|MultiEdit|NotebookEdit|Read|Grep|Glob|Bash|mcp__pmem__.*)$",
)
CODEX_HOOKS = _agent_hooks("codex", "^(Bash|apply_patch|mcp__pmem__.*)$", "^(Bash|apply_patch|mcp__pmem__.*)$")
CODEX_MCP_TOML = '[mcp_servers.pmem]\ncommand = "pmem"\nargs = ["serve"]\n'
