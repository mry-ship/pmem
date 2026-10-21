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
  mode: {gate}             # block 未查该模块的记忆不许改（检索成功返回才放行）/ warn 只提醒一次 / off 只靠规则
  watch: []               # 为空 = 所有已登记模块的路径都受守护
  ignore: ["**/*.md", "docs/**", ".memory/**", ".cursor/**", ".claude/**", ".codex/**", ".agents/**"]
  skip_markers: ["跳过记忆", "skip-memory"]       # 用户这样说时，本对话不查也不写（须是独立短语）
  resume_markers: ["恢复记忆", "resume-memory"]   # 误判或改主意时，说这个重新打开
  analysis_reminder: true   # 对话只查了记忆、没改代码也没写记忆时，结束时提醒一次
  read_digest: true         # Agent 读某模块的代码时，自动附上该模块的记忆摘要（每个对话每个模块一次）
  question_review: true     # 提问涉及某模块、回答前却没看过它的记忆时，回合结束让 Agent 补查并核对回答
write:
  default_status: active  # active 直接生效 / draft 需审阅
  content_min: 20
  content_max: 5000
  recommend_max: 600      # 超过只提示、不拒绝
  max_per_day_per_entity: 5
embedding:
  backend: auto           # auto：装了 pmem[embed] 就用语义检索，否则关键词检索
                          # ollama / openai 的 base_url 只接受本机和 https://api.openai.com
                          # 其他地址须在本机设置 PMEM_EMBED_ALLOW_REMOTE=1，密钥只用 PMEM_OPENAI_API_KEY
wiki:
  auto: true              # 写入或确认记忆后自动重新生成浏览用的 Wiki
  dir: .memory/wiki       # 首次生成时放一个 .gitignore 不进版本库；想提交就删掉它
server:
  watchdog: true          # MCP 服务崩溃、卡死或 pmem 升级后自动重启，Cursor 不用手动重连
  request_timeout: 120    # 单次调用超过这么多秒没响应就判定卡死并重启
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
#   gameplay.Jigsaw.Daily:         # 子模块：名字用点号续写（最多 4 段），父模块必须已登记
#     paths: ["Assets/Game/Jigsaw/Daily/**"]
#     related: [{ module: infra.Build, reason: 每日关卡随包下发 }]   # 名字看不出的深层关联
# synonyms: 同一件事的不同叫法，检索时互相展开，如 - [闪退, 崩溃, crash]（可按 pmem-normalize 技能整理）
# candidates: 冷门目录，先登记路径，有记忆写入后再转为正式模块
# third_party / ignored: 第三方 SDK、示例、生成代码，不参与闸门
"""

RULE_BODY = """\
# 项目研发记忆（pmem）

本项目用 pmem MCP 按模块（`category.Module`，子模块用点号续写，最多 4 段，如 `system.Ads.AdMob`）沉淀研发结论，团队共享。
用户说“跳过记忆”时，本对话不查也不写。

## 何时查
- 改代码前按文件查：`search_memory(path="<文件路径>")`；回答涉及某个模块的原因、方案、现状前按模块查：
  `search_memory(module=..., query="<问题要点>")`。同一模块一个对话查一次即可。
- 不确定模块名先 `list_modules()`；看模块全貌或议题演变用 `memory_graph`；问“当时的结论”给检索带 `as_of`。
- 用结果前按其中的 `*_hint` 处理：`stale` 的先对照代码，仍成立就 `confirm_memory`，不成立写 `correction`；
  `status: seed` 的种子记忆还没经负责人确认，依赖前同样先对照代码；
  改动会影响某条功能记录时先 `search_memory(ids=[...])` 取全文，那是用户要求的行为，不要当冗余代码改回去。
- pmem 的 MCP 工具不可用（没启用，或只有别的记忆服务的同名工具）时，改用终端 `pmem search --module <模块> --brief "<要点>"`
  和 `pmem record`；`pmem` 命令也找不到时，告诉用户先安装 pmem。

## 回复里的【pmem】行（各自成段，前后空一行）
- 开头先写再查：`【pmem检索】<模块>（<要点>）`；不涉及项目代码写 `【pmem检索】不涉及项目模块，未查`。
- 结尾：`【pmem查询】<模块>，用到「<记忆标题>」`（没有相关的写“没有相关记忆”）；
  `【pmem修改】<模块> 已写功能记录「<标题>」；<模块> 无需记录（<原因>）`，
  没改代码写 `【pmem修改】本轮未改代码，无新结论`（有新结论先记下）。写完记忆再结束回答，这几行齐全就不再追加提醒。
