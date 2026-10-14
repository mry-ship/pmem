# pmem：模块目录结构与接入初始化划分 · 设计文档

- 状态：设计稿，待评审
- 日期：2026-10-14
- 上级文档：`2026-10-14-pmem-design.md`（本文细化其第 4.5 节与第 10 节）

---

## 1. 问题与依据

### 1.1 参考实现的模块是怎么“长歪”的

参考实现把**目录等同于模块**：扫描脚本 `sync_modules.py` 只看两个固定目录（`TileMatch/Assets/TileMatch/Script` 与 `GameMain/Scripts/Framework`）的第一层子目录名，每个子目录变成一个模块。对 TileMatch 真实目录核对后，问题分三类：

| 问题 | 真实情况 | 结果 |
|---|---|---|
| 技术组件被当成模块 | `Framework/` 下 18 个子目录多数是框架组件：`DataNode`（5 个脚本）、`DataTable`（6）、`ObjectPool`（9）、`Input`（1）、`PlayerData`（1）、`Activity`（2）… | 登记出十几个 `infra.*` 模块，大多一直是空的 |
| 真正的业务单元没被扫到 | `GameMain/Scripts/Runtime/General/` 下有约 20 个活动：`BalloonRise`、`CardSet`、`Pinata`、`LeaderBoard`、`TilePass`、`ClimbBeanstalk`…；`Merge/Scripts/` 下有十几个子活动 | 目录里没有，只能靠 AI 写入时临时起名，造成近义重复 |
| 同一功能散在多处 | `ClimbBeanstalk` 出现在 `Runtime/General/ClimbBeanstalk`、`Runtime/General/ClimbBeanstalkLevel`、`TileMatch/ClimbBeanstalk_Christmas`、`_Halloween`、`_MiddleSummer`、`_MotherDay`、`_Valentine`；`WorldCup` 同时在 `TileMatch/Script/UI/WorldCup` 和文档目录 | 一个功能被拆成多个名字，或者只登记了其中一处路径 |

另外两个现象：

- `Assets/` 第一层有约 30 个第三方 SDK 目录（`GoogleMobileAds`、`MaxSdk`、`AppsFlyer`、`Firebase`、`Spine`、`I2`、`TextMesh Pro`…），和业务目录 `Jigsaw`、`FarmSudoku`、`MonopolyGame`、`Merge` 混在一起，固定的忽略名单无法覆盖。
- 本项目业务代码几乎没有 `asmdef`，`asmdef` 基本都属于第三方 SDK。所以在这类项目里，**`asmdef` 不是业务边界信号，反而是识别第三方的信号**。

### 1.2 根本原因

1. **把目录当模块**：目录是代码的物理组织方式，模块是业务单元；一个业务单元往往跨多个目录（不同层、不同根、不同变体）。
2. **没有区分目录的角色**：容器目录（`Scripts`、`General`）、按类型分的层目录（`UI`、`Editor`）、杂物目录（`Common`、`Utility`）、第三方目录、业务目录被一视同仁。
3. **没有粒度门槛**：没有“这个候选会不会被反复讨论”的判断，冷门小组件也单独成模块。
4. **没有记录人工决定**：被否决的候选下次扫描还会再冒出来。

### 1.3 设计原则

- **模块是业务单元，不是目录。** 一个模块拥有多条路径；路径到模块是多对一。
- **先判断目录的角色，再提取业务单元。**
- **用证据决定粒度。** 证据主要是近半年的团队修改热度；没有证据的候选不登记为模块。
- **脚本出确定性草案，AI 只处理低置信项，人只回答有限的问题。**
- **所有人工决定都写进配置**，增量同步时不再重复提问。

---

## 2. 模块目录结构（`modules.yaml`）

### 2.1 完整示例

