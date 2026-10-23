# pmem v0.6 模块规格实施计划

- 日期：2026-10-23
- 依据：`docs/superpowers/specs/2026-10-23-pmem-module-spec-design.md`
- 状态：M1–M4 已实现（2026-10-23）。同日补上美术设计一节：无画面写「本模块无画面」，不计入首稿未完成。同日又补上目录的留空列，以及技能里的三处缺口：旧稿没有美术节时插进去、父模块不复制子模块正文、正文不靠打开文件。`pmem init` 不改已有 config.yaml，缺省由读取时合并。迁移规格文件（rename/merge）仍未做。不在本计划里直接改安装包版本号。

**目标**：每个已登记模块一份可提交的当前规格。命令行负责骨架、目录和「这轮改过但规格没写」的判定；正文由 `pmem-spec` 技能按模块写入。更新发生在改动的那一轮，每个模块一次，不整篇覆盖。

**架构**：新代码放在 `src/pmem/generate/spec.py`（骨架、文首事实、索引、写出保护）和 `src/pmem/cli/spec_cmd.py`（命令）。提醒放在现有 `hooks/reminders.py`，规格写入的登记放在 `hooks/gate.py` 的工具调用之后。技能模板放在 `generate/templates.py`，由 `generate/integrations.py` 的 `_write_skills` 写到各 Agent。

**技术栈**：与仓库现有一致。测试 `uv run pytest -q`，风格 `uv run ruff check src tests`。仓库根目录 `c:\Users\ZhengLangPC\Desktop\Cursor-Project-Memory`。

---

## 里程碑

| 里程碑 | 内容 | 验收 |
|---|---|---|
| M1 | 规格文件、`pmem spec` / `init` / `index` / `--check` | `tests/test_spec.py` 通过；再次 init 不覆盖三节正文 |
| M2 | `pmem-spec` 技能模板，并在 `pmem init` 时写入 | 模板含首稿、当轮分段更新、新模块当轮写全策划；`pmem init` 不覆盖已有 config |
| M3 | 回合结束提醒，`spec_written` 登记 | 改了模块没写规格会提醒一次；无需记录、免记录文件、写过规格文件时不提醒 |
| M4 | 手册、架构说明、总设计第 11 节补上 `pmem spec` | 三处都能找到命令；Wiki 的说明不变 |

路线表（README 与总设计第 14 节）在立项时已经改：v0.6 是模块规格，类型安全改为 v0.7。M4 不再改版本归属。

---

## M1 骨架与命令

- [x] **失败测试先写在 `tests/test_spec.py`**
  - `init` 为一个已登记模块写出 `.memory/specs/<模块>.md`：三节标题、文首事实标记、`spec:empty`、策划节的 `spec:design-gap`。
  - 手改三节后再 `init`，三节字节级不变，缺文件的其他模块仍会补骨架。
  - `index` 重写 `index.md`，并只更新 `spec:facts` 标记之间的路径和上下级。
  - 模块名含 `..` 或 `spec.dir` 指到项目外时不写文件，命令返回 2。
  - `--check` 在仍有 `spec:empty` 时返回 1，全部首稿完成时返回 0。`pmem spec` 不加 `--check` 时只打印，返回 0。
  - 废弃模块出现在列表里，标为不要求补，`--check` 不计它。
- [x] 运行 `uv run pytest tests/test_spec.py -q`，确认因缺少实现而失败。
- [x] 实现 `src/pmem/generate/spec.py`：沿用 Wiki 的文件名校验（可抽共用函数，不改 Wiki 的生成结果）。
- [x] `src/pmem/core/config.py` 的默认配置增加 `spec.dir: .memory/specs`、`spec.reminder: true`。`generate/templates.py` 的配置模板同步这两行。
- [x] `src/pmem/cli/main.py` 增加子命令 `spec`，转到 `cli/spec_cmd.py`。`--check`、`init`、`index`、`--root`。
- [x] 再跑 `tests/test_spec.py`，然后 `uv run ruff check src tests`。

## M2 技能

- [x] 在 `generate/templates.py` 增加 `SPEC_SKILL`，`integrations.py` 的 `_write_skills` 增加 `pmem-spec`。
- [x] 技能写明：先 `pmem spec` 看缺谁；首稿读该模块路径，写程序和现状，策划只写代码里看得到的四类，其余保留 `spec:design-gap`；当轮更新只改正波及段落；新模块当轮写全策划；写前 `search_memory` 核对功能记录；一轮一个模块只写一次。
- [x] 测试：渲染后的技能正文含这几条约束；对已有项目跑 init 合并时，不覆盖用户的 `spec.dir`。对照现有「init 不覆盖配置」的测试放在同一处或 `tests/test_spec.py`。

## M3 提醒

- [x] 失败测试：本轮 `edited` 含某模块、规格文件不在 `spec_written` 时，`on_stop` 的 `followup_message` 点名该模块，并写明不要整篇重写。
- [x] 同一模块声明「无需记录」、或改动的文件都在 `gate.record_exempt`、或 `spec_written` 已有该模块、或 `spec.reminder` 为 false、或 `gate.mode` 为 off 时，不提醒。
- [x] 每个模块只提醒一次（与现有 `nudged` 一样，规格用单独的状态键，避免和功能记录的提醒互相抵消）。
- [x] `hooks/gate.py` 在工具调用之后：路径落在 `spec.dir` 且文件名对应某模块时写入 `spec_written`。该路径仍被 `gate.ignore` 挡住，不进入 `edited`。
- [x] 测试放在 `tests/test_reminders.py`（若现有结束提醒测试在别的文件，跟到那个文件）。跑相关测试与 `uv run ruff check src tests`。

## M4 文档

- [x] `docs/pmem-guide.html` 的命令表和配置示例加上 `pmem spec`、`spec.dir`、`spec.reminder`。
- [x] `docs/architecture.md` 的 `generate` 包说明和命令分发表加上 spec。
- [x] `docs/superpowers/specs/2026-10-14-pmem-design.md` 第 11 节命令表加上 `pmem spec`。
- [x] README 的维护表加一行：看模块当前规格、补首稿。路线表不再改版本归属。
- [x] 不改 Wiki 的生成、gitignore 和「需核实」行为。相关 Wiki 测试保持通过。

## 迁移

- `migrate rename` / `merge` 把 `.memory/specs/<旧>.md` 改到新模块名。并入 M1 若改动面小，否则在 M1 之后单列任务，并给 `tests/test_spec.py` 加一条改名后的路径断言。
- 拆分和废弃不自动改四节正文。`pmem spec` 的文字说明即可。