- 本对话已查过的模块沿用上次结果。以 `[pmem]` 开头的消息是自动提醒：直接处理，不要向用户确认。

## 何时写（到时机直接写，不问用户、不等提醒）
- **功能记录（改了模块就写）**：每个改过的模块一条 `feature`，同一任务带 `draft_id` 覆盖；写需求来源、必须保持的行为、
  适用条件、入口。只改测试、生成代码、配置或行为没变的改动不写；还没实现的需求写 `plan`。
- **教训（有才写）**：看代码看不出、又会让下一个人走弯路的，各写一条：被排除的方向 `exclusion`（最值钱）、
  根因或坑 `conclusion`（推翻旧结论用 `correction`）、约束和风险 `risk`、方案取舍 `decision`。
  结论写在适用的最高一层：对所有子模块都成立的写到父模块。
- 各字段怎么填见 `record_memory` 的说明（终端见 `pmem record --help`）和写入返回的 `hints`、`similar`。
- 不写密码、密钥、个人信息。
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
   - 大业务下的细分按这个梯子从低往高选，够用就停：模块内议题（`entities`）→ 组件或变体（`components`、`variants`）
     → 子模块（名字用点号续写，如 `system.Ads.AdMob`，最多 4 段；父模块必须先登记，可以只作分组、不写路径）
     → 独立模块。子模块要有自己的代码路径，且有只对它成立的教训才值得拆；
     平台（iOS/Android）、渠道、版本是适用条件，写进记忆的 `applies`，不要单独做一层，除非各自有独立的代码目录。
     跨分支的深层关联（如打包脚本与广告 SDK）在模块的 `related` 里写 `{{ module: 模块, reason: 原因 }}`。
3. 写入 `.memory/modules.yaml`（保留文件头注释与 `categories`）。
4. 运行 `pmem doctor`，处理“未覆盖目录”“路径重叠”“空壳模块”，直到覆盖率 ≥ 95%。
5. 告诉用户：划分已完成，可以提交 `.memory/` 与 pmem init 生成的 Agent 配置到版本库，团队成员安装 pmem 后即可使用。
   记忆库从空开始的头几周用处不大，建议接着说“按 pmem-seed 技能提炼种子记忆”。

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
   - 一条放不下（超过 5000 字）时，按子议题拆成 2～3 条，每条只 `--supersedes` 它覆盖的那几条旧记忆。
   - 类型：有排除项或风险且是重点时用 exclusion / risk，否则用 conclusion。
   - 写一句 `--summary`（60 字以内的现状结论）；旧记忆里有验证方法的，合并进 `--verify`。
4. 执行上一步 `pmem compact` 输出里给出的 `pmem record ... --supersedes <id> ...` 命令写入。旧记忆不会被删除，只是不再出现在检索结果里；关联代码自动继承。
5. 全部处理完后运行 `pmem doctor` 确认提示消失，并提醒用户提交 `.memory/`。
   合并错了（丢了内容、合了不该合的）：`pmem compact --undo <合并后的 id>`，原记忆重新现行，再重新合并。

## 注意
- 拿不准某条旧结论是否仍成立时，保留它并注明“待确认”，不要擅自丢弃。
- 适用条件不同的记忆不合并（如一条只在 iOS 成立、一条只在 Android 成立，或配置、版本前提不同）：
  合并会丢掉细分的约束，下一个人会在不成立的前提下套用。各自保留，或按条件拆成几条并写清 `--applies`。
- 功能记录（feature）和教训不要合并到一条里；同一功能的多条功能记录可以合并，必须保持的行为一条都不能丢。
- 不同作者的记忆也可以合并，合并后的作者是你；在正文末尾注明“合并自 N 条记忆”即可。
- 不要用 `delete` 或直接删文件。
"""

SEED_SKILL = """\
---
name: pmem-seed
description: 接入 pmem 后为常改的模块提炼种子记忆，让记忆库不从空开始。用户说“提炼种子记忆”“按 pmem-seed”“给模块补记忆”时使用。
---
<!-- {generated} -->
# pmem 种子记忆

新接入的项目记忆库是空的，头几周检索什么都查不到。这一步由你从项目已有的资料里，为最常改的模块提炼一批结论，
写成**种子记忆**（status: seed）。种子记忆立即能被检索到，标着“种子”；负责人确认后才转为正式记忆。

## 步骤

