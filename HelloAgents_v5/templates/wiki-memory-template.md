# 功能记忆体：{title}

> 目的：沉淀“为什么改 / 怎么改 / 如何回归”，让后续排查与迭代可以快速复现与验证。

- id: `{id}`（建议可排序且唯一，例如 `HA20260210-153012`）
- module: `{module}`（`backend` / `frontend` / `both` / `Misc`）
- source: `{source}`（例如：`helloagents/plan/...`、`issues/*.csv`、验收文档等）
- status: `dev={dev_state}, review={review_state}, git={git_state}`
- updated_at: `{updated_at}`（YYYY-MM-DD HH:mm:ss）

## 目标与背景

- 目标：{goal}
- 现状/问题：{problem}
- 边界/不做：{out_of_scope}

## 变更内容

- 变更点 1：{change_1}
- 变更点 2：{change_2}

## 关键决策（可选）

- 决策ID/ADR：{decisions}（例如：`202602110930_xxx#D001`、`ADR-001`）
- 决策摘要：{decision_summary}

## 影响范围

- 影响模块：{modules}
- 影响文件：{files}
- API/数据/权限：{api_data_perm}

## 验证与证据

- 最小验证步骤：
  - {step_1}
  - {step_2}
- 结果摘要：{result_summary}
- 证据入口（日志/截图/请求样例/脚本）：{evidence_links}

## 回归入口与注意事项

- 需要重点回归的场景：{regression_scenarios}
- 可能的兼容性影响：{compatibility_notes}

## 风险与回滚

- 风险：{risks}
- 回滚方案：{rollback_plan}

## refs（真相源）

- {ref_1}（`path:line`）
- {ref_2}（`path:line`）
