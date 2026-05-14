# 多代理（multi_agent）协作指南（HelloAgents_v5）

> 目标：把“并行信息收集/多视角审查”与“受控写入落地”拆开管理，既吃到多代理的吞吐，又不引入写冲突与口径漂移。

## 1. 可用性门禁（必须先确认）

> 结论：**未确认 multi_agent 可用时，一律按“单代理串行”执行。**

multi_agent 属于 Codex CLI 的实验特性，需要显式启用。至少满足其一：

- 在 Codex CLI 用 `/experimental` 启用 **Multi-agents** 并重启
- 在 `~/.codex/config.toml`（或项目 `.codex/config.toml`）中启用：

```toml
[features]
multi_agent = true
```

- 从 CLI 启用 feature（如果你的 Codex 版本支持）：`codex --enable multi_agent`

> 注意：子代理继承当前 sandbox/权限策略，但以“非交互审批”运行；需要新审批的动作会直接失败并回传给主流程。

### 1.1 默认启用策略（无需提示词）

- 只要 **已确认 `multi_agent` 可用**且 **roles 已配置**，HelloAgents_v5 在 `evaluate/analyze/design` 阶段对“只读信息收集/评审”应**默认自动启用**（主代理主动 spawn，用户无需额外提示）。
- explorer 的并行策略默认使用 `#3.3` 的 **slice 分片模板**，避免多个 explorer 重复扫描同一批文件。

### 1.2 禁用开关（用户可覆盖，最多只需提示词禁用）

当用户显式要求“不要多代理/单代理”，或在提示词中写任一开关时，主代理必须禁用自动 spawn：
- `HA_MULTI_AGENT=off`：禁用所有子代理（按单代理串行执行）
- `HA_EXPLORER_SLICES=off`：仅禁用 explorer 分片并行（保留 `ha_product/ha_reviewer` 等只读评审视角，除非用户同时禁用 `HA_MULTI_AGENT`）
- `HA_EXPLORER_SLICES=2|4`：强制 explorer slice 数（覆盖默认自动选择）

## 2. 两种“并行”不要混淆

### 2.1 并行信息收集（强烈推荐）

适合交给子代理的任务：
- 代码库探索（入口、调用链、引用分布）
- 文档/配置扫描（真相源定位）
- 日志/错误信息归因
- 多视角审查（安全/质量/测试风险）

子代理输出应该“短且可验证”：
- 结论（1-3 句）
- 证据锚点（文件路径/关键词/命中位置）
- 风险等级与下一步（可选）

### 2.2 受控并行写入（可选，门槛高）

允许并行写入的前提（缺一不可）：
1) 已确认 `multi_agent` 可用
2) 主代理已完成：上下文收敛 → 决策定稿 → 产出“写入包”
3) 不同子代理 **不写同一文件**；同一文件多处修改默认由主代理合并后一次写入
4) 子代理严格“只写不想”：不得补全/推理/扩范围/改口径；冲突就停止回报
5) 子代理完成后，主代理必须逐包验收（回读关键片段 + diff + 最小相关测试）

默认策略：
- **写入串行是常态**；并行写入只用于“明确可分割、互不冲突”的补丁落地（例如后端/前端完全不同目录，且每包都有清晰最小验收）。

### 2.3 执行顺序（DAG + 快速落地路径）

- `task.md` 的 DAG 表示依赖关系，不等于时间顺序；执行前先看 DAG，能并行的节点优先并行做“只读收集/写入包准备”。
- `快速落地路径` 是 DAG 上的推荐主路径：优先完成最小闭环（vertical slice），避免一上来铺开全部支线导致返工。
- 受控并行写入只在“无依赖 + 无写冲突”时开启；同一文件或顺序依赖强的节点必须串行。
- 子代理不应被要求“自动识别 task 并自行写入实现”：为保证可追溯与不跑偏，必须由主代理提供写入包（目标文件/区域/补丁内容/最小验收），子代理严格照做。

## 3. 角色（agent roles）设计：多角色分工怎么落地

