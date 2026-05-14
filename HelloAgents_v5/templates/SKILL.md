---
name: templates
description: 文档模板集合；创建Wiki或方案包文件时读取；包含所有知识库模板和方案文件模板
---

# 文档模板集合（HelloAgents_v5）

> 本 SKILL 只负责“模板导航 + 选择建议”。模板真相源在 `templates/` 目录下的具体文件中。
> 若本文与模板文件内容不一致，以模板文件为准。

## 0. 使用原则（必须）

1. 将模板中的 `[...]` / `{...}` 占位符替换为实际内容。
2. **语言规范**：除代码标识符/命令/日志外，默认使用中文；必要时保留英文技术术语。
3. **最小必要**：只读取并填充你当前要用的模板文件，避免把所有模板一次性加载进上下文。
4. **真相源优先**：模板文件为真相源；脚本/文档若引用模板，以模板文件为准。

更完整的“模板落地/存在性检查/脚本降级”规则见：`references/services/templates.md`。

## 1. 场景 → 模板选择

- **输出格式（SSOT）**：`output-format.md`
- **方案包（why/how/task）**：`plan-why-template.md`、`plan-how-template.md`、`plan-task-template.md`
- **变更记录（Changelog）**：`changelog-template.md`
- **变更历史索引（history/index.md）**：`history-index-template.md`
- **知识库（wiki）**：
  - 总览：`wiki-overview-template.md`
  - 架构：`wiki-arch-template.md`
  - API：`wiki-api-template.md`
  - 数据模型：`wiki-data-template.md`
  - 模块页：`wiki-module-template.md`
  - 记忆体单页：`wiki-memory-template.md`
  - 记忆体索引：`wiki-memories-index-template.md`
- **项目技术约定（project.md）**：`project-template.md`
- **版本号定位参考（可选）**：`version-source-map.md`

## 2. 模板清单（按典型落点）

> 说明：落点以 `helloagents/` 知识库结构为参考；具体以项目实际结构与脚本约定为准。

### 2.1 对话输出 SSOT（不落盘）

- `output-format.md`：阶段输出/等待确认/取消/错误的统一格式。

### 2.2 方案包（plan/）

- `plan-why-template.md` → `helloagents/plan/YYYYMMDDHHMM_<feature>/why.md`
- `plan-how-template.md` → `helloagents/plan/YYYYMMDDHHMM_<feature>/how.md`
- `plan-task-template.md` → `helloagents/plan/YYYYMMDDHHMM_<feature>/task.md`

### 2.3 变更记录与索引

- `changelog-template.md` → `helloagents/CHANGELOG.md`
- `history-index-template.md` → `helloagents/history/index.md`

### 2.4 知识库（wiki/）

- `project-template.md` → `helloagents/project.md`
- `wiki-overview-template.md` → `helloagents/wiki/overview.md`
- `wiki-arch-template.md` → `helloagents/wiki/arch.md`
- `wiki-api-template.md` → `helloagents/wiki/api.md`
- `wiki-data-template.md` → `helloagents/wiki/data.md`
- `wiki-module-template.md` → `helloagents/wiki/modules/<module>.md`
- `wiki-memories-index-template.md` → `helloagents/wiki/memories/index.md`
- `wiki-memory-template.md` → `helloagents/wiki/memories/<module>/<id>_<slug>.md`（或 `<id>.md`，以项目约定为准）

### 2.5 参考材料（按需）

- `version-source-map.md`：用于定位“版本号从哪里读/怎么递增”，常用于更新 `CHANGELOG.md`。

## 3. 推荐使用流程

1. 先根据你的任务选择 **1 个**模板文件。
2. 直接读取该模板文件内容并填充占位符。
3. 写入目标文件后，补齐必要的交叉链接（如 `history/index.md` 指向归档、`CHANGELOG.md` 指向方案包/记忆体）。
