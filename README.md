# pmem：给 Cursor / Claude Code / Codex 用的项目研发记忆

Agent 改代码前，先查这个模块以前踩过的坑；改完之后，把新得出的结论留给下一个人。
记忆按业务模块存成 Markdown 文件，放在仓库的 `.memory/` 里，跟代码一起提交、一起评审，整个团队共享。不需要服务器，也不需要数据库。

```text
你：修一下拼图奖励重复发放
Agent：（自动查 gameplay.Jigsaw 的记忆）
       已有排除项：不要在客户端去重，根因是服务端 Claim 没有按关卡做幂等……
       我按这个方向修改服务端，并补测试。
```

## 能带来什么

接入后运行 `pmem report`，会从本机记录里算出下面这些数字。数据只存在你自己电脑上，不会上传。

| 指标 | 含义 |
|---|---|
| 检索命中率 | Agent 改代码前查记忆，有多少次查到了相关结论 |
| 避坑提示 | 命中的结果里有多少次是“排除项 / 风险 / 更正”，也就是前人明确说过别这么做 |
| 跨人复用 | 有多少次用上了同事写的记忆，这些知识原本只在那个人脑子里 |
| 记忆被采用 | 返回给 Agent 的记忆里，有多少条在它的回复中被明确用到（保守下限）；同一对话里自己刚写的记忆不算 |
| 记忆使用 | 每条记忆被返回、被用到的次数：最常被用到的几条；常被返回却从没被用到、值得复查的几条；一直没被检索到的 |
| 闸门 / 提醒转化 | 被提醒“先查再改”“改完记一下”之后，有多少次真的照做了 |
| 知识资产 | 有记忆的模块占比；只有一位作者的模块；近半年改动多却还没有记忆的模块 |

想要更硬的证据，可以用 `pmem bench` 做对照实验：同一个任务，有记忆跑一遍、没记忆跑一遍，比较成功率、token、耗时和工具调用次数。见下文“衡量收益”。

**真实数据实测。** 把一个游戏项目已有的 853 条研发记忆（53 个模块）导入 pmem，和原来的向量库记忆服务对比。共 13 个限定模块的查询，每个都事先人工确认了目标记忆，两边都只看前 3 条：

| | pmem | 原记忆服务 |
|---|---|---|
| 前 3 条命中目标记忆 | 9 / 13 | 4 / 13 |
| 模块里较早的记忆（6 个查询） | 4 / 6 | 0 / 6 |
| 单次检索耗时 | 1–14 毫秒 | 依赖本机 Ollama 服务 |

差距主要来自排序方式。原服务按向量相似度取出至少 20 条候选，再按日期从新到旧截取，所以不超过 20 条的模块（53 个里有 42 个）总是返回最新几条，查询词不起作用；大模块里的老结论也会被新记忆挤掉。pmem 按“相关度为主、时间衰减为辅”排序，老的根因和排除项照样能被找回。两边共同的短板是同义改写：只写了“崩溃”的记忆，搜“闪退”两边都找不到。pmem 现在用两种方式补上：写记忆时 Agent 顺手填 `aliases`（这条记忆的其他叫法）；团队常见的同义叫法登记在 `modules.yaml` 的 `synonyms` 里，检索时自动扩展（见“日常怎么用”）。

## 5 分钟接入

