# pmem：面向项目与团队的 AI 研发记忆系统 · 设计文档

- 状态：设计稿，待评审
- 日期：2026-10-14
- 产品名：`pmem`（暂定，发布前再定）
- 来源：在《AI 研发记忆系统 · 模式指南》（TileMatch 自用版）和其参考实现（`TileMatch_iLar/tools/dev-memory`、`.cursor/hooks/*`）基础上产品化

---

## 1. 背景与目标

### 1.1 背景

参考实现是作者在一个手游项目里自用的外接记忆：Python MCP 服务 + LanceDB + Ollama 嵌入 + Cursor 规则 + Hooks 闸门。6 周数据表明模式有效（所查模块有 30 条以上记忆时回退率约降到 1/3，被纠正率一上线就降一半以上），但它是**单人、单项目、手工配置**的：

- 项目名写死在环境变量、服务名、工具说明、Hooks 路径与提示、模块扫描脚本里；
- 记忆存在个人机器的向量库里，团队无法共享，换嵌入模型会丢数据；
- 接入时没有模块划分流程，库从空开始，头两周几乎无效；
- 读代码发现若干缺陷（见附录 A），其中几条直接导致命中率低和写入静默丢失。

### 1.2 目标

把这套模式做成**别人能引入自己项目使用**的产品：

1. **通用**：任何项目类型（游戏、App、后端、工具）、任何语言，项目特有信息只存在项目配置里。
2. **适合团队**：v0.1 面向 1–20 人团队，记忆随仓库共享；为大团队的中心服务预留存储接口。
3. **适合 Cursor**：规则 + MCP + Hooks + 项目技能，团队成员拉下代码、装一次工具即可用。
4. **可持续**：接入时有一套初始化划分流程；日常有同步、健康报告、收口与迁移工具，模块体系能长期演化而不乱。
5. **零额外大模型费用**：工具本身不调用任何大模型 API；需要判断的步骤交给引入方自己的 Cursor Agent。

### 1.3 非目标（v0.1 不做）

- 中心服务后端、权限、看板（v0.4+）
- 自动从对话中用大模型抽取事实（Mem0/Zep 式）
- 非 Cursor IDE 的专门适配（MCP 工具本身通用，规则/Hooks 只生成 Cursor 版）
- 面向终端用户的“个人偏好记忆”

### 1.4 已确定的决策

| 决策 | 结论 |
|---|---|
| 版本控制 | Git 与 SVN 都支持 |
| 第一版规模 | 小/中团队：仓库文件 + 本地索引；存储接口为中心服务预留 |
| 记忆是否进仓库 | 可以，所有有仓库权限的人可见 |
| 实现语言 | Python（`uv tool install` / `pipx` 分发） |
| 验证项目 | 自建小型合成仓库（自动化测试）+ 一个开源项目（真实验证）；不在 TileMatch 上首发 |

---

## 2. 用户与使用旅程

### 2.1 角色

| 角色 | 频率 | 做什么 | 目标耗时 |
|---|---|---|---|
| 引入者（技术负责人） | 接入时一次 | 安装、`pmem init`、确认模块划分、提交 | 1–2 小时 |
| 日常使用者 | 每天 | 装一次工具，之后正常用 Cursor | 首次 5 分钟，之后无感 |
| 模块负责人 | 每 1–2 周 | 看健康报告、确认合并与登记 | 每次约 30 分钟 |

**设计底线：日常使用者几乎什么都不用做。**

### 2.2 引入者旅程

```text
uv tool install pmem
cd <repo>
pmem init                       # 问答 → 生成配置骨架
pmem scan                       # 确定性扫描 → 模块草案 + 待决清单
# 在 Cursor 里："按记忆初始化流程划分模块"   ← 项目技能 pmem-bootstrap
pmem doctor                     # 覆盖率与自检，必须全绿
# 可选，在 Cursor 里："为热点模块提炼种子记忆"  ← 项目技能 pmem-seed
提交 .memory/ 与 .cursor/ 下的生成文件
把生成的《团队接入说明》贴给成员
```

### 2.3 日常使用者旅程

```text
uv tool install pmem            # 一次
拉取代码 → 打开 Cursor → 启用项目 MCP 服务（Cursor 提示时确认）
有问题时：pmem doctor
```

### 2.4 模块负责人旅程

```text
pmem health                     # 健康报告
# 在 Cursor 里："按收口流程处理本周报告"      ← 项目技能 pmem-consolidate
pmem migrate ...                # 改名 / 合并 / 拆分 / 废弃
pmem sync                       # 新目录 → 新模块候选（只追加）
```

---

## 3. 总体架构

### 3.1 三层划分

| 层 | 归属 | 内容 | 是否进版本控制 |
|---|---|---|---|
| 通用引擎 | pmem 包 | CLI、MCP 服务、存储、索引、扫描器、Hooks 逻辑、模板 | 否（安装的包） |
| 项目配置与数据 | 引入方仓库 `.memory/` | `config.yaml`、`modules.yaml`、`entries/` | 是 |
| 生成文件 | 引入方仓库 `.cursor/` 等 | 规则、`hooks.json`、`mcp.json`、项目技能、启动包装脚本 | 是 |

**硬约束：通用引擎代码里不得出现任何具体项目的名字、路径或模块。**

### 3.2 分工原则

- **CLI 做确定性的事**：扫描、校验、建索引、生成文件、迁移、报告。
- **Cursor Agent 做判断性的事**：模块划分、种子记忆提炼、重复合并建议。通过随包生成的项目技能执行，使用引入方自己的模型额度。

### 3.3 组件关系

```text
Cursor
 ├─ 规则文件（始终加载）       —— 何时查、何时写、怎么写
 ├─ Hooks → pmem hook <事件>   —— 闸门、本对话状态、草稿注入
 ├─ MCP → pmem serve           —— search_memory / record_memory / list_modules
 └─ 项目技能                   —— bootstrap / seed / consolidate

pmem serve（看门狗：崩溃 / 超时 / 代码更新时重启子进程并重新握手，连接不断）
 └─ pmem serve --worker
 ├─ ModuleRegistry   ← .memory/modules.yaml（别名归一、路径→模块）
 ├─ Storage(接口)    ← FilesStorage: .memory/entries/**.md   （将来 RemoteStorage）
 ├─ Index            ← 用户缓存目录 SQLite（向量 + trigram 全文）
 ├─ Embedder(接口)   ← onnx（默认）/ ollama / openai 兼容
 └─ VCS(接口)        ← git / svn / none
```

### 3.4 关键原则：MCP 服务不知道当前对话

MCP 服务拿不到对话 id。**所有“本对话”相关的逻辑只放在 Hooks 里**（是否已检索某模块、改过哪些模块、本对话的草稿 id、是否“跳过记忆”）。Hooks 通过 `preToolUse` 的 `updated_input` 把需要的信息注入到 MCP 调用参数中（见 8.2、9.2；是否生效需按 13.2 实测）。

---

## 4. 数据模型

### 4.1 目录布局（引入方仓库）

