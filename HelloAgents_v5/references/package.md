# 方案包生命周期（HelloAgents_v5）

## 路径规范

- 工作区：`helloagents/plan/YYYYMMDDHHMM_<feature>/`
- 历史区：`helloagents/history/YYYY-MM/YYYYMMDDHHMM_<feature>/`

## 必需文件

- `why.md`
- `how.md`
- `task.md`

## task.md 结构（implementation 推荐）

- 必须包含 `DAG（依赖关系图）`（表达依赖，不等于时间顺序）
- 必须包含 `快速落地路径（推荐执行顺序，不必机械按章节顺序）`（用 Step 1..N 显式引用任务编号，给出最短可运行闭环）

## 元数据标记（推荐）

为提升一致性与可预测性，方案包文件允许携带以下元数据行（建议置于首个标题后，脚本与人工流程保持一致）：

- `> **@pkg_type:** implementation|overview`（`why.md/how.md/task.md`）
  - `overview`：用于共识沉淀，不进入开发实施阶段（`develop` 视为不可执行）
  - `implementation`：可执行方案包（默认）
- `> **@status:** completed|skipped | YYYY-MM-DD HH:mm`（`task.md`）
  - 迁移到 `history/` 前/后用于标记执行结论与时间戳
- `> **@final_confirm:** YES|NO（...）`（`why.md`）
  - 最终执行前的“收口定稿”确认标记：只有 `YES（已收口定稿，仅按此口径执行）` 才允许进入 `develop` 写入
  - 由 `scripts/validate_package.py <package> --require-finalized` 强制门禁（要求 `final_gate.score=10`）

无脚本环境下的手动创建/校验/迁移细则见：`references/rules/noscript.md`。

## 状态符号

- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 跳过
- `[?]` 待确认

## 生命周期

1. 设计阶段创建方案包。
2. 实施阶段按 `task.md` 逐条执行并更新状态。
3. 完成后迁移到 `history/` 并更新 `history/index.md`。

## 遗留方案处理

- 阶段结束扫描 `plan/` 遗留方案包。
- 用户可选择迁移或保留。

## 校验项

- 目录命名合法。
- 三个必需文件存在且非空。
- `task.md` 至少包含一个任务项。