```yaml
schema_version: 1

categories:
  activity:
    label: 限时运营活动
    include: 限时、可开关、有排期的运营玩法；一个活动一个模块
    exclude: 常驻的局外玩法 → gameplay
    hints: [Pass, Event, Challenge, Rank, LeaderBoard, Race, Calendar, Chest, Collection]
  system:
    label: 平台与商业化
    hints: [Ads, Ad, IAP, Purchase, Login, Account, Firebase, Push, Notification, RemoteConfig, Privacy]
  economy:
    label: 货币与数值
    hints: [Shop, Coin, Gold, Gem, Currency, Reward, Gift, Pack, PiggyBank, Inventory]
  gameplay: { label: 核心与常驻玩法 }
  level:    { label: 关卡与难度, hints: [Level, DDA, Difficulty, Stage] }
  infra:
    label: 技术底座
    hints: [UI, Sound, Audio, Localization, Pool, Resource, Download, Debug, Input, Scene, Procedure, Utility]

decision_order: [activity, gameplay, level, economy, system, infra]

boundaries:
  - 广告接入与策略 → system.Ads；看广告领奖励的数值 → economy.Rewards
  - 活动自己的界面、奖励、埋点都归该活动模块，不拆到 infra 或 economy

entities:                     # 全局议题词表：标准写法 → 别名
  Config: [config, settings, 开关, 配置]
  Flow: [flow, 流程, 状态机]
  Reward: [reward, 奖励]

naming:
  strip_suffixes: [Panel, UI, View, Window, Manager, Mgr, Controller, Service, System, Module, Scripts, Level]
  variant_words: [Christmas, Xmas, Halloween, Easter, Valentine, Thanksgiving, MotherDay, MiddleSummer]
  generic_names: [Game, Main, Common, Base, General, Misc, Menu, Core]

modules:
  activity.ClimbBeanstalk:
    paths:
      - TileMatch/Assets/GameMain/Scripts/Runtime/General/ClimbBeanstalk/**
      - TileMatch/Assets/GameMain/Scripts/Runtime/General/ClimbBeanstalkLevel/**
      - TileMatch/Assets/TileMatch/ClimbBeanstalk_*/**
    variants: [Christmas, Halloween, MiddleSummer, MotherDay, Valentine]
    aliases: [ClimbBeanstalkLevel]
    entities: [Config, Reward, Schedule, Level]
    owners: []
    origin: scan              # scan / manual / auto（写入时自动建）
    status: active            # active / deprecated / merged_into:<module>

  gameplay.Merge:
    paths: [TileMatch/Assets/Merge/**]
    origin: scan

  activity.GemMerchant:
    parent: gameplay.Merge    # 只用于分组展示与相近模块提示，不改变地址
    paths: [TileMatch/Assets/Merge/Scripts/GemMerchant/**]
    origin: scan

  infra.Framework:            # 伞形模块：收纳冷门小组件
    paths:
      - TileMatch/Assets/GameMain/Scripts/Framework/DataNode/**
      - TileMatch/Assets/GameMain/Scripts/Framework/DataTable/**
      - TileMatch/Assets/GameMain/Scripts/Framework/ObjectPool/**
    components: [DataNode, DataTable, ObjectPool, Input, PlayerData, Task]   # 被折叠的组件名，自动成为议题
    origin: scan

candidates:                   # 冷候选：不登记为模块
  activity.Ladybug:
    paths: [TileMatch/Assets/GameMain/Scripts/Runtime/General/Ladybug/**]
    reason: 近 180 天 0 次团队提交，4 个脚本
    promote_when: first_memory   # 第一次有人写记忆，或热度超过门槛时转正

third_party:                  # 已确认的第三方目录：不扫描、不守护
  - TileMatch/Assets/GoogleMobileAds/**
  - TileMatch/Assets/MaxSdk/**
  - TileMatch/Assets/Firebase/**

ignored:                      # 人工否决过的候选，增量同步不再提
  - { path: TileMatch/Assets/TileMatch/Script/Demo, reason: 示例代码 }
```

### 2.2 字段说明

