# pmem：给 Cursor 用的项目研发记忆

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
| 记忆被采用 | 返回给 Agent 的记忆里，有多少条在它的回复中被明确用到（保守下限） |
| 闸门 / 提醒转化 | 被提醒“先查再改”“改完记一下”之后，有多少次真的照做了 |
| 知识资产 | 有记忆的模块占比；只有一位作者的模块；近半年改动多却还没有记忆的模块 |

想要更硬的证据，可以用 `pmem bench` 做对照实验：同一个任务，有记忆跑一遍、没记忆跑一遍，比较成功率、token、耗时和工具调用次数。见下文“衡量收益”。

## 5 分钟接入

前提：已安装 [uv](https://docs.astral.sh/uv/)、Python ≥ 3.10、Cursor；项目使用 Git 或 SVN（也可以都不用）。

**1. 安装（每人一次）**

```bash
uv tool install "pmem[embed] @ git+<pmem 仓库地址>"
```

`[embed]` 会启用中文语义检索：首次使用时下载约 90 MB 的模型，所有项目共用。不需要语义检索可以去掉 `[embed]`，此时只用关键词检索。

**2. 在项目根目录初始化（每个项目一次）**

```bash
pmem init --type game      # 可选 game / app / backend / generic，决定默认的模块大类
```

它会生成 `.memory/`（配置、模块目录、记忆）和 `.cursor/`（规则、技能、Hooks、MCP 配置）。已有的 Cursor 配置只会合并，不会覆盖。

**3. 在 Cursor 里启用（每人一次）**

打开 Cursor 设置 → MCP，把 `pmem` 打开。这一步只能手动完成。

**4. 划分模块（每个项目一次）**

在 Cursor 里对 Agent 说：“按 pmem-bootstrap 技能划分模块”。Agent 会扫描目录和最近的提交热度，生成 `.memory/modules.yaml`，你确认即可。
一个模块是一个业务单元（例如 `gameplay.Jigsaw`），不是一个目录：它可以包含多个路径，也可以起别名。

**5. 自检并提交**

```bash
pmem doctor                 # 检查配置、模块覆盖率、Cursor 接入、语义模型
git add .memory .cursor && git commit -m "接入 pmem"
```

团队其他人拉下代码后，只需要做第 1 步和第 3 步。

## 日常怎么用

基本什么都不用做：

- **改代码前**：Agent 按规则先查要改文件所属模块的记忆。它忘了也没关系，Hooks 会在它第一次修改“有记忆的模块”时拦一下，提示它先查。
- **得出结论后**：只在三个时机写记忆：确认根因、排除某个方向或定下方案、改完并验证通过。一轮对话结束时，如果改了模块却没写记忆，会提醒一次；没有新结论的话回复“无需记录”即可。
- **不想被打扰**：在提问里写“跳过记忆”，本次对话就不查也不写。

也可以在终端里直接用：

```bash
pmem search --path Assets/Game/Jigsaw/JigsawReward.cs     # 按文件查
pmem search --module Puzzle "重复发放"                       # 按模块 + 关键词查（别名自动归一）
pmem record --module gameplay.Jigsaw --entity Reward --kind exclusion --content-file note.txt
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
记忆写入后不再修改。要推翻旧结论，就新写一条，在 `supersedes` 里填旧记忆的 id，旧的那条会自动从检索结果中隐藏。如果锚点代码后来改了，检索结果会带上 `stale: true`，提示需要核实。

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
| `gate.mode` | `off` 只靠规则；`warn`（默认）首次修改有记忆的模块时拦一次；`block` 没查过就不许改 |
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
  uv tool install "pmem[embed,import] @ git+<pmem 仓库地址>"
  pmem import --lancedb <源库目录> --catalog <源 modules.yaml> --author <团队名> --dry-run   # 先预览
  pmem import --lancedb <源库目录> --catalog <源 modules.yaml> --author <团队名>
  pmem reindex
  ```

  导入的类型默认都是 `conclusion`，`--guess-kind` 会按正文开头猜测排除、风险等类型。含疑似密钥的条目会被跳过并列出。`--catalog` 只在 `modules.yaml` 还没有模块时生效，导入后要给模块补上 `paths`，闸门才能按文件定位模块。
- **用 SVN 可以吗？** 可以。作者和版本号取自 SVN，新记忆会自动 `svn add`。
- **Hook 出错会不会卡住我？** 不会。Hook 任何异常都会直接放行，错误写入用户缓存目录的 `hook-errors.log`，`pmem doctor` 会显示最近的错误。

架构与设计取舍见 [docs/architecture.md](docs/architecture.md)。
