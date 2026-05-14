# 状态管理（HelloAgents_v5）

## 状态变量

- `WORKFLOW_MODE`: `INTERACTIVE | AUTO_FULL | AUTO_PLAN`
- `CURRENT_STAGE`: `EVALUATE | TWEAK | ANALYZE | DESIGN | DEVELOP | KB`
- `SCRIPTS_ENABLED`: `true/false`（默认 `true`；用户要求无脚本或脚本不可用时置为 `false`，并按 `references/rules/noscript.md` 执行）
- `MODE_EXECUTION`: `true/false`
- `HA_MULTI_AGENT`: `auto/off`（默认 `auto`；`off` 表示禁用所有子代理，按单代理串行执行；注意这与 Codex 配置的 `[features].multi_agent` 是不同概念：前者是“流程开关”，后者是“能力是否可用”）
- `HA_EXPLORER_SLICES`: `auto/off/2/4`（默认 `auto`；控制 explorer 分片并行：`off` 禁用 explorer 子代理；`2/4` 强制 slice 数；`auto` 按需求自动选择 2~4）
- `DELIVERY_MODE`: `NORMAL | CLOSE_LOOP`（默认 `NORMAL`；两种模式均要求同步知识库；`CLOSE_LOOP` 额外强制：记忆体 + 本地 git commit）
- `KB_CREATE_MODE`: `0 | 1 | 2 | 3`（可选；默认 `1`）
  - `0=OFF`：不自动创建/重建知识库结构（仅在用户显式 `~init/~upgrade` 或明确同意时执行）
  - `1=ON_DEMAND`：按需提示执行 `~init`，不自动创建
  - `2=ON_DEMAND_AUTO_FOR_CODING`：在编码/交付类任务中，知识库缺失时允许自动创建
  - `3=ALWAYS`：尽量保持知识库结构完整（缺失则创建/补齐）
- `CREATED_PACKAGE`: 当前设计阶段创建的方案包路径
- `CURRENT_PACKAGE`: 当前执行阶段选中的方案包路径
- `KB_SKIPPED`: 是否跳过知识库操作（默认不跳过；仅用户强制要求且二次确认后允许）

## 用户覆写（提示词开关）

用户可以在提示词中写下列开关来覆写默认行为（不写则保持默认自动策略）：

- `HA_MULTI_AGENT=off`：强制禁用多代理（不 spawn 任何子代理）
- `HA_EXPLORER_SLICES=off|2|4`：控制 explorer 分片并行（仅影响 explorer；除非同时禁用 `HA_MULTI_AGENT`）

## 命令触发状态设置

- `~auto`：`WORKFLOW_MODE=AUTO_FULL`，`CURRENT_STAGE=EVALUATE`
- `~ship`：`WORKFLOW_MODE=AUTO_FULL`，`CURRENT_STAGE=EVALUATE`，`DELIVERY_MODE=CLOSE_LOOP`
- `~plan`：`WORKFLOW_MODE=AUTO_PLAN`，`CURRENT_STAGE=EVALUATE`
- `~exec`：`MODE_EXECUTION=true`，`CURRENT_STAGE=DEVELOP`
- `~init/~upgrade`：`CURRENT_STAGE=KB`
- 其他命令：按需设置，不强制进入完整流程

## 阶段流转

- `EVALUATE` 判定 `TWEAK` → `TWEAK`
- `EVALUATE` 判定 `LIGHT/STANDARD` → `ANALYZE`
- `ANALYZE` 完成 → `DESIGN`
- `DESIGN` 确认后 → `DEVELOP`
- `DEVELOP` 完成 → 结束并清理状态

## 状态重置协议

在以下场景清理临时状态：
- 流程完成
- 用户取消
- 严重错误终止

清理项：
- `CURRENT_STAGE`
- `MODE_EXECUTION`
- `CREATED_PACKAGE`
- `CURRENT_PACKAGE`
- `SCRIPTS_ENABLED`
- `DELIVERY_MODE`