| 字段 | 作用 |
|---|---|
| `categories.*.include / exclude` | 给 AI 和人看的归类口径 |
| `categories.*.hints` | 扫描器做大类建议时用的关键词（来自项目类型预设，可改） |
| `naming.strip_suffixes` | 提取业务名时去掉的后缀，`ShopPanel` → `Shop` |
| `naming.variant_words` | 变体词，`ClimbBeanstalk_Halloween` → `ClimbBeanstalk` + 变体 `Halloween` |
| `naming.generic_names` | 泛化词：去后缀后如果只剩这些词（如 `GamePanel` → `Game`），不自动聚类，交给人决定 |
| `modules.*.paths` | 多条 glob；路径到模块的映射是多对一 |
| `modules.*.variants` | 同一活动的季节或主题变体，自动加入议题候选 |
| `modules.*.parent` | 分组关系（大玩法下的子活动），只影响展示和相近提示 |
| `modules.*.components` | 伞形模块收纳的小组件名，自动作为议题 |
| `modules.*.origin` | 来源：扫描、人工、写入时自动建；健康报告据此区分 |
| `candidates` | 证据不足的候选，不出现在 `list_modules` 里 |
| `third_party` | 确认过的第三方目录 |
| `ignored` | 人工否决的候选，防止重复提问 |

### 2.3 路径解析规则

- 文件路径匹配多个模块时，**最具体的 glob 获胜**（字面字符更多、通配更少的优先）。伞形模块的路径天然不如业务模块具体，所以业务模块总是优先。
- 同等具体又冲突时报错，`pmem doctor` 要求人工解决。
- `third_party` 与 `ignored` 中的路径永远不映射到模块，也不受闸门守护。
- 落在 `candidates` 路径里的文件：检索按候选名进行（不存在时返回空 + 提示），写入第一条记忆时候选自动转正为模块。

---

## 3. 目录的五种角色

扫描器先给每个目录判定角色，再决定如何处理。判定同时看**结构**和**名字**，名字只是辅助。

| 角色 | 判定 | 处理 |
|---|---|---|
| **第三方** | 见 4.3 的打分 | 排除，记入 `third_party` 待确认 |
| **容器** | 自身直接包含的代码文件 ≤ 子树的 10%，且有 ≥ 3 个含代码的子目录；或名字在容器词表里（`Scripts`、`Script`、`Runtime`、`Framework`、`General`、`Base`、`src`、`lib`、`app`、`packages`、`modules`、`features`、`Source`） | 向下穿透，本身不成为候选 |
| **层目录** | 名字在层词表里（`UI`、`View(s)`、`Panel(s)`、`Model(s)`、`Data`、`Controller(s)`、`Service(s)`、`Manager(s)`、`Editor`、`Prefabs`、`Sprites`），或子目录/文件名大多带同一后缀 | 向下穿透，子目录或文件名作为业务名参与跨层聚类 |
| **杂物目录** | 名字在杂物词表里（`Common`、`Misc`、`Utility`、`Utils`、`Helpers`、`Shared`、`Tools`） | 归入伞形模块（如 `infra.Common`），名字作为议题 |
| **业务目录** | 以上都不是，且含代码 | 成为业务单元候选 |

补充规则：

- **纯资源目录**（不含代码，如 `Merge/Prefabs_Easter`、`Sprites_Xmas`）不成为候选；名字能和某个业务单元聚类时，作为该模块的附加路径。
- **测试目录**（`Test`、`Tests`、`Testing`）默认忽略；名字能对应到业务单元时作为附加路径。
- **`Editor` 目录**：子目录名能对应到业务单元时并入（`Editor/Jigsaw` → `gameplay.Jigsaw`），否则归入 `infra.Tools`。

---

## 4. 扫描流水线

扫描器 = **通用流水线 + 项目类型适配器**。流水线的每一步都与语言无关，适配器只提供“词表和信号”。

```text
① 找源码根 → ② 排除第三方 → ③ 建目录树并计算指标 → ④ 判定目录角色
→ ⑤ 提取业务名 → ⑥ 跨层聚类 → ⑦ 定粒度 → ⑧ 建议大类 → ⑨ 输出草案与待决清单
```

