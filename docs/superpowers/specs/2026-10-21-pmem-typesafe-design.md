# pmem v0.6 类型安全与规则化设计

日期：2026-10-21　状态：计划，待确认（进度见 [Issue #15](https://github.com/mry-ship/pmem/issues/15)）

## 1. 背景与目标

记忆只能“提醒” AI：AI 没看到、看到了没照做，错误照样发生。按代码场景的经验，记忆大约能防住六成可重复的错误。
尺寸、格式、参数范围、调用顺序这类**机械错误**，写成类型或校验规则后可以接近 100% 拦下，还能在调用外部接口之前拦，不花冤枉钱。
同时，pmem 自己读外部输入（Hook 数据、`config.yaml`、`modules.yaml`、记忆文件头）的地方靠散落的 `isinstance` 判断，配置写错时报错难懂，Hook 出错又会直接放行，闸门静默失效。

目标：

1. **教训升级成规则**：反复出现的机械教训，健康报告提示写成规则（代码项目的静态分析、类型约束，美术技能的参数校验）；写成后记忆标明“已由规则保障”，规则文件一改，记忆跟着标“需核实”。
2. **结构化的适用条件**：在自由文字的 `applies` 之外，增加按项目声明的、带类型的条件字段（平台、资源类型、模型、版本），检索时精确过滤。
3. **边界校验**：pmem 读外部输入的四处统一校验，报错写清“哪个文件、哪个字段、应该是什么”。
4. **返回契约与内部类型检查**：MCP 工具返回的字段写成类型定义；pmem 源码纳入 pyright 检查。

不做：

- 在 Hook 里引入 Pydantic 等重依赖（见 2.3）；
- 把记忆正文结构化（正文继续是自由文字）；
- pmem 自己执行用户项目的规则或类型检查（Cursor 已把代码检查的报错交给 AI，避免重复建设）；
- 自动生成规则代码（只提示、给出建议的规则描述，由 AI 或人写）。

## 2. 现状

### 2.1 pyright 扫描（标准模式，2026-10-21）

共 316 个报错：

| 类别 | 数量 | 说明 |
|---|---|---|
| 属性访问（reportAttributeAccessIssue） | 239 | 228 个在 `hooks/` 的 6 个组合类里：闸门由几个类拼成，彼此用到对方的属性，pyright 认不出，属于假报错 |
| 参数类型（reportArgumentType） | 43 | 多为 YAML、JSON 读出来的值没有收窄类型 |
| 可能为空却直接使用（Optional 访问、下标） | 29 | 少数可能真会在空值时崩溃 |
| 其他 | 5 | 运算、返回值、缺少导入 |

按文件：`hooks/mcp.py` 61、`hooks/memories.py` 42、`hooks/reminders.py` 39、`hooks/review.py` 37、`hooks/snapshot.py` 28、`hooks/guard.py` 21。

### 2.2 外部输入的校验

| 输入 | 位置 | 现在 |
|---|---|---|
| Hook 收到的数据 | `hooks/payload.py` | 14 处 `isinstance`，转码损坏时按字段抠取（`_partial`） |
| `modules.yaml` | `core/registry.py` | 11 处 `isinstance`，`paths` 写成字符串等报 `RegistryError` |
| `config.yaml` | `core/config.py` | 9 处 `isinstance`，数值和列表加载时校验，报 `ConfigError`；拼错的键（如 `gate.mod`）静默忽略 |
| 记忆文件头 | `core/entry.py` | 7 处 `isinstance`，缺必填项报 `ValueError`；不认识的顶层字段原样写回 |

### 2.3 约束

- **Hook 不能加载重依赖**：每次工具调用起一个 Hook 进程，`tests/test_layering.py` 有子进程测试确认导入闸门后没有加载 numpy、yaml、service。
  Pydantic 导入约 0.1～0.2 秒，放进 Hook 会让每次工具调用都变慢。Hook 一侧只用标准库（`TypedDict` + 手写校验）。
- **旧版兼容**：新增的记忆字段旧版会原样保留但不理解；新增的配置项旧版忽略。
- 健康报告已有“同一议题反复更正（同类错误重复出现）”一节，规则化提示在它的基础上扩展。

## 3. 设计

### 3.1 教训升级成规则

**健康报告新增一节“可以写成规则的教训”**，满足任一条件的议题列入：

- 同一模块、同一议题的现行排除项、风险、更正不少于 3 条（`health.rule_min`，默认 3）；
- 已在“同一议题反复更正”里出现，且议题被检索命中过 5 次以上。

每行给出：模块、议题、这几条的标题、建议的规则形态。建议形态按模块的路径猜测：

| 路径特征 | 建议 |
|---|---|
| `.py` | ruff 自定义规则、类型标注收紧、断言 |
| `.ts`/`.js` | ESLint 规则、TypeScript 类型 |
| `.cs` | Roslyn 分析器、`[Obsolete]`、编辑器校验 |
| 技能目录（`.cursor/skills/**`） | 技能脚本里的参数和输出校验（Pydantic、Zod） |
| 其他 | 检查清单、提交前脚本 |

pmem-consolidate 技能增加一步：对这一节的议题，和用户确认后写规则，再按 3.2 记录。

**成效**：机械教训的防住率从约六成提到接近 100%；记忆库里同议题的碎记忆被一条“由规则保障”的功能记录替代，越用越精简。
**开支**：开发 1～2 天；只在运行 `pmem health` 时计算，日常 0。

### 3.2 “已由规则保障”字段 `enforced_by`

记忆新增可选字段 `enforced_by: [路径#规则名, ...]`，写法同 `anchors`。

- `record_memory` 和 `pmem record --enforced-by` 支持写入；覆盖时没传沿用原值。
- **过期核对**：`enforced_by` 里的文件和 `anchors` 一样参与核对，规则文件改了或删了，这条记忆标“需核实”，`check` 里写明“规则文件改过”。
- **展示**：检索、读码摘要、Wiki 在标题后标“（已由规则拦截）”；读码摘要里已由规则保障的教训排在未保障的之后，名额让给仍需靠记忆防的。
- **典型写法**：规则写好后，写一条功能记录“X 已由规则 Y 拦截，原因见被替代的几条”，`enforced_by` 填规则，`supersedes` 填那几条教训。
- 健康报告“可以写成规则的教训”跳过已有 `enforced_by` 的议题。

**成效**：规则和记忆不会各说各话；规则被删或改坏时有人知道。
**开支**：开发 1 天；运行时多核对几个文件，可忽略。

### 3.3 结构化的适用条件 `when`

项目在 `config.yaml` 声明条件维度和取值：

```yaml
facets:
  platform: [ios, android, pc]      # 列出取值：写入时只能用这些
  asset: [character, scene, ui, vfx]
  model: str                        # str：任意文字，按不区分大小写相等比较
```

- 记忆新增可选字段 `when: {platform: [ios], model: flux-1.1}`；值可以是单个或列表。写入时按声明校验：未声明的维度、不在取值里的值报错并列出可选值。
- `search_memory` 新增参数 `when={...}`：记忆的 `when` 与查询有交集或记忆没写 `when` 的保留，明确冲突的排除（例如查 `platform: android` 时排除只写了 `ios` 的）。不传 `when` 时行为不变。
- `applies` 保留，用于无法枚举的前提；规则文字提示“能用 facets 表达的写进 when”。
- 没声明 `facets` 的项目：`when` 字段不可用，一切照旧。

**成效**：多平台、美术项目里检索不再混入另一平台、另一模型的经验；估计这类项目的无关条目减少三成以上。
**开支**：开发 2～3 天；检索时多一次过滤，可忽略。

### 3.4 边界校验

新增 `core/schema.py`（只用标准库）：用 `TypedDict` 描述四类输入的结构，一个通用校验函数逐字段检查类型和取值，报错带字段路径：

```
.memory/config.yaml：gate.mode 应是 warn / block / off 之一，实际是 "blok"
.memory/config.yaml：不认识的键 gate.mod，是不是 gate.mode？（已忽略）
.memory/modules.yaml：modules.system.Ads.paths 应是列表，实际是字符串
```

- `config.yaml`、`modules.yaml`：替换现有零散判断；拼错的键给出相近键名提示（只警告，不拒绝）。`pmem doctor` 汇总这些提示。
- 记忆文件头：字段类型错误报错并指出文件；不认识的字段仍原样保留（前向兼容）。
- Hook 数据：只校验 pmem 用到的字段；结构不对时记 `hook_error` 事件并放行（行为不变），`pmem doctor` 能看到原因。

**成效**：配置写错时一眼看到哪里错；Hook 因数据结构变化静默失效的情况能被发现。
**开支**：开发 2～3 天；运行时不到 1 毫秒，Hook 不加载新依赖。

### 3.5 返回契约

`service/` 下为 `search_memory`、`record_memory`、`memory_graph`、`list_modules` 的返回写 `TypedDict`（`items`、`features`、`children`、`related`、各类 `*_hint` 等）。
测试按类型定义检查真实返回：字段改名、漏写、类型变了直接失败，避免 AI 读到的格式悄悄变化。

**成效**：工具返回格式稳定；新增字段有地方登记。**开支**：开发 1 天；运行时 0。

### 3.6 内部类型检查

- Hook 组合类：加一个声明共享属性的基类（或 `Protocol`），消掉约 228 个假报错。
- 逐个核对 29 处可能为空的访问，补判空或收紧类型。
- pyright 基础模式纳入测试（与 `test_layering.py` 同类的一个测试，pyright 作为开发依赖）；先覆盖 `core`、`index`、`service`、`catalog`，Hook 清零后再纳入。

**成效**：消除潜在崩溃；以后的改动自动把关。**开支**：开发约 1.5 天；检查一次约 10 秒，只在开发时跑。

## 4. 涉及的功能模块与文件

| pmem 模块 | 文件 | 改动 |
|---|---|---|
| feature.Metrics | `metrics/health.py` | “可以写成规则的教训”一节 |
| infra.Model | `core/entry.py`、`core/config.py`、新增 `core/schema.py` | `enforced_by`、`when` 字段，`facets` 配置，边界校验 |
| feature.ModuleCatalog | `core/registry.py` | `modules.yaml` 校验改用 schema |
| feature.Retrieval | `index/store.py`、`index/anchors.py` | `when` 过滤；`enforced_by` 参与过期核对 |
| feature.Tools | `service/search.py`、`service/record.py`、`server/app.py` | 新参数、返回契约、工具说明 |
| feature.Gate | `hooks/payload.py`、`hooks/*` | Hook 数据校验；组合类类型声明；摘要里“已由规则拦截”排后 |
| feature.Onboarding | `generate/templates.py`、`cli/doctor_cmd.py` | 规则文字（能用 facets 的写 when）、consolidate 技能新步骤、doctor 汇总配置提示 |
| infra.Common | `tests/`、`pyproject.toml`、文档 | pyright 测试、手册与主页 |

## 5. 分阶段实施

1. **规则化**（3.1、3.2）：约 2～3 天。对用户成效最大，代码和美术场景都能用。
2. **边界校验与判空**（3.4、3.6 的判空部分）：约 3 天。
3. **结构化条件**（3.3）：约 2～3 天。先在一个美术或多平台项目里试 `facets`。
4. **契约与内部检查**（3.5、3.6 其余）：约 2.5 天。

合计约 9.5～11.5 天。每个阶段先写测试，全量 pytest 通过；第 1、3 阶段在临时项目里用“生图技能 + 尺寸教训”场景实际跑一遍。

## 6. 成效与开支汇总

| 项 | 适合程度 | 成效（估算） | 开发 | 运行开销 |
|---|---|---|---|---|
| 教训升级成规则 | 很适合 | 机械教训防住率约六成 → 接近 100%；代码场景被纠正比例再降 5～10 个百分点，美术场景重试再降约 15 个百分点 | 1～2 天 | 日常 0 |
| `enforced_by` | 很适合 | 规则与记忆联动核对，碎记忆被替代 | 1 天 | 可忽略 |
| 边界校验 | 很适合 | 配置写错有明确提示；Hook 静默失效可发现 | 2～3 天 | 不到 1 毫秒 |
| 判空 | 很适合 | 消除潜在崩溃 | 0.5 天 | 0 |
| `when` 结构化条件 | 美术、多平台项目适合 | 无关条目减少三成以上 | 2～3 天 | 可忽略 |
| 返回契约 | 适合 | 工具返回格式稳定 | 1 天 | 0 |
| Hook 类型声明 + pyright | 适合 | 改动自动把关 | 1 天 + 0.5 天 | 仅开发时 |

成效数字均为推算，第 1、3 阶段完成后用 `scripts/eval_real_queries.py` 和试点项目的 `pmem report` 校正。

## 7. 风险

- **规则过严卡住探索**：建议形态里写明分级，“一定错”的拦、“通常不建议”的只警告；美术技能尤其要注意。
- **facets 声明过多**：维度一多，写记忆的负担变重。建议每个项目不超过 4 个维度，doctor 超过时提示。
- **旧版混用**：旧版读到 `enforced_by`、`when` 会保留但不理解，检索不过滤、不标“已由规则拦截”，不出错；发布说明写明升级建议。
- **pyright 版本漂移**：固定开发依赖版本，避免升级后突然多出报错让测试失败。

## 8. 待确认

1. 规则化提示的阈值：同议题 3 条现行教训，是否合适？
2. `when` 不匹配时直接排除，还是只降权？（本稿：明确冲突才排除，没写 `when` 的照常返回）
3. 读码摘要里“已由规则拦截”的教训排后，还是干脆不显示？
4. 实施顺序按第 5 节，还是先做结构化条件给美术试点？