前提：已安装 [uv](https://docs.astral.sh/uv/)、Python ≥ 3.10，以及 Cursor、Claude Code、Codex 中的至少一个；项目使用 Git 或 SVN（也可以都不用）。

**1. 安装（每人一次）**

```bash
uv tool install "pmem[embed] @ git+https://github.com/mry-ship/pmem"
```

`[embed]` 会启用中文语义检索：首次使用时下载约 90 MB 的模型，所有项目共用。不需要语义检索可以去掉 `[embed]`，此时只用关键词检索。

**2. 在项目根目录初始化（每个项目一次）**

```bash
pmem init --type game                        # 可选 game / app / backend / generic，决定默认的模块大类
pmem init --agents cursor,claude,codex       # 指定接入哪些工具；默认 auto
```

它会生成 `.memory/`（配置、模块目录、记忆），再按 `--agents` 给各工具生成规则、Hooks 和 MCP 配置。默认 `auto` 总是接入 Cursor；项目里已有 `.claude/` 或 `CLAUDE.md` 时接入 Claude Code，已有 `.codex/` 或 `AGENTS.md` 时接入 Codex。`--agents all` 三个都接。已有的配置只会合并，不会覆盖；`CLAUDE.md`、`AGENTS.md` 里只更新 `<!-- pmem:begin -->` 到 `<!-- pmem:end -->` 之间的段落。

| 工具 | 生成的文件 |
|---|---|
| Cursor | `.cursor/rules/pmem.mdc`、`.cursor/skills/pmem-*`、`.cursor/hooks.json`、`.cursor/mcp.json` |
| Claude Code | `CLAUDE.md` 中的 pmem 段落、`.claude/skills/pmem-*`、`.claude/settings.json`、`.mcp.json` |
| Codex | `AGENTS.md` 中的 pmem 段落、`.codex/hooks.json`、`.codex/config.toml` |

三个工具共用同一份 `.memory/` 和同一套闸门逻辑：Hooks 统一调用 `pmem hook <事件> --agent <工具>`，pmem 把各工具的输入输出格式转换成同一种。

**3. 在工具里启用（每人一次）**

- Cursor：打开设置 → MCP，把 `pmem` 打开。这一步只能手动完成。
- Claude Code：首次打开项目时批准 `.mcp.json` 里的 pmem 服务；用 `/hooks` 可以查看已接入的 Hook。
- Codex：先信任本项目（未信任时不加载项目里的 `.codex/`），再在 `/hooks` 里审阅并信任 pmem 的 Hook。

**4. 划分模块（每个项目一次）**

在 Cursor 里对 Agent 说：“按 pmem-bootstrap 技能划分模块”。Agent 会扫描目录和最近的提交热度，生成 `.memory/modules.yaml`，你确认即可。
一个模块是一个业务单元（例如 `gameplay.Jigsaw`），不是一个目录：它可以包含多个路径，也可以起别名。

**5. 自检并提交**

```bash
pmem doctor                 # 检查配置、模块覆盖率、各工具接入、语义模型
git add .memory .cursor && git commit -m "接入 pmem"
```

接入了 Claude Code 或 Codex 的话，把上面列出的对应文件一并提交。

团队其他人拉下代码后，只需要做第 1 步和第 3 步。

## 日常怎么用

基本什么都不用做：

- **改代码前**：Agent 按规则先查要改文件所属模块的记忆。它忘了也没关系，Hooks 会拦下对“有记忆的模块”的修改，直到它查过这个模块；查哪个模块只放行哪个模块。检索报错也算查过，MCP 不可用时在终端运行 `pmem search --module <模块>` 同样有效，不会把 Agent 卡死。
- **得出结论后**：只在三个时机写记忆：确认根因、排除某个方向或定下方案、改完并验证通过。一轮对话结束时，如果改了模块却没写记忆，会提醒一次；整个对话只查了记忆、没改代码也没写记忆时，也会对查过的模块提醒一次。没有新结论的话回复“无需记录”即可。不想要后一种提醒，可在 `.memory/config.yaml` 里设置 `gate.analysis_reminder: false`。
- **用之前核对**：检索结果里 `stale: true` 的记忆，表示写下（或上次核对）之后关联代码又改过、文件已不存在或找不到对应方法，`check` 字段写明是哪一种。Agent 打开代码核对后，仍然成立就调用 `confirm_memory` 刷新核对日期（排序也按这个日期算新旧），已不成立就写一条 correction 替代它。改动日期从 Git/SVN 记录里批量查出，没有版本库时看文件修改时间。
- **写入时规整**：写记忆的 Agent 本身就是大模型，规整由它完成，不调用外部服务。规则要求它把现象的其他叫法写进 `aliases`（如“闪退 / 崩溃 / crash”）；写入结果会带回同一议题下已有的相近记忆（`similar`），由 Agent 判断是新增、覆盖草稿，还是用 `supersedes` 替代旧结论。
- **不想被打扰**：在提问里写“跳过记忆”，本次对话就不查也不写。

**同义词组。** 团队里常混用的叫法登记在 `modules.yaml` 顶层，检索时查询词会自动扩展到同组的其他叫法（扩展词权重略低于原词），所有模块通用：

```yaml
synonyms:
  - [闪退, 崩溃, crash]
  - [卡顿, 掉帧, lag]
```

不知道该登记哪些时，对 Agent 说“按 pmem-normalize 技能整理同义词”：它用 `pmem terms` 列出记忆里的高频词，起草词组，你确认后写入，再用 `pmem search` 验证。

**轻量图谱与时间维度。** 不需要额外存储，全部从现有记忆推出来。`memory_graph` 工具（终端里是 `pmem graph`）给出一个模块的议题时间线：每条结论从哪天生效、哪天被哪条替代；以及相关模块：和哪些模块共用代码文件、正文里提到过哪些模块。按模块检索时结果也会附带 `related`。`search_memory` 的 `as_of` 参数（终端里是 `--as-of`）按某一天的视角检索，只看那天之前写下的记忆，用于回答“当时为什么这么定”。

也可以在终端里直接用：

```bash
pmem search --path Assets/Game/Jigsaw/JigsawReward.cs     # 按文件查
pmem search --module Puzzle "重复发放"                       # 按模块 + 关键词查（别名、同义词自动扩展）
pmem search --module Puzzle "重复发放" --as-of 2026-06-01    # 按当时的视角查
pmem record --module gameplay.Jigsaw --entity Reward --kind exclusion --content-file note.txt --alias 重复领取
pmem confirm <记忆 id>...                                    # 核对后仍然成立，刷新核对日期
pmem graph --module gameplay.Jigsaw [--entity Reward]        # 议题时间线与相关模块
pmem terms --module gameplay.Jigsaw                          # 高频词，用于整理同义词组
pmem anchors [--module X] [--apply]                          # 给没有关联代码的旧记忆补 anchors（默认只预览）
pmem list                                                    # 模块与记忆数量
```

一条记忆就是一个文件，例如 `.memory/entries/gameplay.Jigsaw/01M4X6AZN6N1AX9M6E6P34SRX4.md`：

```markdown
---
id: 01M4X6AZN6N1AX9M6E6P34SRX4
module: gameplay.Jigsaw
entity: Reward
kind: exclusion
author: zhangsan
note_date: '2026-10-14'
anchors: [Assets/Game/Jigsaw/JigsawReward.cs#Claim]
---
拼图奖励在断线重连时会重复发放：服务端 Claim 接口没有按关卡做幂等校验……不要在客户端做去重。
```

`kind` 有五种：conclusion 结论、exclusion 排除项、correction 更正、risk 风险、decision 决定。
记忆写入后不再修改正文（`confirm` 只更新 `verified` 核对日期）。要推翻旧结论，就新写一条，在 `supersedes` 里填旧记忆的 id，旧的那条会自动从检索结果中隐藏。`anchors` 是记忆关联的代码（文件或 `文件#方法`），使用前核对就靠它；从别的系统导入的旧记忆往往没有，可以用 `pmem anchors` 从正文里提到的文件名、类名自动补上。

## 衡量收益

**日常数据：`pmem report`**

```bash
pmem report --days 30          # 加 --json 可导出原始数字
```

```text
【收益】
  检索记忆 42 次，命中 31 次（74%）
  避坑提示 9 次：命中结果里含排除项、风险或更正
  跨人复用 14 次：用到了 3 位同事写的记忆
  记忆被采用：对话中返回 58 条，Agent 回复里明确用到 21 条（36%，按字面重合计，是保守下限）
【记忆使用】……返回 3 次以上却从没被用到（可能过时、写得不清楚或归错模块，值得复查）：
    [01M3...] system.Ads/Banner 返回 5 次：Banner 适配改为……
【对话对照】改了代码的对话，按“是否用到既有记忆”分组，比较 token、轮数、时长的中位数
【知识资产】……值得优先补记忆：economy.Shop、system.Ads
```

报告里的“对话对照”只是观察数据：两组对话的任务难度本来就不同，每组少于 5 个对话时报告会注明“样本不足”。

**对照实验：`pmem bench`**

从项目历史里挑出“如果当时知道某条结论就能少走弯路”的问题，写成用例（参考 [`bench/cases.yaml`](bench/cases.yaml)）：

```yaml
cases:
  - id: gate-guidance
    commit: e258c6e                      # 问题还存在的那个提交
    prompt: 描述问题，就像真实提需求，不要提示答案
    check: uv run pytest -q .bench_check  # 退出码 0 视为修好
    check_files:                          # Agent 做完后才放进去的隐藏验收
      .bench_check/test_x.py: bench/checks/test_x.py
```

```bash
pmem bench --dry-run           # 先确认用例有效：起始提交上验收应当失败
uv pip install cursor-sdk      # 或安装时用 pmem[embed,bench]
export CURSOR_API_KEY=...      # Cursor Dashboard → Integrations
pmem bench                     # 每个用例：有记忆、无记忆各跑 repeats 次
```

每次运行都在独立的 git worktree 中进行。有记忆组使用当前的记忆库和 pmem 工具，无记忆组清空记忆，两组都不加载其他 Cursor 设置。结果写入 `bench-results/summary.md`，内容是通过率、耗时、token、工具调用次数的对比。注意：这会真实消耗 Agent 额度。

## 配置

`.memory/config.yaml`（随仓库提交，团队共用）里常调的几项：

| 配置 | 说明 |
|---|---|
| `gate.mode` | `block`（默认）没查过该模块就不许改，尝试过检索即放行；`warn` 首次修改时拦一次；`off` 只靠规则 |
| `gate.analysis_reminder` | `true`（默认）对话只查了记忆、没改也没写时，结束时提醒一次 |
| `gate.watch` / `gate.ignore` | 只守护或排除哪些路径 |
| `write.default_status` | `active` 写入即生效；`draft` 需要人工审阅 |
| `embedding.backend` | `auto` / `onnx` / `ollama` / `openai` / `none` |

## 常见问题

- **Windows 上 Hook 收到的中文是乱码？** 这是 Cursor 在非 UTF-8 代码页下的转码问题，pmem 已经自动兼容。开启 Windows 设置里的“使用 Unicode UTF-8 提供全球语言支持”可以从根本上避免。
- **第一次查询很慢？** 第一次使用会下载语义模型。运行一次 `pmem doctor` 可以提前下载好。
- **`modules.yaml` 写错了？** 所有命令都会提示出错的行号；`pmem doctor` 还会检查模块覆盖率和路径重叠。
- **检索结果不对劲，或者换了嵌入模型？** 运行 `pmem reindex` 清空本机缓存并重建，同时列出无法解析的记忆文件。
- **查询明明没有相关记忆，为什么还返回了几条？** 检索总是返回得分最高的几条，由 Agent 读正文判断是否相关。用真实数据试过相关度阈值，相关和不相关的得分区间重叠，设阈值会把真命中也挡掉，所以没有加。写记忆时把常用叫法写全（如“闪退/崩溃”），比任何阈值都管用。
- **已有一套研发记忆（LanceDB 版 tilematch-dev-memory 一类），能搬过来吗？** 可以只读导入，源库不会被修改，重复执行会跳过已导入的条目：

  ```bash
  uv tool install "pmem[embed,import] @ git+https://github.com/mry-ship/pmem"
  pmem import --lancedb <源库目录> --catalog <源 modules.yaml> --author <团队名> --dry-run   # 先预览
  pmem import --lancedb <源库目录> --catalog <源 modules.yaml> --author <团队名>
  pmem reindex
  ```

  导入的类型默认都是 `conclusion`，`--guess-kind` 会按正文开头猜测排除、风险等类型。含疑似密钥的条目会被跳过并列出。`--catalog` 只在 `modules.yaml` 还没有模块时生效，导入后要给模块补上 `paths`，闸门才能按文件定位模块。
- **同一个议题写了十几条零碎记忆怎么办？** 功能连续迭代几天后很常见：检索时这些碎片互相挤占名额，还经常是同一方案的不同阶段，Agent 得自己判断哪条是最终状态。`pmem doctor` 会提示有多少议题可以合并；在 Cursor 里对 Agent 说“按 pmem-compact 技能合并记忆”，它会用 `pmem compact` 读出每个议题的全部正文，提炼成一两条现状，并用 `supersedes` 替代旧记忆。旧文件仍保留在版本库里，只是不再被检索到。在 TileMatch 的真实数据上，一个 13 条、2500 字的议题合并成 2 条、约 1150 字；相关查询从前 3 条全是互相矛盾的碎片，变成第 1 条就是完整现状。
- **用 SVN 可以吗？** 可以。作者和版本号取自 SVN，新记忆会自动 `svn add`。
- **Hook 出错会不会卡住我？** 不会。Hook 任何异常都会直接放行，错误写入用户缓存目录的 `hook-errors.log`，`pmem doctor` 会显示最近的错误。

架构与设计取舍见 [docs/architecture.md](docs/architecture.md)。
