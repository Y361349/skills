# 快速流程示例（含 multi_agent 分工）

用户输入：
- 请把登录接口超时问题修复，并补充验证。

前置（可选但推荐）：
- 确认已启用 `multi_agent`（见：`references/multi_agent.md`）；未启用则跳过“子代理并行”，按单代理串行执行。

路由结果：
1. `evaluate`：评分通过，复杂度判定为 `LIGHT`
   - 并行（只读，默认自动）：自动 spawn `ha_product`/`ha_reviewer` 做“评分建议 + 追问列表”，主代理汇总定稿（失败则降级串行）
2. `analyze`：定位登录模块与调用链
   - 并行（只读，默认自动）：自动 spawn `ha_explorer` 做“入口/调用链/证据锚点定位”，主代理汇总结论（失败则降级串行）
3. `design`：创建 `why/how/task`
   - 产物门禁（强烈推荐）：`task.md` 必须包含 `DAG（依赖关系图）` + `快速落地路径（推荐执行顺序，不必机械按章节顺序）`，方便实现阶段按依赖/主路径推进
   - 并行（只读，默认自动）：自动 spawn `ha_reviewer` 做“安全/正确性/测试风险”审查，主代理合并到方案包（失败则降级串行）
   - 并行（只读，按需自动）：若需要补齐产品分析/验收 → 自动 spawn `ha_product` 输出可粘贴段落
   - 并行（只读，按需自动）：若 `frontendImpact=possible|yes` → 自动 spawn `ha_ui_designer` 输出可粘贴段落
4. `develop`：实现、测试、同步知识库、迁移历史
   - 执行顺序：优先按 `快速落地路径` 走最小闭环（vertical slice），其余支线在依赖满足后补齐
   - 门禁（强制）：执行前必须通过 `scripts/validate_package.py <package> --require-finalized`（`final_gate.score=10`），并将 `why.md` 元信息更新为 `@final_confirm=YES`
   - 默认：写入串行；测试/构建/回归只由主代理执行
   - 受控并行写入（可选）：主代理先产出“写入包”，再 spawn `ha_writer_backend`/`ha_writer_frontend` 落地，主代理逐包验收

输出：
- 使用 `templates/output-format.md` 汇总结果