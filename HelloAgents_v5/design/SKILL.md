---
name: design
description: 方案设计阶段规则；生成方案包（why/how/task），支持复杂任务多方案对比与风险规避。
---

# 方案设计（D）

## 目标

- 形成可执行、可验证、可追溯的方案包。

## 前置条件

- `analyze` 阶段已完成。

## 执行步骤

1. 选择设计深度
   - 简单任务：单方案。
   - 复杂任务：2-3个可行方案并给出推荐。

2. 创建方案包（脚本优先）
   - 按 `references/rules/tools.md` 调用 `scripts/create_package.py` 生成方案包骨架：`helloagents/plan/YYYYMMDDHHMM_<feature>/`。
   - 冲突（同名目录已存在）：脚本会自动追加 `_v2/_v3...`。
   - 类型选择：默认 `implementation`；若仅用于共识沉淀可用 `--type overview`（此类方案包不进入 `develop`）。
   - **复杂度元信息自动写入（强制）**：
     - 必须将 `evaluate` 的 `complexity_initial` 与 `analyze` 的 `complexity_review` 传给脚本：`--complexity-initial/--complexity-review`。
     - 必须将交付模式传给脚本：`--delivery-mode NORMAL|CLOSE_LOOP`。
     - 结果：脚本会在 `why.md` 标题下写入元信息：`@pkg_type/@complexity_initial/@complexity_review/@delivery_mode`，便于后续追溯与治理强度选择。
     - 说明：元信息值必须包含中文说明（脚本会自动格式化为 `STANDARD（跨模块/多路径/架构变化/高风险）`、`NORMAL（普通交付（必须同步知识库））` 这种“枚举+中文说明”形式；手工补齐也必须保持同等格式）。
   - 若 `SCRIPTS_ENABLED=false` 或脚本不可用：按 `references/rules/noscript.md#4-手动创建方案包` 手动创建（保持 `@pkg_type` 标记一致）。
     - 手动创建时，必须在 `why.md` 标题下补齐同等元信息（与脚本一致）。

