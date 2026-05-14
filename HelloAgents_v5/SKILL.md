---
name: helloagents_v5
description: HelloAgents_v5（多代理分工增强版）。在 v4 的阶段/命令 + 输出SSOT + 脚本化方案包链路基础上，补齐对 Codex CLI `multi_agent` 的分工编排：agent roles/自定义子代理/受控并行写入门禁；用于软件开发与维护类请求（修改/修复/新增/重构/测试/规划/知识库），按需路由到 evaluate/analyze/design/develop/tweak/kb/templates 子技能。
version: "5.0.1"
metadata:
  based_on:
    - HelloAgents_v4
    - HelloAgents_v3
    - HelloAgents_v2
  compatibility: non-invasive
  multi_agent: true
---

# HelloAgents_v5 - 多代理分工增强版

> 目标：在不依赖外部 `AGENTS.md` 的前提下，提供“阶段化 + 命令编排 + 输出SSOT + 脚本化基建”的完整工作流能力。

## 设计原则

1. 非侵入：技能本体可独立运行，不要求外部全局提示词才能工作。
2. 真相源优先：用户指令 > 文档/配置 > 代码实现 > 经验。
3. 最小必要：先定位、再精读、再最小改动、再验证。
4. 可恢复：任何阶段可取消、重试、降级、升级。
5. 可脚本化：重复性动作优先走 `scripts/`；脚本不可用或用户禁用时，按 `references/rules/noscript.md` 的手动流程继续（不影响交付）。
6. 可预测：关键门禁/异常输出使用 SSOT 模板，失败可定位、可复现。

## 多代理分工（multi_agent，v5 新增）

- **可用性门禁**：未确认 `multi_agent` 已启用时，一律按“单代理串行”执行（见 `references/multi_agent.md`）。
- **默认分工**：在 `evaluate/analyze/design` 阶段（满足门禁时）默认自动并行 spawn 只读子代理做评分/收集/决策补齐（`ha_product/ha_reviewer/ha_explorer/ha_ui_designer` 按阶段与门禁启用）；写入默认串行，受控并行写入必须先产出“写入包”并由主代理验收。
- **自定义子代理**：通过 `config.toml` 的 `[agents]` 定义 role，并在 spawn 子代理时指定 `agent_type=<role>`（见 `references/multi_agent.md`）。
- **默认自动启用（无需额外提示词）**：只要 `multi_agent` 可用且 roles 已配置，HelloAgents_v5 会自动启用只读并行（尤其是“方案包评分评审/影响面定位”的 explorer 分片并行）。如需禁用/降并行度，仅需在提示词中覆写：`HA_MULTI_AGENT=off` 或 `HA_EXPLORER_SLICES=off|2|4`（详见 `references/state.md` 与 `references/multi_agent.md`）。

## 阶段模型

```text
E0 需求评估(evaluate) → A 项目分析(analyze) → D 方案设计(design) → P 开发实施(develop)
                         ↘ T 微调(tweak)
```

- `evaluate/`: 只基于用户输入做需求评分与复杂度判定。
- `analyze/`: 获取项目上下文与影响面分析。
- `design/`: 产出可执行方案包（why/how/task）。
- `develop/`: 按任务清单实施、验证、同步知识库、迁移历史。
- `tweak/`: 小改动直达模式，超范围时自动升级。
- `kb/`: 知识库创建、同步、审计、上下文读取。
- `templates/`: 输出格式和文档模板。

## 脚本化能力（可选但推荐）

> 说明：脚本负责“纯文件/结构化动作”，内容分析与决策仍由 AI 在阶段规则中完成。
> 脚本调用与降级接手约定见：`references/rules/tools.md`；无脚本环境（`SCRIPTS_ENABLED=false`）见：`references/rules/noscript.md`。

