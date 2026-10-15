---
name: pmem-bootstrap
description: 为项目首次划分 pmem 模块并写入 .memory/modules.yaml。用户说“划分模块”“按 pmem-bootstrap”“初始化记忆模块”时使用。
---
<!-- 由 pmem init 生成，重新运行 pmem init 会覆盖；如需调整请改 .memory/config.yaml -->
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