Codex 支持通过 `config.toml` 的 `[agents]` 定义角色，并在 spawn 子代理时选择对应角色（`agent_type=<name>`）。

### 3.1 推荐的最小角色集合（可直接用）

为避免覆盖你已有的内置角色（如 `explorer`），HelloAgents_v5 默认推荐使用 **`ha_*` 前缀**的自定义角色名：

- `default`：主代理/编排者（汇总、决策、最终写入与验收）
- `ha_explorer`：只读探索（代码检索、定位、引用分布、证据锚点）
- `ha_reviewer`：只读审查（安全/正确性/测试风险/可维护性）

可选扩展（按需启用）：
- `ha_product`：只读产品决策（目标用户/范围/验收/成功指标），用于补齐 `why.md` 的“产品分析/验收与验证”
- `ha_ui_designer`：只读 UX/UI 决策（用户旅程/交互/状态/文案/视觉规范），用于补齐 `why.md` 的 UX/UI 章节（当 `frontendImpact=possible|yes`）
- `ha_writer_backend`：后端写入执行者（只接收“写入包”）
- `ha_writer_frontend`：前端写入执行者（只接收“写入包”）

> 如果你明确希望覆盖内置 `explorer` 角色，也可以用 `explorer` 作为 role 名称；但请自行评估对既有工作流的影响。

可直接复制示例配置：
- `examples/codex-config-multi-agent.example.toml`：启用 `multi_agent` + roles 声明
- `examples/agents/*.toml`：各 role 的 `config_file` 示例（只读/写入门禁/输出格式）

### 3.2 角色配置建议

- `explorer/reviewer`：建议 `sandbox_mode="read-only"`（或等价只读策略），避免误写
- `product/ui_designer`：建议 `sandbox_mode="read-only"`；只输出“可粘贴的决策建议段落”，不直接写入
- `writer_*`：只在需要时启用写权限；并在流程上强制“写入包 + 主代理验收”
- `model_reasoning_effort`：
  - explorer：`low|medium`
  - reviewer：`high`
  - writer：`medium|high`（取决于补丁复杂度）

> 角色配置的真相源与 schema 以 Codex 官方配置文档为准；HelloAgents 只提供可执行的默认分工建议。

### 3.3 分片并行（slice）默认模板（跨项目通用，提效关键）

**核心认知：role 不是并行度。**
- `config.toml` 里的 `role` 只是“子代理配置模板”（模型/只读门禁/输出格式/工具偏好）。
- **并行度取决于 spawn 的实例数量**：同一个 `ha_explorer_fast` role 可以 spawn 多次；每个实例负责一个 slice。

**为什么要 slice：**
- 避免多个 explorer 重复扫同一批文件，降低 I/O 与上下文噪声。
- 让每个 explorer 只产出“可复核证据锚点”，主代理更快汇总定稿。

#### 默认 4-slice（建议上限=4）

> 适用于任何项目；不依赖具体仓库目录名。优先用“目录启发 + 文件类型 glob”收敛 scope，目录不确定就用 glob 兜底。

1) `BACKEND`
   - include_globs（示例）：`**/*.java`、`**/*.kt`、`**/*.go`、`**/*.py`、`**/*.cs`
   - dir_hints（示例）：`server/`、`backend/`、`api/`、`services/`、`src/main/`
2) `FRONTEND`
   - include_globs：`**/*.vue`、`**/*.ts`、`**/*.tsx`、`**/*.js`、`**/*.jsx`、`**/*.css`、`**/*.scss`
   - dir_hints：`web/`、`frontend/`、`ui/`、`apps/`、`packages/`、`src/`
3) `DB`
   - include_globs：`**/*.sql`
   - dir_hints：`db/`、`migrations/`、`flyway/`、`liquibase/`、`schema/`
4) `DOCS_CONFIG`
   - include_globs：`**/*.md`、`**/*.yml`、`**/*.yaml`、`**/*.toml`、`**/*.json`、`**/*.env*`
   - dir_hints：`docs/`、`.github/`、`deploy/`、`config/`