1. 运行 `pmem seed --plan`，看候选模块（按近半年改动热度排序，已有足够记忆的排在后面）。
   和用户确认这次处理哪几个模块，默认取前 5 个；用户指定了模块就只做那些。
2. 一次处理一个模块，资料按价值从高到低读：
   - 提交说明：`--plan` 输出里给了命令，重点看 fix、回滚、“改为”“兼容”“不要”这类提交；
   - 模块目录里的文档、README、设计说明，以及代码里的 `NOTE`、`HACK`、`WARNING`、“注意”“不要”“原因”注释；
   - 已有的测试名和断言（常常写明了边界条件）。
3. 每个模块提炼 10～20 条，每条一个独立结论，按议题（entity）归类：
   - 只写下一个人改这块代码前最需要知道的：为什么这样设计、试过但放弃的方向、踩过的坑、隐含的约束、边界条件；
   - 不写代码本身就能看出来的（“这个类负责 X”），不写“改了哪个方法”；
   - 每条写清依据（哪次提交、哪份文档、哪段注释），拿不准的不写，或写明“推测，待确认”；
   - `anchors` 写到函数（`路径#函数名`），`aliases` 写上现象的常用叫法。
4. 用命令行写入，正文放进 UTF-8 文件（如 `$env:TEMP/seed.md`），每条执行一次：
   `pmem record --seed --module <模块> --entity <议题> --kind <类型> --content-file <文件> --anchor <路径#函数名> --alias <叫法>`
   同一议题当天默认最多写 5 条（`.memory/config.yaml` 的 `write.max_per_day_per_entity`），超了就把相关结论合并成一条。
5. 全部写完运行 `pmem seed`，把待确认列表交给用户过目：
   - 确认的：`pmem seed --accept --module <模块>`（或逐条 `pmem seed --accept <id> ...`）；
   - 不要的：`pmem seed --reject <id> ...`（标为归档，不再出现在检索里）。
6. 提醒用户提交 `.memory/`。

## 注意
- 宁少勿错：一条错误的种子记忆会误导之后每一个查到它的人。
- 不写密码、密钥、个人信息；提交说明里出现的人名不要抄进正文。
- 不要用 `--seed` 以外的方式批量写入，也不要直接创建记忆文件。
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

