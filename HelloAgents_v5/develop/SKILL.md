---
name: develop
description: 开发实施阶段规则；按方案包执行代码改动、验证测试、同步知识库并迁移历史。
---

# 开发实施（P）

## 目标

- 将方案包转化为可验证交付物，并完成文档与历史归档闭环。

## 合法进入条件（满足其一）

1. 方案设计后用户强确认“确认开始实现”。
2. `~auto` 模式持续推进。
3. `~exec` 命令直接执行现有方案包。

## 进入前置校验（强制）

在开始任何写入（代码/配置/知识库/方案包状态）之前，必须先校验“合法进入条件”是否满足。若不满足：
- 使用 `templates/output-format.md` 的 **G6.2 路由/验证错误**格式输出
- 回退到 `design`（或停在只读分析，等待用户确认）

## 执行步骤

1. 选定方案包（必须完整）
   - 自动模式优先使用当前创建包（`CREATED_PACKAGE`）。
   - 执行模式支持用户选择目标方案包。
   - 需要枚举方案包时：
     - `SCRIPTS_ENABLED=true`：按 `references/rules/tools.md` 调用 `scripts/list_packages.py`（必要时加 `--history`）。
     - `SCRIPTS_ENABLED=false`：按 `references/rules/noscript.md#6-手动枚举方案包` 手动枚举。
   - 建议先校验：
     - `SCRIPTS_ENABLED=true`：按 `references/rules/tools.md` 调用 `scripts/validate_package.py <package-name>`。
     - `SCRIPTS_ENABLED=false`：按 `references/rules/noscript.md#5-手动校验方案包` 校验必需文件与任务统计。

   - **最终收口定稿门禁（强制，执行评分必须=10）**
     - 目的：确保执行阶段只有一个最终口径，不残留可选/多选/占位符/待确认项。
     - `SCRIPTS_ENABLED=true`：必须运行 `scripts/validate_package.py <package-name> --require-finalized`。
     - 通过条件：输出 `final_gate.score=10` 且 `final_gate.passed=true`。
     - 若未通过：必须回退到 `design` 收口定稿并修正方案包；**禁止进入任何写入**（代码/配置/知识库/方案包状态）。
     - 定稿确认落点（必须）：在 `why.md` 写入元信息 `> **@final_confirm:** YES（已收口定稿，仅按此口径执行）`（推荐用脚本：`scripts/update_package_metadata.py <package-name> --final-confirm YES`，避免手改格式错误）。
     - 交互要求（强制）：只允许向用户提出“单一确认问题”（例如：`确认收口定稿`），禁止再给“可选/多选”选项；AUTO_FULL 模式下若未定稿同样必须停下等待确认（不可自动代替用户确认）。

2. 读取任务清单
   - 执行顺序以 `task.md` 的 `DAG（依赖关系图）` 为准：依赖满足即可提前执行，不必机械按章节编号。
   - 推荐先按 `快速落地路径（推荐执行顺序）` 走最小闭环（vertical slice），再按 DAG 补齐支线任务。
   - 任务状态：`[ ] [√] [X] [-] [?]`。
   - 若执行过程中发现“影响面/风险/跨端”导致复杂度升级（或与 `why.md` 元信息不一致）：必须更新 `why.md` 的 `@complexity_review`（脚本：`scripts/update_package_metadata.py`；无脚本：手工更新元信息行），并在输出中说明升级原因与新增门禁。

3. 开始改动前强确认（安全门禁）
   - 若 `WORKFLOW_MODE=AUTO_FULL`：视为用户已授权连续执行，可跳过口令门禁；但必须在输出中显式标注“当前为 AUTO_FULL，将直接写入”。（见 `references/state.md`）
   - 交互模式强确认口令（任一匹配即视为确认）：`确认开始实现` / `确认开始代码实现` / `确认开始落地`
   - 未确认时：必须使用 `templates/output-format.md` 的 **G6.4 交互询问输出格式** 输出“强确认：是否开始实现”，并停止；只允许继续只读分析与解释，不允许任何写入（代码/配置/知识库/方案包状态）。

