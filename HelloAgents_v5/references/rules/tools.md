# 工具调用规则（HelloAgents_v5）

本规则定义：
- 内部阶段模块（evaluate/analyze/design/develop/tweak/kb/templates）的调用门控
- 脚本执行规范（路径、编码、参数、错误恢复）
- 脚本执行报告（ExecutionReport JSON）与 AI 降级接手流程

> 目标：把“重复性、纯文件/结构化动作”交给脚本做；把“理解、决策、内容生成”留给 AI 做。

---

## 0. 脚本模式判定（必做）

为适配**无脚本环境**并提升一致性与可预测性，调用脚本前必须先判定脚本模式：

- 若用户明确要求“无脚本/不允许运行脚本” → 设置 `SCRIPTS_ENABLED=false`，并按 `references/rules/noscript.md` 执行手动流程。
- 若 Python 不可用、脚本文件不存在、或脚本运行失败（权限/策略/路径） → 立即切换到无脚本模式（`SCRIPTS_ENABLED=false`），并按 `references/rules/noscript.md` 继续；禁止反复重试导致流程不可预测。
- 仅当 `SCRIPTS_ENABLED=true` 且脚本存在且 Python 可用时，才进入下文的 `2.x` 脚本调用规范。

---

## 1. 路径基准（必读）

```yaml
SKILL_ROOT: HelloAgents_v5/           # 本技能目录（SKILL.md 所在目录）
SCRIPT_DIR: {SKILL_ROOT}/scripts/     # 脚本目录
TEMPLATE_DIR: {SKILL_ROOT}/templates/ # 模板目录（供脚本 create/validate/migrate 读取）
WORKSPACE_DIR: <项目根目录>/helloagents/
```

说明：
- **脚本模板目录**：本技能采用 `templates/` 作为脚本模板根目录（非 `assets/templates/`）。
- **工作区目录**：所有方案包/知识库文件一律落在用户项目的 `helloagents/` 下。

---

## 2. 脚本调用规范

### 2.1 基本要求

1. 始终使用绝对路径调用脚本，并用双引号包裹路径（Windows 兼容）
2. 强制开启 UTF-8：`python -X utf8`
3. 项目根目录 `--path` 为可选参数；不传时脚本默认使用当前工作目录（cwd）

### 2.2 脚本清单与用法

```yaml
create_package.py:
  用法: python -X utf8 "{SCRIPT_DIR}/create_package.py" <feature> [--type <implementation|overview>] [--path <项目根目录>]
        [--complexity-initial <TWEAK|LIGHT|STANDARD|UNKNOWN>] [--complexity-review <TWEAK|LIGHT|STANDARD|UNKNOWN>]
        [--delivery-mode <NORMAL|CLOSE_LOOP>]
  产物: helloagents/plan/YYYYMMDDHHMM_<feature>/{why.md,how.md,task.md}
  说明: 会在 why.md 标题下写入元信息：@pkg_type/@complexity_initial/@complexity_review/@delivery_mode/@final_confirm

validate_package.py:
  用法: python -X utf8 "{SCRIPT_DIR}/validate_package.py" [--path <项目根目录>] [--require-finalized] [<package-name>]
  产物: JSON（单包或全量校验结果，包含 final_gate.score/passed）

update_package_metadata.py:
  用法: python -X utf8 "{SCRIPT_DIR}/update_package_metadata.py" <package-name|package-path> [--path <项目根目录>]
        [--pkg-type <implementation|overview>] [--complexity-initial <...>] [--complexity-review <...>] [--delivery-mode <...>]
        [--final-confirm <YES|NO>] [--apply-to <why|how|task|all>] [--dry-run]
  产物: 更新 why/how/task 中的元信息行（默认仅 why.md）

list_packages.py:
  用法: python -X utf8 "{SCRIPT_DIR}/list_packages.py" [--path <项目根目录>] [--history] [--format <table|json>]

migrate_package.py:
  用法: python -X utf8 "{SCRIPT_DIR}/migrate_package.py" <package-name> [--path <项目根目录>] [--status <completed|skipped>] [--all]
  产物: plan/ → history/YYYY-MM/ + 更新 history/index.md

project_stats.py:
  用法: python -X utf8 "{SCRIPT_DIR}/project_stats.py" [--path <项目根目录>]
  产物: JSON（规模、技术栈、依赖、目录深度、阈值判定）

upgradewiki.py:
  用法: python -X utf8 "{SCRIPT_DIR}/upgradewiki.py" --scan|--init|--backup|--write <json-file> [--path <项目根目录>]
  说明: 仅做文件系统操作；内容分析由 AI 在 kb 阶段完成
```

---

## 3. 脚本存在性检查与降级

调用任何脚本前，必须验证脚本文件存在：
- 存在：正常执行
- 不存在：切换到无脚本模式（`SCRIPTS_ENABLED=false`），并按 `references/rules/noscript.md` 的手动流程执行（创建目录/写入文件/移动目录/更新索引等）；输出中标注“脚本不可用，已切换无脚本模式”

---

## 4. ExecutionReport（脚本执行报告机制）

部分脚本会输出 JSON 格式的执行报告，用于 AI 在脚本失败或部分完成时继续接手。

### 4.1 报告结构

```json
{
  "script": "create_package",
  "success": true,
  "completed": [
    { "step": "创建 plan/ 目录", "result": "...", "verify": "..." }
  ],
  "failed_at": "写入 why.md",
  "error_message": "权限不足...",
  "pending": ["创建 why.md", "创建 how.md"],
  "context": {
    "feature": "user-login",
    "pkg_type": "implementation",
    "package_path": "..."
  }
}
```

### 4.2 AI 降级接手流程（必须执行质量检查）

1. 解析脚本输出的 JSON
2. `success=true`：继续后续阶段流程
3. `success=false`：
   - 逐条核验 `completed`（目录/文件确实存在、内容不为空）
   - 若发现 completed 不可信/不完整：先修复
   - 按 `pending` 列表补齐剩余动作

> 注意：降级接手时仍需遵守输出 SSOT（`templates/output-format.md`）与“强确认门禁”。

---

## 5. 常见错误与恢复

```yaml
Python 不可用:
  - 尝试 python3
  - 仍失败 → 切换到无脚本模式（SCRIPTS_ENABLED=false），按 references/rules/noscript.md 执行

路径错误:
  - 目录不存在 → 创建后重试
  - 权限不足 → 停止并提示用户处理

模板缺失:
  - create/validate 依赖 templates/
  - 模板缺失 → 先提示并中止脚本路径，改走 AI 直接生成文件内容
```
