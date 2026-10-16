# pmem：给 AI 编程助手挂一个项目记忆

> **绑定一次，之后自动运行。** AI 改代码前会先查这个模块以前的结论，得出新结论后再记下来。
> 记忆是仓库里的 Markdown 文件，跟代码一起提交、团队共享，不需要服务器，也不上传任何数据。
> 支持 Cursor、Claude Code、Codex。

📖 [图文使用手册](https://mry-ship.github.io/pmem/pmem-guide.html) · [Wiki](https://github.com/mry-ship/pmem/wiki)

## 它做什么

- **改前先查**：AI 要改某个文件时，pmem 找到它所属的业务模块（如 `gameplay.Jigsaw`），把以前的根因、排除过的方向、风险交给 AI。
- **问答也查**：AI 读到或在某个模块里搜索代码时，自动附上该模块现行结论的摘要；问题提到的、或本轮看过代码的模块没查过，回合结束时要求 AI 查过再核对一遍回答。
- **改后记录**：确认根因、排除了某个方向、改完验证通过时，AI 按模块写一条记忆。
- **自动兜底**：AI 忘了查就去改，Hook（工具调用前后自动执行的脚本）会拦下修改，并在拦截提示里直接列出该模块的排除项、风险和更正，直到查过为止；改了代码却没记，回合结束时提醒一次。
- **不用过期结论**：记忆关联的代码后来改过或被删了，检索结果、读代码摘要、模块全貌和 Wiki 里都会标出“需核实”。关联代码写到函数（`路径#函数名`）时按函数判断，同文件里改别的函数不算。

![一次对话的流程](docs/images/pmem-flow.svg)

## 接入（约 5 分钟）

```bash
# 1. 安装（每人一次）
uv tool install "pmem[embed] @ git+https://github.com/mry-ship/pmem"

# 2. 在项目根目录绑定（每个项目一次）
pmem init --type game            # 项目类型：game / app / backend / generic
```

3. **打开开关**：Cursor 设置 → MCP → 启用 `pmem`（Claude Code、Codex 首次打开项目时批准即可）。
4. **划分模块**：对 AI 说“按 pmem-bootstrap 技能划分模块”，确认它给出的表格。
5. **提交**：运行 `pmem doctor` 自检，然后把 `.memory/` 和 `.cursor/` 提交到版本库。

队友拉代码后，只需要做第 1 步和第 3 步。需要 [uv](https://docs.astral.sh/uv/)（Python 包管理工具）和 Python 3.10 以上。

## 日常使用

正常提需求、修 bug 即可，不用做额外的事。

| 你说 | 效果 |
|---|---|
| 跳过记忆 | 这次对话不查也不写；AI 第一次读代码时会说明记忆已关闭 |
| 恢复记忆 | 撤销本对话的“跳过记忆” |
| 按 pmem-compact 技能合并记忆 | 同一议题的零碎记忆合并成一条 |
| 按 pmem-normalize 技能整理同义词 | 登记“闪退 / 崩溃”这类不同叫法，换个说法也能搜到 |

一条记忆就是一个文件，例如 `.memory/entries/gameplay.Jigsaw/01M4X6AZN6N1AX9M6E6P34SRX4.md`：

```markdown
---
module: gameplay.Jigsaw
entity: Reward
kind: exclusion          # conclusion 结论 / exclusion 排除项 / correction 更正 / risk 风险 / decision 决定
anchors: [Assets/Game/Jigsaw/JigsawReward.cs#Claim]
---
断线重连时奖励重复发放：根因是服务端 Claim 没有按关卡做幂等校验，不要在客户端去重。
```

## 维护

| 什么时候 | 做什么 |
|---|---|
| 提交代码时 | 把 `.memory/` 里新增的记忆一起提交 |
| 新增业务模块 | 在 `.memory/modules.yaml` 里加模块和它的路径 |
| 不定期 | `pmem doctor` 体检；它会提示没提交的记忆和可以合并的议题 |
| 想看效果 | `pmem report`：命中率、避坑次数、跨人复用 |
| 想通读全部结论 | 打开 `.memory/wiki/index.md`：每模块一页，含议题、现行结论、相关模块和代码链接，关联代码之后改过的标“需核实”。每次写入记忆后自动重新生成，也可手动 `pmem wiki` |
| 升级 | `uv tool upgrade pmem`，再在项目里运行一次 `pmem init` 刷新 Hook 配置（不会覆盖已有的 config.yaml、modules.yaml）；`pmem doctor` 发现配置是旧版时会提示 |

## 效果

**和没有记忆系统相比**（一个游戏项目的真实对话，改过代码的对话：没有记忆时 122 个，有记忆后 62 个）：

| 指标 | 没有记忆 | 有记忆 |
|---|---|---|
| 被用户纠正的比例 | 基准 | **下降 54%～69%** |
| 每次改代码的耗时 | 基准 | **下降 36%～44%** |
| 读写 token 总量 | 基准 | **下降 18%** |
| 长对话全程不回退 | 27% | **52%** |

这组数据是同一项目上一代记忆服务上线前后的对比，不是对照实验；pmem 自己的端到端对比还没测（可以用 `pmem bench` 做）。

**和上一代记忆服务相比**（853 条真实记忆离线回放）：18 个人工核对的查询里，正确结论排进前 3 的从 6 个提高到 16 个；单次检索从 300～400 毫秒降到中位 9 毫秒；写进去的记忆不会再被悄悄删掉（上一代约 19%）。

## 效率与 token

pmem 本身会额外消耗一些 token，换来的是少走弯路、少返工。以下在本仓库实测（11 个模块，记忆合计约 3.5 万 token；按 GPT-4o 的分词计算，其他模型相近）：

| 什么时候 | 额外 token | 额外耗时 |
|---|---|---|
| 每个对话：加载规则 | 约 850 | 无 |
| 每个模块每个对话一次：检索（默认 5 条） | 中位约 1500，最多约 2600 | 检索约 10 毫秒 |
| 读到某模块代码时附摘要（每模块每对话一次） | 约 530 | Hook 约 0.3 秒 |
| 没查就改被拦下 | 约 115 | Hook 约 0.3 秒 |
| 其他工具调用 | 0 | Hook 约 0.2 秒 |

- **记忆再多也不会线性增长**：AI 不直接读记忆文件，只拿检索返回的前几条，被替代的旧结论不返回；853 条记忆的项目单次开销和这里基本一样。
- **一个典型修 bug 对话**：涉及 1～2 个模块，额外约 3000～5000 token；一次因为不知道旧结论而改错、返工，通常就不止这个数。上面的对比里，算上少走的弯路，读写 token 总量反而下降了 18%。
- **想再省**：`.memory/config.yaml` 里可以关掉读代码摘要（`gate.read_digest`）和问答审查（`gate.question_review`）；说“跳过记忆”则本对话完全不查不写。

## 常用命令

```bash
pmem search --path <文件>              # 查某个文件所属模块的记忆
pmem search --module <模块> "关键词"    # 按模块和关键词查；加 --brief 每条一行
pmem list                              # 模块和记忆数量
pmem doctor                            # 体检
pmem report                            # 本机收益报告
pmem wiki                              # 生成浏览用的模块 Wiki
```

全部命令、配置项和常见问题见 [使用手册](https://mry-ship.github.io/pmem/pmem-guide.html)；设计取舍见 [架构说明](docs/architecture.md)。

## 已知限制

- Claude Code、Codex 的接入只做过模拟测试，还没在真实会话里跑过。
- Cursor 不允许在提问时注入内容，所以纯问答（不读代码）的记忆审查发生在回合结束时：AI 先回答，再被要求查记忆并修正。Claude Code 可以在提问时直接附上摘要。
- 收益报告只统计本机数据。
- 终端里的写操作靠解析命令识别：重定向、`Set-Content`、`cp`/`mv`、`git checkout/restore/apply`、`python -c`、套一层的 `powershell -Command`/`cmd /c`/`bash -c`、先 `cd` 再写相对路径，以及所运行脚本里的字面路径都能认出。脚本里拼接出来的路径、格式化工具和 `git stash`/`reset` 这类不认识的命令事前认不出：命令执行后比对未提交文件（Git、SVN 都支持），改到没查过的模块时立即提醒补查（只能事后提醒，拦不住）。仓库大到单次比对超过 1 秒时，这项比对暂停 24 小时。
- 队友没装 pmem 时，闸门和审查都不生效（Hook 起不来，按设置放行，不会卡住）；新对话开始时的 Hook 经 `.memory/bin/pmem-hook` 调用，会提示 Agent 让用户先安装。
- 按函数判断过期只支持 Git；SVN 和找不到函数时按文件判断。
- Windows PowerShell 5 里把 pmem 输出再接给 `Select-String` 等命令会乱码（它按 GBK 解码），直接看输出或用 `--brief`。
