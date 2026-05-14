# 知识库服务（HelloAgents_v5）

> 目的：统一知识库（`helloagents/`）的创建/读取/同步约定，确保“文档反映代码真实状态”。

## 1. SSOT 结构（摘要）

详细结构以 `kb/SKILL.md` 为准；典型形态：

```text
helloagents/
├── CHANGELOG.md
├── project.md
├── wiki/overview.md
├── wiki/{arch,api,data}.md
├── wiki/modules/<module>.md
├── wiki/memories/index.md
├── plan/YYYYMMDDHHMM_<feature>/{why,how,task}.md
└── history/index.md
```

## 2. 上下文获取策略（推荐顺序）

1. 若知识库已存在：优先读 `project.md`、`wiki/overview.md`、相关 `wiki/modules/*.md`。
2. 若知识库缺失或信息不足：再扫描代码库补齐（避免一次性读取过多无关文件）。

## 3. 同步原则（必须）

- **代码是执行事实真相源**：当文档与代码不一致时，默认更新文档以匹配代码（除非代码明显是 bug，且本次任务目标就是修复它）。
- **最小必要更新**：只更新与本次变更相关的模块/接口/数据/流程。

## 4. 同步触发与落点（最小）

- **模块行为变更**：更新 `wiki/modules/<module>.md`（入口定位 + 真相源索引 + 回归入口）。
- **接口变更**：同步到 `wiki/api.md`（索引为主，避免复制大段实现）。
- **数据/DDL 变更**：同步到 `wiki/data.md`。
- **跨模块/重要变更**：建议补一条记忆体 `wiki/memories/<module>/<id>_<slug>.md`，并登记到 `wiki/memories/index.md`。
- **每次交付**：按 `templates/changelog-template.md` 更新 `CHANGELOG.md`，并确保 `history/index.md` 有可追溯索引。

## 5. 开关与边界

- `KB_CREATE_MODE`：是否自动创建/补齐知识库结构，详见 `kb/SKILL.md` 与 `references/state.md`。
- 若用户明确要求“不写任何文档/不创建 helloagents/”：必须先说明“知识库同步为交付必做项”；仅当用户二次确认仍要求跳过时才允许跳过，并在最终输出中标注风险。