```text
.memory/
  config.yaml
  modules.yaml
  entries/
    <category>.<Module>/
      <ULID>.md
  bootstrap/                # 初始化中间产物，可提交也可忽略
    scan-report.json
    decisions.md
  bin/
    pmem-hook               # 启动包装脚本（POSIX）
    pmem-hook.cmd           # 启动包装脚本（Windows）
```

### 4.2 记忆文件格式

一条记忆一个 Markdown 文件，YAML 头 + 正文：

```markdown
---
id: 01JA7K3M2X9F4Q8W6ZB1C2D3E4
module: gameplay.Jigsaw
entity: Reward
kind: exclusion
status: active
supersedes: [01J9ZZ0000000000000000000A]
anchors:
  - Assets/Game/Jigsaw/JigsawReward.cs#Grant
revision: "git:3f2a9c1"
author: zhangsan
note_date: 2026-10-14
source:
  conversation: 2635c1a0-46e1-46fa-b833-1fab18bc2a1a
---
排除：奖励重复发放不是网络重试导致的……
```

| 字段 | 必填 | 谁填 | 约束 |
|---|---|---|---|
| `id` | 是 | 服务端 | ULID，按时间可排序，同时是文件名 |
| `module` | 是 | AI | 写入时按别名归一为标准写法 |
| `entity` | 是 | AI | 别名归一；比较不区分大小写，存标准写法 |
| `kind` | 是 | AI | `conclusion` / `exclusion` / `correction` / `risk` / `decision` |
| `status` | 是 | 服务端 | `draft` / `seed` / `active` / `archived`；“已被替代”由索引推算，不写入文件 |
| `supersedes` | 否 | AI | 被本条推翻的记忆 id 列表 |
| `anchors` | 否 | AI | `相对路径` 或 `相对路径#符号` |
| `revision` | 是 | 服务端 | `git:<短哈希>` / `svn:r<号>` / `none` |
| `author` | 是 | 服务端 | 见 6.2 |
| `note_date` | 是 | 服务端 | 写入当天，`YYYY-MM-DD` |
| `source.conversation` | 否 | Hook 注入 | 用于“同一批”判定与追溯 |
| 正文 | 是 | AI | 默认 100–5000 字，建议 200–600 字 |

### 4.3 不可变原则

- 记忆文件**写入后不再修改**，唯一例外：
  1. 同一对话内覆盖**本人尚未提交**的草稿（`draft_id` 覆盖，见 8.2）；
  2. 负责人通过 CLI 归档（`status: archived`）。
- 推翻旧结论 = 新建一条并在 `supersedes` 里写旧 id；旧文件不动。
- 这样 Git 与 SVN 下都几乎不会产生合并冲突（每个文件名唯一，且基本只增不改）。

### 4.4 `config.yaml`

```yaml
schema_version: 1
project:
  name: my-game                 # 仅用于展示与缓存目录区分
  type: game                    # game / app / backend / generic（只在 pmem init 时决定大类预设）
vcs: auto                       # auto / git / svn / none
svn_auto_add: true              # SVN 下写入新记忆时自动 svn add
embedding:
  backend: auto                 # auto / onnx / ollama / openai / none
  model: ""                     # 留空用内置默认模型
  model_path: ""                # 离线环境可指定本地模型目录
  base_url: ""                  # 只接受本机和 https://api.openai.com；其他地址要本机 PMEM_EMBED_ALLOW_REMOTE=1
gate:
  mode: block                   # off / warn / block
  watch: ["Assets/Game/**", "src/**"]   # 留空表示全部代码
  ignore: ["**/*.md", "docs/**", ".memory/**", ".cursor/**"]
  skip_markers: ["跳过记忆", "skip-memory"]
  resume_markers: ["恢复记忆", "resume-memory"]
write:
  default_status: active        # active（小团队）/ draft（需审阅）
  content_min: 20
  content_max: 5000
  max_per_day_per_entity: 5     # 超出时拒绝并要求合并，不静默删除
  secret_patterns: []           # 内置规则总是生效；这里追加项目自己的正则
search:
  limit: 5
  max_per_batch: 2
  recency_half_life_days: 90
```

完整配置项与默认值以 `src/pmem/core/config.py` 的 `DEFAULTS` 和手册 `docs/pmem-guide.html` 为准；取值写错时所有命令统一报 `ConfigError`。

### 4.5 `modules.yaml`

> 完整结构以《模块目录结构与接入初始化划分》（`2026-10-14-pmem-modules-bootstrap-design.md`）第 2 节为准，下面是精简示意。

```yaml
schema_version: 1
categories:
  system:   { label: 平台与商业化, include: "...", exclude: "..." }
  activity: { label: 限时运营活动, include: "...", exclude: "..." }
  gameplay: { label: 核心与常驻玩法 }
  level:    { label: 关卡与难度 }
  economy:  { label: 货币与数值 }
  infra:    { label: 技术底座 }
decision_order: [activity, gameplay, level, economy, system, infra]
boundaries:
  - "广告接入与策略 → system.Ads；看广告领奖励的数值 → economy.Rewards"
entities:                       # 全局标准词表 + 别名
  Config: [config, settings, 开关, 配置]
  Flow: [flow, 流程, 状态机]
  Reward: [reward, 奖励]
modules:
  gameplay.Jigsaw:
    paths: ["Assets/Game/Jigsaw/**", "Config/Jigsaw*.json"]
    owners: [zhangsan]
    aliases: [Puzzle, activity.Jigsaw]
    entities: [Config, Flow, Reward, Balance]
    status: active              # active / deprecated / merged_into:<module>
```

规则：

- 大类在初始化确认后冻结；新增大类只能通过 `pmem migrate` 并经负责人确认。
- 模块名与议题名比较不区分大小写，存储用标准写法。
- 路径重叠时“更具体的路径优先”；同等具体时报错，必须人工解决。

---

## 5. 存储与索引

### 5.1 存储接口

```python
class Storage(Protocol):
    def write(self, entry: Entry, draft_id: str | None) -> WriteResult: ...
    def get(self, entry_id: str) -> Entry | None: ...
    def iter_all(self) -> Iterable[Entry]: ...
    def changes_since(self, cursor: str | None) -> tuple[list[Change], str]: ...
    def archive(self, entry_id: str, by: str) -> None: ...
```

v0.1 只实现 `FilesStorage`（`.memory/entries/**.md`）；v0.4 增加 `RemoteStorage`，工具接口、文件格式、模块目录不变。

### 5.2 索引

- 位置：`<用户缓存目录>/pmem/<仓库路径哈希>/<嵌入模型标识>/index.db`，不进版本控制。
- 引擎：SQLite（WAL 模式）。
  - `entries` 表：元信息 + 文件路径、修改时间、内容哈希；
  - `vectors` 表：向量（BLOB）；检索时把目标模块的向量载入 numpy 暴力计算；
  - `fts` 虚表：FTS5 trigram 分词，支持中文关键词。