### 4.1 第 ① 步：找源码根

- 适配器给出主语言的代码扩展名与常见根目录（Unity：`Assets/**/*.cs`；Node：`packages/*`、`apps/*`、`src`；Java：`src/main/java`）。
- 通用兜底：统计全仓代码文件分布，代码文件占比高的顶层目录作为根。
- 允许多个根（TileMatch 就有 `GameMain/Scripts`、`TileMatch/Script`、`Merge/Scripts`、`Jigsaw`、`FarmSudoku`、`MonopolyGame` 等）。

### 4.2 第 ③ 步：指标

对每个目录计算：

| 指标 | 计算 | 用途 |
|---|---|---|
| `code_files`、`loc` | 代码文件数、行数 | 规模 |
| `heat_180d` | 近 180 天触及该子树的团队提交数 | **粒度的主要依据** |
| `authors_180d` | 近 180 天的提交作者 | 负责人候选、第三方判定 |
| `bulk_only` | 是否只被“大批量提交”触及 | 第三方判定 |
| `namespaces` | 代码中的命名空间或包名（适配器提供） | 第三方判定、聚类辅助 |

计算热度时要过滤噪声：

- 忽略触及超过 100 个文件的提交（导入 SDK、整体合并、批量格式化）；
- 只统计代码文件，不统计 `.meta`、贴图、预制体等资源；
- SVN 的复制和合并记录（`A ... (从 ...)`）不计入；
- SVN 日志里是仓库路径（`/branches/.../TileMatch_iLar/...`），要用 `svn info` 的相对 URL 换算成工作副本路径。

性能：在 TileMatch 上 `svn log -v -l 200` 约 4.5 秒。热度结果缓存到用户缓存目录，增量同步只拉新修订。没有版本控制或历史太短时，退化为只按规模判断，并把置信度标为低。

### 4.3 第 ② 步：第三方识别

逐目录打分，**1 个强信号或 2 个弱信号**即判为第三方，全部进入待决清单批量确认：

| 强信号 | 弱信号 |
|---|---|
| 路径在通用排除表里（`node_modules`、`vendor`、`Plugins`、`ThirdParty`、`Packages`、`ExternalDependencyManager`、`Standard Assets`、`TextMesh Pro`、`com.*`） | 名字在适配器的已知 SDK 名单里（`GoogleMobileAds`、`MaxSdk`、`AppsFlyer`、`Firebase`、`Spine`、`I2`…） |
| 子树根部有独立的包清单（`package.json` 且名字不属于本项目、`*.podspec`、`LICENSE` + `asmdef`） | 命名空间不属于项目的主命名空间 |
| | 近 180 天只被大批量提交触及，或从未被团队修改 |

区分“第三方 SDK”和“团队自己的封装”：`Assets/Firebase`（SDK，热度只来自升级）与 `Framework/Firebase`（团队封装，有日常提交、命名空间属于项目）靠热度和命名空间区分，后者保留为业务候选。

### 4.4 第 ⑤ 步：提取业务名

对业务目录、层目录下的子目录、层目录里的文件名，统一做名字归一：

1. 按 `_`、`-`、空格切分，去掉变体词与版本号（`V2`、`2026`、`_847`），记录变体；
2. 反复去掉 `strip_suffixes` 里的后缀（`ClimbBeanstalkLevel` → `ClimbBeanstalk`，`ShopPanel` → `Shop`）；
3. 结果如果落入 `generic_names`（`GamePanel` → `Game`），停止归一，保留原名并标为待决；
4. 转成大驼峰，作为聚类键。

**层优先的代码库**（后端常见：`controller/OrderController.java`、`service/OrderService.java`、`repository/OrderRepository.java`）中，业务单元是文件而不是目录。层目录下直接按**文件名**提取业务名：`OrderController`、`OrderService`、`OrderRepository` → `Order`。

### 4.5 第 ⑥ 步：跨层聚类