3. 补齐内容与校验（脚本优先）
   - 事实一致性与口径锚点（强制，反幻觉门禁）
     - 任意“事实性信息”（接口路径/入参字段/返回字段/表名字段/枚举值/配置 key/权限点/类名方法/文件路径）必须满足其一：
       - 给出**证据锚点**（文档或代码中可定位的证据）
       - 显式标记为 `[?] 待确认`（并在 `task.md` 增加对应“确认/定位”任务）
     - 证据锚点写法（最小必要即可）：
       - 文档证据：`docs/xxx.md#小节标题` 或 `固定资产管理实现方案v2/xxx.md#小节标题`
       - 代码证据：`path/to/file.ts` + 关键符号/关键词（可被 `code-index` 搜到）
   - 占位符治理（强制）
     - 禁止在**可执行任务**中保留占位符目标（如 `path/to/file.ts`、`**/*.java`、`...`、`xxx`）
     - 若尚未定位真实路径/符号：必须先写“定位任务”（例如：用 `code-index` 按关键词检索后再落 task）
   - 并行/串行策略（强制）
     - 并行可用于“只读信息收集”（代码检索定位 + 并行精读片段）：允许并行做 `code-index` 检索，以及用 Desktop Commander 以 `offset/length` 分段精读多个文件片段，用于加快上下文收集
     - 并行可用于“决策建议补齐”（只读，默认自动）：若已确认 `multi_agent` 可用且 roles 已配置，本阶段默认并行 spawn `ha_reviewer` 做风险审查；若方案包类型为 `implementation` 且（`complexity_review=STANDARD` 或需求包含“功能/流程/范围/验收/角色/权限”等产品决策项）则并行 spawn `ha_product`；若 `frontendImpact=possible|yes` 或用户显式 `UI=on` 则并行 spawn `ha_ui_designer`。子代理只输出“可直接粘贴段落”，主代理统一定稿写入方案包（子代理不得直接写文件）
     - 受控并行写入（允许，但必须满足全部前提）
       - `multi_agent` 可用性门禁（强制）：仅当已确认启用 `multi_agent`（例如：`[features].multi_agent = true`，或在 CLI 用 `/experimental` 启用 Multi-agents 并重启）且子代理工具可用时，才允许 spawn 子代理并行写入；否则必须降级为“单代理 + 只读并行信息收集”，写入一律串行（详见 `references/tooling.md#8-并行与-multi_agent（必须说清楚）`）
       - 主代理先完成：汇总上下文 → 做决策 → 产出“写入包”（明确到：目标文件/区域、补丁内容、预期结果、最小验收）
       - 子代理禁止思考/补全/擅自改口径：只按“写入包”执行写入（推荐 Desktop Commander `edit_block` 最小替换），并回报成功/失败；失败或冲突必须立即停止并回报（不得自行调整/猜测）
       - 写冲突控制：不同子代理不得写同一文件；同一文件多处修改默认串行（或由主代理合并后一次写入）
     - 串行阶段（必须）：决策定稿、补丁合并、验证与回归（测试/构建），以及任何需要“再思考”的改动
     - 汇总输出前必须做一次口径一致性校验（why/how/task 三者不互相矛盾）
   - 依赖关系图与并行批次（强制）
     - `task.md` 必须输出“依赖关系图（DAG）”，并在任务标题上标注依赖（例如 `（依赖 1.1）`）
     - `task.md` 必须输出“快速落地路径（推荐执行顺序，不必机械按章节顺序）”：用 Step 1..N 显式引用任务编号（如 `1.2/3.1/4.3`），给出“最短可运行闭环（vertical slice）”的推荐主路径，并说明这样排序的门禁理由（接口契约/数据准备/权限/入口/错误分支）
     - 必须区分：可并行节点（只读信息收集；受控并行写入=主代理定稿后分发写入包） vs 必须串行节点（汇总/决策/补丁合并/验证、同文件写冲突、顺序依赖、风险门禁、数据迁移）
     - 必须给出粗粒度估时与资源占用：每个 Phase/模块的预估耗时（人日/小时）+ 关键资源（需要的环境/权限/服务、测试预计耗时、是否高 IO/DB 变更）
   - 补齐/更新 `why.md`：背景、目标、范围、验收。
   - 补齐/更新 `how.md`：技术方案、风险、回滚、验证。
   - 若存在关键取舍（多方案权衡/长期影响/契约变更等）：在 `how.md` 记录决策ID（见 `references/decision-id.md`），并在后续 CHANGELOG/记忆体中引用，保证可追溯。
   - 补齐/更新 `task.md`：任务分解、依赖关系、验收点（implementation 类型必须至少 1 个任务项）。
   - 按 `references/rules/tools.md` 调用 `scripts/validate_package.py` 校验方案包可执行性与任务统计。
   - **强制门禁**：implementation 类型若缺少 `@complexity_initial/@complexity_review/@delivery_mode`，或元信息未包含中文说明（未按 `枚举（中文说明）` 形式填写），`validate_package.py` 将给出 `issues` 并置 `executable=false`（需先补齐/修正元信息再进入后续阶段）。
   - 若在补齐过程中发现复杂度与 `@complexity_review` 不一致（例如新增跨模块依赖/跨端影响/EHRB）：必须立即更新 `why.md` 元信息（脚本：`scripts/update_package_metadata.py`；无脚本：手工改元信息行），并在输出中说明原因。
   - 若 `SCRIPTS_ENABLED=false` 或脚本不可用：按 `references/rules/noscript.md#5-手动校验方案包` 手动校验并在输出中给出结论。
   - 跨端确认门禁（前端影响面/展示口径）
     - 输入：从 `analyze` 阶段结论读取 `frontendImpact = none|possible|yes`（或用户显式 `UI=on/off`）。
     - 若 `frontendImpact in (possible, yes)`：
       - `why.md`：必须补齐 `#用户体验（UX，可选）`（至少：关键页面/交互、状态设计、展示口径与文案、心智负担控制）；需要视觉规范时再补 `#视觉与动效（UI，可选）`。
       - `task.md`：必须加入并保留三条阻断任务（建议放在 `## 0. 规划与前置确认` 下）：
         - 前端影响面确认（受影响端/页面/入口/权限/字段/交互）
         - 前端展示口径确认（字段含义/单位/舍入/文案/错误提示与后端对齐）
         - 前端心智负担评审与交互简化（必要时反推后端契约优化，避免复杂性转嫁）
     - 若 `frontendImpact = none`：保持最小化方案包，移除上述两条前端确认任务；UX/UI 章节可省略。
     - 若无法判断：按 `templates/output-format.md#G6.4` 询问用户确认；AUTO 模式默认按 `possible` 处理。

4. 风险规避
   - 必须包含安全与回滚策略。
   - 若涉及 EHRB，必须包含审批/确认门禁说明。

5. 进入实施门禁
   - 交互模式需用户确认“确认开始实现”。
   - 自动模式按命令策略推进。

## 输出要求

- 使用 `templates/output-format.md`。
- 输出必须包含：方案摘要、文件清单、风险摘要、下一步。

## 阶段退出条件

- 方案包完整（why/how/task齐全）。
- 用户确认进入 `develop` 或流程结束（~plan）。