- 模块隔离为**逻辑过滤**（按 `module` 列），不再一个模块一张物理表；这也彻底避开表名大小写在不同操作系统上不一致的问题。
- “已被替代”集合 = 所有 `active`/`seed` 记忆的 `supersedes` 并集，建索引时推算。

### 5.3 增量更新

- 不依赖版本控制的 Hook（`svn update` 没有可靠的客户端 Hook）。
- 每次检索前做增量检查（节流：同一进程 10 秒内最多一次）：遍历 `entries/` 比对修改时间与内容哈希，只为变化的文件重算向量。
- 本地未提交的记忆同样进索引，作者立即受益。
- 多个 Cursor 窗口各起一个服务进程：SQLite WAL + 重建时文件锁。

### 5.4 嵌入后端

| 后端 | 用途 | 说明 |
|---|---|---|
| `onnx`（默认） | 进程内推理 | 无常驻服务；首次下载模型；支持 `model_path` 离线 |
| `ollama` | 已有 Ollama 的团队 | 兼容参考实现 |
| `openai` | 兼容 OpenAI 接口的嵌入服务 | 内网自建服务 |

- 默认模型须为**多语言/中文友好的小模型**（约 100 MB 量级）。具体型号用评测集对比后确定（见 13.3）。参考实现使用的 `nomic-embed-text` 以英文为主，不作为中文项目默认。
- 嵌入不可用时**退化为纯关键词检索**，返回中注明 `degraded: keyword_only`，不报错。

---

## 6. 版本控制适配

### 6.1 接口

```python
class VCS(Protocol):
    def detect(self, root: Path) -> bool: ...
    def revision(self) -> str: ...                 # "git:3f2a9c1" / "svn:r48213"
    def current_user(self) -> str | None: ...
    def is_uncommitted(self, path: Path) -> bool: ...
    def add(self, path: Path) -> None: ...         # SVN 下纳入版本控制
    def churn(self, since_days: int) -> dict[str, ChurnStat]: ...   # 扫描器用
```

### 6.2 差异处理

| 事项 | Git | SVN |
|---|---|---|
| 代码版本 | 当前提交短哈希 | 工作副本修订号 |
| 作者 | `git config user.name` | 配置项 `PMEM_AUTHOR` → 系统用户名（SVN 无可靠的“当前用户”） |
| 新文件纳入版本控制 | 由开发者提交时处理 | `svn_auto_add: true` 时写入即 `svn add` |
| 未提交判定（草稿覆盖） | `git status` 未跟踪或已修改 | `svn status` 为 `?` 或 `A` |
| 审阅 | 正常合并请求 | 无合并请求：小团队直接生效 + 健康报告兜底；可选 CI 校验格式 |
| 修改热度 | `git log --numstat` | `svn log -v`（按路径计数） |

都检测不到时为 `none`：版本号记 `none`，不支持草稿覆盖的“未提交”判定（退化为同一对话内允许覆盖）。

---

## 7. MCP 工具接口（给 AI 用）

只暴露 3 个工具。删除、全量列出、迁移只在 CLI 中提供，**不暴露给 AI**。

### 7.1 `search_memory`

| 参数 | 说明 |
|---|---|
| `module` | `category.Module`；与 `path` 二选一 |
| `path` | 文件路径，服务端按 `paths` 映射为模块 |
| `entity` | 可选；别名归一、不区分大小写 |
| `query` | 可选；关键词或自然语言 |
| `limit` | 默认 5，上限 10 |

返回（紧凑 JSON）：

```json
{"ok":true,"module":"gameplay.Jigsaw","resolved_from":"path","fallback":"module",
 "items":[{"id":"01JA...","entity":"Reward","kind":"exclusion","date":"2026-10-14",
           "author":"zhangsan","stale":false,"content":"..."}],
 "degraded":null}
```

- 模块不存在：`items: []`、`module_exists: false`、`similar_modules`，不建模块。
- 指定议题无结果：**真正退回整模块检索**，并标 `fallback: "module"`。

### 7.2 排序规则（初始值，按评测集调参）

```text
rel     = 0.6 * vec_sim_norm + 0.4 * bm25_norm        # 无嵌入时 rel = bm25_norm
bonus   = 0.15 * entity_match + 0.05 * (kind in {exclusion, correction})
recency = 0.5 ** (age_days / recency_half_life_days)
score   = (rel + bonus) * (0.7 + 0.3 * recency)
```

- 默认排除已被替代与已归档的记忆。
- 多样性：同一批（同 `source.conversation`；缺失时为同作者 + 同模块 + 90 分钟窗口）前 `max_per_batch` 条按原位置排，超出的降到其他相关结果（关键词命中或锚点挨着）之后、不相关的之前。
- 对返回的每条记忆校验 `anchors`：文件不存在，或文件里找不到符号名 → `stale: true`。

### 7.3 `record_memory`

| 参数 | 说明 |
|---|---|
| `module`、`entity`、`kind`、`content` | 必填 |
| `supersedes` | 可选，推翻的旧记忆 id |
| `anchors` | 可选，相关代码位置 |
| `draft_id` | 可选；通常由 Hook 自动注入 |
| `source_conversation` | 可选；由 Hook 自动注入 |

服务端行为：

1. 归一化模块与议题；大类不存在 → 报错并列出允许的大类。
2. 校验字数；敏感信息扫描命中 → 拒绝并指出命中片段的位置。
3. 同模块 + 议题 + 当天已达上限 → **拒绝**，返回当天已有记忆的 id，要求带 `draft_id` 合并。
4. 带 `draft_id` 且该文件为本人未提交 → 覆盖；否则拒绝并提示改用 `supersedes` 新建。
5. 写文件；SVN 且 `svn_auto_add` → `svn add`；更新索引。
6. 新模块 → 照常写入，返回 `new_module: true` 与 `similar_modules`。
7. 返回 `warnings` 数组，任何非致命问题都明确告知 AI。

### 7.4 `list_modules`

- 参数：`category` 可选。
- 每个模块返回：名字、条数、前 10 个已用议题、别名、是否登记。
- 不显示既无记忆也未登记的模块；登记但为空的模块合并为一行计数，节省 token。

---

## 8. 写入与检索的行为约定（规则文件内容要点）

### 8.1 何时写

只在三个时机写，且一个任务一个模块只保留一条（后续写入覆盖草稿）：

1. 根因确认；
2. 方向被排除，或方案确定；
3. 改完并验证通过。

只描述“改了哪个方法”的不写（交给版本控制）。

### 8.2 草稿覆盖

- 由 Hook 在 `record_memory` 调用前注入 `draft_id`（本对话已在该模块写过、且文件未提交）。
- 如果实测 `updated_input` 对 MCP 工具无效，退回方案：写入返回中带 `draft_id`，规则要求 AI 在同一任务的后续写入中携带。

### 8.3 何时查

- 改受守护代码前，按文件所属模块查一次；一个对话通常 1–3 次。
- 新对话的第一次检索，议题留空，关键词放进 `query`。
- 上下文压缩后、切换到新模块时重新查。

