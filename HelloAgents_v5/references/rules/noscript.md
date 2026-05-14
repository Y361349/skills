# 无脚本模式（SCRIPTS_ENABLED=false）

本文件是 **HelloAgents_v5** 的“无脚本环境”兜底规则：当用户要求不运行脚本、Python 不可用、或 `scripts/` 缺失时，使用本规则以**纯文件操作**完成同等工作流，并保持输出的一致性与可预测性。

---

## 1. 何时启用

满足任一条件即启用：
- 用户明确要求“无脚本/不允许运行脚本”
- Python 不可用或运行失败（含权限/策略限制）
- 目标脚本文件不存在

启用后：
- 设置 `SCRIPTS_ENABLED=false`
- 禁止再尝试运行任何 `HelloAgents_v5/scripts/*.py`
- 所有“脚本动作”改为本文件的手动流程

---

## 2. 路径基准

与 `references/rules/tools.md` 一致：

```yaml
SKILL_ROOT: HelloAgents_v5/
TEMPLATE_DIR: {SKILL_ROOT}/templates/
WORKSPACE_DIR: <项目根目录>/helloagents/
```

---

## 3. 手动动作对照表

| 原脚本 | 手动替代 | 主要产物 |
|---|---|---|
| `scripts/create_package.py` | 见“手动创建方案包” | `helloagents/plan/<package>/{why,how,task}.md` |
| `scripts/validate_package.py` | 见“手动校验方案包” | 结构化校验结论（写入输出摘要） |
| `scripts/list_packages.py` | 见“手动枚举方案包” | 方案包列表（plan/history） |
| `scripts/migrate_package.py` | 见“手动迁移方案包” | `helloagents/history/...` + 更新 `history/index.md` |
| `scripts/project_stats.py` | 见“手动规模判定” | 大/中/小规模结论（保守策略） |
| `scripts/upgradewiki.py` | 见“手动知识库 init/upgrade/validate” | `helloagents/` 知识库结构与文件 |

---

## 4. 手动创建方案包（替代 `create_package.py`）

**输入：**
- `feature`：功能名称（可含中文/空格/符号）
- `pkg_type`：`implementation|overview`（默认 `implementation`）

**步骤：**
1. 确保目录存在：`{WORKSPACE_DIR}/plan/`
2. 生成 `package_name`（与脚本一致）：
   - `timestamp = 当前时间 YYYYMMDDHHMM`
   - `slug = feature.trim().toLowerCase()`，将“非字母/数字/中文”的连续字符替换为 `-`，并去掉首尾 `-`
   - `base = {timestamp}_{slug}`
   - 若 `{WORKSPACE_DIR}/plan/{base}` 已存在，则依次尝试 `{base}_v2/_v3...`，直到找到不存在者
3. 创建目录：`{WORKSPACE_DIR}/plan/{package_name}/`
4. 生成 `why.md`：
   - 读取模板：`{TEMPLATE_DIR}/plan-why-template.md`
   - 替换：`[功能名称]` → `feature`
   - 在首个 `#` 标题后插入（与脚本一致，**implementation 必填**）：
     - `> **@pkg_type:** {pkg_type}`
     - `> **@complexity_initial:** {complexity_initial}`（**必须**写成 `STANDARD（...）` 这种“枚举+中文说明”形式；不允许仅写 `STANDARD`）
     - `> **@complexity_review:** {complexity_review}`（同上；若与初判一致可写同值）
     - `> **@delivery_mode:** {delivery_mode}`（**必须**写成 `NORMAL（...）` 或 `CLOSE_LOOP（...）` 这种“枚举+中文说明”形式）
     - `> **@final_confirm:** NO（未收口定稿/禁止执行）`（最终执行前由主代理收口定稿后更新为 `YES（已收口定稿，仅按此口径执行）`）
5. 生成 `how.md`：
   - 读取模板：`{TEMPLATE_DIR}/plan-how-template.md`
   - 替换：`[功能名称]` → `feature`
   - 在首个 `#` 标题后插入：`> **@pkg_type:** {pkg_type}`
6. 生成 `task.md`：
   - `overview`：使用如下最小结构（与脚本一致），并在首个标题后插入 `> **@pkg_type:** overview`
     ```md
     # 任务清单: {feature}

     目录: `helloagents/plan/{package_name}/`

     > **@pkg_type:** overview
     > 无执行任务（概述文档，不进入开发实施阶段）

     ## 说明
     - 本方案包用于沉淀共识/范围/风险，不包含可执行任务。
     - 如需落地实施，请创建 `implementation` 类型方案包。
     ```
   - `implementation`：
     - 读取模板：`{TEMPLATE_DIR}/plan-task-template.md`
     - 替换：`[功能名称]` → `feature`
     - 替换：`YYYYMMDDHHMM_<feature>` → `{package_name}`
     - 在首个 `#` 标题后插入：`> **@pkg_type:** implementation`
7. 验证（必须做）：
   - `why.md/how.md/task.md` 均存在且非空（UTF-8）
   - `implementation` 类型：`task.md` 至少包含 1 条 checkbox 任务（例如 `- [ ] ...`）

---

## 5. 手动校验方案包（替代 `validate_package.py`）

对 `{WORKSPACE_DIR}/plan/{package_name}/` 执行：
1. 必需文件存在性：`why.md/how.md/task.md`（缺任一 → 不可执行）
2. `pkg_type` 检测（任一文件包含）：`> **@pkg_type:** overview` / `implementation`（默认 `implementation`）
3. **元信息完整性（implementation 强制）**：`why.md` 必须包含（且值需包含中文说明，形如 `枚举（中文说明）`）：
   - `> **@complexity_initial:** ...`
   - `> **@complexity_review:** ...`
   - `> **@delivery_mode:** ...`（`NORMAL|CLOSE_LOOP`）