- 方案包创建：`scripts/create_package.py`（生成 `why/how/task`）
- 方案包校验：`scripts/validate_package.py`
- 方案包迁移：`scripts/migrate_package.py`（`plan/` → `history/`）
- 项目规模统计：`scripts/project_stats.py`（大型项目判定）
- 知识库工具：`scripts/upgradewiki.py`（scan/init/backup/write）

## 模式定义

- `INTERACTIVE`：默认交互模式，每个关键门禁等待用户确认。
- `AUTO_FULL`：全授权连续执行（~auto）。
- `AUTO_PLAN`：执行到方案设计后停止（~plan）。
- `MODE_EXECUTION`：直接执行现有方案包（~exec）。
- `DELIVERY_MODE`：交付模式：`NORMAL`（默认：必须同步知识库）/ `CLOSE_LOOP`（闭环交付：在同步知识库基础上，强制记忆体 + 本地 git commit）；详见 `references/state.md`。

状态变量与切换规则详见：`references/state.md`

## 命令面

- `~auto`：需求评估后连续执行到开发完成。
- `~ship`：闭环交付执行（等价于 `~auto` + `DELIVERY_MODE=CLOSE_LOOP`）。
- `~plan`：需求评估+分析+设计，产出方案包。
- `~exec`：直接执行 `helloagents/plan/` 中已有方案包。
- `~init`：初始化或重建知识库。
- `~upgrade`：升级知识库结构和模板。
- `~clean`：处理遗留方案包。
- `~test`：执行测试。
- `~review`：代码审查。
- `~validate`：校验知识库和方案包。
- `~rollback`：回滚最近变更。
- `~help`：展示命令帮助。

命令细则详见：`references/commands.md`

## 路由规则（先判定再读取）

1. 若用户显式输入 `~` 命令：按 `references/commands.md` 路由。
2. 若为开发请求：先读取 `evaluate/SKILL.md`。
3. `evaluate` 判定为微调：读取 `tweak/SKILL.md`。
4. `evaluate` 判定为轻量迭代/标准开发：读取 `analyze/SKILL.md`。
5. `analyze` 完成后读取 `design/SKILL.md`。
6. `design` 完成并满足门禁后读取 `develop/SKILL.md`。
7. 涉及知识库创建/同步：随时读取 `kb/SKILL.md`。
8. 需要写文档时：读取 `templates/SKILL.md` 与对应模板。

## 关键门禁

- 需求评分门禁：评分 < 8 分默认追问，不进入后续阶段。
- 强确认门禁（INTERACTIVE）：开始写入代码前，必须收到“确认开始实现”（或同义口令）。
- 强确认门禁（AUTO_FULL）：用户显式输入 `~auto/~ship` 视为已授权开始实现；若希望“先确认再落地”，请改用默认交互流程或先 `~plan`。
- 风险门禁：检测到 EHRB（高风险行为）时，强制升级为标准开发。

## 工具协同

工具决策树详见：`references/tooling.md`

- 定位：`code-index`
- 精读：Desktop Commander
- 语义：`mcp-lsp-bridge`
- 改动：Desktop Commander（`edit_block`/`write_file`）
- 验证：测试/构建命令

## 输出规范

统一输出格式 SSOT：`templates/output-format.md`

- 阶段完成/等待确认/取消/错误均使用标准格式。
- 输出必须包含：状态、阶段内容、文件清单、下一步。

## 方案包与知识库约定

- 方案包路径：`helloagents/plan/YYYYMMDDHHMM_<feature>/`
- 历史归档：`helloagents/history/YYYY-MM/YYYYMMDDHHMM_<feature>/`
- 知识库根：`helloagents/`

详情见：`references/package.md` 与 `kb/SKILL.md`

## 最小启动清单

1. 读取本文件完成路由判定。
2. 读取 `evaluate/SKILL.md` 完成需求门禁。
3. 根据判定加载 `tweak` 或 `analyze→design→develop`。
4. 输出遵循 `templates/output-format.md`。