- 聚类键相同的节点（不同根、不同层、不同变体）合并成一个候选，拥有多条路径。
- 例：`General/ClimbBeanstalk` + `General/ClimbBeanstalkLevel` + `TileMatch/ClimbBeanstalk_*` → 一个候选，带 5 个变体；`UI/ShopPanel` + `General/Shop` → 一个候选。
- 近似但不相同的键（编辑距离小、互为前缀，如 `Gold` 与 `GoldCollection`）**不自动合并**，放进待决清单。

### 4.6 第 ⑦ 步：定粒度（避免空模块的核心）

对每个聚类后的候选：

| 条件（默认值可配置） | 结果 |
|---|---|
| `heat_180d ≥ 5`，或 `code_files ≥ 30` 且 `heat_180d ≥ 1` | **独立模块** |
| 不满足上面的条件，且位于容器内的组件（如 `Framework/DataNode`） | **折叠进伞形模块**（以容器名命名，如 `infra.Framework`），原名进 `components`，自动作为议题 |
| 不满足，且是某个已有业务候选的子目录 | **并入父候选**，原名作为议题 |
| 不满足，且独立存在（如 `General/Ladybug`） | **冷候选**，进 `candidates`，不登记 |
| 某个业务候选有 ≥ 3 个子目录各自满足独立条件（如 `Merge/Scripts/*`） | **父子分组**：父候选成为模块，子候选各自成为模块并标 `parent` |

门槛的含义：模式指南的数据显示，模块要累积到一定条数才产生效果，而半年里几乎没人改的代码几乎不会被讨论。用热度做门槛，就是用证据预测“会不会有人来写记忆”。

### 4.7 第 ⑧ 步：建议大类

按优先级综合以下信号，给出大类和置信度：

1. 带变体词 → 强烈倾向 `activity`；
2. 名字命中某大类的 `hints`；
3. 位置提示：位于 `Framework` 等底座容器下 → `infra` 或 `system`（再按 `hints` 细分）；
4. 父子关系：子候选默认继承父候选所在大类的推荐，限时类子活动倾向 `activity`。

置信度低（信号冲突或没有信号）的进入待决清单。

### 4.8 第 ⑨ 步：输出

| 文件 | 内容 |
|---|---|
| `.memory/bootstrap/scan-report.json` | 全部目录角色、指标、聚类、打分过程，便于复查 |
| `.memory/bootstrap/modules.draft.yaml` | **确定性草案**：高置信项已填好 |
| `.memory/bootstrap/decisions.md` | 待决清单：每项带默认建议，可整体接受 |

---

## 5. 项目类型适配器

适配器只提供词表和信号，不改变流水线。

| 类型 | 源码根 | 容器词 | 层词 | 业务单元信号 | 第三方信号 |
|---|---|---|---|---|---|
| Unity | `Assets/**/*.cs` | `Scripts`、`Script`、`Runtime`、`Framework`、`General`、`Base` | `UI`、`Panel`、`View`、`Prefabs`、`Editor`、`Model`、`Data` | 业务目录、命名空间；团队自己的 `asmdef` | `Plugins`、`Packages`、`com.*`、外部 `asmdef`、已知 SDK 名单 |
| Node / 前端 | `packages/*`、`apps/*`、`src` | `src`、`lib`、`app`、`packages` | `components`、`hooks`、`utils`、`services`、`store`、`styles` | 工作区包、`features/*`、`pages/*`、`routes/*` | `node_modules`、`dist`、外部包清单 |
| Java / Kotlin 后端 | `src/main/java/<根包>` | 根包路径 | `controller`、`service`、`repository`、`dto`、`entity`、`config` | Maven/Gradle 子模块、按业务分的包、层目录下的文件名 | `target`、`generated` |
| Go | `cmd/*`、`internal/*`、`pkg/*` | `internal`、`pkg` | `handler`、`service`、`repo` | `internal` 下的包 | `vendor` |
| Python | `src/<包>`、项目包 | 顶层包 | `api`、`models`、`services`、`utils` | 子包、Django app | `venv`、`site-packages` |
| .NET | `*.csproj` 所在目录 | 解决方案目录 | 同 Unity | 项目（csproj）、命名空间 | `packages`、`bin`、`obj` |
| 通用兜底 | 代码占比高的顶层目录 | 结构判定 | 结构判定 | 目录结构 + 热度 | 通用排除表 |