---

## 9. 闸门（Hooks）

### 9.1 生成的 `hooks.json`（示意）

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [{ "command": ".memory/bin/pmem-hook session" }],
    "beforeSubmitPrompt": [{ "command": "pmem hook prompt" }],
    "preToolUse": [{
      "command": "pmem hook pre-tool",
      "matcher": "Write|StrReplace|Edit|MultiEdit|EditNotebook|Delete|Shell|MCP|record_memory|search_memory",
      "failClosed": false
    }],
    "afterMCPExecution": [{ "command": "pmem hook after-mcp" }],
    "afterFileEdit": [{ "command": "pmem hook edited" }],
    "postToolUse": [{ "command": "pmem hook post-tool", "matcher": "Read|Grep|Glob|SemanticSearch|codebase_search|Shell" }],
    "preCompact": [{ "command": "pmem hook compact" }],
    "stop": [{ "command": "pmem hook stop", "loop_limit": 1 }]
  }
}
```

只有 sessionStart 经 `.memory/bin/pmem-hook` 包装脚本（没装 pmem 时提醒用户安装），其余直接调用 `pmem hook <事件>`。
以 `src/pmem/generate/templates.py` 的 `CURSOR_HOOKS` 为准；Claude Code、Codex 的配置见同文件。

### 9.2 各事件行为

| 事件 | 行为 |
|---|---|
| `beforeSubmitPrompt` | 用户原话含跳过标记 → 本对话 `skip=true` |
| `preToolUse` 改文件 | 路径不在 `watch` 或在 `ignore` → 放行。否则算出模块；本对话未检索该模块且未跳过 → 按 `gate.mode`：`warn` 放行并给 `agent_message`，`block` 拒绝。提示中给出准确的 `search_memory(module="...")` |
| `preToolUse` 终端命令 | 识别明显写文件的模式（重定向、`Set-Content`、`Out-File`、`sed -i`、`tee` 等）并提取路径，同上处理；无法提取路径则放行 |
| `preToolUse` `record_memory` | 注入 `draft_id`（满足 8.2 条件时）与 `source_conversation` |
| `afterMCPExecution` | 仅当返回 `ok:true`：检索 → 记录已检索模块；写入 → 记录模块与记忆 id |
| `afterFileEdit` | 记录本对话改过的模块 |
| `preCompact` | 清空已检索模块集合 |
| `stop` | 改过但未写记忆的模块 → 追加一次提醒并点名模块；其他情况不提醒 |

### 9.3 本对话状态

- 位置：`<用户缓存目录>/pmem/<仓库路径哈希>/sessions/<对话id>.json`，7 天过期清理。
- 内容：`searched_modules`、`edited_modules`、`written`（模块 → 记忆 id）、`skip`、`compacted_at`。
- 拿不到对话 id：不写共享状态；`block` 档降级为放行 + 提醒。

### 9.4 兜底

- Hook 自身异常：放行，写错误日志；`pmem doctor` 展示最近错误。
- 启动包装脚本找不到 `pmem`：输出提示“请安装 pmem”（作为 `agent_message`/`user_message`），而不是静默放行。

### 9.5 力度档位与推广建议

| 档位 | 行为 | 建议使用时机 |
|---|---|---|
| `off` | 只有规则文件 | 试用观察 |
| `warn`（新项目默认） | 放行 + 提醒 AI 先查 | 前两周 |
| `block` | 未检索则拒绝修改 | 库攒起来、团队习惯后 |

---

## 10. 接入初始化流程

> 扫描流水线、目录角色判定、粒度门槛、待决清单与提问预算的细化设计见《模块目录结构与接入初始化划分》（`2026-10-14-pmem-modules-bootstrap-design.md`）第 3–6 节，以该文档为准。

### 10.1 第 0 步：项目画像（`pmem init` 问答）

不再问答：项目类型和闸门力度用参数给出（`--type game --gate warn`），其余由扫描和 `pmem-bootstrap` 技能决定；`--agents` 选择要接入的 Agent（cursor、claude、codex、all、auto）。

### 10.2 第 1 步：确定性扫描

通用信号：

- 目录树（默认深度 4）、各目录文件数与代码行数；
- 文档目录、配置表目录；
- 近 6 个月修改热度与主要作者（VCS 适配器）。

语言/引擎适配器（v0.1：Unity、Node；v0.2：Java、.NET、Go、Python）：

| 适配器 | 边界信号 |
|---|---|
| Unity | `*.asmdef`、命名空间、`Assets/` 下业务目录 |
| Node | 工作区配置（`workspaces`、`pnpm-workspace.yaml`）、各包 `package.json` |

内置处理：

- **默认忽略**：`node_modules`、`Library`、`Temp`、`Plugins`、`ThirdParty`、`vendor`、`Generated`、`dist`、`build` 等。
- **容器目录穿透**：`Framework`、`Core`、`Common`、`Base`、`Runtime`、`Editor`、`Scripts`、`src`、`lib`、`app`、`packages` 等只作为容器，向下一层找业务单元。

输出 `.memory/bootstrap/scan-report.json`：

```json
{"candidates":[{"path":"Assets/Game/Jigsaw","name":"Jigsaw","adapter":"unity",
  "signals":{"files":84,"loc":12034,"churn_6m":312,"authors":["zhangsan","lisi"],
             "has_config":true,"has_docs":false,"asmdef":"Game.Jigsaw"},
  "container":false}]}