4. 逐项实现与最小改动
   - 先定位再修改。
   - 每次改动应可回溯到任务项。
   - 受控并行写入（可选，用于加速；不满足条件则禁用）
     - `multi_agent` 可用性门禁（强制）：仅当已确认启用 `multi_agent`（例如：`[features].multi_agent = true`，或在 CLI 用 `/experimental` 启用 Multi-agents 并重启）且子代理工具可用时，才允许 spawn 子代理；否则必须降级为单代理串行写入（详见 `references/tooling.md#8-并行与-multi_agent（必须说清楚）`）
     - 仅在主代理已“汇总上下文→决策定稿”并产出“写入包（文件/区域/补丁内容/最小验收）”后，才允许并行分发给子代理执行
     - 子代理只负责写入（推荐 Desktop Commander `edit_block` 最小替换）：不得自行补全/推理/扩展范围/改口径；遇到冲突或上下文不匹配必须停止并回报
     - 写冲突控制：不同子代理不得写同一文件；同一文件多处修改默认由主代理合并后一次写入
     - 主代理验收门禁（强制）：子代理写入完成后，必须由主代理串行验收（查看 diff + 回读关键片段 + 最小相关测试）；验收不通过不得进入下一任务
     - 测试/回归门禁（强制）：任何测试/构建/回归命令必须只能由主代理执行；子代理禁止跑测试与回归

5. 验证与测试（阻断门禁）
   - 先跑最小相关测试，再扩大验证范围。
   - **主代理专属门禁（强制）**：测试/构建/回归必须只能由主代理执行；子代理禁止执行（避免环境争用与结果不可追溯）
   - **阻断性失败（默认更安全、更可预测）**：
     - `task.md` 中的测试任务（如 `## 5. 测试`）默认视为阻断性
     - 直接影响核心路径的构建/测试失败也视为阻断性
   - 阻断性失败处理：必须使用 `templates/output-format.md` 的 **G6.2 阻断性测试失败**模板输出，并等待用户选择（修复重试/跳过继续/终止）。
   - 非阻断性失败：可记录为警告并继续，但必须在最终总结中列出风险与影响范围。

6. 同步知识库
   - 按改动类型更新 API/数据/架构/模块文档。
   - 必须同步 `helloagents/CHANGELOG.md`：记录本次变更，并引用方案包/记忆体/决策ID（如有）。

6.1 闭环交付（当 `DELIVERY_MODE=CLOSE_LOOP` 时强制）
   - 目标：在不引入 CSV 台账的情况下，达到“实现 → 文档同步（SSOT）→ 记忆体沉淀 → 本地提交”的效果。
   - 记忆体（强制）：
     - 确保 `helloagents/wiki/memories/index.md` 存在；不存在则按 `templates/wiki-memories-index-template.md` 创建或先执行 `~init`。
     - 新增记忆体文档：`helloagents/wiki/memories/<module>/<id>_<slug>.md`
       - `id`：建议可排序（例如 `HA20260210-153012`），确保唯一。
       - `module`：按影响面取 `backend|frontend|both|Misc`（无法判断时用 `Misc`，避免脑补业务归属）。
       - 内容至少包含：目标/背景、变更点、影响范围、验证与证据、回归入口、风险与回滚、refs（路径+关键行号）。
     - 更新索引：在 `helloagents/wiki/memories/index.md` 表格中追加/更新一行，填入 `id/title/module/source/memory_doc/status/updated_at`。
   - 本地 git commit（不 push，强制）：**建议在完成“7. 迁移方案包”后再执行**，确保归档移动与 `history/index.md` 更新也纳入同一个 commit（避免闭环结束后仍残留未提交变更）。提交细则见：`references/functions/commit.md`。

7. 迁移方案包（脚本优先 / 无脚本兜底）
   - `SCRIPTS_ENABLED=true`：按 `references/rules/tools.md` 调用 `scripts/migrate_package.py <package-name> --status completed`。
   - `SCRIPTS_ENABLED=false`：按 `references/rules/noscript.md#7-手动迁移方案包` 执行（含 `task.md @status` 与 `history/index.md` 更新）。
   - 迁移后结果应满足：`plan/` 中源目录不存在、`history/YYYY-MM/<package>/` 存在、`history/index.md` 已追加记录。
   - 若整体未执行/用户放弃：使用 `status=skipped` 迁移并标注未执行。

7.1 闭环交付：本地 git commit（当 `DELIVERY_MODE=CLOSE_LOOP` 时强制）
   - 迁移完成后执行提交（避免迁移后还有未提交变更）。
   - 使用 `git status --porcelain` 确认变更范围；只提交与本次任务相关的代码 + `helloagents/` 工作区产物（方案包/知识库/记忆体）。
   - 提交细则（确认/默认不 push/Conventional Commits/可选推送）见：`references/functions/commit.md`。

## 输出要求

- 使用 `templates/output-format.md`。
- 输出必须包含：任务状态统计、验证结果、文件清单、下一步；若执行闭环交付，补充：记忆体路径与 commit 哈希（如可获取）。

## 阶段退出条件

- 任务执行完成并完成迁移。
- 或用户明确终止并保留进度。