v0.1 实现 Unity、Node 与通用兜底；其余在 v0.2 补齐。

### 5.1 项目类型预设

每种项目类型一份预设，内容包括：大类及 `include/exclude/hints`、判定顺序、边界口径模板、议题词表、`naming` 默认值。预设只是起点，初始化时可以改，冻结后写入 `modules.yaml`。

---

## 6. 接入初始化流程（细化）

| 步骤 | 执行者 | 产物 | 预计耗时 |
|---|---|---|---|
| 1. 项目画像 | `pmem init` 问答（5 问） | `config.yaml`、选定的预设与适配器 | 3 分钟 |
| 2. 扫描 | `pmem scan` | 扫描报告、确定性草案、待决清单 | 1–5 分钟 |
| 3. AI 复核 | Cursor 技能 `pmem-bootstrap` | 处理低置信项，补名字与边界 | 10–20 分钟 |
| 4. 人工决定 | 技能引导，逐项提问 | 冻结大类，写入决定 | 10–20 分钟 |
| 5. 校验 | `pmem doctor --coverage` | 覆盖率、重叠、空模块检查 | 1 分钟 |
| 6. 种子记忆（可选） | 技能 `pmem-seed` | 热点模块的种子记忆 | 20–30 分钟 |
| 7. 生成并提交 | `pmem init --finish` | 规则、Hooks、MCP 配置、技能、团队说明 | 2 分钟 |

### 6.1 待决清单的固定类型

待决项只有以下几类，每项都带默认建议，人可以逐项改，也可以整体接受：

| 编号 | 类型 | 默认建议 |
|---|---|---|
| D1 | 第三方目录确认 | 按打分结果，批量确认 |
| D2 | 大类置信度低 | 按判定顺序给出首选 |
| D3 | 近似名字是否合并 | 不合并 |
| D4 | 父子分组：子单元成为模块还是议题 | 满足独立门槛的成为模块 |
| D5 | 杂物目录归到哪个伞形模块 | `infra.Common` |
| D6 | 冷候选是否提前转正 | 保持冷候选 |
| D7 | 同名候选落在两个大类 | 按判定顺序取第一个 |
| D8 | 泛化名（`GamePanel` 等）归属 | 归入所在根目录对应的核心模块 |

### 6.2 提问预算

- 高置信项打包一次确认：“以下 22 个模块高置信，整体确认？”
- 其余逐项提问，**总数不超过 15 个**；超出部分按默认建议处理，并写进 `decisions.md` 留待收口时复查。

### 6.3 校验项（`pmem doctor --coverage`）

| 检查 | 不通过的条件 |
|---|---|
| 覆盖率 | 业务代码中未映射到任何模块的文件超过 5% |
| 重叠 | 同等具体的 glob 映射到不同模块 |
| 空壳模块 | 登记的模块热度为 0，且来源为扫描（应进入冷候选） |
| 大类数量 | 少于 4 或多于 8 |
| 模块数量 | 初始少于 10 或多于 60（只提醒） |
| 名字规范 | 模块名带日期、版本号或变体词 |

---

## 7. 可持续：增量同步与模块演化

### 7.1 `pmem sync`

复用同一条流水线，只输出差异：

- 新出现的业务单元 → 新候选（按门槛决定是模块还是冷候选）；
- 冷候选热度超过门槛，或已有人写入记忆 → 建议转正；
- 已登记模块 90 天热度为 0 且没有记忆 → 建议降为冷候选或折叠进伞形模块；
- 已有模块出现新路径（如新增一个季节变体目录）→ 建议追加路径。

