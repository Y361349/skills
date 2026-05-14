---
name: analyze
description: 项目分析阶段规则；完成上下文获取、影响面分析、技术风险识别，为方案设计提供输入。
---

# 项目分析（A）

## 目标

- 获取任务所需最小项目上下文。
- 输出可执行的技术边界与风险列表。

## 前置条件

- `evaluate` 已完成并判定进入 `LIGHT` 或 `STANDARD`。

## 执行步骤

1. 知识库状态检查
   - 若知识库缺失，标记问题并按需触发 `kb/SKILL.md`（建议先 `~init` 建好结构）。

2. 项目规模判定（可选但推荐）
   - 按 `references/rules/tools.md` 的脚本调用规范运行 `scripts/project_stats.py`。
   - 若 `SCRIPTS_ENABLED=false` 或脚本不可用：按 `references/rules/noscript.md#8-手动规模判定` 保守判定并启用分批策略。
   - 若判定为大型项目：按 `references/rules/scaling.md` 启用分批读取策略。

3. 上下文获取
   - 优先读取知识库核心文档（`project.md`、`wiki/overview.md`、`wiki/arch.md`）。
   - 信息不足时再扫描代码库；大型项目遵循分批策略。

4. 影响面定位
   - multi_agent 只读并行（默认自动启用）：除非用户显式禁用（例如：`HA_MULTI_AGENT=off` 或口头“单代理/不要子代理”），在已确认 `multi_agent` 可用且 roles 已配置时，主代理必须自动并行 spawn explorer 做“入口/锚点/引用分布定位”，主代理汇总定稿（spawn 失败则降级串行）。
     - explorer 数量默认 **2~4**；若用户显式指定 `HA_EXPLORER_SLICES=2|4|off`，按其覆盖（`off` 表示不启用 explorer 分片并行，回退为单代理串行检索）。
     - 第 1 轮（快速锚点核验）：优先使用 `ha_explorer_fast`（若未配置则用 `ha_explorer`）
       - 分片并行（slice，上限=4，跨项目通用）：优先按 `references/multi_agent.md#3.3` 的默认 4-slice 模板切片（同一 role 可 spawn 多次；每个 explorer 只负责一个 slice，禁止跨 slice 扫描）。
         - `BACKEND`：优先只检索 `<backend_root>/`（若能识别）；否则用 `**/*.java|**/*.kt|**/*.go|**/*.py|**/*.cs` 等 glob 全仓兜底。
         - `FRONTEND`：优先只检索 `<frontend_root>/`（若能识别）；否则用 `**/*.vue|**/*.ts|**/*.tsx|**/*.js|**/*.jsx` 等 glob 全仓兜底。
         - `DB`：仅当需求涉及 SQL/落库/迁移/表结构时启用；否则不必起该 slice。glob 示例：`**/*.sql`。
         - `DOCS_CONFIG`：仅当需求涉及配置/权限点/环境差异/文档约定时启用；否则不必起该 slice。glob 示例：`**/*.md|**/*.yml|**/*.yaml|**/*.toml|**/*.json|**/*.env*`。
       - scope/分片确定方式（强制，保证全局通用）：主代理先做“仓库形状探测”（顶层目录 + 构建/依赖清单文件，如 `pom.xml`/`go.mod`/`package.json`），能判定就收敛到目录 scope；探测到多个候选 root 时可按 root 分片增加 explorer 数（建议 ≤4）并行核验；仍不确定则向用户追问。
     - 要求：每个 explorer 必须声明 `slice_id` 与 scope、避免重复检索；输出仅包含“证据锚点 + 缺失/未确认清单 + 关键词”。
     - 两轮策略（默认启用，避免子代理卡住/超时沉默）：
       - 第 1 轮（快速锚点核验）：**只做“锚点存在性核验/关键词命中/引用分布”**，不要深挖调用链、不要在子代理里 `refresh_index/build_deep_index`。
       - 第 2 轮（按需深挖调用链）：当第 1 轮无法判定责任模块/权限链路/关键分支时，由**主代理**再 spawn 1-2 个 explorer（优先 `ha_explorer_deep`；若未配置则用 `ha_explorer`）对 1-2 条关键路径做深挖；输出仍以“证据锚点”为主，避免长篇过程日志。
   - 使用 `code-index` 定位相关文件、符号、调用点（初始化流程见 `references/tooling.md`）。
   - 形成“必改/可选/不改”边界，并给出最小验证路径。
   - 跨端影响面判定（前端确认门禁）
     - 目标：判断本次“后端改动”是否影响任一前端（Web/UniApp/其它客户端）的展示/交互/口径。
     - 输出：给出 `frontendImpact = none|possible|yes`，并附 1-3 条依据（写入分析结论）。
     - 若 `frontendImpact in (possible, yes)`：补充“心智负担”评审要点（1-3条），优先从用户视角描述复杂度来源；如发现复杂度主要由后端契约/约束导致，标注“可在后端消解”的候选改动点。
     - 判定启发式（最小必要，避免脑补）：
       - `yes`：需求/变更点明确包含页面/交互/文案/字段展示/表单校验/权限可见性/菜单路由；或接口/字段变更属于前端直接消费（列表/详情/表单）。
       - `possible`：仅改后端但涉及接口字段含义/单位/舍入、枚举/状态、错误码/错误提示、权限点、校验规则、排序/分页/过滤等，可能需要前端同步。
       - `none`：纯后端内部能力（Job/定时/存储/日志/监控/离线脚本）且无对外契约变化。
     - 证据优先（能查就别猜）：
       - 若已知接口路径/权限点/关键字段名：优先用 `code-index` 在前端代码中检索引用（命中即为强证据，`frontendImpact` 通常至少为 `possible`，多数场景可直接判为 `yes`）。
     - 覆盖规则（用户意图优先）：
       - 若用户显式 `UI=on`：至少为 `possible`。
       - 若用户显式 `UI=off`：默认可按 `none` 处理；但若出现明显 `yes/possible` 信号，必须提示风险并询问是否仍按 `UI=off` 执行。
     - 不确定时的处理：
       - 若无法在 `possible` 与 `none` 之间判断：使用 `templates/output-format.md#G6.4` 向用户确认“是否需要前端口径/展示同步”。
       - AUTO 模式（~auto/~exec）下若无人可确认：默认按 `possible` 处理（更保守，避免漏同步）。