#### 2-slice / 4-slice 选择建议（默认规则，可被用户指令覆盖）

- 只做后端缺陷定位：`BACKEND`（1 个）
- 常规需求/方案包评审（多数场景）：`BACKEND + FRONTEND`（2 个）
- 明确涉及 SQL/落库/迁移：`+ DB`（3 个）
- 明确涉及配置/权限点/环境差异/文档约定：`+ DOCS_CONFIG`（4 个）
- **仓库形状不明**、或你追求“更快首轮证据覆盖”：直接 `4-slice`（4 个）

#### 给 explorer 的任务消息模板（强烈推荐，减少跑偏）

主代理给每个 explorer 的消息应至少包含：
- `slice_id`：`BACKEND|FRONTEND|DB|DOCS_CONFIG`
- `scope_hint`：优先目录范围（若可识别），否则写“按 include_globs 全仓兜底”
- `include_globs` / `exclude_hints`：让其检索收敛且可复现
- `keywords`：本轮要核验的锚点关键词（1-3 个，避免泛搜）

要求（强制口径）：
- explorer **只在本 slice 内检索**；跨 slice 需求一律标记“未确认”，建议主代理交给对应 slice 补证。
- 输出必须包含：`slice_id + 实际 scope + file:line` 证据锚点（至少 3 条）+ 缺失/未确认清单。

## 4. 子代理输出格式（强制口径）

为避免“上下文污染 + 口径漂移”，子代理输出必须按以下结构返回：

```text
【结论】...
【证据】<文件/路径/关键词/命中点>
【风险】low|medium|high（可选）
【建议下一步】...（可选）
```

当子代理执行“写入包”时必须额外包含：

```text
【写入包ID】...
【修改结果】success|failed
【失败原因】...（仅 failed 时）
【自检】回读关键片段/定位点（最小必要）
```

## 5. 与 HelloAgents 阶段的对齐方式

- `evaluate`：常规需求评估在不扫描代码的前提下（只基于用户输入），在未禁用（`HA_MULTI_AGENT=off`）且已确认 `multi_agent` 可用/roles 已配置时，默认自动并行 spawn `ha_product`/`ha_reviewer` 做“评分建议 + 追问列表”，主代理汇总给出最终评分与下一步（spawn 失败则降级串行）。
  - 当用户请求为“方案包评分评审/why-how-task 评审”时：默认追加并行 spawn **2~4 个** explorer 做只读锚点核验（按 `#3.3` slice 分片：`BACKEND/FRONTEND` 为默认必选；`DB/DOCS_CONFIG` 仅在需求涉及时启用；上限=4）。优先用 `ha_explorer_fast`（未配置则用 `ha_explorer`）；若 `HA_EXPLORER_SLICES=off` 则跳过 explorer 分片。
- `analyze`：在未禁用（`HA_MULTI_AGENT=off`）且已确认 `multi_agent` 可用/roles 已配置时，默认自动并行 spawn **2~4 个** explorer 做“影响面定位/证据锚点补齐”（按 `#3.3` slice 分片；上限=4），主代理汇总定稿（spawn 失败则降级串行）。
  - 两轮策略：第 1 轮只做锚点/引用分布核验（优先 `ha_explorer_fast`）；第 2 轮按需再深挖 1-2 条关键调用链（优先 `ha_explorer_deep`）。
  - 可选提效角色（推荐）：在全局 `~/.codex/config.toml` 配置 `ha_explorer_fast`（第 1 轮）与 `ha_explorer_deep`（第 2 轮），避免“同一 role 既要快又要深”的配置拉扯。
- `design`：若已确认 `multi_agent` 可用且 roles 已配置，默认自动并行 spawn `ha_reviewer` 做风险审查；并按需自动并行 spawn `ha_product`/`ha_ui_designer` 输出可直接粘贴段落，主代理统一定稿写入 `why.md`（子代理不得写文件）
- `develop`：默认串行写入；若启用受控并行写入，只允许 `ha_writer_*` 按写入包落地，主代理统一验收与跑测试