`third_party`、`ignored` 和已有模块的名字永远不会被改动或重复提出。

### 7.2 写入时自动建的模块

AI 写入一个目录里没有的模块名时：

1. 先与 `candidates` 比对，命中则直接转正；
2. 否则照常写入，`origin: auto`，返回相近模块；
3. 健康报告单独列出 `origin: auto` 的模块，收口时由负责人登记路径或合并。

### 7.3 演化操作

| 操作 | 效果 |
|---|---|
| 改名 | 旧名成为别名，读写自动转发 |
| 合并 | 被合并模块标为 `merged_into`，路径并入目标模块 |
| 拆分 | 按路径或议题重新分配记忆 |
| 折叠 | 小模块并入伞形模块，原名进入 `components` |
| 转正 / 降级 | 冷候选与模块之间互转 |

所有操作都通过 `pmem migrate` 执行并修改 `modules.yaml`，提交后对全团队生效。

---

## 8. 在 TileMatch 上的推演（示意）

以下按本文规则推演，**未实际计算热度**，仅用于说明规则效果；正式验证在示例项目和开源项目上进行。

| 位置 | 参考实现 | 本方案 |
|---|---|---|
| `Assets/` 第一层约 30 个 SDK 目录 | 未处理（扫描范围外） | 识别为第三方，批量确认后排除 |
| `Framework/Ads`（133 个脚本） | `system.AdChase` 等 | 独立模块 `system.Ads`（下设议题或子模块由人决定） |
| `Framework/Purchase`、`Login`、`Firebase` | `system.IAP`、`infra.Login`、`system.Firebase` | 按热度：`system.IAP`、`system.Account`、`system.Firebase` |
| `Framework/DataNode`、`DataTable`、`ObjectPool`、`Input`、`PlayerData`、`Activity` 等小组件 | 各自成为 `infra.*` 模块，大多为空 | 折叠进 `infra.Framework`，组件名作为议题 |
| `Runtime/General/*`（约 20 个活动） | 未登记 | 穿透容器 `General`，热度达标的成为 `activity.*`，其余进冷候选 |
| `ClimbBeanstalk` 的 7 处目录 | 分散或缺失 | 一个模块 `activity.ClimbBeanstalk`，带 5 个变体 |
| `TileMatch/Script/UI/*` | 整体当作 `infra.UI` | 穿透层目录：`UI/WorldCup` 并入 `activity.WorldCup`，`UI/ShopPanel` 与 `General/Shop` 聚类，`UI/GamePanel` 为泛化名进入待决 |
| `Merge/Scripts/*` 十几个子活动 | 未登记 | 父子分组：`gameplay.Merge` + 达标的子活动模块（标 `parent`） |
| `Merge/Prefabs_*`、`Sprites_*` | 未处理 | 纯资源目录，按名字作为对应模块的附加路径，否则忽略 |

---

## 9. 对上级设计文档的影响

- 第 4.5 节 `modules.yaml` 以本文第 2 节为准（新增 `naming`、`variants`、`parent`、`components`、`origin`、`candidates`、`third_party`、`ignored`）。
- 第 10 节初始化流程以本文第 6 节为准（新增独立的 `pmem scan` 步骤、确定性草案、固定待决类型与提问预算）。
- 第 11 节 `pmem sync` 以本文第 7.1 节为准。
- 第 7.1 节 `search_memory`：落在冷候选路径中的文件，按第 2.3 节处理。

---

## 10. 已定事项（2026-10-14 确认）

1. 粒度门槛先用默认值（热度 5 次、30 个文件），在示例项目与开源项目上校准后再调整。
2. 伞形模块以所在容器命名（如 `infra.Framework`）；杂物目录默认归 `infra.Common`。
3. 父子分组时，子模块的大类允许与父模块不同（如 `gameplay.Merge` 下的 `activity.GemMerchant`）。
4. 已知 SDK 名单随包内置并定期更新，同时允许项目在 `config.yaml` 中追加。