```

### 10.3 第 2 步：划分草案（技能 `pmem-bootstrap`，由 Cursor Agent 执行）

- 输入：扫描报告、大类预设、判定顺序模板。
- 产出：`modules.yaml` 草案（含 `paths`、`aliases`、`entities`、负责人候选）与 `.memory/bootstrap/decisions.md`（争议清单）。
- 粒度目标：大类 4–8 个；初始模块 15–40 个；每个模块必须有 `paths`；预计少于 5 条记忆的候选降为议题。

### 10.4 第 3 步：人工确认

技能引导 Agent 每次只问一个争议项；结束时冻结大类，写入 3–5 条 `boundaries`。

### 10.5 第 4 步：覆盖率校验（`pmem doctor`）

- 每个受守护文件恰好映射到一个模块，或被 `ignore`；
- 路径重叠按“更具体优先”，同等具体时报错；
- 业务代码覆盖率目标 ≥ 95%；不达标不能完成初始化。

### 10.6 第 5 步：种子记忆（可选，技能 `pmem-seed`）

- 按修改热度取前 5–10 个模块；
- Agent 从文档、提交说明、关键代码注释中，为每个模块提炼 10–20 条，`status: seed`；
- 引入者确认后转为 `active`（`pmem seed --accept`）。

### 10.7 第 6 步：生成接入文件

- `.cursor/rules/pmem.mdc`（约 1k token：协议、大类表每类 2–3 个示例、写入规范）
- `.cursor/hooks.json`、`.cursor/mcp.json`
- `.cursor/skills/pmem-bootstrap|pmem-seed|pmem-consolidate/SKILL.md`
- `.memory/bin/pmem-hook`、`.memory/bin/pmem-hook.cmd`
- 每个生成文件头部写明“由 pmem 生成，请勿手改”与 `schema_version`

`.cursor/mcp.json`（示意）：

```json
{ "mcpServers": { "pmem": { "command": "pmem", "args": ["serve"] } } }
```

`pmem serve` 从当前工作目录向上查找 `.memory/config.yaml` 定位仓库根（是否可用 `${workspaceFolder}` 变量待实测）。

### 10.8 第 7 步：团队接入说明

生成一段可直接贴给成员的说明：安装命令、启用 MCP、`pmem doctor`。

---

## 11. 日常维护

| 命令 | 作用 |
|---|---|
| `pmem doctor` | 自检覆盖率、接入状态、可合并议题等；接入后约每 24 小时后台巡检一次，有问题才提一行；只检查、不改库 |
| `pmem sync` | 重新扫描，列出新目录与新模块候选；只追加，不改已有名字；`--apply` 才写入（细则见模块与初始化设计文档第 7.1 节） |
| `pmem health` | 健康报告：未登记模块、疑似重复模块、检索落空热点（模块 × 议题）、无归属新目录、可能过时的记忆、60 天无人检索的模块、被拒绝的写入统计等 |
| `pmem report` | 收益报告：闸门拦截、检索与采用、对话内重复等（本机统计） |
| `pmem migrate rename A B` | 改名，旧名自动成为别名 |
| `pmem migrate merge A B` | A 的路径、别名等并入 B，A 标为 `merged_into:B`，记忆文件随之搬到 B；默认只预览，`--apply` 才写 |
| `pmem migrate split A --to B=路径 [--by path\|entity] [--assign id=模块]` | 拆分，按路径或议题重新分配；记忆按关联代码的新归属分配，判断不了的留在 A 并列出 |
| `pmem migrate deprecate A` | 废弃：只读，拒绝新写入 |
| `pmem archive <id>` | 负责人归档单条记忆 |
| `pmem reindex` | 删除并重建本地索引 |
| `pmem import --lancedb <路径>` | 从参考实现的 LanceDB 库导入 |
| `pmem init` | 升级 pmem 后重新运行，更新规则、技能和 Hooks（已有的 config.yaml、modules.yaml 不覆盖）。首次生成配置时在终端询问是否开启规格提醒，直接回车保持关闭；没有终端时不询问 |
| `pmem spec` | 模块规格目录 `.memory/specs/`：不加参数列出完成情况，`init` 为缺文件的模块写骨架（不覆盖已写正文），`complete` 是补全入口（铺骨架并列出首稿未完成的模块，有未完成时返回 1，正文仍由技能写到九成八；`fill` 是旧名），`index` 刷新目录和文首事实，留空列标出策划或美术仍留空以及旧稿缺节，`--check` 有未完成首稿时返回 1。策划、美术、程序、现状由 `pmem-spec` 技能写；无画面的美术节写「本模块无画面」，不计入未完成。`pmem init`、`sync --apply` 和自动登记写入新模块时也补骨架。规格提醒默认不提示（`spec.reminder` 缺省 false）。`spec.dir` 指到项目外时返回 2 |

### 11.1 本地统计

服务端在用户缓存目录记录（不进仓库、不上传）：每次检索的模块、议题、是否命中、是否退回；每次写入的结果与拒绝原因。`pmem report` 基于它生成。

### 11.2 收口节奏

- 小团队：一人每两周看一次报告，约 30 分钟。
- 中团队：各模块负责人处理自己模块，每周一次。

---

## 12. 定死与可配置

| 定死（模式核心） | 可配置 |
|---|---|
| 三级地址：大类.模块 + 议题 | 大类、模块、路径、负责人、别名、议题词表 |
| 记忆文件不可变；更正靠新建 + `supersedes` | 字数与条数上限、检索条数、时间衰减 |
| 改代码前先查的闸门机制 | 闸门力度、受守护路径、跳过标记 |
| 记忆类型五分类 | 嵌入后端与模型 |
| AI 不能删除记忆 | 规则语言、默认写入状态 |

---

## 13. 质量保障

### 13.1 测试

- 单元测试（pytest）：别名归一、路径映射与重叠判定、替代关系推算、排序与多样性、写入校验（上限拒绝、草稿覆盖条件、敏感信息）、增量索引。
- 合成样例仓库（测试中生成）：Unity 风格、Node 单仓多包；分别初始化为 Git 与 SVN 工作副本（本机无 `svn` 时跳过 SVN 用例）。
- Hook 契约测试：录制真实 Cursor Hook 输入作为测试数据。
- 检索评测集：问题 → 期望命中的记忆 id，计算前 5 条召回率，用于调参与选模型。
- 三系统 CI：Windows / macOS / Linux。

### 13.2 必须先实测的 Cursor 行为（v0.1 第一项任务）

1. 各事件输入里对话 id 的字段名；`preToolUse` 对 MCP 工具的输入结构。
2. `preToolUse` 返回 `updated_input` 对 MCP 工具参数是否生效。
3. MCP 工具的 matcher 写法（`MCP:...`）。
4. `beforeSubmitPrompt`、`preCompact`、`afterFileEdit` 的输入字段。
5. Windows 下 Hook 命令由哪种 shell 执行，`.cmd` 包装是否需要。
6. 项目级 `.cursor/mcp.json` 的工作目录与变量支持。

`pmem doctor` 需检测 Hook 是否真的被触发（例如写入心跳文件），格式变化时明确报错而非静默失效。

### 13.3 嵌入模型选型

用合成评测集 +（经作者同意后）参考实现已有记忆的离线副本，对比 2–3 个多语言小模型的前 5 条召回率、体积与速度，选定默认模型。

### 13.4 安全

- 写入前敏感信息扫描（密钥、令牌、私钥、口令赋值等）。
- 记忆进仓库后所有有权限者可见，规则与文档中明确说明。

---

## 14. 版本规划

| 版本 | 范围 |
|---|---|
| v0.1 | `init`（通用扫描 + Unity/Node 适配）、带路径与别名的模块目录、文件存储 + SQLite 混合索引、3 个 MCP 工具、闸门全套事件、Git/SVN 适配、`doctor`、`reindex`、`import --lancedb`、bootstrap 技能 |
| v0.2 | 已完成：`pmem-seed` 技能与 `pmem seed`、健康报告 `pmem health`（`pmem report` 已用作收益报告）、`migrate rename/merge/deprecate/tidy`、`archive`（记归档日期、原状态与归档人）、代码锚点过时校验（按函数）；`pmem sync`（只追加）、`migrate split`；consolidate 做成 `pmem-consolidate` 技能（按健康报告逐节收口，合并与同义词仍交给 `pmem-compact`、`pmem-normalize`），健康报告增加“疑似互相矛盾的记忆”；语言适配器因扫描改为通用轻量扫描、由 Agent 划分模块，只补充了 Go/PHP、iOS、.NET、Python 的依赖与构建目录 |
| v0.3 | 记忆质量与上下文效率：写入策略改为“有教训才写”、对话内去重、一行标题、全项目级坑、验证方法、验收度量，详见 14.2 |
| v0.3.1 | 写得全、找得准：功能记录（改了模块就写）与教训分层检索、模块教训汇总、适用条件、规划需求、免记录文件、合并不跨条件，详见 14.3 |
| v0.3.2 | 看得见、可验收：记忆图 `pmem map`（演化过程 + 漏记、断链、悬而未决、过期自检）、合并回滚、跳过复查、严格的清理候选，详见 14.4 |
| v0.4+ | 治理闭环与团队化：自动新建模块的转正提示、召回审计建议（已实现）；团队汇总（导出文件进仓库，不搭服务）、`RemoteStorage` 中心服务、身份与权限、审计、看板（长期搁置）。以后评估：模块依赖/调用关系，详见 14.5 |
| v0.5 | 父子模块与回复格式：模块名用点号续写最多 4 段，父子关系由名字表达；查子模块带上级教训、查父模块附各下级最新记忆标题；手工 `related`；改名级联、sync 提议拆子模块、health“父子模块结构”；回复用【pmem检索】【pmem查询】【pmem修改】行，结尾声明过的模块不再追加提醒；正文上限 5000 字；安装包版本号从此与路线对齐（0.5.0）。设计见 `2026-10-21-pmem-module-hierarchy-design.md` |
| v0.5.1 | 新模块自动登记：Hook 在改到没登记的代码目录时立即、会话开始时按 `sync.interval_minutes` 拉起后台 `pmem sync --auto`；目录指纹没变就跳过，平时不读提交历史，每 `sync.full_hours` 做一次完整扫描；`sync.auto` 默认 `apply` 只追加，正文有注释时退回提醒；结果写明新增数量，`pmem sync --history` 看最近 20 次；路径匹配缓存编译结果（大项目规划 4.8 → 2.1 秒） |
| v0.6 | 已完成（安装包 0.6.0），模块规格：与 Wiki 平级，每个已登记模块一份可提交的当前文档（策划设计、美术设计、程序设计、模块现状）。无画面的美术节写「本模块无画面」；有画面的写下风格、布局、状态、动效和资源规格。单拿一份就能在别处重做该模块。旧模块先按代码写首稿，策划和美术只记录代码或资源里看得到的部分；之后在改动的那一轮更新一次，不整篇覆盖、不定时重扫、不做记忆过期核对。规格提醒默认不提示。设计见 `2026-10-23-pmem-module-spec-design.md` |
| v0.7 | 计划，类型安全与规则化（2026-10-23 从 v0.6 顺延，范围不变）：反复出现的机械教训由健康报告提示写成规则（静态分析、类型、技能参数校验），记忆用 `enforced_by` 标明“已由规则保障”并随规则文件核对；项目声明 `facets` 后记忆可写带类型的适用条件 `when`、检索按条件过滤；`config.yaml`、`modules.yaml`、记忆文件头、Hook 数据统一边界校验（Hook 只用标准库）；MCP 返回契约与 pyright 检查。设计见 `2026-10-21-pmem-typesafe-design.md`，Issue #15 |

### 14.1 v0.1 验收标准

- 在合成仓库与选定开源项目上，`init` 全流程 1 小时内完成，覆盖率 ≥ 95%；
- Windows 与 macOS 上 `pmem doctor` 全绿；
- 写入零静默丢失（所有拒绝都有明确返回）；
- 闸门三档行为与 13.2 实测结论一致，契约测试通过；
- 检索评测集前 5 条召回率达到设定目标（基线由 13.3 确定）。

### 14.2 v0.3 任务：记忆质量与上下文效率

目标：记忆越积累，AI 越准（少犯同样的错）、越快（老问题不用从头排查）、越省 token。

v0.2 末本仓库的实测基线（2026-10-19）：

- 现行 147 条记忆中决定占 65%，排除项、风险、更正三类合计 16%（排除项仅 2 条）；96 个议题里 62 个只有 1 条。
- 检索返回 312 条只被采用 60 条（19%，字面重合下限）。
- 带对话 id 的 82 次检索返回 357 条，其中 144 条（40%）是同一对话里已经返回过的。
- 对话输入 token 中位数约 3400 万，97% 是缓存读；记忆文本只占约一成，省 token 的大头在“少读代码、少试错”，不在压缩记忆文本。
- `core/quality.py` 的变更记录检测被绕过：正文以“决定：”开头就算写了原因，提示从不触发。

任务（按优先级）：

1. **写入策略：有教训才写。** 结束提醒不再要求“改了哪个模块就写一条”，改为逐项追问：本轮排除了哪些方向、踩了什么坑、有哪些看代码看不出的约束、为什么选这个方案；都没有就答“无新教训”。规则模板（`pmem init` 生成）同步改写。修复变更记录检测：先去掉类型前缀再判断，并提示“这条内容看代码能否直接看出”。
2. **对话内去重。** 同一对话里已返回过全文的记忆，检索时只给 id 和标题，不再重复正文；要全文时带 `full=true`（命令行 `--full`）。去重是单向的：读代码摘要只给标题，不算“给过全文”。对话 id 沿用 Hook 注入的 `source_conversation`；终端 `pmem search` 拿不到对话 id，由 Hook 在命令执行前把对话 id 和模块写进交接文件（120 秒内按模块认领）。上下文压缩后清空该对话的去重记录。
3. **一行标题。** 记忆新增 `summary` 字段（不超过 60 字），新写入没填时提示并展示自动生成的标题，不拒绝写入；老记忆没有时，取正文第一句并去掉“决定：”这类类型前缀自动生成。读代码摘要、Wiki、闸门拦截提示、去重后的检索结果改用标题；顺带修掉“决定：决定：”重复前缀。检索命中的正文仍返回全文，不做强制两段式（多一次往返会变慢，Agent 也常不去取全文）。
4. **全项目级坑。** 记忆新增可选的适用范围 `scope: project`，锚点仍留在原模块，过期核对照常；任何模块（含还没有记忆的模块）的读代码摘要和闸门提示都带上本对话还没给过的至多 3 条全项目级排除项、风险、更正，同一条每个对话只给一次，上下文压缩后重新给。不另建 `common.*` 模块：它没有路径，闸门和按路径检索都碰不到。
5. **验证方法。** 新增可选字段 `verify`（怎么确认问题已解决或结论仍成立：命令、测试、现象），只在 conclusion、correction 写入时提示填写。不加“现象”字段：已有 `aliases` 承担现象的其他叫法。
6. **验收度量。** 用真实 API Key 跑一次 `pmem bench`（有/无记忆，同一批老问题）；`pmem report` 增加类型占比趋势、对话内重复返回率；`pmem health` 增加“同一议题反复出现更正”的统计，作为“同类错误重复出现”的信号。

不做：

- 按采用率调整检索排序：采用率只在本机、事后从对话记录算出，接入排序会让不同人查到的结果不一致，且 19% 只是字面重合下限，噪声大；继续用 `pmem health` 的“返回多次从没被用到”做人工复查。
- 强制两段式检索（只返回标题、再按 id 取全文），理由见任务 3。

验收标准：

- `pmem bench` 中有记忆一组解决同一批老问题的步数和 token 明显少于无记忆一组；
- 新写入记忆中排除项、风险、更正合计占比 ≥ 30%；
- 对话内重复返回率从 40% 降到 5% 以下；
- 老记忆全部有可用标题（自动生成或人工补写），读代码摘要不再出现类型前缀重复；
- 新字段对旧版本兼容：旧版 pmem 读写带 `summary`、`scope`、`verify` 的文件不丢字段（沿用 `extra` 原样写回）。

### 14.3 v0.3.1 任务：写得全、找得准

状态：已实现（2026-10-19，进度见 GitHub Issue #12）。“规划”最终做成类型 `plan` 而不是状态：状态牵涉归档、恢复、回看等流转规则，类型只影响检索分组。

背景（2026-10-19 讨论）：v0.3 的“有教训才写”让正常做功能的过程没有记录，用户明确要求的行为（看起来像普通实现）容易被后来的 AI 当成冗余改回去。参考一份“代码知识图谱 + 冷热分层 + 记忆医生”的外部方案后确定：做功能照常落库，但功能记录和教训分层存放、分层检索，教训不会被功能记录挤掉。

分层（都是一条一个文件、放在同一模块目录下，按类型区分；不做物理分目录，也不做手工维护的单个汇总文件——前者要迁移且收益相同，后者多人追加会频繁合并冲突并丢失每条的锚点与替代关系）：

| 层 | 内容 | 检索 |
|---|---|---|
| 热 | 现行教训：exclusion、risk、correction、conclusion、decision | 每次查，给全文，按相关度、防错类优先，不限时间 |
| 温 | 现行功能记录 `feature` 与规划 `plan` | 每次查，只给标题（默认最多 3 条，`search.feature_limit` 可调为 0），要全文按 id 取 |
| 冷 | 已被替代、合并、归档的旧记忆 | 默认不查；`as_of` 回看、`memory_graph` 时间线、`pmem map` 使用 |

任务：

1. **功能记录 `feature`。** 改了模块就写，同一任务每个模块一条（`draft_id` 覆盖）。写需求来源（谁要求、为什么）、必须保持的行为、适用条件、入口；不写“改了哪个方法”。结束提醒改为“每个改过的模块写一条功能记录；另外有被排除的方向、根因或坑、约束、方案取舍时再写对应类型的教训；确实不需要记录时回复‘无需记录：<原因>’”。
2. **分层检索。** `search_memory` 的 `items` 只放教训（全文），另返回 `features`（功能记录与规划的标题，按相关度与新近程度）；新增参数 `ids` 按 id 取全文。对话内去重只作用于全文结果。
3. **模块教训汇总。** 读代码摘要只从教训里挑（排除项、风险、更正、决定、结论），另附至多 2 条锚点在当前文件上的功能记录标题；改前拦截提示除了模块的排除项、风险、更正，也列出锚点在目标文件上的功能记录标题（“改回去”最常发生在这里）。
4. **适用条件 `applies`。** 新增可选字段，写这条记忆在什么前提下成立；检索说明要求 AI 先判断前提是否满足，不满足就忽略这条。
5. **规划 `plan`。** 还没实现的需求单独用 `plan` 类型，不进教训组、不当现行结论；实现后写功能记录并 `supersedes` 它。
6. **免记录文件。** 只改测试、生成代码、纯配置等文件（`gate.record_exempt`，glob 列表）时不提醒写功能记录；闸门的改前检查不受影响。
7. **合并不跨条件。** `pmem-compact` 技能：相似但适用条件不同的记忆不合并，防止丢失细分约束。
8. **度量。** 防错类占比只在教训里统计；`pmem report` 增加“功能记录覆盖率”（改过代码、需要记录的模块里写了功能记录的比例）。

验收：报告里功能记录覆盖率 ≥ 80%；防错类占教训的比例不下降；读代码摘要里功能记录最多 2 条，教训名额不减少；已接入项目重跑 `pmem init` 后拿到新规则。

### 14.4 v0.3.2 任务：看得见、可验收

状态：已实现，GitHub Issue #13 已关闭（2026-10-20）。实现时的取舍：

- 记忆图只从记忆文件推出（`index/memmap.py`），不读版本库；HTML 是数据内嵌、不联网的单文件 SVG，默认写到 Wiki 目录（`map.html`），和 Wiki 一样不进版本库。Wiki 每个模块页最多画 40 个节点，超出的较早议题只给提示。
- 漏记按“近 N 天（默认 30）有提交的模块里同期一条功能记录都没有”判断，跳过超大提交（与热度扫描同一阈值）、免记录文件、`.memory/` 和已废弃模块；漏记和覆盖率只是提示，不是硬指标。断链里“更正没写替代对象”也包括纠正代码旧行为、本来就没有旧记忆的更正，提示里写明这类可以不管。
- 合并回滚用新字段 `reverted: {on, by}` 实现：撤销的合并产物归档并标记，它的 `supersedes` 不再生效（原规则是归档记忆的替代关系仍然算数，撤销是唯一例外）；`as_of` 回看撤销日之前的日期时仍按替代算。`pmem archive --restore` 同时清掉撤销标记，即重做合并。已被更新的记忆替代的合并产物拒绝撤销，因为撤销后原记忆仍被隐藏。
- 清理候选的前提收紧为：有关联代码时必须全部不存在；没有关联代码时才看正文提到的文件和类（至少 2 处）。关联代码还有一处在就不算候选。正文提到的文件只认源码文件和带目录的路径（`config.yaml` 这类不带目录的多是运行时文件，`Next.js` 是产品名）；类名先按同名文件找，找不到再整词搜源码（Python、TS 的类名和文件名不对应）。

1. **记忆图 `pmem map`。** 一条命令生成整个项目的记忆演化图：按模块分区、模块内按议题排时间线；节点按类型着色（排除项/更正 = 失败或纠错，结论/决定/功能 = 落地，风险 = 注意，规划 = 未实现）；`supersedes` 画实线，同议题内“排除项之后出现结论/决定/功能”画虚线并标明是推断。输出本地 HTML（可缩放、点开看全文）和 Wiki 里的 Mermaid 图。
2. **图上自检与总评。** 漏记（模块近期有提交但同期没有功能记录）、断链（更正没有替代对象；同议题前后结论矛盾却无替代关系）、悬而未决（只有排除项、后面没有落地）、过期（关联代码改过未核对）。顶部给出模块数、覆盖率、断链、悬而未决、过期数，作为“存储做得好不好”的验收；它证明结构完整，不证明对 AI 有用（后者看 `pmem report` 与 `pmem bench`）。
3. **合并回滚。** 按替代关系恢复被合并的原记忆（合并产物归档、原记忆重新现行）。现在归档合并产物不会让原记忆复现。
4. **跳过复查。** 改了代码却没写功能记录（含回复“无需记录”）的模块列入 `pmem health`。
5. **严格的清理候选。** 只归档、不删除、由人确认。“建议归档”须同时满足：关联代码全部不存在、正文提到的路径/标识符在代码里几乎找不到（< 20%）、同议题没有其他现行记忆、没有被其他记忆引用、统计期内本机没被用过（本机检索太少时不用这一条）。只满足一部分的列为“待核对”（核对后确认或写更正）。排除项、风险、更正、全项目级和种子记忆最多到“待核对”。每条附判断依据。

不借鉴（外部方案中）：相似度阈值（实测分不开）、时间衰减打分（老规则往往更重要，用代码是否变化判断过期）、用大模型判断模块归属（花 token、不稳定）、冷库存原始对话（易带密钥、撑大仓库）、后台自动改写记忆（团队共享文件出现无人审核的改动与冲突）、提问时注入（Cursor 不支持）。

### 14.5 v0.4 任务：治理闭环与团队化

状态：前两项已实现（2026-10-20，见 GitHub Issue #14）；后两项长期搁置，近期没有必要做，确有多人实时共享的需求时再重新评估。

1. **转正提示（已实现）。** `pmem health` 的“未登记模块”按这些记忆的关联代码给出建议登记的 paths（同一目录 2 个以上文件登记整个目录，否则登记单个文件，最多 5 条），并列出这些代码现在归哪个模块：都归同一个已登记模块的多半是笔误，提示 `migrate merge`；冷候选提示 `pmem sync --apply` 转正。不自动改 `modules.yaml`：模块是业务划分，需要人确认。
2. **召回审计（已实现）。** 本机检索够多（≥ 20 次）时，现行教训 ≥ 10 条、按模块检索 ≥ 10 次、但被返回过的教训 < 30% 的模块列入 `pmem health`，附从没返回的议题；议题 ≥ 8 个时提示可拆模块。只看教训：功能记录在检索里只给标题、不进事件的 ids。本仓库上线时各模块被返回过的教训占 67%～100%，不触发。
3. **团队汇总（搁置，方向已定）。** 不搭中心服务：各人把本机统计导出成文件提交到仓库，负责人汇总，零运维。要解决的问题：导出内容不带检索原文、对话 id 等隐私；文件按人分开，避免合并冲突；汇总口径与单机 report 一致。
4. **`RemoteStorage` 中心服务、身份与权限、审计、看板（搁置）。** 等团队汇总的文件方案用起来、确认确实需要实时共享后再设计。

### 14.6 v0.6 任务：模块规格

状态：已完成（2026-10-23，安装包 0.6.0，GitHub Issue #16）。设计见 `2026-10-23-pmem-module-spec-design.md`，实施顺序见 `docs/superpowers/plans/2026-10-23-pmem-module-spec.md`。模块改名、合并时规格目录还不会跟着搬。

每个已登记模块一份当前规格，目录 `.memory/specs/`，进版本库，与 Wiki 分开。一份里是策划设计、美术设计、程序设计、模块现状，单拿这一份要能在别处把模块重做出来。没有画面的，美术节写「本模块无画面」。首稿由技能按代码来写，命令行只生成骨架和目录。以后在改动的那一轮更新一次，只改正波及的段落，策划和美术保留。规格提醒默认不提示。不做定时重扫，也不在规格上标需核实。

### 14.7 v0.7 任务：类型安全与规则化

状态：计划。2026-10-23 从 v0.6 顺延，范围不改。设计见 `2026-10-21-pmem-typesafe-design.md`，GitHub Issue #15。

---

## 15. 产品仓库结构

```text
Cursor-Project-Memory/
  pyproject.toml
  src/pmem/
    cli/          # init / doctor / serve / hook / sync / report / migrate / archive / reindex / import / upgrade
    server/       # MCP 工具定义
    core/         # Entry、ModuleRegistry、别名归一、路径映射、替代关系
    storage/      # base.py、files.py（将来 remote.py）
    index/        # sqlite 索引、embedder/（onnx、ollama、openai）、排序与多样性
    vcs/          # git.py、svn.py、none.py
    scan/         # generic.py、adapters/（unity.py、node.py …）
    hooks/        # prompt、pre_edit、pre_record、track、edited、compact、stop
    templates/    # presets/、vocab/、rules/、hooks/、mcp/、skills/、bin/
  tests/
    fixtures/     # 合成仓库生成器、录制的 Hook 输入、检索评测集
  docs/
