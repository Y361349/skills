# 模板服务（HelloAgents_v5）

> 目的：把“模板选择 → 落地到文件 → 质量检查/降级”集中管理，避免在多个 SKILL 中重复。

## 1. 路径基准

> 与 `references/rules/tools.md` 保持一致。

```yaml
SKILL_ROOT: HelloAgents_v5/
TEMPLATE_DIR: {SKILL_ROOT}/templates/
WORKSPACE_DIR: <项目根目录>/helloagents/
```

## 2. 模板清单（按落点）

| 模板文件 | 典型落点 | 用途 |
|---|---|---|
| `output-format.md` | （不落盘） | 阶段输出 SSOT |
| `plan-why-template.md` | `helloagents/plan/.../why.md` | 方案包：为什么改 |
| `plan-how-template.md` | `helloagents/plan/.../how.md` | 方案包：怎么改 |
| `plan-task-template.md` | `helloagents/plan/.../task.md` | 方案包：做什么/验收 |
| `changelog-template.md` | `helloagents/CHANGELOG.md` | 变更日志 |
| `history-index-template.md` | `helloagents/history/index.md` | 变更历史索引 |
| `project-template.md` | `helloagents/project.md` | 项目技术约定 |
| `wiki-*-template.md` | `helloagents/wiki/*.md` | wiki 文档族 |
| `version-source-map.md` | （按需引用） | 版本号定位参考 |

## 3. 使用前检查（必做）

1. **模板文件存在**：使用前先确认 `TEMPLATE_DIR` 下对应文件存在。
2. **目标目录存在**：落盘前先确认目标目录存在（不存在则创建）。
3. **模板缺失的降级**：
   - 优先：提示用户修复/补齐模板文件。
   - 必须继续时：允许 AI 按“最小可用结构”手动生成，并在输出中明确标注“模板缺失，已降级生成”。

## 4. 落地质量门禁（最小）

- **方案包**：`why/how/task` 三文件存在且非空；`task.md` 至少 1 条任务；必要时保留元信息行（如 `@pkg_type`）。
- **CHANGELOG / history**：链接指向存在的方案包（`plan/` 或 `history/`），避免悬空链接。
- **wiki**：`wiki/overview.md` 的“快速链接”应能导航到 `project/arch/api/data/memories/history/CHANGELOG`。

## 5. 与脚本的集成点

- 脚本模式（`SCRIPTS_ENABLED=true`）下，`scripts/create_package.py` / `scripts/upgradewiki.py` / `scripts/validate_package.py` 会依赖 `templates/`。
- 无脚本模式：按 `references/rules/noscript.md` 的手动流程执行（仅做文件系统动作，内容仍按模板落地）。
