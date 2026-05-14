# `~commit`（HelloAgents_v5）

> 目的：把“本次变更”用可检索、可追溯的方式提交到 Git。
> 默认只做**本地提交**；推送需要用户明确选择。

## 命令用法

- `~commit`
- `~commit <message>`：用户提供的 `<message>` 作为摘要（summary），其余仍按规范补齐（type/scope/body）。

## 触发

- 用户显式输入：`~commit` / `~commit <message>`，或明确表达“提交/commit”。
- 禁止：用户未表达提交意图时自动提交。

## 约束（必读）

1. **必须确认**：展示“变更摘要 + 提交信息预览 + 选项”，得到用户确认后再执行。
2. **最小提交**：只提交与本次任务相关的代码 + `helloagents/` 工作区产物（方案包/知识库/记忆体），避免把无关文件误提交。
3. **默认不 push**：除非用户明确选择“提交并推送”。

## 1) 环境检测（命令）

```bash
git rev-parse --git-dir
git status --porcelain
git branch --show-current
git remote -v
```

异常处理：
- 非 Git 仓库：提示用户初始化或切换目录，流程结束。
- 无变更：提示无需提交，流程结束。

## 1.1) 可选：同步远程信息（不改工作区）

> 仅用于判断是否落后 upstream；不会修改工作区文件。若仅本地提交且不推送，可跳过。

```bash
git fetch --all --prune
git status -sb
```

若需要“基于最新远程再提交”：建议先完成本地 commit，再在推送前执行 `git pull --rebase`（见 6) 推送），比在未提交/工作区不干净时直接 pull 更安全。

## 2) 变更摘要（命令）

```bash
git diff --stat
git diff
```

建议输出摘要：
- 变更文件数、主要目录/模块
- 是否包含 `helloagents/wiki/memories/` 与 `helloagents/CHANGELOG.md`（若启用闭环交付）

## 3) 提交信息规范（Conventional Commits）

**推荐格式：**
`<type>(<scope>): <summary>`

常见 type：`feat | fix | docs | refactor | perf | test | build | ci | chore | revert`

建议约束：
- `summary`：动词开头，≤50 字符，不加句号
- `body`（可选）：说明动机/影响/风险，每行≤72 字符

scope 建议使用：模块/子系统/目录名，例如 `erp`、`auth`、`wiki`、`admin-web`。

若本次生成了记忆体 id（如 `HA20260210-153012`），建议带上，便于追溯：
- `feat(erp): 补齐 ERP 菜单路由 (HA20260210-153012)`

## 4) 交互确认（必须）

展示以下信息并等待用户选择：
- 当前分支、是否存在远程（`git remote -v`）
- 变更摘要（`git diff --stat`）
- 提交信息预览

选项建议：
- [1] 仅本地提交（推荐）
- [2] 提交并推送（仅当存在远程时展示）
- [3] 修改提交信息
- [4] 取消

用户选择“修改提交信息”时：更新提交信息 → 重新展示确认（循环直到提交或取消）。

## 5) 执行提交（仅在确认后）

```bash
git add -A
git commit -m "<提交信息>"
```

## 6) 推送（仅在用户选择后）

> 原则：先确保本地基于最新远程，再推送；遇到冲突必须停下来让用户处理。

```bash
git fetch --all --prune
```

如检测到远程领先（或推送失败提示需要先更新），优先：
```bash
git pull --rebase
```

- 若出现冲突：输出冲突文件清单与最小处理建议，停止自动推送。
- 无冲突：
```bash
git push origin <branch>
```

## 7) 完成输出（建议）

至少包含：
- 提交信息
- commit hash
- 变更文件数（或 `git diff --stat` 摘要）
- 下一步（例如：运行测试 / 继续开发 / 执行 `~ship`）