CONSOLIDATE_SKILL = """\
---
name: pmem-consolidate
description: 按 pmem health 健康报告定期收口记忆库：核对过时记忆、处理互相矛盾的结论、归档、合并零碎记忆、确认种子、整理模块目录。用户说“整理记忆库”“收口记忆”“按 pmem-consolidate”，或负责人每两周例行检查时使用。
---
<!-- {generated} -->
# pmem 记忆库收口

记忆写得越多，越容易出现过时、互相矛盾、零碎重复的条目，检索质量随之下降。
这一步由你按健康报告逐节处理，目标是：检索到的每条记忆都现在成立，同一议题不自相矛盾。

## 步骤

1. 运行 `pmem health`（默认统计 60 天，可加 `--days`），用户指定了模块时只处理那些模块的条目。
   把报告里有哪些节、各多少条先告诉用户，按下面的顺序一节一节处理，每节处理完简短汇报。
2. 【疑似互相矛盾的记忆】一对一对看：`pmem search --id <id1> <id2>` 读两条全文（按 id 取不受“本对话已给过”折叠影响），
   再打开关联代码判断哪条现在成立。
   - 确实冲突：写一条 correction，`--supersedes` 填过时那条的 id，正文写清现在的结论和当初为什么会有另一种说法；
   - 两条都成立（例如一条讲选定的方案，一条讲排除的另一个方向）：`pmem confirm <较早那条的 id>`，之后不再提示。
3. 【可能过时的记忆】按模块打开 `pmem search --module <模块> --brief "<要点>"` 里标“⚠ 需核实”的条目和它列出的文件：
   - 仍成立：`pmem confirm <id> ...`；
   - 不再成立但有新结论：写 correction 替代；
   - 整件事已经不存在（功能下线、代码删除）：`pmem archive <id> ...`（可用 `--restore` 撤销）。
4. 【零碎记忆可合并】【同一模块里名字相近的议题】：按 pmem-compact 技能合并；名字相近但不是同一议题的跳过。
5. 【检索落空热点】：有现成结论的补写记忆；叫法不同的按 pmem-normalize 技能登记同义词。
6. 【待确认的种子记忆】：`pmem seed` 列出来交给用户过目，确认的 `pmem seed --accept <id> ...`，不要的 `pmem seed --reject <id> ...`。
   【改了代码却没写功能记录】：问改这些模块的人当时的需求，有用户要求的行为就补一条 feature；确实不用记的跳过。
   【建议归档】【清理待核对】：逐条看依据（✓ 满足、✗ 不满足）并打开相关代码。
   - 建议归档的：列表交给用户确认后再 `pmem archive <id> ...`，不要自己直接归档；
   - 待核对的：仍成立就 `pmem confirm <id>`，代码搬了就 `pmem anchors --rename`，不成立写 correction 替代；
     排除项、风险、更正即使代码删了也可能仍有价值（防止有人再走老路），默认保留。
7. 模块目录相关的几节，先预览、给用户确认后再加 `--apply`：
   - 【未登记模块】【疑似重复模块】：`pmem migrate merge <被并入> <保留>`；未登记模块确属新业务时，把报告建议的 paths 登记进 modules.yaml，冷候选用 `pmem sync --apply` 转正；
   - 【召回偏低】：用 `pmem search --module <模块> --entity <议题> --brief` 看从没返回的议题，常问却查不到的补 aliases 或按 pmem-normalize 登记同义词；议题太杂的给用户看 `pmem migrate split <模块> --by entity --to <新模块>=<议题>[,<议题>]` 的预览；
   - 【记忆还在旧模块名下】：`pmem migrate tidy`；
   - 【父子模块结构】：兄弟模块重复的教训，对所有下级都成立就在父模块写一条、`--supersedes` 填各下级那几条的 id；
     只有一个下级、自己又没有路径和记忆的父模块，按报告给的命令合并；缺父模块的在 modules.yaml 登记它；
     旧的 `parent` 字段按报告给的 `pmem migrate rename` 改成点号名字；`pmem sync` 提议的子模块确认后用它给出的 split 命令拆；
   - 【没有归属模块的代码目录】：`pmem sync` 预览新模块和要追加的路径；
   - 一个模块管得太宽、需要拆开时：`pmem migrate split <模块> --to <新模块>=<路径>`，预览里列出的“跨模块”“无法判断”的记忆用 `--assign <id>=<模块>` 指定去向；
   - 个别记忆写错了模块：`pmem migrate move <id> ... --to <模块>`；
   - 代码文件或目录改名、函数搬到别的文件后，大批记忆标“需核实”且提示文件不存在：`pmem anchors --rename <旧路径>=<新路径>`（也可写 `路径#函数名`）改写关联代码，再逐条核对后 confirm。
8. 全部处理完再跑一次 `pmem health`，确认处理过的节已消失，提醒用户提交 `.memory/`。

## 注意
- 拿不准哪条成立时不要擅自改，列出来问负责人；一次最多问 10 个问题。
- 只用 pmem 命令修改记忆，不要直接改或删 `.memory/entries/` 下的文件。
- 不写密码、密钥、个人信息。
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

CURSOR_HOOKS = {
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


def _agent_hooks(agent: str, pre_matcher: str, post_matcher: str, extra: dict | None = None) -> dict:
    def handler(event: str) -> list[dict]:
        return [{"type": "command", "command": f"pmem hook {event} --agent {agent}", "timeout": 30, **(extra or {})}]

    return {
        "UserPromptSubmit": [{"hooks": handler("prompt")}],
        "PreToolUse": [{"matcher": pre_matcher, "hooks": handler("pre-tool")}],
        "PostToolUse": [{"matcher": post_matcher, "hooks": handler("post-tool")}],
        "PreCompact": [{"hooks": handler("compact")}],
        "Stop": [{"hooks": handler("stop")}],
    }


# Windows 上 Claude Code 另有 PowerShell 工具；没装 Git Bash 时 Hook 起不来默认会拦下工具，
# onFailure: continue 让 pmem 没装好时照常放行（不认这个字段的旧版 Claude Code 直接忽略）
CLAUDE_HOOKS = _agent_hooks(
    "claude",
    "^(Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell|mcp__pmem__.*)$",
    "^(Write|Edit|MultiEdit|NotebookEdit|Read|Grep|Glob|Bash|PowerShell|mcp__pmem__.*)$",
    {"onFailure": "continue"},
)
CODEX_HOOKS = _agent_hooks("codex", "^(Bash|apply_patch|mcp__pmem__.*)$", "^(Bash|apply_patch|mcp__pmem__.*)$")
CODEX_MCP_TOML = '[mcp_servers.pmem]\ncommand = "pmem"\nargs = ["serve"]\n'