5. 风险识别
   - 技术风险、兼容性风险、性能风险、安全风险。
   - 标注是否触发 EHRB 额外门禁。

6. 复杂度复核（初判 → 复核）
   - 输入：`evaluate` 阶段的复杂度初判（`TWEAK|LIGHT|STANDARD`）。
   - 目标：结合本阶段新发现的“影响面/依赖/风险/跨端”信息，复核是否需要升级复杂度。
   - 复核启发式（最小必要，避免脑补）：满足任一条件通常应升级为 `STANDARD`：
     - 跨模块/跨目录影响面明显扩大（多个核心链路/多入口）
     - 前后端联动或影响任一客户端展示口径（`frontendImpact in (possible, yes)`）
     - 出现 EHRB 风险信号（权限/认证/敏感数据/高风险数据操作）
     - 验收口径不清晰且需要补充方案/回滚/测试门禁
   - 输出：给出 `complexity_initial` 与 `complexity_review`（可相同或升级），并说明“升级原因”或“保持原因”。

7. 方案输入整理
   - 关键目标
   - 成功标准
   - 技术约束
   - 影响面清单
   - 复杂度（初判/复核）与交付模式建议（NORMAL/CLOSE_LOOP）

## 输出要求

- 使用 `templates/output-format.md`。
- 输出必须包含：
  - 上下文来源（知识库/代码）与规模判定（如执行了统计）
  - 影响面
  - 复杂度（初判/复核）与必要原因说明
  - 主要风险
  - 下一步进入 `design`

## 阶段退出条件

- 已形成可用于设计阶段的输入包。
- 用户取消或转入问答模式。