```

---

## 16. 待定问题

1. 产品正式名称。
2. 用于真实验证的开源项目（Unity 或 Node 单仓多包，各选一个候选后再定）。
3. 默认嵌入模型型号（13.3 评测后确定）。
4. 开源许可证。
5. 13.2 中的 Cursor 行为实测结论，可能影响 9.1 与 8.2 的具体实现。

---

## 附录 A：参考实现中发现的问题与对应设计

| 问题 | 位置 | 本设计中的处理 |
|---|---|---|
| 指定议题无结果时退回整模块检索，但随后又按议题过滤掉，退回无效 | `store.py` 第 573–598 行 | 7.1：真正退回并标注 `fallback` |
| 同议题同日超过 5 条时静默删除最早的，返回仍为成功 | `store.py` 第 513–531 行 | 7.3：拒绝并要求合并 |
| 语义召回后按日期取前 5，新压过相关 | `store.py` 第 611–618 行 | 7.2：相关度为主、时间衰减、批内多样性 |
| 拿不到对话 id 时共用 `default` 状态 | `memory_gate_track.py`、`memory_gate_pre_edit.py` | 9.3：不共享状态，降级处理 |
| 闸门只拦 `Write/StrReplace/EditNotebook`，终端命令可绕过 | `hooks.json` | 9.2：覆盖 `Delete` 与终端写文件模式 |
| “跳过记忆”依赖改文件 Hook 里的 `prompt` 字段，可能拿不到 | `memory_gate_pre_edit.py` | 9.2：改在 `beforeSubmitPrompt` 识别 |
| 模块名区分大小写且直接用作表名，跨操作系统行为不一致 | `registry.py`、`store.py` | 4.5、5.2：归一化 + 逻辑过滤 |
| `delete_memory` 作为 MCP 工具暴露，靠规则禁止 | `server.py` | 7：不暴露给 AI |
| 扫描脚本写死项目目录、别名与前缀，并扫出按技术层划分的空模块 | `sync_modules.py` | 10.2：通用扫描 + 适配器 + 容器目录穿透 |
| LanceDB 目录登记问题需要大量兼容代码与修复工具 | `store.py` | 5.2：SQLite 单文件索引，索引仅为可重建缓存 |
| 换嵌入模型需换库，曾丢失约 160 条未迁移记忆 | 模式指南 7.2 | 3.1、5.2：文件为准，索引可随时重建 |
| 英文为主的嵌入模型处理中文记忆 | `mcp.json` | 5.4：默认多语言小模型，评测后选定 |
