# pmem：给 AI 编程助手挂一个项目记忆

> **绑定一次，之后自动运行。** AI 改代码前会先查这个模块以前的结论，得出新结论后再记下来。
> 记忆是仓库里的 Markdown 文件，跟代码一起提交、团队共享，不需要服务器，也不上传任何数据。
> 支持 Cursor、Claude Code、Codex。

📖 [图文使用手册](https://mry-ship.github.io/pmem/pmem-guide.html)

## 它做什么

- **改前先查**：AI 要改某个文件时，pmem 找到它所属的业务模块（如 `gameplay.Jigsaw`），把以前的根因、排除过的方向、风险交给 AI。
- **问答也查**：AI 读到某个模块的代码时，自动附上该模块现行结论的摘要；问题提到的模块本轮没查过，回合结束时要求 AI 查过再核对一遍回答。
- **改后记录**：确认根因、排除了某个方向、改完验证通过时，AI 按模块写一条记忆。
- **自动兜底**：AI 忘了查就去改，Hook（工具调用前后自动执行的脚本）会拦下修改，直到查过为止；改了代码却没记，回合结束时提醒一次。
- **不用过期结论**：记忆关联的代码后来改过或被删了，检索时会标出“需核实”。

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
| 跳过记忆 | 这次对话不查也不写 |
| 无需记录 | 回应结束提醒：这次没有新结论 |
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
| 想通读全部结论 | `pmem wiki`：生成每模块一页的 Markdown（默认 `.memory/wiki/`），含议题、现行结论、相关模块和代码链接 |
| 升级 | `uv tool upgrade pmem` |

## 效果

在一个游戏项目的 853 条真实记忆上实测：

- **检索更准**：18 个人工核对的查询里，正确结论排进前 3 的有 16 个；上一代记忆服务只有 6 个。
- **更快**：单次检索中位 9 毫秒。
- **省 token**：每次只返回最相关的几条，记忆再多单次开销也基本不变。

同一项目里，“有项目记忆”和“没有记忆”相比，被用户纠正的比例下降 54%～69%，改代码耗时下降 36%～44%。这是上一代记忆服务上线前后的对比；pmem 自身的端到端收益还没测。

## 常用命令

```bash
pmem search --path <文件>              # 查某个文件所属模块的记忆
pmem search --module <模块> "关键词"    # 按模块和关键词查
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