4. 解析 `task.md` 任务项（与脚本一致的匹配口径）：
   - 匹配行：`^[-*]\s*\[([ √X?-])\]\s+`
   - 统计：总数、各状态数（pending/completed/failed/skipped/uncertain）
5. 可执行性判定（与脚本一致的核心规则）：
   - `overview`：`executable=false`
   - `implementation`：
     - 任务总数为 0 → `executable=false`
     - 若 pending=0 且 completed=total → 建议迁移至 `history/`（`executable=false`）
     - 若 failed>0 → 输出警告并进入用户决策

6. **最终收口定稿门禁（强制，执行评分=10）**：
   - `why.md` 必须包含：`> **@final_confirm:** YES（已收口定稿，仅按此口径执行）`
   - `why.md/how.md/task.md` 中不得出现未收口标记（举例）：
     - 任何 `（...可选...）` / `（...多选...）`
     - `可选项` / `可选附加项` / `多选` / `二选一`
     - `<A|B|C>`（多选占位符）
     - `path/to/` / `联网：<` / `时保留；none 时删除` 等占位符或条件说明
   - `task.md` 不得存在 `[?]` 待确认任务；三文件不得残留 `[?]` 标记
   - 未通过时：禁止开始任何代码写入，先回到 `design` 收口定稿并让用户给出唯一最终确认

---

## 6. 手动枚举方案包（替代 `list_packages.py`）

1. 枚举 `plan/`：`{WORKSPACE_DIR}/plan/*`
2. 过滤命名：仅保留形如 `^\d{12}_.+` 的目录（与脚本命名一致）
3. 排序：按目录名（时间戳）倒序
4. 每个包输出最小信息（建议）：
   - 名称
   - 是否完整（why/how/task 是否齐全）
   - `task.md` checkbox 任务数量

---

## 7. 手动迁移方案包（替代 `migrate_package.py`）

**输入：**
- `package_name`
- `status`：`completed|skipped`

**步骤：**
1. 更新 `task.md` 状态标记（置于标题后；存在则替换）：
   - `> **@status:** {status} | YYYY-MM-DD HH:mm`
2. 更新 checkbox（尽量保守，保持可追溯）：
   - `status=skipped`：将所有任务标记为 `[-]`
   - `status=completed`：将仍为 `[ ]` 的任务标记为 `[√]`（已是 `[X]/[-]/[?]/[√]` 的保持不动）
3. 计算归档目录 `YYYY-MM`：取 `package_name` 的前 6 位（如 `202512` → `2025-12`）
4. 确保目录存在：`{WORKSPACE_DIR}/history/YYYY-MM/`
5. 移动目录：
   - 源：`{WORKSPACE_DIR}/plan/{package_name}/`
   - 目标：`{WORKSPACE_DIR}/history/YYYY-MM/{package_name}/`
6. 确保 `history/index.md` 存在：
   - 不存在则从模板创建：`{TEMPLATE_DIR}/history-index-template.md`
7. 更新 `history/index.md`（与脚本一致的最小约定）：
   - 索引表新增一行：
     `| {timestamp} | {feature} | - | ✅已完成/[-]未执行 | {YYYY-MM}/{package_name}/ |`
   - 在 `### YYYY-MM` 下追加一条：
     `- [{package_name}]({YYYY-MM}/{package_name}/) - ✅已完成/[-]未执行`
8. 验证（必须做）：
   - `plan/{package_name}` 不存在
   - `history/YYYY-MM/{package_name}` 存在
   - `history/index.md` 包含新记录

---

## 8. 手动规模判定（替代 `project_stats.py`）

在无法可靠统计时，**保守按“大型项目”处理**，直接启用 `references/rules/scaling.md` 的分批策略（避免过度读取导致不确定性上升）。

若可统计（任选其一即可）：
- 使用 `code-index`/文件枚举估算“源代码文件数/代码行数/模块数”
- 达到阈值（文件数>500 或 行数>50000 或 模块数>30）即视为大型项目

---

## 9. 手动知识库 init/upgrade/validate（替代 `upgradewiki.py`）

### 9.1 `~init`（最小可用结构）

在 `{WORKSPACE_DIR}/` 创建（不存在则创建，存在则不覆盖，优先补齐缺失项）：
- `CHANGELOG.md`（参考 `templates/changelog-template.md`）
- `project.md`（参考 `templates/project-template.md`）
- `wiki/overview.md`（参考 `templates/wiki-overview-template.md`）
- `wiki/arch.md`（参考 `templates/wiki-arch-template.md`）
- `wiki/api.md`（参考 `templates/wiki-api-template.md`）
- `wiki/data.md`（参考 `templates/wiki-data-template.md`）
- `wiki/modules/` 目录（按需创建 `<module>.md`，参考 `templates/wiki-module-template.md`）
- `history/index.md`（参考 `templates/history-index-template.md`）

### 9.2 `~upgrade`

原则：只做“结构与模板级”升级，避免无关重写。
- 先做备份（目录复制或 Git commit）
- 对比模板：补齐缺失文件/缺失章节（不强制重写已有内容）

### 9.3 `~validate`（最小校验）

- 结构完整性：核心文件是否存在（见 9.1 清单）
- 链接一致性：`wiki/overview.md` 的快速链接、`history/index.md` 的归档链接是否可达
- 方案包可执行性：按“手动校验方案包”检查 plan/ 下待执行包
